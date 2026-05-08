# AI Trading Fund

Autonomous multi-agent futures trading fund built on the Claude Agent SDK. Trades CME futures and futures options through Topstep.

## Status

**Scaffolded, not live.** All broker/market-data/news tools are stubs that raise `NotImplementedError`. No order can reach a real venue until you drop in credentials and wire the corresponding client. This is intentional — the risk surface demands a careful review before anything goes live.

## Architecture

```
runtime/        event-driven orchestrator (market-hours scheduler)
agents/         system prompts — CIO, PM, Risk Manager, Options Risk,
                Execution Trader, Compliance, and sector analysts
tools/          MCP servers — Topstep (ProjectX), market data, news,
                vault (Obsidian), state store
hooks/          PreToolUse risk gate, audit logger, cost tracker
state/          SQLite — positions, orders, P&L, risk metrics, audit log
vault/          Obsidian brain — theses, playbooks, journals, agent notes
config/         YAML — risk limits, model assignments, Topstep rules, symbols
logs/           append-only JSONL of agent reasoning and decisions
```

Two stores by design:

- **SQLite (`state/`)** — operational, structured, atomic. Positions, orders,
  P&L, risk metrics, audit log. Single source of truth for "what are we
  holding right now."
- **Obsidian vault (`vault/`)** — qualitative knowledge. Theses, playbooks,
  daily journals, post-trade reviews, lessons learned. Human-readable and
  human-editable. Agents read it on wake and append notes on decisions.

## Safety model

Three layers, in this order:

1. **Prompt-level rules** in each agent's system prompt (soft)
2. **Risk Manager agent** reviews each proposed order (peer review)
3. **PreToolUse risk hook** (`hooks/risk_gate.py`) — **hard gate** that
   blocks any order-placing tool call if it violates:
   - No naked short positions (no outright short futures; no short options
     without defined-risk cover)
   - Daily loss limit (config-driven; also enforces Topstep Combine rule)
   - Trailing drawdown (Topstep Combine rule)
   - Max contracts per symbol and aggregate (config-driven)
   - Consistency rule (Topstep: no single day > 50% of total profit)
   - Market-session check (no orders outside session)

The hook is the last line of defense. Prompts can be ignored; hooks cannot.

**Every order proposal — without exception — passes through the Risk Manager
agent before the execution trader is allowed to call the broker tool.**
The PM does not hand orders directly to execution. The orchestrator enforces
this routing; the risk manager either approves, approves-with-modifications,
or blocks. Options orders additionally require the Options Risk agent's
approval. The PreToolUse hook is the final check after both.

## Setup

```bash
# 1. Python 3.11+
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install
pip install -e ".[dev]"

# 3. Config
cp .env.example .env         # fill in keys
# review and edit config/risk_limits.yaml — these are YOUR limits

# 4. Initialize state store
python -m state.db init

# 5. Dry-run the orchestrator (paper mode by default, stubs still raise)
fund
```

## What you need to do before first run

- Fill `.env` (at minimum `ANTHROPIC_API_KEY`)
- Fill `config/risk_limits.yaml` with YOUR limits (the file ships with sane
  placeholders clearly marked `# TODO user:`)
- Implement the Topstep client in `tools/topstep.py` once you have ProjectX
  credentials — the MCP tool interface is already defined
- Pick and implement at least one market-data source in
  `tools/market_data.py`
- Review `agents/risk_manager.md` and `agents/options_risk.md`

## Agents

Each agent is a system prompt plus a model assignment. See `agents/README.md`
for the full roster and their responsibilities.

Model defaults (tunable in `config/models.yaml`):

- **Haiku 4.5** for routine polling, news triage, playbook lookup, journal
  entries, and order formatting
- **Sonnet 4.6** for analyst research, position sizing, post-trade reviews
- **Opus 4.7** reserved for Risk Manager, Options Risk, and novel
  market-regime reasoning — escalation is explicit

## Conventions

- All times are UTC in the DB; displayed in `America/Chicago` (CME time)
- Every agent decision goes to the append-only audit log with rationale
- The risk hook is the only place order-blocking logic lives — no duplicates
- No network calls inside the risk hook path; all required state must be
  in SQLite before the hook runs

## Roadmap

1. Wire ProjectX, smoke-test on Topstep demo
2. Plug in one market-data feed + one news feed
3. First paper run with a single analyst (energies) and the full risk stack
4. Expand analyst roster
5. Topstep Combine attempt
6. Funded account
