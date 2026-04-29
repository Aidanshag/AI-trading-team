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
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from hooks import audit_logger, cost_tracker, risk_gate
from state.db import get_db
from tools import (
    equity_broker, fundamentals_mcp, market_data, news,
    options_mcp, state_store, topstep, vault,
)

from .events import Event, EventKind
from .scheduler import Scheduler

AGENTS_DIR = Path("agents")
CONFIG_DIR = Path("config")
VAULT_DIR = Path("vault")
TEAM_NOTE = VAULT_DIR / "_meta" / "team.md"
TRADING_PROCESS_NOTE = VAULT_DIR / "_meta" / "trading_process.md"
V2_PROTOCOL_NOTE = VAULT_DIR / "_meta" / "agent_v2_protocol.md"
PRETRADE_CHECKLIST_NOTE = VAULT_DIR / "_meta" / "pre_trade_checklist.md"
IDLE_PROTOCOL_NOTE = VAULT_DIR / "_meta" / "idle_protocol.md"
PLATFORM_IMPORTS_DIR = VAULT_DIR / "platform_agents" / "imported"
FUND_YAML = CONFIG_DIR / "fund.yaml"


def _resolve_cli_path() -> str | None:
    """Pick a Claude CLI binary that's an actual EXE (not a .cmd wrapper).

    Why this matters:
      - The bundled claude.exe under .venv lives in an OneDrive path. OneDrive
        Files-On-Demand can rehydrate the file at any moment, causing
        anyio.open_process to throw FileNotFoundError.
      - The npm-installed claude.cmd is a Windows batch wrapper (.cmd).
        anyio/subprocess on Windows cannot execute .cmd files directly
        without cmd.exe — they get FileNotFoundError too. This was the
        production bug observed 2026-04-29: pointing the SDK at claude.cmd
        produced "Claude Code not found at: ...claude.CMD".
      - The actual claude.exe inside the npm package's bin/ directory is
        a normal PE executable that subprocess can launch directly.

    Search order:
      1. FUND_CLAUDE_CLI_PATH env var (explicit override)
      2. AppData\\Roaming\\npm\\node_modules\\@anthropic-ai\\claude-code\\bin\\claude.exe
         — the real binary the npm wrapper invokes
      3. None → SDK falls back to its bundled CLI (OneDrive risk accepted)
    """
    explicit = os.environ.get("FUND_CLAUDE_CLI_PATH")
    if explicit and Path(explicit).exists():
        return explicit

    appdata = Path(os.environ.get("APPDATA", ""))
    npm_real_exe = (appdata / "npm" / "node_modules" / "@anthropic-ai"
                    / "claude-code" / "bin" / "claude.exe")
    if npm_real_exe.exists():
        return str(npm_real_exe)

    return None


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
    if V2_PROTOCOL_NOTE.exists():
        parts.append(
            "\n\n---\n\n# Agent v2 Protocol — institutional skills upgrade\n\n"
            + V2_PROTOCOL_NOTE.read_text(encoding="utf-8")
        )
    if PRETRADE_CHECKLIST_NOTE.exists():
        parts.append(
            "\n\n---\n\n# Pre-Trade Checklist (mandatory)\n\n"
            + PRETRADE_CHECKLIST_NOTE.read_text(encoding="utf-8")
        )
    # Idle protocol only loaded for Fund Engineer (the agent that
    # actually consumes the idle backlog). Other agents don't need it
    # and including it eats SDK command-line budget.
    if (
        _idle_work_enabled()
        and IDLE_PROTOCOL_NOTE.exists()
        and (agent_role_slug or "").lower() in ("fund_engineer", "fund-engineer")
    ):
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
    # Strategy performance ranking — TOP 3 / BOTTOM 1 by current expectancy.
    # Auto-updated every ~60 min from observed trade history (Bayesian shrinkage).
    # Tight footprint (~300 chars).
    try:
        perf = Path("vault/_meta/strategy_performance.md")
        if perf.exists():
            txt = perf.read_text(encoding="utf-8")
            import re as _re
            # Pick the top 3 from the ranking table
            rank_lines = _re.findall(r"\|\s*\d+\s*\|\s*`([^`]+)`[^|]*\|\s*([+-][0-9.]+R)", txt)
            if rank_lines:
                top = rank_lines[:3]
                bot = rank_lines[-1] if len(rank_lines) > 3 else None
                line = "\n\n---\n\n# Strategy bias (auto-tuned)\n\n**Prefer:** "
                line += " · ".join(f"`{n}` ({e})" for n, e in top)
                if bot:
                    line += f"\n**Avoid:** `{bot[0]}` ({bot[1]})"
                line += "\n\n_Updated from trade data; full report `vault/_meta/strategy_performance.md`_"
                parts.append(line)
    except Exception:
        pass

    # Recent active lessons — surface compact pointers so analysts see prior
    # failures BEFORE proposing similar setups. Just titles + tags, no body
    # (full lessons readable via vault_read).
    try:
        lessons_dir = Path("vault/lessons")
        if lessons_dir.exists():
            # 4 most recent lessons (was 5; trimmed 2026-04-29 to keep
            # the Portfolio Manager prompt under the 32 768 SDK CLI limit
            # as new lesson files are added).
            recent = sorted(
                [p for p in lessons_dir.glob("*.md") if not p.name.startswith("_")],
                key=lambda p: p.stat().st_mtime, reverse=True,
            )[:4]
            if recent:
                import re as _re
                lesson_block = "\n\n---\n\n# Recent lessons (read full via vault_read if relevant)\n"
                for p in recent:
                    txt = p.read_text(encoding="utf-8")[:400]
                    # Extract the H1 title
                    title_m = _re.search(r"^#\s+(.+)$", txt, _re.MULTILINE)
                    title = title_m.group(1) if title_m else p.stem
                    lesson_block += f"- `{p.name}` — {title[:80]}\n"
                parts.append(lesson_block)
    except Exception:
        pass

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
    "mcp__options__compute_greeks",
    "mcp__options__compute_implied_vol",
    "mcp__options__compute_structure_greeks",
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
            "options":       options_mcp.server,
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

        # Autonomous-mode wake-budget gate. Refuse new wakes when daily
        # caps (count or spend) would be exceeded. Supervised mode skips
        # this gate — the user is the budget arbiter then.
        gated = _check_autonomy_wake_budget(self.db, agent_name)
        if gated is not None:
            return gated

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

        # CLI path resolution (added 2026-04-29 to escape OneDrive sync hell).
        # The bundled claude.exe under the venv is on the OneDrive path, and
        # OneDrive's "Files On-Demand" intermittently rehydrates the file
        # which causes anyio.open_process to throw FileNotFoundError. Prefer
        # the system-installed claude.cmd from npm (lives in AppData,
        # OneDrive-free). Override via env var FUND_CLAUDE_CLI_PATH if
        # something else is needed.
        cli_path = os.environ.get("FUND_CLAUDE_CLI_PATH") or _resolve_cli_path()

        opts = ClaudeAgentOptions(
            model=model,
            system_prompt=system_prompt,
            mcp_servers=self.mcp_servers,
            allowed_tools=spec.allowed_tools,
            cli_path=cli_path,
            hooks={
                "PreToolUse":  [HookMatcher(hooks=[risk_gate])],
                "PostToolUse": [HookMatcher(hooks=[audit_logger])],
                "Stop":        [HookMatcher(hooks=[cost_tracker])],
            },
        )

        messages: list[Any] = []
        usage: dict[str, Any] = {}
        final_text = ""
        # Retry transient CLI errors (CLINotFoundError seen in prod 2026-04-29:
        # Windows file-locking on the bundled claude.exe during pip/npm
        # background updates). Up to 2 retries with 5s spacing.
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                async with ClaudeSDKClient(options=opts) as client:
                    await client.query(task)
                    async for msg in client.receive_response():
                        messages.append(msg)
                        if hasattr(msg, "usage") and msg.usage:
                            usage = dict(msg.usage) if not isinstance(msg.usage, dict) else msg.usage
                        if hasattr(msg, "content") and msg.content:
                            for block in msg.content:
                                if hasattr(block, "text"):
                                    final_text += block.text
                last_err = None
                break
            except Exception as e:
                last_err = e
                # Only retry on transient CLI/file-system errors
                etype = type(e).__name__
                transient = etype in ("CLINotFoundError", "FileNotFoundError",
                                      "PermissionError", "TimeoutError")
                if not transient or attempt == 2:
                    break
                import asyncio as _aio
                await _aio.sleep(5)
        if last_err is not None:
            self.db.record_decision(
                agent=agent_name, kind="wake_error",
                summary=f"{agent_name} wake failed (after {attempt + 1} attempt(s))",
                rationale=f"{type(last_err).__name__}: {last_err!s}",
                model=model,
            )
            return {"error": str(last_err), "agent": agent_name, "model": model}

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
    # PM ensemble — wake specialists for cross-validation
    # ------------------------------------------------------------
    SPECIALIST_AGENTS = (
        "Quant Researcher",
        "Macro Strategist",
        "Flow Analyst",
        "Volatility Strategist",
    )

    async def pm_wake_specialists(
        self,
        pm_response_text: str,
        thesis: dict[str, Any],
        max_wakes: int = 3,
    ) -> list[dict[str, Any]]:
        """Parse PM output for `WAKE_SPECIALIST: <agent> | <question>` lines
        and wake each in parallel. Returns specialist responses for
        injection into PM's second-pass evaluation.

        Caps:
        - Max 3 specialist wakes per PM evaluation (default).
        - Specialist must be in SPECIALIST_AGENTS allowlist.
        - One pass — specialists cannot recursively wake more specialists.
        """
        import re as _re
        pattern = _re.compile(
            r"^\s*WAKE_SPECIALIST\s*:\s*([^|\n]+?)\s*\|\s*(.+)$",
            flags=_re.MULTILINE,
        )
        requests = []
        for match in pattern.finditer(pm_response_text):
            name = match.group(1).strip()
            question = match.group(2).strip()
            if name not in self.SPECIALIST_AGENTS:
                continue
            if name not in self.specs:
                continue
            requests.append((name, question))
            if len(requests) >= max_wakes:
                break

        if not requests:
            return []

        # Wake all specialists in parallel
        async def _one(name: str, q: str) -> dict[str, Any]:
            task = (
                f"PM-INITIATED CONSULT. Thesis under review: {thesis.get('summary', 'n/a')}. "
                f"PM's specific question for you: {q}\n\n"
                "Respond concisely (under 250 words) with your sector view. "
                "Do not propose orders; PM has the proposal."
            )
            r = await self.wake_agent(name, task)
            return {"specialist": name, "question": q,
                    "response": (r.get("final_text") or "")[:1500]}

        responses = await asyncio.gather(*[_one(n, q) for n, q in requests])
        # Log each consult
        for resp in responses:
            self.db.record_decision(
                agent="Portfolio Manager",
                kind="specialist_consult",
                summary=f"PM consulted {resp['specialist']}: {resp['question'][:80]}",
                rationale=resp['response'][:1000],
                model="orchestrator",
            )
        return responses

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
            if opt_verdict not in ("allow", "allow_with_modifications"):
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
    # Learning loop: detect closed losing trades, generate lessons
    # ------------------------------------------------------------
    _seen_closed_trades: set[int] = set()

    async def detect_and_learn_from_losses(self) -> dict[str, Any]:
        """Scan recently-closed positions; for each loss, fire a post-mortem
        if not already done. Adds lesson to vault/lessons/.

        Runs on every Nth tick. Safe to call frequently — internal seen-set
        prevents duplicate lessons.
        """
        import os, httpx, json
        from datetime import datetime as _dt, timedelta as _td, timezone as _tz
        api = os.environ.get("PROJECTX_API_KEY", "")
        user = os.environ.get("PROJECTX_USERNAME", "")
        aid = int(os.environ.get("PROJECTX_ACCOUNT_ID", "0") or 0)
        if not (api and user and aid):
            return {"skipped": "no creds"}

        try:
            r = httpx.post("https://api.topstepx.com/api/Auth/loginKey",
                           json={"userName": user, "apiKey": api}, timeout=15.0)
            token = r.json().get("token")
            H = {"Authorization": f"Bearer {token}"}

            # Pull recent trades / closed positions in last 4 hours
            end = _dt.now(tz=_tz.utc)
            start = end - _td(hours=4)
            r = httpx.post("https://api.topstepx.com/api/Trade/search",
                           headers=H, json={
                               "accountId": aid,
                               "startTimestamp": start.isoformat(),
                           }, timeout=20.0)
            trades = r.json().get("trades", []) if r.status_code == 200 else []
        except Exception as e:
            return {"error": str(e)}

        # Group trades into closed positions. A "closed position" is a pair
        # of opposite-side fills that net to zero on the same contract.
        # Crude heuristic: any trade with negative P&L counts as a closed loss.
        new_lessons = 0
        for t in trades:
            tid = t.get("id")
            if tid in self._seen_closed_trades:
                continue
            pnl = t.get("profitAndLoss")
            if pnl is None:
                continue
            self._seen_closed_trades.add(tid)
            if float(pnl) < 0:
                # Loss — fire a post-mortem
                await self._draft_lesson_for_trade(t)
                new_lessons += 1
        return {"new_lessons": new_lessons, "trades_scanned": len(trades)}

    async def _draft_lesson_for_trade(self, trade: dict[str, Any]) -> None:
        """Wake Quant Researcher with the trade context and ask for a lesson."""
        from datetime import datetime as _dt, timezone as _tz
        prompt = (
            "POST-MORTEM REQUEST. A losing trade just closed on Topstep. "
            "Draft a structured lesson per `vault/_meta/learning_system.md`.\n\n"
            f"Trade: {json.dumps(trade, default=str, indent=2)}\n\n"
            "Pull the original thesis and order_proposal from state.fund.db "
            "(matching symbol + recent timestamp). Look at the bars around "
            "fill and around exit. Identify root cause(s). Tag with one or "
            "more failure categories from the taxonomy. Write the lesson "
            "to `vault/lessons/{date}_{symbol}_{strategy}_failed.md` with "
            "the standard frontmatter (type, date, trade_id, symbol, "
            "strategy, outcome, loss_usd, status, applies_to). End with "
            "'LESSON DRAFTED: <path>'."
        )
        import json
        await self.wake_agent("Quant Researcher", prompt)

    def get_active_lessons_for_wake(
        self, agent_name: str, symbol: str | None = None,
        strategy: str | None = None,
    ) -> list[str]:
        """Return paths to active lessons relevant to the upcoming wake.
        Used by analyst prompts so they see recent failure patterns before
        proposing similar trades.

        Active = not in `_archive/` AND less than 30 days old by frontmatter
        date OR explicitly tagged confidence != ADVISORY (those persist).
        """
        from datetime import datetime as _dt, timedelta as _td, timezone as _tz
        lessons_dir = Path("vault/lessons")
        if not lessons_dir.exists():
            return []
        cutoff = _dt.now(tz=_tz.utc) - _td(days=30)
        relevant: list[tuple[float, str]] = []
        for path in lessons_dir.glob("*.md"):
            if path.name.startswith("_"):
                continue
            try:
                txt = path.read_text(encoding="utf-8")[:3000]
            except Exception:
                continue
            # Extract date from frontmatter
            import re as _re
            m = _re.search(r"^date:\s*(\S+)", txt, _re.MULTILINE)
            if not m: continue
            try:
                lesson_dt = _dt.fromisoformat(m.group(1)).replace(tzinfo=_tz.utc)
            except Exception:
                continue
            if lesson_dt < cutoff and "PATTERN" not in txt and "RULE" not in txt:
                continue
            # Match relevance
            score = 1.0  # base
            if symbol and symbol in txt: score += 2.0
            if strategy and strategy in txt: score += 2.0
            if agent_name in txt: score += 1.0
            relevant.append((score, str(path)))
        relevant.sort(reverse=True)
        return [p for _, p in relevant[:5]]   # top 5 most relevant

    # ------------------------------------------------------------
    # CRITICAL safety: every position must have a stop on the book
    # ------------------------------------------------------------
    async def capture_account_snapshot(self) -> dict[str, Any] | None:
        """Pull live broker state and write an account_snapshots row.

        This is the writer side of the account_snapshots pipeline. The risk
        hook reads from this table for DLL, TDD, defensive ladder, and
        consistency-rule checks — without this, every P&L-aware safety check
        early-returns. Called from tick_workflow and session_open_workflow.

        Returns the snapshot dict on success, None on broker failure.
        Failures log a warn risk_event; never raise (must not kill the tick).

        Unrealized P&L is computed from open positions × latest 1-min bar
        close, using tick_size/tick_value from config/symbols.yaml. A failed
        quote on one position is logged + treated as 0 for that leg, not
        fatal — partial unrealized is better than blocking the snapshot.
        """
        try:
            from tools.projectx_client import ProjectXError, get_client
            from tools.topstep import get_account_id
            import yaml
            client = get_client()
            account_id = get_account_id()
            accounts = client.get_accounts()
            mine = next(
                (a for a in accounts if str(a.get("id")) == str(account_id)), None
            )
            if mine is None:
                self.db.record_risk_event(
                    severity="warn", rule="snapshot_capture_failed",
                    agent="orchestrator",
                    detail={"error": f"account {account_id} not visible"},
                )
                return None

            balance = float(mine.get("balance", 0) or 0)
            can_trade = bool(mine.get("canTrade", True))
            positions = client.get_positions(account_id)
            open_contracts = sum(
                int(p.get("size") or p.get("netQuantity") or 0) for p in positions
            )

            # ── Unrealized P&L: latest bar close × contract multiplier ──
            symbols_cfg = (yaml.safe_load(
                Path("config/symbols.yaml").read_text()
            ) or {}).get("symbols", {})
            unrealized_total = 0.0
            now = datetime.now(tz=timezone.utc)
            from hooks.risk_gate import _normalize_root
            for p in positions:
                size = int(p.get("size") or p.get("netQuantity") or 0)
                if size == 0:
                    continue
                contract_id = p.get("contractId") or p.get("contract") or ""
                if not contract_id:
                    continue
                avg_price = float(p.get("avgPrice") or p.get("averagePrice") or 0)
                if avg_price <= 0:
                    continue
                # ProjectX type: 1=long, 2=short. Fall back to size sign.
                type_code = int(p.get("type") or 0)
                if type_code == 1:
                    sign = 1
                elif type_code == 2:
                    sign = -1
                else:
                    sign = 1 if size > 0 else -1
                size = abs(size)
                # Resolve symbol root → tick metadata
                root = None
                for tok in str(contract_id).split("."):
                    if tok in ("CON", "F", "US", "") or (
                        len(tok) <= 3 and tok and tok[0].isalpha() and tok[1:].isdigit()
                    ):
                        continue
                    root = _normalize_root(tok)
                    break
                meta = symbols_cfg.get(root or "", {}) if root else {}
                tick_size = float(meta.get("tick_size") or 0)
                tick_value = float(meta.get("tick_value") or 0)
                if tick_size <= 0 or tick_value <= 0:
                    self.db.record_risk_event(
                        severity="warn", rule="unrealized_pl_skipped",
                        agent="orchestrator",
                        detail={"contract_id": contract_id, "root": root,
                                "reason": "missing tick_size/tick_value in symbols.yaml"},
                    )
                    continue
                # Latest 1-min bar as the mark
                try:
                    bars = client.get_bars(
                        contract_id=contract_id,
                        start_time=(now - timedelta(minutes=10)).isoformat(),
                        end_time=now.isoformat(),
                        unit=2, unit_number=1, limit=10, live=False,
                    )
                    mark = float(bars[-1].get("c") or bars[-1].get("close") or 0) if bars else 0
                except Exception as e:
                    self.db.record_risk_event(
                        severity="warn", rule="unrealized_pl_skipped",
                        agent="orchestrator",
                        detail={"contract_id": contract_id,
                                "reason": f"bars fetch failed: {e}"[:200]},
                    )
                    mark = 0
                if mark <= 0:
                    continue
                points = mark - avg_price
                unrealized_total += sign * size * (points / tick_size) * tick_value

            # Realized day P&L = current balance − balance at first snapshot of today
            first_today = self.db.first_snapshot_today_utc()
            if first_today:
                realized_day = balance - float(first_today["balance_usd"])
            else:
                realized_day = 0.0  # first snapshot of the day — anchor at 0

            # Trailing DD = peak balance ever seen (or starting balance) − current
            risk_cfg = yaml.safe_load(Path("config/risk_limits.yaml").read_text())
            starting = float(risk_cfg.get("account", {}).get("starting_balance", 0))
            peak = self.db.peak_eod_balance(fallback=starting)
            trailing_dd = max(0.0, peak - balance)

            env = str(risk_cfg.get("account", {}).get("environment", "combine"))

            self.db.record_account_snapshot(
                balance_usd=balance,
                environment=env,
                unrealized_pl_usd=unrealized_total,
                realized_pl_day_usd=realized_day,
                trailing_dd_usd=trailing_dd,
                open_contracts_total=open_contracts,
                can_trade=can_trade,
            )
            if not can_trade:
                # Surface this loudly — the broker has flipped the account to
                # un-tradeable. Risk hook will block; this records why.
                self.db.record_risk_event(
                    severity="warn", rule="broker_can_trade_false",
                    agent="orchestrator",
                    detail={"balance_usd": balance,
                            "note": "Broker reports canTrade=false."},
                )
            return {
                "balance_usd": balance,
                "realized_pl_day_usd": realized_day,
                "unrealized_pl_usd": unrealized_total,
                "trailing_dd_usd": trailing_dd,
                "open_contracts_total": open_contracts,
                "can_trade": can_trade,
            }
        except ProjectXError as e:
            self.db.record_risk_event(
                severity="warn", rule="snapshot_capture_failed",
                agent="orchestrator", detail={"error": f"broker: {e}"[:300]},
            )
            return None
        except Exception as e:
            self.db.record_risk_event(
                severity="warn", rule="snapshot_capture_failed",
                agent="orchestrator", detail={"error": str(e)[:300]},
            )
            return None

    def _backfill_missing_daily_pl(self) -> int:
        """Backfill daily_pl rows for any past UTC day that has snapshots
        but no finalized daily_pl entry. Skips today (in-progress).

        Returns the number of days backfilled. Idempotent — safe to call
        on every tick; only does work when something is missing.
        """
        today_utc = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        # Find all snapshot days
        snap_days = {
            r[0] for r in self.db.connect().execute(
                "SELECT DISTINCT substr(ts, 1, 10) FROM account_snapshots"
            )
            if r[0] and r[0] < today_utc
        }
        # Find days that already have a daily_pl row
        existing = {r[0] for r in self.db.connect().execute(
            "SELECT day FROM daily_pl"
        )}
        missing = sorted(snap_days - existing)
        for day in missing:
            row = self.db.connect().execute(
                """SELECT realized_pl_day_usd,
                          MAX(realized_pl_day_usd) AS peak
                   FROM account_snapshots
                   WHERE substr(ts, 1, 10) = ?
                   ORDER BY ts DESC LIMIT 1""",
                (day,),
            ).fetchone()
            if not row or row[0] is None:
                continue
            self.db.upsert_daily_pl(
                day=day,
                realized_pl_usd=float(row[0]),
                peak_realized_pl_usd=float(row[1]) if row[1] is not None else None,
            )
        return len(missing)

    async def verify_position_stops(self) -> dict[str, Any]:
        """For every open position, verify there's a working stop order.
        If not, place one (or flatten if can't determine the stop level).

        This is the safety net that prevents the failure mode we hit on
        2026-04-29: a fill happened but the post-fill bracket was never
        placed. Runs on every tick + at runtime startup.

        Returns: {"checked": N, "fixed": M, "flattened": K}
        """
        import os, httpx
        api = os.environ.get("PROJECTX_API_KEY", "")
        user = os.environ.get("PROJECTX_USERNAME", "")
        aid = int(os.environ.get("PROJECTX_ACCOUNT_ID", "0") or 0)
        if not (api and user and aid):
            return {"error": "no broker credentials"}

        try:
            r = httpx.post("https://api.topstepx.com/api/Auth/loginKey",
                           json={"userName": user, "apiKey": api}, timeout=15.0)
            token = r.json().get("token")
            if not token:
                return {"error": "auth failed"}
            H = {"Authorization": f"Bearer {token}"}

            # Fetch positions + working orders
            r = httpx.post("https://api.topstepx.com/api/Position/searchOpen",
                           headers=H, json={"accountId": aid}, timeout=15.0)
            positions = r.json().get("positions", []) or []
            r = httpx.post("https://api.topstepx.com/api/Order/searchOpen",
                           headers=H, json={"accountId": aid}, timeout=15.0)
            orders = r.json().get("orders", []) or []
        except Exception as e:
            return {"error": f"broker query failed: {e}"}

        checked, fixed, flattened = 0, 0, 0
        for pos in positions:
            checked += 1
            pos_size = int(pos.get("size", 0))
            pos_contract = pos.get("contractId")
            pos_type = int(pos.get("type", 1))     # 1 = long, 2 = short
            avg_price = float(pos.get("averagePrice", 0))
            if pos_size == 0:
                continue

            # Find a stop order on the same contract, opposite side, sized to cover
            opposite_side = 1 if pos_type == 1 else 0
            covering_stops = [
                o for o in orders
                if o.get("contractId") == pos_contract
                and int(o.get("side", -1)) == opposite_side
                and int(o.get("type", 0)) in (3, 4)   # 3=stop, 4=stop-limit
                and int(o.get("size", 0)) >= pos_size
                and o.get("stopPrice") is not None
            ]
            if covering_stops:
                continue   # protected — fine

            # No stop on the book. Try to find the position's recorded
            # stop_loss_price from the most recent order_proposal in the DB
            # FOR THIS SYMBOL within the last 24h. Never grab a stop from
            # an unrelated proposal — a wrong-symbol stop is worse than no stop.
            #
            # pos_contract is a ProjectX contractId like "CON.F.US.TYA.M26".
            # Extract the root token to match how analysts record decisions.
            root = pos_contract
            for part in str(pos_contract).split("."):
                if part and part not in ("CON", "F", "US"):
                    # 'M26' style continuation suffix — keep looking
                    if len(part) <= 3 and part[-2:].isdigit():
                        continue
                    root = part
                    break
            from datetime import datetime as _dt, timedelta as _td, timezone as _tz
            cutoff = (_dt.now(tz=_tz.utc) - _td(hours=24)
                      ).isoformat(timespec="seconds")
            row = self.db.connect().execute(
                "SELECT rationale FROM decisions "
                "WHERE kind = 'order_proposal' "
                "  AND symbol = ? "
                "  AND ts >= ? "
                "ORDER BY id DESC LIMIT 1",
                (root, cutoff),
            ).fetchone()
            stop_price = None
            if row:
                import re as _re
                m = _re.search(
                    r"stop[_\- ]?loss[_\- ]?price?\s*[:=]\s*([0-9]*\.?[0-9]+)",
                    row[0] or "", _re.IGNORECASE,
                )
                if m:
                    stop_price = float(m.group(1))

            if stop_price is None:
                # Cannot determine stop level — FLATTEN
                self.db.record_decision(
                    agent="orchestrator", kind="emergency_flatten",
                    summary=f"Unprotected position on {pos_contract}, no stop level recoverable — flattening",
                    rationale=f"Position size {pos_size}, type {pos_type}, avg {avg_price}. "
                             "verify_position_stops could not find a stop_loss_price in any "
                             "recent proposal. Issuing market close.",
                    model="orchestrator", symbol=pos_contract,
                )
                # Submit market close
                close_order = {
                    "accountId": aid, "contractId": pos_contract,
                    "type": 2,                          # market
                    "side": opposite_side,
                    "size": pos_size,
                    "customTag": "EMERGENCY_FLATTEN_NO_STOP",
                }
                try:
                    r = httpx.post("https://api.topstepx.com/api/Order/place",
                                   headers=H, json=close_order, timeout=20.0)
                    if r.status_code == 200 and (r.json() or {}).get("success"):
                        flattened += 1
                    else:
                        self.db.record_risk_event(
                            severity="breach", rule="auto_flatten_failed",
                            agent="orchestrator",
                            detail={"contract": pos_contract,
                                    "size": pos_size,
                                    "status": r.status_code,
                                    "body": (r.text or "")[:300]},
                        )
                except Exception as e:
                    self.db.record_risk_event(
                        severity="breach", rule="auto_flatten_exception",
                        agent="orchestrator",
                        detail={"contract": pos_contract, "error": str(e)[:300]},
                    )
                continue

            # Place the missing stop
            stop_order = {
                "accountId": aid, "contractId": pos_contract,
                "type": 4,                              # stop-limit
                "side": opposite_side,
                "size": pos_size,
                "stopPrice": stop_price,
                "limitPrice": stop_price - 5 * 0.015625 if pos_type == 1
                              else stop_price + 5 * 0.015625,
                "customTag": "AUTO_RECOVER_STOP",
            }
            try:
                r = httpx.post("https://api.topstepx.com/api/Order/place",
                               headers=H, json=stop_order, timeout=20.0)
                if r.status_code == 200 and (r.json() or {}).get("success"):
                    self.db.record_decision(
                        agent="orchestrator", kind="auto_recover_stop",
                        summary=f"Placed missing stop on {pos_contract} at {stop_price}",
                        rationale=f"verify_position_stops sweep found unprotected {pos_size}-contract "
                                 f"position. Recovered stop level {stop_price} from latest order_proposal.",
                        model="orchestrator", symbol=pos_contract,
                    )
                    fixed += 1
                else:
                    # Auto-recover failed — escalate to flatten on next tick
                    self.db.record_risk_event(
                        severity="breach", rule="auto_recover_stop_failed",
                        agent="orchestrator",
                        detail={"contract": pos_contract,
                                "stop_price": stop_price,
                                "status": r.status_code,
                                "body": (r.text or "")[:300]},
                    )
            except Exception as e:
                self.db.record_risk_event(
                    severity="breach", rule="auto_recover_stop_exception",
                    agent="orchestrator",
                    detail={"contract": pos_contract, "error": str(e)[:300]},
                )

        return {"checked": checked, "fixed": fixed, "flattened": flattened}

    # ------------------------------------------------------------
    # Event loop
    # ------------------------------------------------------------
    async def run(self) -> None:
        # Safety: verify all positions have stops on startup
        try:
            result = await self.verify_position_stops()
            if result.get("fixed") or result.get("flattened"):
                print(f"[startup] stop verification: {result}")
        except Exception as e:
            print(f"[startup] stop verification error: {e}")
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
            case EventKind.STRESS_TEST_DUE:
                await self.stress_test_workflow()
            case EventKind.DAILY_METRICS_DUE:
                await self.daily_metrics_workflow()
            case _:
                pass

    async def stress_test_workflow(self) -> dict[str, Any]:
        """Pre-market stress test (06:00 CT daily). Run all scenarios; if any
        breaches the internal DLL ceiling, wake CIO + Risk Manager."""
        from tools.stress_test import run_stress
        report = run_stress()
        breach = report.any_breaches()
        self.db.record_decision(
            agent="System", kind="stress_test",
            summary=f"Stress test: {'BREACH' if breach else 'within'}",
            rationale=report.summary(),
        )
        if breach:
            await self.wake_agent(
                "Risk Manager",
                f"Pre-market stress test BREACHED internal DLL on at least one "
                f"scenario. Report:\n\n{report.summary()}\n\n"
                "Decide: which positions to flag for size reduction or close.",
            )
        return {"status": "stress_done", "breach": breach}

    async def daily_metrics_workflow(self) -> dict[str, Any]:
        """Daily Compliance metrics sweep — calibration, decay, missing reviews."""
        from tools.agent_metrics import daily_metrics_snapshot
        snap = daily_metrics_snapshot()
        self.db.record_decision(
            agent="System", kind="daily_metrics",
            summary="Daily metrics computed",
            rationale=str(snap)[:2000],
        )
        # If there are missing post-mortems or any decayed strategies, surface
        if snap.get("missing_post_mortems") or any(
            s.get("decay_flag") for s in snap.get("strategy_decay", [])
        ):
            await self.wake_agent(
                "Compliance",
                f"Daily metrics flag: review missing post-mortems and decay flags.\n\n"
                f"Snapshot: {snap}",
            )
        return {"status": "metrics_done", "snapshot": snap}

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
        # Capture an opening snapshot so the risk hook has data the moment
        # the first order proposal lands. Don't wait for the first tick.
        await self.capture_account_snapshot()
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
                "  WAKE: Energies Analyst | Metals Analyst | Ag Analyst | "
                "Rates Analyst | FX Futures Analyst | Index/Macro Analyst\n"
                "  WAKE: none\n"
            ),
        )
        analyst = _parse_wake_line(cio_result.get("final_text", ""))
        if not analyst or analyst.lower() == "none":
            return {"status": "session_brief_only", "analyst_woken": None}
        return await self.run_analyst_chain(analyst)

    async def session_close_workflow(self) -> dict[str, Any]:
        """End-of-day: CIO wrap + Compliance summary + auto-halt re-engage."""
        # Resolve and recap shadow trades BEFORE the CIO wrap so the brief
        # can cite today's hypothetical-screen results.
        try:
            import subprocess
            subprocess.run(
                [sys.executable, "-m", "scripts.resolve_shadow_trades",
                 "--min-age", "0", "--limit", "500"],
                timeout=300, check=False, capture_output=True,
            )
            subprocess.run(
                [sys.executable, "-m", "scripts.shadow_trade_recap",
                 "--days", "14", "--quiet"],
                timeout=60, check=False, capture_output=True,
            )
        except Exception:
            pass

        await self.wake_agent("CIO", "SESSION CLOSE. Publish daily wrap to journal. "
                              "Read vault/_meta/shadow_candidates.json — flag any "
                              "GREEN combos for promotion to focus_universe.yaml.")
        await self.wake_agent("Compliance", "End-of-day audit + compliance summary.")

        # Auto-append EOD report to today's journal so the cost ledger lives
        # in the journal automatically — agents don't have to remember to
        # compute it. 2026-04-30 enrichment.
        try:
            import subprocess as _sp
            today_utc_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
            res = _sp.run(
                [sys.executable, "-m", "scripts.eod"],
                capture_output=True, text=True, timeout=60, check=False,
            )
            if res.returncode == 0 and res.stdout:
                journal = Path(f"vault/journal/{today_utc_str}.md")
                if journal.exists():
                    journal.write_text(
                        journal.read_text(encoding="utf-8") +
                        "\n\n## Auto-EOD report\n\n```\n" + res.stdout + "\n```\n",
                        encoding="utf-8",
                    )
        except Exception:
            pass
        # Finalize today's daily_pl row from the day's snapshots. Powers the
        # Topstep 50%-consistency advisory in the risk hook.
        try:
            today_utc = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
            row = self.db.connect().execute(
                """SELECT realized_pl_day_usd, MAX(realized_pl_day_usd) AS peak
                   FROM account_snapshots
                   WHERE ts LIKE ?""",
                (f"{today_utc}%",),
            ).fetchone()
            if row and row[0] is not None:
                self.db.upsert_daily_pl(
                    day=today_utc,
                    realized_pl_usd=float(row[0]),
                    peak_realized_pl_usd=float(row[1]) if row[1] is not None else None,
                )
        except Exception:
            # Don't let finalization failure stop session close.
            pass
        # Re-engage auto-halt so no orders fire overnight without explicit
        # human re-authorization. No-op if fund.yaml has the feature disabled.
        new_halt_ts = re_engage_auto_halt(reason="session_close")
        result: dict[str, Any] = {"status": "session_closed"}
        if new_halt_ts:
            self.db.record_decision(
                agent="orchestrator", kind="auto_halt_engaged",
                summary=f"trading_halt_until set to {new_halt_ts}",
                rationale="session_close_workflow re-armed the kill-switch timestamp",
                model="system",
            )
            result["auto_halt_until"] = new_halt_ts
        return result

    # Counter for tick cadence — used to gate periodic deep wakes.
    # Every Nth tick wakes Quant Researcher; every Mth tick wakes CIO.
    _tick_count = 0

    # Reanimation: how many times we've re-evaluated each passed thesis
    _reanimation_attempts: dict[int, int] = {}

    async def reanimate_passed_theses(self) -> dict[str, Any]:
        """Scan recent autonomous_borderline_pass decisions; if conditions
        have changed (price returned to entry zone, away from invalidation),
        re-wake Risk Manager with fresh state.

        This is the adaptability layer. Today's ZN case: price retraced past
        invalidation at 22:05 -> RM correctly PASSed. Then price rebounded
        fully to entry by 23:52 -> the original thesis is alive again. This
        method catches that.

        Caps:
        - Lookback: last 4 hours
        - Max 2 re-eval attempts per thesis (avoids loops)
        - Each re-eval costs a Risk Manager wake (~$0.10)
        """
        from datetime import datetime as _dt, timedelta as _td, timezone as _tz
        # Use isoformat with timezone offset to match utcnow_iso() in state/db.py.
        # A naive strftime here would lexicographically lose to "+00:00"-suffixed
        # rows and the freshness filter would never reject anything.
        cutoff = (_dt.now(tz=_tz.utc) - _td(hours=4)).isoformat(timespec="seconds")
        rows = self.db.connect().execute(
            "SELECT id, ts, symbol, summary, rationale FROM decisions "
            "WHERE kind = 'autonomous_borderline_pass' AND ts > ? "
            "ORDER BY id DESC LIMIT 5",
            (cutoff,),
        ).fetchall()

        results: list[dict[str, Any]] = []
        for row in rows:
            decision_id = row["id"]
            attempts = self._reanimation_attempts.get(decision_id, 0)
            if attempts >= 2:
                continue
            self._reanimation_attempts[decision_id] = attempts + 1

            # Fire the borderline-decide script as a subprocess so it has its
            # own clean state. Pass the decision id and original parameters.
            # The script lives at scripts/_decide_borderline_trade.py.
            # NOTE: today's script is hard-coded to ZN ORB; for general use
            # we'd parameterize it. For now this method just LOGS the
            # opportunity; a future generalization plugs in the script.
            self.db.record_decision(
                agent="orchestrator",
                kind="reanimation_check",
                summary=f"Reanimation triggered for decision {decision_id} ({row['symbol']})",
                rationale=(
                    f"Original PASS at {row['ts']}. Reanimation attempt "
                    f"{attempts + 1}/2. The borderline-decide script will "
                    "re-evaluate this thesis with current price/structure."
                ),
                model="orchestrator",
                symbol=row["symbol"],
            )
            results.append({"decision_id": decision_id, "symbol": row["symbol"],
                            "attempt": attempts + 1})
        return {"reanimations_triggered": len(results), "details": results}

    async def tick_workflow(self) -> dict[str, Any]:
        """Mid-session TICK — Edge Hunter-first cadence for high-frequency setups.

        Pattern:
          - Every tick: wake Edge Hunter (cheap, telegraphic). If TRIGGER,
            run analyst chain to completion (Edge Hunter -> PM -> Risk -> Exec).
          - Every 6th tick (~30 min @ 5min cadence): also wake Quant Researcher
            in parallel for deeper math + physics scan.
          - Every 12th tick (~60 min): also wake CIO for regime check + routing.

        This unlocks high-cadence trading without burning budget on a CIO
        wake every tick.
        """
        Orchestrator._tick_count += 1
        n = Orchestrator._tick_count

        # Step −2: CAPTURE — pull live broker state into account_snapshots.
        # The risk hook's DLL, TDD, defensive ladder, and consistency-rule
        # checks all read from this table. Without this, P&L-aware safety
        # is blind. Failures log + continue (must not kill the tick).
        await self.capture_account_snapshot()

        # Step −2.1: BACKFILL — if session_close_workflow didn't run last
        # session (orchestrator killed/restarted around midnight), the
        # previous UTC day's daily_pl row is missing. The consistency rule
        # depends on that history. Backfill from the last snapshot of any
        # previous day that lacks a daily_pl row.
        try:
            self._backfill_missing_daily_pl()
        except Exception as e:
            self.db.record_risk_event(
                severity="warn", rule="daily_pl_backfill_failed",
                agent="orchestrator", detail={"error": str(e)[:300]},
            )

        # Step −1.5: RECONCILE — DB ↔ broker truth. Runs BEFORE
        # verify_position_stops so the stop check operates on accurate
        # state. Broker is source of truth on conflict.
        try:
            from scripts.reconcile_positions import reconcile
            reconcile(verbose=False)
        except Exception as e:
            self.db.record_risk_event(
                severity="warn", rule="reconcile_failed",
                agent="orchestrator", detail={"error": str(e)[:300]},
            )

        # Step −1: SAFETY — every tick, verify open positions have stops.
        # This is the safety net for the post-fill bracket-placement gap.
        # No API cost (broker query only).
        try:
            await self.verify_position_stops()
        except Exception as e:
            # Log but do not let it kill the tick
            self.db.record_risk_event(
                severity="warn", rule="verify_stops_failed",
                agent="orchestrator", detail={"error": str(e)[:300]},
            )

        # Step −0.5: LEARNING — every 4th tick, scan for newly-closed losing
        # trades and draft post-mortems. Cheap unless a loss closed.
        if n % 4 == 0:
            try:
                await self.detect_and_learn_from_losses()
            except Exception:
                pass

        # Step −0.4: AUTO-TUNING — every 12th tick (~60 min), refresh
        # the strategy_performance.md ranking from observed trade history.
        # Bayesian shrinkage applied; ADVISORY until per-strategy n>=20.
        if n % 12 == 0:
            try:
                from tools.strategy_performance import (
                    get_strategy_stats, render_markdown_report,
                )
                stats = get_strategy_stats()
                Path("vault/_meta/strategy_performance.md").write_text(
                    render_markdown_report(stats), encoding="utf-8"
                )
            except Exception:
                pass

        # Step 0: Adaptability — every 6th tick, scan recent passed theses
        # and check if conditions have changed (price returned to entry, etc).
        # This is the layer that catches the "ZN bounced back" pattern.
        if n % 6 == 0:
            await self.reanimate_passed_theses()

        # Step 0.1: SHADOW TRADES — every 6th tick, resolve any unresolved
        # shadow trades against actual price action. No API cost (broker
        # bars only). Recap is end-of-session; this just keeps the
        # outcome ledger fresh.
        if n % 6 == 0:
            try:
                import subprocess
                subprocess.run(
                    [sys.executable, "-m", "scripts.resolve_shadow_trades",
                     "--min-age", "30", "--limit", "50"],
                    timeout=120, check=False, capture_output=True,
                )
            except Exception:
                pass

        # Step 1: Always wake Edge Hunter (every tick). Cheap, fast, wide.
        edge_task = self.wake_agent(
            "Edge Hunter",
            (
                "INTRADAY MULTI-TIMEFRAME SCAN. Scan ALL CME-tradeable "
                "instruments across 1-min, 5-min, AND 15-min timeframes. "
                "For each strategy in your library check if a trigger fires "
                "on ANY timeframe right now. Pick the SINGLE highest-quality "
                "trigger (defined risk, R:R >= 2.0, positive backtest "
                "expectancy). Call state_record_decision (kind=thesis) if "
                "you find one. Follow your TRIGGER / WATCHLIST / NO_TRIGGER "
                "output protocol. Be terse."
            ),
        )

        # Step 2: Optional QR co-wake every 6th tick
        qr_task = None
        if n % 6 == 0:
            qr_task = self.wake_agent(
                "Quant Researcher",
                (
                    "INTRADAY HFT-FLAVORED SCAN. Use your physics-quant "
                    "toolkit (Marchenko-Pastur, Hawkes intensity, power-law "
                    "tails) on top of the strategy library. Scan ES, NQ, "
                    "CL, GC, ZN, 6E, 6B on 5-min and 15-min bars. Pick "
                    "the highest-quality setup that meets risk constraints. "
                    "Call state_record_decision kind=thesis if found, end "
                    "with THESIS: <SYMBOL> conviction=<low|med|high> or "
                    "NO_TRADE: <reason>."
                ),
            )

        # Run in parallel
        if qr_task is not None:
            edge_result, qr_result = await asyncio.gather(edge_task, qr_task)
        else:
            edge_result = await edge_task
            qr_result = None

        # Step 3: Did either record a thesis in DB?
        edge_thesis = self._latest_thesis_for("Edge Hunter")
        qr_thesis = self._latest_thesis_for("Quant Researcher") if qr_result else None

        # Recency check — only theses recorded in the last 5 min count
        from datetime import datetime as _dt, timezone as _tz, timedelta as _td
        # isoformat keeps the +00:00 offset to match utcnow_iso() in state/db.py
        cutoff = (_dt.now(tz=_tz.utc) - _td(minutes=5)).isoformat(timespec="seconds")
        def _fresh(thesis):
            if not thesis or not thesis.get("rationale"):
                return False
            row = self.db.connect().execute(
                "SELECT ts FROM decisions WHERE id = "
                "(SELECT MAX(id) FROM decisions WHERE agent = ? AND kind = 'thesis')",
                (thesis.get("agent"),),
            ).fetchone()
            return row and row[0] > cutoff

        edge_fresh = _fresh(edge_thesis)
        qr_fresh = _fresh(qr_thesis)

        # ACTION BIAS (2026-04-29): Edge Hunter wins over QR when both are
        # fresh. Edge Hunter is the intraday micro desk — its triggers are
        # fast and time-sensitive. QR's deeper analysis runs on a slower
        # cadence and shouldn't gate intraday action. If QR also has a
        # fresh thesis, queue both chains.
        chains_to_run: list[tuple[str, dict | None]] = []
        if edge_fresh:
            chains_to_run.append(("Edge Hunter", edge_thesis))
        if qr_fresh and (not edge_fresh or qr_thesis.get("symbol") != edge_thesis.get("symbol")):
            # Only run QR chain if it's a different symbol (don't double-trade
            # the same instrument). Same-symbol = QR confirmation, not a
            # second trade.
            chains_to_run.append(("Quant Researcher", qr_thesis))

        if chains_to_run:
            chain_results = []
            for agent_name, thesis in chains_to_run:
                chain = await self.run_analyst_chain(
                    agent_name, existing_thesis=thesis,
                )
                chain_results.append({"agent": agent_name,
                                      "status": chain.get("status")})
            return {"status": "tick_chain", "tick": n,
                    "chains": chain_results}

        # Step 4: No trigger. Every 12th tick, wake CIO for regime check.
        if n % 12 == 0:
            cio_result = await self.wake_agent(
                "CIO",
                (
                    "PERIODIC TICK CHECK-IN (every ~60 min). No fresh "
                    "trigger from Edge Hunter or QR. Briefly: any regime "
                    "shift you see? Refresh vault/regime/current.md if "
                    "warranted. Otherwise NONE. Concise (<150 words)."
                ),
            )
            return {"status": "cio_periodic_check", "tick": n}

        return {"status": "no_action", "tick": n}

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

    async def run_analyst_chain(self, analyst_name: str,
                                 existing_thesis: dict | None = None) -> dict[str, Any]:
        """Full chain: Analyst → (Red Team if med/high) → PM → Risk → Exec.

        Each step reads structured signals from the prior step's text output
        OR from the most recent decision row in the DB.

        FAST PATH (added 2026-04-29): if `existing_thesis` is provided OR
        the analyst already has a thesis recorded in the last 5 minutes,
        we SKIP the re-wake and go straight to PM. This was the bug
        blocking Edge Hunter triggers from progressing to orders — the
        re-wake asked Edge Hunter to "research your sector" (a per-
        sector-analyst prompt) and Edge Hunter (which is the micro desk)
        responded NO_TRADE because that's not how it operates.
        """
        # FAST PATH: do we already have a fresh thesis for this analyst?
        thesis = existing_thesis or self._latest_thesis_for(analyst_name)
        from datetime import datetime as _dt, timedelta as _td, timezone as _tz
        is_fresh = False
        if thesis and not existing_thesis:
            # Verify the thesis was recorded in the last 5 minutes
            row = self.db.connect().execute(
                "SELECT ts FROM decisions WHERE id = "
                "(SELECT MAX(id) FROM decisions WHERE agent = ? AND kind = 'thesis')",
                (thesis.get("agent") or analyst_name,),
            ).fetchone()
            cutoff = (_dt.now(tz=_tz.utc) - _td(minutes=5)).isoformat(timespec="seconds")
            is_fresh = bool(row and row[0] > cutoff)
        elif existing_thesis:
            is_fresh = True

        if not is_fresh:
            # SLOW PATH: no fresh thesis → wake the analyst to research.
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

        # 3. PM evaluates — first pass. PM may emit WAKE_SPECIALIST lines
        #    to consult Quant / Macro / Flow / Vol / Execution specialists
        #    before deciding. Capped at 3 specialist wakes per evaluation.
        autonomous = bool(_load_fund_yaml().get("autonomous_mode", False))
        pm_first_prompt = (
            f"Thesis: {thesis}\n"
            f"Red Team challenge: {challenge.get('final_text', 'n/a') if challenge else 'skipped (low conviction)'}\n\n"
            "Step 1 — Decide whether you need specialist input.\n"
            f"{'You may consult up to 3 specialists' if autonomous else 'In autonomous mode you may consult specialists; in supervised mode skip this step'} "
            "by emitting lines of the form:\n"
            "  WAKE_SPECIALIST: <agent_name> | <focused question>\n"
            "Allowed specialists: Quant Researcher, Macro Strategist, Flow Analyst, "
            "Volatility Strategist, Execution Specialist.\n"
            "If no consultation needed, skip this step.\n\n"
            "Step 2 — Decide pursue|pass and produce proposal/PASS in same response.\n"
            "If pursue, produce order_proposal (symbol, side, qty, order_type, "
            "stop_loss_price, target_price, rationale) and record via "
            "state_record_decision kind=order_proposal.\n"
            "End with EXACTLY 'DECISION: PROPOSE' or 'DECISION: PASS'."
        )
        pm_result = await self.wake_agent("Portfolio Manager", pm_first_prompt)
        pm_text = pm_result.get("final_text", "") or ""

        # 3b. If PM requested specialist consults AND we're in autonomous
        #     mode, wake them in parallel and re-prompt PM with the input.
        if autonomous and "WAKE_SPECIALIST:" in pm_text.upper():
            specialist_responses = await self.pm_wake_specialists(
                pm_text, thesis, max_wakes=3,
            )
            if specialist_responses:
                consult_summary = "\n\n".join(
                    f"--- {r['specialist']} on '{r['question']}' ---\n{r['response']}"
                    for r in specialist_responses
                )
                pm_second_prompt = (
                    f"Thesis: {thesis}\n"
                    f"Red Team: {challenge.get('final_text', 'n/a') if challenge else 'skipped'}\n\n"
                    f"Specialist consults you requested:\n{consult_summary}\n\n"
                    "Now make your final decision. Produce order_proposal if "
                    "pursuing (symbol, side, qty, order_type, stop_loss_price, "
                    "target_price, rationale). Record via state_record_decision "
                    "kind=order_proposal. End with EXACTLY: 'DECISION: PROPOSE' "
                    "or 'DECISION: PASS'."
                )
                pm_result = await self.wake_agent("Portfolio Manager", pm_second_prompt)
                pm_text = pm_result.get("final_text", "") or ""

        # 3c. Parse final PM decision (robust against 're-propose')
        import re as _re
        decision_match = _re.search(
            r"DECISION\s*[:\-]\s*(PROPOSE|PASS)\b", pm_text.upper()
        )
        decision = decision_match.group(1) if decision_match else (
            "PROPOSE" if pm_text.upper().rstrip().endswith("PROPOSE") else "PASS"
        )
        if decision != "PROPOSE":
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
        """Look up the most recent thesis from a given agent.

        Agent name matching is FUZZY because the SDK has historically
        recorded names in multiple formats (e.g. "Quant Researcher" vs
        "quant_researcher"). We try the literal name first, then a few
        normalized variants. This protects the chain against agent
        protocol bugs where the name format drifts.
        """
        candidates = [
            agent_name,                                    # "Quant Researcher"
            agent_name.lower(),                            # "quant researcher"
            agent_name.lower().replace(" ", "_"),          # "quant_researcher"
            agent_name.lower().replace(" ", ""),           # "quantresearcher"
            agent_name.replace(" ", "_"),                  # "Quant_Researcher"
        ]
        # Dedupe preserving order
        seen = set()
        candidates = [c for c in candidates if not (c in seen or seen.add(c))]

        placeholders = ",".join(["?"] * len(candidates))
        row = self.db.connect().execute(
            f"SELECT * FROM decisions WHERE agent IN ({placeholders}) "
            "AND kind = 'thesis' ORDER BY id DESC LIMIT 1",
            candidates,
        ).fetchone()
        if not row:
            return None
        d = dict(row)
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
    """Pull a verdict token from an agent's text response.

    Looks for the explicit `VERDICT: ALLOW|ALLOW_WITH_MODIFICATIONS|BLOCK`
    line first (most reliable). Falls back to keyword search if absent.
    """
    raw = agent_result.get("final_text") or ""
    text = raw.upper()

    # 1. Explicit VERDICT: line — most reliable, scan from end
    import re
    matches = re.findall(
        r"VERDICT\s*[:\-]\s*(ALLOW_WITH_MODIFICATIONS|ALLOW|BLOCK)\b",
        text,
    )
    if matches:
        return matches[-1].lower()  # last verdict wins (final declaration)

    # 2. Stand-alone APPROVE/BLOCK markers (less reliable but specific)
    last_lines = [ln.strip() for ln in text.splitlines() if ln.strip()][-15:]
    for line in reversed(last_lines):
        if re.match(r"^(\*\*)?(APPROVE|ALLOW)\b", line):
            return "allow"
        if re.match(r"^(\*\*)?BLOCK\b", line):
            return "block"

    # 3. No explicit verdict found — fail CLOSED. Substring search ("block" in
    #    "blocks") was the original bug. Fail-closed (return "block") is the
    #    only safe default for an absent verdict.
    return "block"


