---
name: feedback-topstep-vs-ib-separate-workstreams
description: "Topstep (fund/Combine, prop capital path) and Interactive Brokers (personal/invested capital) are SEPARATE workstreams. IB is post-Combine, not a substitute or migration path. They coexist."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 01330334-e95e-4182-b81f-d9cbbd00f2f1
---

User strategic directive 2026-05-15: Topstep and Interactive Brokers are two **distinct, parallel** workstreams — not interchangeable, not a migration path.

**Topstep (CURRENT PRIORITY):**
- Prop-capital path. $50K Combine → funded account → XFA → multi-account scaling
- Strict risk rules: DLL, TDD, consistency, profit targets, max-trade caps
- Everything in this codebase currently routes through Topstep / ProjectX
- Goal: pass Combine, sustain XFA, scale via N accounts
- Decision rules in `risk_limits.yaml`, `current_goal.md`, `strategic_roadmap.md`

**Interactive Brokers (FUTURE / PARALLEL):**
- Personal capital + invested capital (the user's own money / future investor capital)
- NO third-party prop rules — full discretion on stops, position sizes, drawdowns
- Wider instrument universe (stocks, options, FX, bonds, crypto vs Topstep's futures-only)
- Different broker, different account, different code path (would need new `tools/ib_client.py`)
- **NOT yet active.** Topstep Combine must pass FIRST.

**How they coexist (post-Combine state):**
- BOTH brokers running simultaneously
- Topstep accounts: copy-trading the validated strategy at micro contracts under prop rules
- IB account: discretionary + automated trading on personal capital with the same brain's signals but DIFFERENT risk parameters
- Strategy library can be SHARED, but per-account exit rules / position sizing / risk caps differ
- Each broker has its own data feed, its own monitoring, its own sentinel rules

**How to apply:**
- Until Combine passes: any IB work is research-only, not deployed
- Don't suggest "moving Topstep work to IB" or "trading the same on both" — they have different rule sets
- When IB is eventually wired, it gets its own client module, its own risk config, its own sentinel checks
- The `live_allowlist` may need a `broker:` field to route signals to the right execution layer (or two separate allowlists)
- Multi-account scaling on Topstep (strategic_roadmap Phase 2) is DIFFERENT from IB activation — those are independent expansions
- Topstep symbols (52 futures) are a subset of IB's universe; equities desk in this repo would route IB-only

## What they SHARE (added 2026-05-17 per user direction)

The two workstreams can share IDEAS / DATA / RESEARCH / SKILLS / KNOWLEDGE — they improve each other through cross-pollination. Specifically shared:
- Strategy library (`tools/backtest/strategies.py`) — strategies are brokerless code
- Backtest engine (`tools/backtest/engine.py`)
- Vault: `vault/principles/`, `vault/lessons/`, `vault/research/`, `vault/_meta/principles.md`
- Agent prompts (`agents/`)
- Universal walk-forward + shadow-discovery infrastructure

What they DO NOT share — the **trader process**. Topstep has `scripts/live_trader.py` + `tools/projectx_client.py`. IB will get its own `scripts/ib_trader.py` (NOT YET BUILT — user builds at appropriate time). Cross-routing is forbidden.

## Vault structure for the two workstreams

- `vault/futures/` — Topstep-only knowledge (Combine rules, futures-specific playbooks, journal)
- `vault/ib/` — IB-only knowledge (data pulls, IB-specific research, instrument deep-dives, dormant journal)
- `vault/_meta/`, `vault/principles/`, `vault/lessons/`, `vault/research/` — shared cross-workstream knowledge

## Implementation status as of 2026-05-17

- ✅ IB Gateway installed at `ibgateway/`, LIVE mode, API on port 4001
- ✅ `tools/ib_client.py` built — read-only methods only (DATA collection)
- ✅ Connection verified — account `U25471643` reachable
- ✅ `vault/ib/` directory structure created with READMEs
- ⏳ NEXT: IB Phase 2 historical backfill (Sat 5/23 per `vault/_meta/weekly_calendar.md`) — pull 10yr of bars for multi-regime walk-forward
- ⏳ FUTURE: IB trader (`scripts/ib_trader.py`) — user-built at appropriate time

Related: [[feedback-multi-account-scaling]] (Topstep N-account strategy — separate from IB), [[project-hedge-fund]] (overall fund structure), [[reference-topstep-rules]] (Topstep-specific rules that don't apply to IB).
