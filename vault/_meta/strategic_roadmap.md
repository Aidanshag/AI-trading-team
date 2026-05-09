---
type: strategic_roadmap
created: 2026-05-09
purpose: North-star roadmap for the fund — preserves the strategic framing across sessions
status: active reference (update as priorities shift)
---

# Strategic roadmap — autonomous AI futures fund

This document is the north-star reference. Every Claude or Cowork session should read this on session start to understand the broader plan. Individual session work tracks against this.

## The fund's actual goal (revised 2026-05-09)

**Build a single reliable trading strategy that delivers 5-10% per year per account, then scale by REPLICATING across multiple Topstep accounts via copy-trading.**

This is NOT a "find the best alpha" problem. It's a "build reliable infrastructure that compounds across N accounts" problem. The two require different engineering decisions.

### Phase 1: Pass the Combine + validate single-account
**Where we are now (May 2026 → ~30 days post-pass)**

Goal: prove that ONE account with ONE strategy works in production matching backtest predictions.

Success criteria:
- Pass Combine ($3,000 cumulative profit, ≥5 days, no day > 50%, no DLL/TDD breach)
- 30 days of live data showing actual slippage, hit rate, expectancy match backtest predictions within ±20% tolerance
- No catastrophic operational failures (process crashes, OCO race losses, missed trades > 1 night)
- Documented per-cell live vs OOS variance so we know which cells actually work

Active strategy: `gap_fill_wide` on extended set (ZN/ZB/ZT/ZF/NG/6E), 26 cells.

### Phase 2: Build replication infrastructure
**Months 2-6 post-Combine pass**

Goal: support multiple Topstep accounts running the same validated strategy.

Prerequisites BEFORE this phase:
1. Phase 1 complete — single account validated
2. **Topstep policy research** — confirm copy-trading across accounts is allowed; understand simultaneous Combine rules; understand cross-account aggregation rules
3. Hard truth understood: 5 accounts running same strategy = perfectly correlated drawdowns

Build out:
- Multi-account orchestrator (`tools/account_orchestrator.py`) — one trader pattern, N account connections
- Per-account isolation (each has its own DLL/TDD tracking, halt independently)
- Fund-level dashboard (across all accounts)
- Risk parity sizing AT FUND LEVEL, not per-account
- Bootstrap funding plan: pass Combine 1 → use FA1 income to fund Combine 2 → etc.

### Phase 3: At-scale operation
**6-12 months out**

5-10 accounts running same strategy with possible decorrelation tweaks:
- Vary parameters per account (account A: gap_fill_wide; account B: pairs strategy; account C: multi-day swing)
- Stagger account activation (not all 5 firing at once)
- Monthly net P&L = N × per-account-P&L − N × subscriptions

Target outcome: 10 accounts × $50K × 7-10%/yr = $35-50k/yr net.

## What "good engineering" means at this fund

Re-anchored 2026-05-09 from prior optimization-driven framing:

1. **Reliability >> peak performance**. A 7%/yr strategy that NEVER blows up beats 30%/yr that occasionally gives back 50%.
2. **Replicability** — every component must be deterministic, copy-able to a fresh account, documentable.
3. **Friction-first design** — slippage, fees, subscriptions are FIRST inputs to every model, not afterthoughts. Backtest assumption defaults pessimistic; lowering it requires evidence.
4. **Measurement before optimization** — predictions explicit before deploying; actuals measured after; variance is the headline. (See `feedback_close_the_gap.md`.)
5. **Engineer for outlasting individuals** — every agent replaceable, every decision documentable, every metric reproducible.

## What's working in the current system

- Two-layer architecture (brain produces validated cells; knife executes) — keep
- Memory + vault for institutional knowledge — keep
- Safety floors (DLL, TDD, per-trade caps) — keep
- Multi-agent specialization with coordination — keep
- Auto-commit + git for total-recall persistence — keep
- Cell auto-promote (cowork-shipped 2026-05-08) — keep
- Slippage tracker (CLI-shipped 2026-05-08) — keep, this is core measurement
- Preflight as the daily session ritual — keep, expand

