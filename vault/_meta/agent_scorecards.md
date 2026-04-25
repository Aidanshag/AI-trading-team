---
type: scorecards
updated: 2026-04-23
rolling_window: 100
---

# Agent scorecards

CIO-maintained weekly snapshot of every trading-originating agent's performance. Rolling 100-trade window. First meaningful update will appear once any agent has closed ≥ 20 trades (shadow + real, combined).

See `config/agent_performance.yaml` for the thresholds. See [[cio|CIO standing prompt]] for the process.

## Current tiering (seed — no data yet)

| Agent | Tier | Trades | Win rate | Avg R | Process | Weeks below | Notes |
|---|---|---|---|---|---|---|---|
| Energies Analyst    | — | 0 | — | — | — | 0 | insufficient data |
| Metals Analyst      | — | 0 | — | — | — | 0 | insufficient data |
| Ags Analyst         | — | 0 | — | — | — | 0 | insufficient data |
| Rates Analyst       | — | 0 | — | — | — | 0 | insufficient data |
| FX Futures Analyst  | — | 0 | — | — | — | 0 | insufficient data |
| Index/Macro Analyst | — | 0 | — | — | — | 0 | insufficient data |
| Growth/Tech Analyst (eq, learning) | — | 0 | — | — | — | 0 | equity desk idle |
| Defensive Analyst (eq, learning)   | — | 0 | — | — | — | 0 | equity desk idle |
| Cyclicals Analyst (eq, learning)   | — | 0 | — | — | — | 0 | equity desk idle |
| Financials Analyst (eq, learning)  | — | 0 | — | — | — | 0 | equity desk idle |
| Single-Name Options (eq, learning) | — | 0 | — | — | — | 0 | equity desk idle |

## Tier definitions

- **Top**: win rate > 55%, avg R > 1.5 on rolling-100. Normal wake + 1.2× sizing boost.
- **Standard**: default — meeting thresholds.
- **Watch**: win rate < 45% or avg R < 1.0 on rolling-100. Half-sizing on their proposals; keep waking; flag in weekly review.
- **Bench**: under Watch thresholds for 3+ consecutive weeks. Routine wakes paused; idle-work backlog only. Surfaced to the user with recommendation (keep / rewrite / retire).

## History

*(CIO appends weekly snapshot deltas here)*
