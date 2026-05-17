---
type: workstream_root
workstream: ib
status: ACTIVE — DATA COLLECTION PHASE
opened: 2026-05-17
purpose: Knowledge base for the Interactive Brokers parallel workstream. Distinct from `vault/futures/` (Topstep) but can share strategies, research, lessons, and ideas.
---

# Interactive Brokers — workstream root

## The architecture (read this first)

This fund operates **two parallel broker workstreams**:

1. **Topstep (CURRENT priority)** — prop capital, Combine path, futures-only, strict third-party rules (DLL, TDD, 50% consistency). Lives in `vault/futures/`, `vault/_meta/`, `tools/projectx_client.py`, `scripts/live_trader.py`.
2. **Interactive Brokers (this directory)** — personal + invested capital, no third-party rules, wider instrument universe (stocks, options, FX, bonds, crypto, futures). Lives in `vault/ib/`, `tools/ib_client.py`, and (future) a separate `scripts/ib_trader.py`.

**The two workstreams are NOT migrations of each other.** They coexist. The Topstep account doesn't move to IB; IB doesn't replace Topstep.

## What they share

The two workstreams DO share:

- **Strategy library** (`tools/backtest/strategies.py`) — 36 strategies, brokerless code
- **Backtest engine** (`tools/backtest/engine.py`) — runs on bars, no broker dependency
- **Vault knowledge** — `vault/principles/`, `vault/lessons/`, `vault/research/`, `vault/_meta/principles.md`
- **Agent prompts** (`agents/`) — CIO, Risk Manager, PM, etc.
- **Universal walk-forward + shadow-discovery infrastructure** — strategy validation works on any bars

If a strategy proves edge in Topstep shadow data, IB might use it. If IB's 10-year multi-regime walk-forward surfaces a robust edge, Topstep should consider it. Knowledge flows both ways.

## What they DO NOT share

The two workstreams DO NOT share:

- **The trader process.** Topstep has `scripts/live_trader.py`; IB will have its own (built when user is ready). Different broker APIs, different risk rules, different position-sizing constraints, different fee structures.
- **Risk configuration.** Topstep's `risk_limits.yaml` encodes Combine rules. IB's risk config (future) is the user's personal money — fewer constraints, different stops, no per-day caps.
- **Live execution state.** Topstep's `state/strategy_validation.json:live_allowlist` is for Topstep. IB will have its own allowlist.
- **`feedback_topstep_vs_ib_separate_workstreams.md`** in memory captures this fully.

## Current status (2026-05-17)

- ✅ IB Gateway installed at `ibgateway/`, running in LIVE mode (account unfunded so effectively read-only)
- ✅ API enabled on port 4001, localhost-only
- ✅ `tools/ib_client.py` built — read-only methods (get_accounts, get_historical_bars, get_market_data_snapshot, search_contracts, get_positions)
- ✅ Connection verified — account `U25471643` reachable, account summary readable
- ⏳ **NEXT:** Phase 2 historical data backfill (queued for Sat 5/23 in `weekly_calendar.md`) — pull 10 years of bars on instruments we want to study

## Subdirectory layout

| Path | Purpose |
|---|---|
| `vault/ib/data/` | Data pulls — historical bar samples, snapshot logs, dataset metadata |
| `vault/ib/research/` | IB-specific research — multi-regime walk-forward, options strategies, longer-history validation |
| `vault/ib/instruments/` | Deep-dives on IB-only instruments (stocks, options, crypto, FX pairs) |
| `vault/ib/journal/` | IB trading journal (currently empty — populates when user enables IB trading) |

## Important DO NOT rules

1. **Do NOT use the Topstep trader to place IB orders.** The Topstep trader is hardwired to ProjectX. Cross-routing is forbidden.
2. **Do NOT migrate Topstep risk rules to IB.** IB has different rules; they'll be designed when the IB trader is built.
3. **Do NOT add IB-specific cells to `state/strategy_validation.json:live_allowlist`.** That file is for Topstep. IB will get its own.
4. **Until IB trader is built, IB is DATA ONLY.** No order placement code paths from this directory should reference `IBClient.place_order()` (which doesn't exist anyway — `tools/ib_client.py` is intentionally read-only).

## How knowledge flows between the two

When a finding in one workstream is relevant to the other:
- Cross-link with `[[]]` Markdown links
- Document the finding once in the workstream where it originated
- Mention applicability to the other workstream in the doc
- The vault auditor will catch broken cross-links daily

Example: if IB historical analysis confirms a strategy works across 10 years of multiple regimes, write the finding in `vault/ib/research/`, then link from the strategy's playbook in `vault/futures/playbooks/` if it applies there too.

## Open questions to revisit when IB trader is built

- What position-sizing model? (IB has way more flexibility than Topstep's $150 cap)
- What's the per-account starting capital plan?
- How do we deconflict Topstep + IB if the SAME signal fires (e.g., MNQ pivot_reversal long fires on Topstep AND IB has MNQ)? Probably independently — no shared P&L management.
- Data subscription budget — which exchanges to subscribe to? (Most cost $1.50-15/mo per exchange)
