---
name: All data sources auto-refresh daily
description: User authorized 2026-05-06 to ensure every data source that informs trading is refreshed daily. The full refresh pipeline runs in preflight before each trading session.
type: feedback
originSessionId: 66111817-55d9-4a4c-b2ae-864b18030e59
---
User directive 2026-05-06: "anything involving data, information, and
incoming data should be updated daily. We want the most up-to-date
information."

## Daily refresh pipeline (runs in `scripts/preflight.py`)

Preflight runs at 06:30 ET Mon-Fri via `FundAutoTraderDaily` Windows
scheduled task. Each step refreshes a data source:

| Step | Refreshes | Source |
|---|---|---|
| 1-8 | Standard preflight checks | env, broker, halt, focus universe, snapshot, tests, risk gate, agent CLI |
| **9** | **OOS walk-forward validation** | `daily_strategy_validation.py` — re-fetches 60d 5m bars per symbol, runs walk-forward across all 24 strategies × 14 symbols × 4 sessions × 2 sides; updates `state/strategy_validation.json` with cell statuses (live/shadow), promotions, demotions |
| **10** | **Shadow trade outcomes** | `shadow_trade_resolver.py` — replays each unresolved shadow against subsequent yfinance bars, marks win/loss/expired |
| **11** | **Live R-multiple tracker** | `live_vs_oos_tracker.py` — computes per-cell live R-multiples from `decisions` + `account_snapshots` deltas, compares to OOS predictions, flags underperforming cells |
| **12** | **Lessons auto-promotion** | `auto_promote_lessons.py` — graduates lessons ADVISORY → PATTERN → RULE based on accumulated evidence |

## Always-on (continuous, not daily)

- `account_snapshots` — written every scan (5-15 min cadence)
- `risk_events` — every gate check
- `decisions` — every trigger (theses)
- `orders` — every order placement
- `shadow_trades` — every unvalidated cell trigger
- Economic calendar — auto-regenerated when stale (>6h old) at scan start

## Manually maintained (deliberately not auto-updated)

- `CLAUDE.md`, `agents/*.md`, `vault/_meta/*.md` — narrative documentation
  authored by user or by Claude during sessions. Updated when context
  changes, not on a daily cron.
- `config/risk_limits.yaml`, `config/fund.yaml`, `config/focus_universe.yaml`
  — risk policy, deliberately under user control.
- `vault/lessons/` — written manually or via auto-promote.

## When to add a NEW daily refresh

A new daily refresh is warranted when:
1. The data informs trading decisions
2. The source can become stale within 24h without notice
3. The refresh is automatable (no user input required)

When you spot something that fits these criteria, add it to preflight
as a new `[step N]` block, write a brief block-comment, ensure it
gracefully degrades (warn + continue, never block trading).

## How to verify daily refresh is working

After preflight runs, check:
- `state/strategy_validation.json` — `live_allowlist_generated_at` timestamp
- `vault/research/validation/<date>_daily_validation.md` — fresh report
- `vault/research/live_vs_oos/<date>_live_r_comparison.md` — fresh report
- Latest commit in git log should be auto-commit from previous Stop

If any of those is older than 24h, a refresh step has silently failed.
The preflight is fail-soft on each step (warn + continue), so it's
possible for the trader to start without fresh data. The risk_config_drift
audit catches the most dangerous case (safety floors disabled).
