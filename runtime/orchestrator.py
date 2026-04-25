"""Fund orchestrator.

Wires the Claude Agent SDK together with:
  - per-agent system prompts (agents/*.md)
  - model assignments (config/models.yaml)
  - MCP tool servers (tools/*.py)
  - the PreToolUse risk hook (hooks/risk_gate.py)
  - audit and cost hooks
  - the market-hours scheduler

The orchestration discipline in this module is what guarantees:

    NO ORDER REACHES THE BROKER WITHOUT RISK MANAGER APPROVAL.

It does so at three layers:
  1. Only the `execution_trader` agent is wired with the topstep write tools.
  2. The execution_trader is only invoked with order proposals that carry a
     passing risk_vote from the Risk Manager (and Options Risk, if options).
  3. The PreToolUse hook (hooks/risk_gate.py) is the final guard at the
     tool-call layer, regardless of which agent made the call.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from hooks import audit_logger, cost_tracker, risk_gate
from state.db import get_db
from tools import equity_broker, fundamentals_mcp, market_data, news, state_store, topstep, vault

from .events import Event, EventKind
from .scheduler import Scheduler

AGENTS_DIR = Path("agents")
CONFIG_DIR = Path("config")
VAULT_DIR = Path("vault")
TEAM_NOTE = VAULT_DIR / "_meta" / "team.md"
TRADING_PROCESS_NOTE = VAULT_DIR / "_meta" / "trading_process.md"
IDLE_PROTOCOL_NOTE = VAULT_DIR / "_meta" / "idle_protocol.md"
PLATFORM_IMPORTS_DIR = VAULT_DIR / "platform_agents" / "imported"
FUND_YAML = CONFIG_DIR / "fund.yaml"


def _idle_work_enabled() -> bool:
    """Read config/fund.yaml to see if autonomous idle work is currently on."""
    if not FUND_YAML.exists():
        return False
    try:
        cfg = yaml.safe_load(FUND_YAML.read_text()) or {}
        return bool(cfg.get("idle_work_enabled", False))
    except Exception:
        return False


def _agent_key(name: str) -> str:
    """Normalize an agent name to the snake_case key used in models.yaml.

    Examples:
        'Energies Analyst'      -> 'analyst_energies'
        'Risk Manager'          -> 'risk_manager'
        'Index/Macro Analyst'   -> 'analyst_index_macro'
    """
    n = name.strip().lower().replace("/", "_").replace("-", "_").replace(" ", "_")
    if n.endswith("_analyst"):
        n = "analyst_" + n[: -len("_analyst")]
    return n


def _team_preamble(agent_role_slug: str | None = None) -> str:
    """Shared preamble prepended to every agent's system prompt.

    Structure (in order):
      1. team.md — who we are and how we collaborate
      2. trading_process.md — the formal front-office workflow
      3. Optionally: idle_protocol.md (only when idle_work_enabled is true)
      4. Optionally: platform_agents/imported/{role_slug}.md (if user has
         uploaded a Console agent's instructions for this role)
    """
    if not TEAM_NOTE.exists():
        return ""
    parts = [
        "# Team culture (shared preamble)\n\n",
        TEAM_NOTE.read_text(encoding="utf-8"),
    ]
    if TRADING_PROCESS_NOTE.exists():
        parts.append(
            "\n\n---\n\n# Trading process (the firm's workflow)\n\n"
            + TRADING_PROCESS_NOTE.read_text(encoding="utf-8")
        )
    if _idle_work_enabled() and IDLE_PROTOCOL_NOTE.exists():
        parts.append(
            "\n\n---\n\n# Idle-work protocol (ACTIVE)\n\n"
            + IDLE_PROTOCOL_NOTE.read_text(encoding="utf-8")
        )
    if agent_role_slug:
        import_file = PLATFORM_IMPORTS_DIR / f"{agent_role_slug}.md"
        if import_file.exists():
            parts.append(
                f"\n\n---\n\n# Imported Platform Agent instructions ({agent_role_slug})\n\n"
                "The user maintains a matching agent on the Claude Platform. "
                "Its instructions are reproduced below. Treat as additional context "
                "unless the imported file's frontmatter says `authoritative: true`.\n\n"
                + import_file.read_text(encoding="utf-8")
            )
    parts.append("\n\n---\n\n# Your role\n\n")
    return "".join(parts)


# --------------------------------------------------------------
# Agent identity + wiring
# --------------------------------------------------------------
@dataclass
class AgentSpec:
    name: str
    prompt_path: Path
    model_tier: str                    # cheap | balanced | deep
    can_place_orders: bool
    allowed_tools: list[str]           # MCP tool names
    role: str


READ_ONLY_TOOLS = [
    "mcp__state_store__state_account_snapshot",
    "mcp__state_store__state_positions",
    "mcp__state_store__state_recent_decisions",
    "mcp__state_store__state_risk_events_today",
    "mcp__state_store__state_record_decision",
    "mcp__market_data__get_quote",
    "mcp__market_data__get_bars",
    "mcp__market_data__get_option_chain",
    "mcp__market_data__get_economic_calendar",
    "mcp__news__search_news",
    "mcp__news__web_search",
    "mcp__news__fetch_url",
    "mcp__fundamentals__fred_series",
    "mcp__fundamentals__eia_crude_stocks",
    "mcp__fundamentals__eia_distillate_stocks",
    "mcp__fundamentals__eia_natgas_storage",
    "mcp__fundamentals__cftc_commitments",
    "mcp__fundamentals__usda_crop_progress",
    "mcp__fundamentals__usda_cattle_on_feed",
    "mcp__topstep__topstep_get_account",
    "mcp__topstep__topstep_get_positions",
    "mcp__topstep__topstep_get_working_orders",
    "mcp__vault__vault_read",
    "mcp__vault__vault_list",
    "mcp__vault__vault_append_journal",
    "mcp__vault__vault_upsert_thesis",
    "mcp__vault__vault_append_review",
]

EXECUTION_ONLY_TOOLS = [
    "mcp__topstep__topstep_place_order",
    "mcp__topstep__topstep_cancel_order",
    "mcp__topstep__topstep_flatten_all",
]


def _load_agent_specs() -> dict[str, AgentSpec]:
    """Load every agent prompt and its frontmatter into a spec."""
    import re
    specs: dict[str, AgentSpec] = {}
    search_paths = (
        list(AGENTS_DIR.glob("*.md"))
        + list(AGENTS_DIR.glob("analysts/*.md"))
        + list(AGENTS_DIR.glob("equities/*.md"))
        + list(AGENTS_DIR.glob("equities/analysts/*.md"))
    )
    for path in search_paths:
        if path.name == "README.md":
            continue
        text = path.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
        meta = yaml.safe_load(m.group(1)) if m else {}
        name = meta.get("name", path.stem)
        can_place = bool(meta.get("can_place_orders", False))
        tier = meta.get("model_tier", "balanced")
        role = meta.get("role", "unknown")
        allowed = list(READ_ONLY_TOOLS)
        if can_place:
            allowed += EXECUTION_ONLY_TOOLS
        specs[name] = AgentSpec(
            name=name,
            prompt_path=path,
            model_tier=tier,
            can_place_orders=can_place,
            allowed_tools=allowed,
            role=role,
        )
    return specs


# --------------------------------------------------------------
# Orchestrator
# --------------------------------------------------------------
class Orchestrator:
    def __init__(self) -> None:
        self.specs = _load_agent_specs()
        self.models = yaml.safe_load((CONFIG_DIR / "models.yaml").read_text())
        self.mcp_servers = {
            "topstep":       topstep.server,
            "equity_broker": equity_broker.server,   # IDLE — no tools exposed yet
            "market_data":   market_data.server,
            "news":          news.server,
            "fundamentals":  fundamentals_mcp.server,
            "state_store":   state_store.server,
            "vault":         vault.server,
        }
        self.scheduler = Scheduler()
        self.db = get_db()

    # ------------------------------------------------------------
    # Model resolution
    # ------------------------------------------------------------
    def _resolve_model(self, tier: str) -> str:
        return self.models["defaults"][tier]

    def _resolve_tier_for_agent(self, agent_name: str, fallback_tier: str) -> str:
        """Per-agent override from models.yaml `agents:` wins over frontmatter."""
        agents_map = (self.models.get("agents") or {})
        key = _agent_key(agent_name)
        if key in agents_map:
            return agents_map[key]
        return fallback_tier

    # ------------------------------------------------------------
    # Agent invocation (stub — real SDK wiring in next step)
    # ------------------------------------------------------------
    async def wake_agent(
        self,
        agent_name: str,
        task: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Wake a single agent with a focused task.

        This is where the Claude Agent SDK client gets constructed. The
        implementation below is the intended shape — once claude-agent-sdk is
        installed, uncomment the body. Until then, it records the intent and
        returns a stub response for wiring tests.
        """
        spec = self.specs[agent_name]
        # Per-agent tier override in models.yaml wins over frontmatter default
        effective_tier = self._resolve_tier_for_agent(agent_name, spec.model_tier)
        model = self._resolve_model(effective_tier)
        # Shared preamble: team culture + trading process + optional idle
        # protocol + optional platform-agent import matching this role
        role_slug = spec.prompt_path.stem
        system_prompt = _team_preamble(role_slug) + spec.prompt_path.read_text(encoding="utf-8")

        # --- Real Claude Agent SDK integration ---
        try:
            from claude_agent_sdk import (
                ClaudeAgentOptions,
                ClaudeSDKClient,
                HookMatcher,
            )
        except ImportError:
            self.db.record_decision(
                agent=agent_name, kind="wake_stub",
                summary=f"Woke {agent_name} (SDK not installed)",
                rationale=task[:500], model=model,
            )
            return {"stub": True, "agent": agent_name, "model": model}

        opts = ClaudeAgentOptions(
            model=model,
            system_prompt=system_prompt,
            mcp_servers=self.mcp_servers,
            allowed_tools=spec.allowed_tools,
            hooks={
                "PreToolUse":  [HookMatcher(hooks=[risk_gate])],
                "PostToolUse": [HookMatcher(hooks=[audit_logger])],
                "Stop":        [HookMatcher(hooks=[cost_tracker])],
            },
        )

        messages: list[Any] = []
        usage: dict[str, Any] = {}
        final_text = ""
        try:
            async with ClaudeSDKClient(options=opts) as client:
                await client.query(task)
                async for msg in client.receive_response():
                    messages.append(msg)
                    # Capture token usage + final text when available
                    if hasattr(msg, "usage") and msg.usage:
                        usage = dict(msg.usage) if not isinstance(msg.usage, dict) else msg.usage
                    if hasattr(msg, "content") and msg.content:
                        for block in msg.content:
                            if hasattr(block, "text"):
                                final_text += block.text
        except Exception as e:
            self.db.record_decision(
                agent=agent_name, kind="wake_error",
                summary=f"{agent_name} wake failed",
                rationale=f"{type(e).__name__}: {e!s}",
                model=model,
            )
            return {"error": str(e), "agent": agent_name, "model": model}

        self.db.record_decision(
            agent=agent_name, kind="wake",
            summary=f"{agent_name} wake complete",
            rationale=(final_text[:2000] if final_text else task[:500]),
            model=model,
            tokens_in=int(usage.get("input_tokens", 0)) if usage else None,
            tokens_out=int(usage.get("output_tokens", 0)) if usage else None,
        )
        # Inline cost tracking — record to costs table for daily $ accountability
        self._record_cost(agent_name, model, usage)
        return {
            "agent": agent_name,
            "model": model,
            "final_text": final_text,
            "usage": usage,
            "messages_count": len(messages),
        }

    def _record_cost(self, agent_name: str, model: str, usage: dict) -> None:
        """Update state.costs with this wake's token spend in USD."""
        if not usage:
            return
        from datetime import datetime, timezone
        # Pricing (per million tokens, illustrative — update from anthropic.com)
        prices = {
            "claude-haiku-4-5-20251001": {"in": 1.0,  "out": 5.0,   "cache_in": 0.10},
            "claude-sonnet-4-6":         {"in": 3.0,  "out": 15.0,  "cache_in": 0.30},
            "claude-opus-4-7":           {"in": 15.0, "out": 75.0,  "cache_in": 1.50},
        }
        p = prices.get(model, {"in": 3.0, "out": 15.0, "cache_in": 0.30})
        t_in_uncached = int(usage.get("input_tokens", 0))
        t_in_cached   = int(usage.get("cache_read_input_tokens", 0))
        t_in_create   = int(usage.get("cache_creation_input_tokens", 0))
        t_out         = int(usage.get("output_tokens", 0))
        if (t_in_uncached + t_in_cached + t_in_create + t_out) == 0:
            return
        usd = (
            t_in_uncached * p["in"]       / 1_000_000
            + t_in_cached  * p["cache_in"] / 1_000_000
            + t_in_create  * p["in"] * 1.25 / 1_000_000   # cache write costs more
            + t_out        * p["out"]      / 1_000_000
        )
        day = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        try:
            with self.db.tx() as c:
                c.execute(
                    """INSERT INTO costs
                          (day, agent, model, tokens_in, tokens_out, cached_in, usd_est)
                       VALUES (?,?,?,?,?,?,?)
                       ON CONFLICT(day, agent, model) DO UPDATE SET
                          tokens_in  = tokens_in  + excluded.tokens_in,
                          tokens_out = tokens_out + excluded.tokens_out,
                          cached_in  = cached_in  + excluded.cached_in,
                          usd_est    = usd_est    + excluded.usd_est""",
                    (day, agent_name, model,
                     t_in_uncached + t_in_create, t_out, t_in_cached, usd),
                )
        except Exception:
            pass  # never fail a wake on cost-tracking error

    # ------------------------------------------------------------
    # Thesis-to-proposal path (upstream of submit_proposal)
    # ------------------------------------------------------------
    async def submit_thesis(
        self,
        thesis: dict[str, Any],
    ) -> dict[str, Any]:
        """Analyst publishes thesis → Red Team challenges → PM receives both.

        Called when any analyst produces a thesis with conviction `med` or
        `high`. Low-conviction theses skip the Red Team to save tokens.

        Returns the challenge report; the PM consumes both thesis and
        challenge before deciding whether to submit a proposal.
        """
        conviction = (thesis.get("conviction") or "low").lower()
        if conviction not in ("med", "high"):
            return {"status": "skipped_red_team", "reason": "low conviction"}

        challenge = await self.wake_agent(
            agent_name="Red Team",
            task=(
                "Challenge the following thesis. Produce a challenge report with "
                "three counter-narratives, a null-hypothesis stress test, historical "
                "analog failures, a base-rate sanity check, and a verdict "
                "(strong | gaps | weak). Under 500 words. "
                f"Thesis: {thesis}"
            ),
        )
        return {"status": "challenged", "challenge": challenge}

    # ------------------------------------------------------------
    # Trade workflow — enforces the routing invariant
    # ------------------------------------------------------------
    async def submit_proposal(self, proposal: dict[str, Any]) -> dict[str, Any]:
        """PM → Risk Manager (→ Options Risk if options) → Execution Trader.

        This method is the ONLY code path that can cause a broker order to
        be placed. The sequence here is the firm's non-negotiable workflow.
        """
        # 1. Risk Manager reviews. Deep-tier agent; hard veto.
        risk_result = await self.wake_agent(
            agent_name="Risk Manager",
            task=f"Review the following order proposal against ALL rules. "
                 f"Produce a verdict (allow | allow_with_modifications | block). "
                 f"Proposal: {proposal}",
        )
        verdict = _extract_verdict(risk_result)
        if verdict != "allow" and verdict != "allow_with_modifications":
            return {"status": "blocked_by_risk", "result": risk_result}

        # 2. If options, Options Risk also reviews.
        if proposal.get("asset_type") == "option" or proposal.get("structure_kind"):
            opt_result = await self.wake_agent(
                agent_name="Options Risk",
                task=f"Review this options proposal for structure, Greeks, IV, DTE. "
                     f"Proposal: {proposal}",
            )
            opt_verdict = _extract_verdict(opt_result)
            if opt_verdict != "allow":
                return {"status": "blocked_by_options_risk", "result": opt_result}

        # 3. Execution Trader places the order. PreToolUse hook is the final guard.
        exec_result = await self.wake_agent(
            agent_name="Execution Trader",
            task=f"Execute the following approved proposal. Proposal: {proposal}",
        )
        return {"status": "executed", "result": exec_result}

    # ------------------------------------------------------------
    # Book Monitor — wakes on BOOK_MONITOR_TICK when positions exist
    # ------------------------------------------------------------
    async def book_monitor_sweep(self) -> dict[str, Any]:
        """Wake the Book Monitor only if we have open positions. Skip otherwise."""
        positions = self.db.current_positions()
        if not positions:
            return {"status": "skipped_flat_book"}
        return await self.wake_agent(
            agent_name="Book Monitor",
            task=(
                "Sweep the live book. For each open position compute distance "
                "to stop/target, adverse/favorable ATR moves, time in trade, and "
                "correlated-sector drift. If no alerts fire, respond with exactly "
                "'NO_CHANGE'. If alerts fire, write them to today's journal."
            ),
        )

    # ------------------------------------------------------------
    # Event loop
    # ------------------------------------------------------------
    async def run(self) -> None:
        async for evt in self.scheduler.run():
            await self.handle_event(evt)

    async def handle_event(self, evt: Event) -> None:
        match evt.kind:
            case EventKind.BOOK_MONITOR_TICK:
                await self.book_monitor_sweep()
            case EventKind.SESSION_OPEN:
                await self.session_open_workflow()
            case EventKind.SESSION_CLOSE:
                await self.session_close_workflow()
            case EventKind.TICK:
                await self.tick_workflow()
            case EventKind.IDLE_TICK:
                await self.idle_tick_workflow()
            case EventKind.WEEKLY_REVIEW:
                await self.weekly_review_workflow()
            case _:
                pass

    async def idle_tick_workflow(self) -> dict[str, Any]:
        """Off-hours tick: wake Fund Engineer to do brain-building work.

        Gated by config/fund.yaml:idle_work_enabled. Skipped if disabled.
        Hard-capped via idle_work_guardrails.max_wakes_per_day.
        """
        if not _idle_work_enabled():
            return {"status": "idle_work_disabled"}
        try:
            cfg = yaml.safe_load(FUND_YAML.read_text()) or {}
            cap = int((cfg.get("idle_work_guardrails") or {}).get("max_wakes_per_day", 20))
        except Exception:
            cap = 20
        from datetime import datetime, timezone
        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        n_today = self.db.connect().execute(
            "SELECT COUNT(*) FROM decisions WHERE agent='Fund Engineer' "
            "AND kind='engineering_work' AND ts LIKE ?",
            (f"{today}%",),
        ).fetchone()[0]
        if n_today >= cap:
            return {"status": "daily_cap_reached", "wakes_today": n_today}
        return await self.wake_agent(
            "Fund Engineer",
            (
                "IDLE WAKE. Markets closed. Pick ONE item from "
                "vault/_meta/idle_backlog.md assigned to Fund Engineer "
                "or unclaimed weekend work. Do the work for that one item, "
                "commit your output to git, sign off in today's journal. "
                "Stay strictly within your write scope (vault/** only — no "
                "code, no agent prompts, no configs)."
            ),
        )

    # ------------------------------------------------------------
    # Workflow orchestration — wakes agents in the trading-firm chain
    # ------------------------------------------------------------
    async def session_open_workflow(self) -> dict[str, Any]:
        """CIO publishes daily brief + decides whether to wake an analyst."""
        cio_result = await self.wake_agent(
            "CIO",
            (
                "SESSION OPEN. Do this:\n"
                "1. topstep_get_account → confirm balance.\n"
                "2. vault_read regime/current.md.\n"
                "3. Scan economic calendar via market_data tools.\n"
                "4. vault_append_journal a daily brief (<300 words): regime read, "
                "themes, events to watch, analyst wake plan.\n"
                "5. state_record_decision kind=session_brief.\n\n"
                "End with EXACTLY one of:\n"
                "  WAKE: Energies Analyst | Metals Analyst | Grains Analyst | "
                "Softs Analyst | Livestock Analyst | Rates Analyst | "
                "FX Futures Analyst | Index/Macro Analyst\n"
                "  WAKE: none\n"
            ),
        )
        analyst = _parse_wake_line(cio_result.get("final_text", ""))
        if not analyst or analyst.lower() == "none":
            return {"status": "session_brief_only", "analyst_woken": None}
        return await self.run_analyst_chain(analyst)

    async def session_close_workflow(self) -> dict[str, Any]:
        """End-of-day: CIO wrap + Compliance summary."""
        await self.wake_agent("CIO", "SESSION CLOSE. Publish daily wrap to journal.")
        await self.wake_agent("Compliance", "End-of-day audit + compliance summary.")
        return {"status": "session_closed"}

    async def tick_workflow(self) -> dict[str, Any]:
        """Mid-session tick: CIO decides if any analyst needs to wake."""
        cio_result = await self.wake_agent(
            "CIO",
            (
                "MID-SESSION TICK. Brief check-in. "
                "Read recent decisions and current positions. "
                "If conditions warrant a fresh analyst wake (new headline, "
                "regime shift, price alert), name the analyst. Otherwise "
                "respond NONE. Be conservative — most ticks should be NONE.\n\n"
                "End with EXACTLY:\n"
                "  WAKE: <analyst name>\n"
                "  WAKE: none\n"
            ),
        )
        analyst = _parse_wake_line(cio_result.get("final_text", ""))
        if not analyst or analyst.lower() == "none":
            return {"status": "no_action"}
        return await self.run_analyst_chain(analyst)

    async def weekly_review_workflow(self) -> dict[str, Any]:
        """Sunday meta-review: scorecards + lessons."""
        await self.wake_agent(
            "CIO",
            (
                "WEEKLY REVIEW. Update vault/_meta/agent_scorecards.md with "
                "rolling-window stats per agent (read decisions table). "
                "Identify Watch / Bench tier candidates. Append the review "
                "to vault/reviews/weekly_<date>.md."
            ),
        )
        await self.wake_agent("Compliance", "Weekly audit + scorecard review.")
        return {"status": "weekly_review_done"}

    async def run_analyst_chain(self, analyst_name: str) -> dict[str, Any]:
        """Full chain: Analyst → (Red Team if med/high) → PM → Risk → Exec.

        Each step reads structured signals from the prior step's text output
        OR from the most recent decision row in the DB.
        """
        # 1. Wake the analyst — they research and produce a thesis (or NO_TRADE).
        a_result = await self.wake_agent(
            analyst_name,
            (
                "Research your sector. If you find a clean setup matching one "
                "of your strategy library entries, write a thesis to "
                "vault/theses/{symbol}.md and call state_record_decision with "
                "kind=thesis (include symbol, conviction, direction, stop, "
                "target, rationale). End with one of:\n"
                "  THESIS: <SYMBOL> conviction=<low|med|high>\n"
                "  NO_TRADE: <one-line reason>\n"
                "Conservative bias — most wakes should be NO_TRADE."
            ),
        )
        text = a_result.get("final_text", "")
        thesis_marker = _parse_marker(text, "THESIS:")
        if not thesis_marker:
            return {"status": "no_trade", "analyst": analyst_name}

        thesis = self._latest_thesis_for(analyst_name)
        if not thesis:
            return {"status": "thesis_not_recorded", "analyst": analyst_name}

        # 2. Red Team challenge if conviction warrants it
        conviction = (thesis.get("conviction") or "low").lower()
        challenge = None
        if conviction in ("med", "high"):
            challenge = await self.wake_agent(
                "Red Team",
                (
                    f"Challenge this thesis: {thesis}. Produce challenge report "
                    "(counter-narratives, null-hypothesis test, historical "
                    "analog failures, base-rate, verdict strong|gaps|weak)."
                ),
            )

        # 3. PM sizes a proposal
        pm_result = await self.wake_agent(
            "Portfolio Manager",
            (
                f"Thesis: {thesis}\n"
                f"Red Team challenge: {challenge.get('final_text', 'n/a') if challenge else 'skipped (low conviction)'}\n\n"
                "Decide pursue|pass. If pursue, produce an order proposal "
                "(symbol, side, qty, order_type, stop, target, rationale). "
                "Record via state_record_decision kind=order_proposal. "
                "End with PROPOSE or PASS."
            ),
        )
        if "PROPOSE" not in pm_result.get("final_text", "").upper():
            return {"status": "pm_passed", "analyst": analyst_name}

        proposal = self._latest_proposal()
        if not proposal:
            return {"status": "proposal_not_recorded"}

        # 4. Risk → (Options Risk if options) → Execution
        return await self.submit_proposal(proposal)

    # ------------------------------------------------------------
    # DB helpers — read latest decisions for chain handoffs
    # ------------------------------------------------------------
    def _latest_thesis_for(self, agent_name: str) -> dict[str, Any] | None:
        row = self.db.connect().execute(
            "SELECT * FROM decisions WHERE agent = ? AND kind = 'thesis' "
            "ORDER BY id DESC LIMIT 1",
            (agent_name,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        # Parse rationale for fields if structured (best-effort)
        return {
            "agent": d.get("agent"),
            "symbol": d.get("symbol"),
            "summary": d.get("summary"),
            "rationale": d.get("rationale"),
            "conviction": _extract_field(d.get("rationale", ""), "conviction") or "low",
        }

    def _latest_proposal(self) -> dict[str, Any] | None:
        row = self.db.connect().execute(
            "SELECT * FROM decisions WHERE kind = 'order_proposal' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        return {
            "symbol": d.get("symbol"),
            "summary": d.get("summary"),
            "rationale": d.get("rationale"),
        }


def _parse_wake_line(text: str) -> str | None:
    """Find a 'WAKE: <name>' line in the agent's output."""
    for line in text.splitlines():
        s = line.strip()
        if s.upper().startswith("WAKE:"):
            return s.split(":", 1)[1].strip()
    return None


def _parse_marker(text: str, marker: str) -> str | None:
    """Find any '<MARKER> ...' line in the agent's output."""
    for line in text.splitlines():
        s = line.strip()
        if s.upper().startswith(marker.upper()):
            return s.split(":", 1)[1].strip() if ":" in s else s
    return None


def _extract_field(text: str, field: str) -> str | None:
    """Best-effort extract `field=value` or `field: value` from rationale."""
    import re
    m = re.search(rf"{field}\s*[=:]\s*(\w+)", text, re.IGNORECASE)
    return m.group(1).lower() if m else None


def _extract_verdict(agent_result: dict[str, Any]) -> str:
    """Pull a verdict token from an agent's text response."""
    text = (agent_result.get("final_text") or "").lower()
    if "block" in text or "denied" in text or "rejected" in text:
        return "block"
    if "allow_with_modifications" in text or "modify" in text:
        return "allow_with_modifications"
    if "allow" in text or "approved" in text:
        return "allow"
    # Conservative default
    return "block"