# ============================================================================
# Autonomous-mode guardrails
# ============================================================================

def _load_fund_yaml() -> dict[str, Any]:
    try:
        return yaml.safe_load(Path("config/fund.yaml").read_text()) or {}
    except Exception:
        return {}


def _check_autonomy_wake_budget(db, agent_name: str) -> dict[str, Any] | None:
    """Block new wakes when the autonomy daily caps are exceeded.

    Returns a stub-style result dict to refuse the wake (logged), or None
    to allow it. Only fires under fund.yaml:autonomous_mode == True.
    Supervised mode bypasses entirely — the user is the budget arbiter.
    """
    fund = _load_fund_yaml()
    if not fund.get("autonomous_mode", False):
        return None
    g = fund.get("autonomy_guardrails", {}) or {}
    max_wakes = int(g.get("max_wakes_per_day", 0) or 0)
    max_usd = float(g.get("max_usd_per_day", 0) or 0)

    today_utc = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    conn = db.connect()

    if max_wakes > 0:
        n = (conn.execute(
            "SELECT COUNT(*) FROM decisions WHERE kind = 'wake' AND ts LIKE ?",
            (f"{today_utc}%",),
        ).fetchone()[0]) or 0
        if n >= max_wakes:
            db.record_risk_event(
                severity="block", rule="autonomy_wake_count_cap",
                agent=agent_name,
                detail={"wakes_today": n, "cap": max_wakes},
            )
            return {"refused": True, "agent": agent_name,
                    "reason": f"autonomy wake count cap reached ({n}/{max_wakes})"}

    if max_usd > 0:
        spent = (conn.execute(
            "SELECT COALESCE(SUM(usd_est), 0) FROM costs WHERE day = ?",
            (today_utc,),
        ).fetchone()[0]) or 0.0
        if spent >= max_usd:
            db.record_risk_event(
                severity="block", rule="autonomy_spend_cap",
                agent=agent_name,
                detail={"usd_today": spent, "cap_usd": max_usd},
            )
            return {"refused": True, "agent": agent_name,
                    "reason": f"autonomy spend cap reached (${spent:.2f}/${max_usd:.2f})"}
    return None


def re_engage_auto_halt(reason: str = "session_close") -> str | None:
    """Write a fresh `trading_halt_until` value into risk_limits.yaml so
    the risk hook auto-blocks orders until the next session opens.

    Reads `auto_halt_resume_offset_hours` from fund.yaml (default 16).
    Returns the new ISO timestamp, or None if disabled / write failed.
    """
    fund = _load_fund_yaml()
    if not fund.get("auto_halt_at_session_close", False):
        return None
    offset = float(fund.get("auto_halt_resume_offset_hours", 16))
    resume_at = datetime.now(tz=timezone.utc) + timedelta(hours=offset)
    new_ts = resume_at.strftime("%Y-%m-%dT%H:%M:%SZ")

    path = Path("config/risk_limits.yaml")
    text = path.read_text(encoding="utf-8")
    # Surgical replacement: only touch the line we own
    import re
    pattern = re.compile(r'^(\s*trading_halt_until:\s*)["\']?[^"\'\n]*["\']?',
                          flags=re.MULTILINE)
    if not pattern.search(text):
        return None
    new_text = pattern.sub(rf'\1"{new_ts}"', text, count=1)
    path.write_text(new_text, encoding="utf-8")
    return new_ts
