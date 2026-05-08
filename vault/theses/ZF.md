---
type: thesis
symbol: ZF
sector: rates
conviction: high
direction: intraday (long + short cells both validated)
timeframe: intraday
strategy: gap_fill
status: STANDING_LIVE
primary_driver: overnight gap mean-reversion on belly Treasury
related: [[ZN]], [[ZT]], [[ZB]]
updated: 2026-05-06T23:30:00Z
author: Cowork (Claude)
---

# [[ZF]] — gap_fill standing edge (5Y belly)

> Standing live edge on the 5Y Treasury Note future. Same gap_fill mechanic as [[ZN]]. ZF was added to the focus universe 2026-05-06 (was blocking 3 validated cells from scanning). OOS E=+1.16R, t=+7.95, n=239.

## Thesis

- **Mechanic.** Identical to [[ZN]], [[ZT]], [[ZB]]. Code: `tools/backtest/strategies.py:gap_fill`.
- **Why ZF.** The 5Y is the curve's middle — sensitive to both Fed-path (like [[ZT]]) and term-premium (like [[ZB]]). Overnight gaps in ZF are mostly basis-trade and curve-spread flow rather than directional information; the same fade dynamic as the rest of the curve.
- **Walk-forward evidence (Tier 3, 2026-05-05).** OOS E=+1.16R, t=+7.95, n=239. Source: `vault/research/backtests/2026-05-05_2207_tier3_gapfill_extensions.md`.
- **Live deployment (locked 2026-05-06 22:24 UTC).** Three ZF cells active in `state/strategy_validation.json:live_allowlist`:
  - `gap_fill | ZF | Asian | long` — OOS E=+0.81R, t=+4.66, n=95
  - `gap_fill | ZF | Asian | short` — OOS E=+1.06R, t=+5.59, n=89
  - `gap_fill | ZF | PostClose | short` — OOS E=+1.29R, t=+3.17, n=26 (added 2026-05-06)
- **Per-trade economics.** Tick = $15.625 (same as ZN/ZT). 5-tick stop = $78. Reward/fee ratio comparable to ZT.
- **Note on focus-universe gap.** Per the user's note in `config/focus_universe.yaml`: ZF was in the strategy-validation user filter but missing from the focus universe until 2026-05-06, blocking three validated cells from even scanning. Worth a periodic reconciliation check between the focus universe and the live allowlist to make sure no validated cells are silently shadowed.

## What would kill it

- **Belly-driven curve flatteners/steepeners.** When the curve is repricing aggressively (e.g., 2s5s steepening on cut expectations), ZF gaps reflect new rate-path information and don't fade. Same kill condition as ZT.
- **Same operational kills as the other curve members** — broker stop failure, thin tape, roll noise, refunding-week drift.

## Correlation notes

- **Inside the duration basket.** Same DV01 family as ZT (slightly higher per-contract). Long ZF + long ZN + long ZB = single duration trade.
- **Smallest cell count of the four** (3 vs ZN/ZT 4 and ZB 5). London cells are not yet validated for ZF — the train and OOS samples were too small in the Tier 3 sweep.

## Sizing

- 1 contract per fire. The PostClose short cell has the smallest n (26) — keep at 1 contract until it accumulates ≥30 live observations and the live-vs-OOS gap is positive.

## Standing status

Active. Newest in the live universe; watch the PostClose short cell for early decay since it has the lowest sample-size confidence.

## Related

- Strategy code: `tools/backtest/strategies.py:gap_fill`
- Live allowlist: `state/strategy_validation.json:live_allowlist`
- Tier 3 walk-forward: `vault/research/backtests/2026-05-05_2207_tier3_gapfill_extensions.md`
- Focus universe addition: `config/focus_universe.yaml` (note dated 2026-05-06)
- Curve siblings: [[ZN]] · [[ZT]] · [[ZB]]
