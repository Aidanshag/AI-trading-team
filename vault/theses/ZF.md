---
type: thesis
symbol: ZF
sector: rates
conviction: high
direction: intraday (long + short cells both validated)
timeframe: intraday
strategy: gap_fill_wide
status: STANDING_LIVE
primary_driver: overnight gap mean-reversion on belly Treasury
related: [[ZN]], [[ZT]], [[ZB]]
updated: 2026-05-09T15:00:00Z
author: Cowork (Claude)
---

# [[ZF]] — gap_fill_wide standing edge (5Y belly)

> Standing live edge on the 5Y Treasury Note future. Same `gap_fill_wide` mechanic as [[ZN]] (≥1.5×ATR gap, 1.5×ATR stop, 3-tick floor). ZF was added to the focus universe 2026-05-06 (was blocking 3 validated cells from scanning). Parent-strategy OOS E=+1.16R, t=+7.95, n=239. Smallest cell count of the curve (3).

## Strategy variant — gap_fill → gap_fill_wide (2026-05-08)

Same variant change as ZN: live code path is `gap_fill_wide`, OOS evidence cited below is from parent `gap_fill`. ZF has the same tick value as ZN/ZT ($15.625), so the wide-stop variant produces ~$47 minimum stops (vs ~$15 worst-case under the original gap_fill). Sub-tick stops were the primary failure mode the wide variant addresses.

## Thesis

- **Mechanic (live: `gap_fill_wide`).** Identical to [[ZN]], [[ZT]], [[ZB]]: ≥1.5×ATR gap fires; stop = 1.5×ATR with 3-tick floor; target = prior close; rr_target=1.5. Code: `tools/backtest/strategies.py:gap_fill_wide`.
- **Why ZF.** The 5Y is the curve's middle — sensitive to both Fed-path (like [[ZT]]) and term-premium (like [[ZB]]). Overnight gaps in ZF are mostly basis-trade and curve-spread flow rather than directional information; the same fade dynamic as the rest of the curve.
- **Walk-forward evidence (Tier 3, 2026-05-05).** OOS E=+1.16R, t=+7.95, n=239. Source: `vault/research/backtests/2026-05-05_2207_tier3_gapfill_extensions.md`.
- **Live deployment (allowlist generated 2026-05-08T16:35:49Z).** Three ZF cells active in `state/strategy_validation.json:live_allowlist`:
  - `gap_fill_wide | ZF | Asian | long` — parent OOS E=+0.81R, t=+4.66, n=95
  - `gap_fill_wide | ZF | Asian | short` — parent OOS E=+1.06R, t=+5.59, n=89
  - `gap_fill_wide | ZF | PostClose | short` — parent OOS E=+1.29R, t=+3.17, n=26
  - Note: ZF London cells did NOT make the allowlist (insufficient parent-strategy n). PostClose long is also absent — only the short side cleared the bar.
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

- Strategy code: `tools/backtest/strategies.py:gap_fill_wide` (live), `gap_fill` (parent)
- Live allowlist: `state/strategy_validation.json:live_allowlist`
- Tier 3 walk-forward: `vault/research/backtests/2026-05-05_2207_tier3_gapfill_extensions.md`
- Focus universe addition: `config/focus_universe.yaml` (note dated 2026-05-06)
- Curve siblings: [[ZN]] · [[ZT]] · [[ZB]]