## What we'd do differently if starting fresh today

Not all of these are immediately doable, but the gap analysis matters:

| If starting fresh | Why | Doable when |
|---|---|---|
| **30 days of paper trading on real broker** before any strategy work | Catches slippage/latency/rejection patterns before deploying | Now: pivot Sunday's run to be primarily measurement-focused |
| **Tick-by-tick data** for backtests | Captures bid-ask spread, fill quality realistically | Use Topstep 1-min bars (free upgrade) + accumulated fills (better than synthetic tick) |
| **Multiple broker connections** from day 1 | Reduces single-broker risk; cross-validates fills | Phase 2 — broker_adapter pattern queued |
| **Real-time observability dashboard** | See divergence from prediction immediately | This week: text-based daily summary script (95% of value, 1% of effort) |
| **CI with slippage stress tests** | Catches "looks great, breaks under friction" before merge | Queued for cowork |
| **Engineering-function agents** vs role-played fund agents | Better ontology: data quality, statistical validator, devops, regime, research, capital allocator | Phase 2 — incremental rename + responsibility shift |
| **Risk parity sizing** | Portfolio-level risk targeting, not per-trade caps | Phase 2 — after multi-account orchestrator |
| **Multi-day swing on daily bars** | Slippage is microscopic relative to daily ranges | Research item this month |
| **Pairs / spread arbitrage** | One leg's slippage offsets the other | Research item this month |

## Hard truths embedded in the system design

1. **Most retail algo attempts fail.** The base rate is ugly. The system enforces discipline (fail-closed gates, sample-size requirements) so the human can't override.
2. **Edge × volume × low-friction**, not "smart strategies". Big-edge is rare; volume + low-friction is the path.
3. **5-10%/yr per account is great**. Anyone projecting more is fitting noise.
4. **Discipline beats optimization.** The system must enforce its own discipline; humans override at decision boundaries only.
5. **Capital is more important than alpha**. $500K total exposure × 7%/yr beats $5K × 50%/yr after the math.
6. **Combine economics are pessimistic.** TDD + DLL + consistency rule mean even profitable strategies have meaningful failure rates.

## Active priorities (as of 2026-05-09)

### Immediate (this weekend)
- Strategic roadmap doc (this file)
- Data strategy doc (`vault/_meta/data_strategy.md`)
- CLAUDE.md update with anchor principles
- 1-minute bar option in `tools/bar_fetcher.py`
- Daily summary script (`scripts/daily_summary.py`)

### Sunday onward
- Slippage measurement on first ZN/ZB/ZT/ZF/NG/6E fills
- Cell auto-promote starts learning from live data
- Daily summary captures variance per cell

### This week (cowork queue)
- Slippage-adjusted dollar param sweep (proper successor to today's R-multiple sweep)
- Snapshot extraction trim (trader < 600 lines target)
- Hypothesis-to-live pipeline doc

### This month (research projects)
- Pairs / spread strategy on treasury curve
- Multi-day swing strategy on daily bars
- Adversarial testing harness

### Next quarter (Phase 2 prep)
- Topstep multi-account policy research
- Broker adapter pattern (multi-account stub)
- Engineering-function agent reorganization

### Deferred until Phase 1 validates
- High-hit-rate strategy R&D (premature without validated foundation)
- New strategy `wide_session_drive` (premature)
- Real-time web dashboard (text version proves what to track first)

## How this document gets updated

Append-only at the bottom; section headers reused for current state. When priorities shift materially (like the 2026-05-09 multi-account framing), add a dated note at the top explaining the shift, then update relevant sections.

If you're a future Claude/Cowork session reading this: this is the north star. Specific work tracks against the plan above; deviations need a written reason here.
