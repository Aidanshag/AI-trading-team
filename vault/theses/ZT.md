---
type: thesis
symbol: ZT
sector: rates
conviction: high
direction: intraday (long + short cells both validated)
timeframe: intraday
strategy: gap_fill_wide
status: STANDING_LIVE
primary_driver: overnight gap mean-reversion on short-end Treasury
related: [[ZN]], [[ZB]], [[ZF]]
updated: 2026-05-09T15:00:00Z
author: Cowork (Claude)
---

# [[ZT]] — gap_fill_wide standing edge (strongest signal in the universe)

> Standing live edge on the 2Y Treasury future. Same `gap_fill_wide` mechanic as [[ZN]] (≥1.5×ATR gap, 1.5×ATR stop, 3-tick floor), applied to the short end of the curve. **Tier 3 parent-strategy walk-forward shows ZT is statistically the strongest gap_fill signal across the entire validated universe** — OOS hit 68%, E=+1.41R, t=+11.76 on n=333. If you only had to pick one cell to trade, ZT Asian is the one. Five cells live as of 2026-05-08 promotion.

## Strategy variant — gap_fill → gap_fill_wide (2026-05-08)

Same variant change as ZN: live code path is `gap_fill_wide`, OOS evidence cited below is from parent `gap_fill`. Notable for ZT: the parked param sweep (`vault/research/param_sweeps/gap_fill_2026-05-08_2304.md`) found ZT at `min_gap_atr=1.5, rr_target=1.0` produced OOS E=**+2.80R**, t=+7.79 on n=55 — the strongest wide-variant signal in the curve. This is the wide-variant params, on the short end, in R-multiples; dollar-metric verification is pending the slippage-adjusted re-sweep.

## Thesis

- **Mechanic (live: `gap_fill_wide`).** When ZT opens with `|open − prior_close| ≥ 1.5 × ATR(14)`, fade the gap back toward prior close. Stop = entry ± 1.5 × ATR (with 3-tick hard floor); target = prior close; `rr_target = 1.5`. Code: `tools/backtest/strategies.py:gap_fill_wide`. Parent: `gap_fill`.
- **Why ZT is the cleanest expression.** The 2Y is the most direct read on the Fed funds path over the next 12–18 months. Overnight gaps in ZT are almost always rate-expectation flow (Fed-funds futures repricing, money-market hedging) rather than directional information — and that flow tends to revert to the prior session's anchor once US-hours liquidity arrives. Cleaner microstructure than the long end (which has duration-driven repricing that can extend gaps).
- **Walk-forward evidence (Tier 3, 2026-05-05).** OOS E=+1.41R, t=+11.76, n=333, hit-rate=68.2%. Source: `vault/research/backtests/2026-05-05_2207_tier3_gapfill_extensions.md`. Also confirmed in `vault/research/validation/promotion_log.md` 2026-05-06 entries.
- **Live deployment (allowlist generated 2026-05-08T16:35:49Z).** Five ZT cells active in `state/strategy_validation.json:live_allowlist`:
  - `gap_fill_wide | ZT | Asian | long` — parent OOS E=+1.19R, t=+7.87, n=121
  - `gap_fill_wide | ZT | Asian | short` — parent OOS E=+1.54R, t=+8.63, n=110
  - `gap_fill_wide | ZT | London | long` — parent OOS E=+0.67R, t=+2.49, n=29
  - `gap_fill_wide | ZT | London | short` — parent OOS E=+2.24R, t=+2.97, n=29
  - `gap_fill_wide | ZT | PostClose | long` (added in 2026-05-08 promotion)
  - Sessions in ET: Asian = 20:00–04:00, London = 04:00–09:30, PostClose = 16:00–20:00.
  - Note: ZT PostClose short is NOT in the live allowlist — only the long side cleared the 2026-05-08 promotion bar.
- **Per-trade economics (cleanest in the curve).** Tick = $15.625. Typical 5-tick stop = $78. Typical 7-tick reward = $109. Round-trip fee ~$3. Reward/fee = ~36× — far above the 3× floor. The user's `focus_universe.yaml` notes call this out: *"cleanest economics in the curve."*

## What would kill it

- **Fed-pivot communication shift.** When the Fed signals a turn (hike-pause, pause-cut, cut-pause), the 2Y gaps for days. The fade trade becomes negative-EV because the gap *is* the new information. The high-impact blackout gate handles the print itself; the days that follow need manual override or thesis revision.
- **Money-market dislocations.** SOFR squeezes, repo strain, year-end funding stress — these all show up first in the 2Y. Watch the SOFR-IORB spread; if it's widening, ZT gap_fill is unsafe regardless of the daily validator's verdict.
- **Quarter-end roll dynamics.** ZT has more relative basis activity than ZN because the deliverable basket is narrower. Last 2 weeks of contract life: shadow-only.
- **Liquidity regime change in Asian session.** Same warning as ZN — verify thin-tape gate state before each session.

## Correlation notes

- **Inside the duration basket.** ZT is the lowest-DV01 of the four ([[ZN]] · [[ZB]] · [[ZT]] · [[ZF]]). A 1-tick move on ZT is only $15.625, much smaller than ZB's $31.25 — ZT is naturally smaller in $ terms even at the same contract count.
- **2s10s curve correlation.** ZT and ZN move together but with different sensitivities; in steepening regimes ZT outperforms (rallies more on dovish news, sells off less on hawkish). The gap_fill signal does not care about curve direction — both long and short cells are validated — so this is informational, not directional.
- **Short end vs long end.** ZT and ZB can diverge in regimes where the Fed is cutting front-end while term premium rises long-end. Don't assume ZT and ZB gap_fill signals will fire in the same direction.

## Sizing

- 1 contract per fire. ZT's small per-tick value means even 2-contract sizing is well inside the $250 cap; consider sizing to 2 once ZT cells have ≥30 live observations and the live-vs-OOS gap stays positive. Until then, 1 contract.
- Stacking with other curve cells of the same direction = one trade for the duration basket cap.

## Standing status

Active. **Highest-priority cell to monitor for live performance** — given its statistical strength, decay here would be the most informative signal that something has shifted in the gap-fill regime broadly. If ZT goes red live while ZN/ZB/ZF stay green, it's a 2Y-specific issue (rate-expectation regime change). If all four turn red together, it's a structural shift in the gap-fill mechanic.

## Related

- Strategy code: `tools/backtest/strategies.py:gap_fill_wide` (live), `gap_fill` (parent)
- Param sweep findings: `vault/research/param_sweeps/gap_fill_2026-05-08_2304.md` (parked — slippage-blind; dollar-metric re-sweep pending)
- Live allowlist: `state/strategy_validation.json:live_allowlist`
- Tier 3 walk-forward: `vault/research/backtests/2026-05-05_2207_tier3_gapfill_extensions.md`
- Curve siblings: [[ZN]] · [[ZB]] · [[ZF]]
