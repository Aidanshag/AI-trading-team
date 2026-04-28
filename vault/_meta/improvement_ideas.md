---
type: meta
status: active
updated: 2026-04-25
---

# Improvement ideas — prioritized

Concrete ideas to improve hit rate, intelligence, and operational quality. Ranked by impact ÷ effort. Top 10 first; full backlog below.

## TOP 10 (do these first)

### 1. Walk-forward backtest validation
**Problem**: our 1-year backtest may be overfit to current regime. The 2025-2026 commodity bull worked for trend-follow; same strategies on 2017-2019 might be flat or losing.
**Solution**: when FirstRate Data ($100 one-time) is available, re-run all 5 strategies on rolling 2-year windows back to 2010. Strategies that work in only ONE regime are unreliable.
**Impact**: prevents trading dead strategies. Massive.
**Effort**: medium — needs data + harness extension.

### 2. Per-agent calibration tracking with bench tier promotion
**Problem**: we track agent hit rates conceptually but don't actually demote underperformers.
**Solution**: Compliance computes rolling-100-trade win rate per analyst weekly. Auto-flag anyone < 40% as Watch tier (PM cuts sizing 50%). 3 weeks Watch → Bench (no wakes). User reviews and decides retire/rewrite.
**Impact**: enforces meritocracy across the team.
**Effort**: low — Compliance prompt + a SQL query.

### 3. Real-time fund metrics dashboard
**Problem**: status.ps1 is OK but you have to run it. No "at-a-glance" daily snapshot.
**Solution**: web-based or Rich-CLI dashboard that auto-refreshes: balance, day P&L, open positions, working orders, today's cost, agent activity timeline, current regime read, recent risk events. Single pane.
**Impact**: situational awareness compounds.
**Effort**: medium — `rich` package can render a live dashboard in ~200 lines.

### 4. Drawdown-adaptive sizing with auto-cooldown
**Problem**: defensive ladder triggers at $-150/$-300/$-500 by ladder. But the ladder is *prompt-level* discipline. Need automatic enforcement at the *risk hook* level.
**Solution**: extend `hooks/risk_gate.py` to read current day P&L from snapshot, automatically apply tighter caps below thresholds. Currently we describe the ladder; this enforces it.
**Impact**: bulletproof drawdown protection.
**Effort**: low — extend existing `_check_combine_defense()` (write it).

### 5. Daily pre-market stress test cron
**Problem**: stress_test.py exists; no one runs it automatically.
**Solution**: scheduler emits `STRESS_TEST_DUE` event at 06:00 CT daily. Orchestrator runs `tools.stress_test.run_stress()`. If any scenario breaches internal DLL ceiling, wake CIO + Risk Manager with the report.
**Impact**: catches vulnerable books before they break.
**Effort**: low — 30 lines wiring.

### 6. Trade journal enforcement with auto-flag
**Problem**: post-trade reviews are theoretical; nobody enforces.
**Solution**: Compliance scans closed trades from last 24h, flags any without a recorded `post_trade_review` decision. Daily Compliance summary lists missing reviews. Cumulative misses → CIO wake.
**Impact**: forces the post-trade learning loop that real desks use.
**Effort**: low — Compliance prompt + a SQL query.

### 7. Strategy decay detection (auto-suspend)
**Problem**: a strategy can stop working and we won't notice for months.
**Solution**: Quant Researcher computes rolling-100 hit rate per strategy weekly. If hit rate falls 30% below documented expectation, auto-suspend (PM stops accepting new theses citing that strategy until manually reviewed).
**Impact**: stops bleeding from dead strategies.
**Effort**: low — Quant Researcher prompt + a SQL query + a config flag per strategy.

### 8. Cross-agent ensemble bonus for high-conviction trades
**Problem**: a single analyst's view is fragile. Multiple specialists agreeing is much stronger signal.
**Solution**: when 3+ specialists agree (e.g., Energies analyst + Macro Strategist + Flow Analyst all bullish on /CL), PM applies a +50% sizing multiplier (within risk caps). When only one specialist is positive → standard sizing. When specialists conflict → reduced sizing or pass.
**Impact**: leans into multi-signal edges and away from single-source bets.
**Effort**: medium — PM prompt + decision-table sweep code.

### 9. Anti-portfolio tracker
**Problem**: we know what we trade. We don't track what we deliberately passed. Missing this signal — what would have happened?
**Solution**: every "PM passed" decision logs symbol + thesis + rationale. Compliance scores them weekly: how would they have done if taken?  Tells us if we're being too cautious (lots of passed winners) or correctly cautious.
**Impact**: calibrates the PM's pass-rate.
**Effort**: low — already logging passes; need scoring code.

### 10. Live news RSS ingester
**Problem**: news tool stubs out RSS; agents can't actually fetch headlines.
**Solution**: implement `tools/news.py:search_news` against the RSS feeds in `config/news_sources.yaml`. Return last N headlines matching keyword + symbol filter. No API key needed. Free.
**Impact**: agents get real news context without paid subscriptions.
**Effort**: medium — ~150 lines using `feedparser` + httpx.

---

## FULL BACKLOG (pick from here as time allows)

### Strategy expansion
- Implement EIA-surprise event-driven backtest (event_strategies.py stub exists)
- WASDE-surprise grain backtest
- FOMC-day index reaction backtest
- Crush spread backtest (ZS / ZL+ZM)
- Gold-silver ratio mean reversion backtest
- Brent-WTI arb backtest

### Risk infrastructure
- Real-time exposure dashboard (sector betas, correlations)
- Liquidity-aware sizing (% of 20-day ADV cap)
- Pair-correlation breakdown alert
- Margin headroom monitoring
- Pre-mortem requirement on every Risk approval

### Agent improvements
- Per-pair disagreement tracking (when X disagrees with Y, who's right more often?)
- Quarterly agent retrospective auto-generated from journal
- Coverage rotation (analysts swap sectors monthly to break bias)
- Adversarial backtest (Red Team challenge integrated into backtest pass criteria)

### Operations
- Database daily backup (state/fund.db → backup/)
- Slippage model recalibration (compare modeled vs actual fills weekly)
- Position revalidation cron (every 24h, analyst re-approves their open thesis)
- Margin call simulation
- Outage recovery runbook

### Tools
- Microstructure analyzer (order book replay, market impact)
- NLP news sentiment scorer (free, can use HuggingFace local)
- Economic calendar tracker (FRED + USDA + EIA RSS feeds)
- Fund metrics export (snapshot to CSV/PDF for review)

### Brain expansion (Fund Engineer continues)
- All remaining product deep-dives
- Event playbooks: FOMC, CPI, JOLTS, ECB, BoE, BOJ, RBA, USDA, EIA Wednesday
- Symbol-specific seasonal patterns library
- Post-trade review templates

### Quality processes
- Pre-mortem on every position (Risk Manager imagines the worst case)
- Lessons-learned → playbook → hard rule promotion path
- Strategy deprecation policy (auto-retire after N weeks of decay)
- Coverage rotation (sector rotation monthly to break confirmation bias)

### Meta
- Trading philosophy doc (what are our beliefs?)
- Anti-portfolio with weekly scoring (what we passed)
- Quarterly retrospective generated from journal
- "Mentor" agent that connects to external wisdom (Druckenmiller frameworks)

## How to use this list

When you (or Claude) have engineering time, pick from TOP 10 first. After all 10 are done, dip into the backlog by category — pick the category that addresses the current weakness.

The TOP 10 alone could occupy 10-20 hours of engineering work, but each one ships an immediate improvement. Don't try to do them all at once — one per session is plenty.
