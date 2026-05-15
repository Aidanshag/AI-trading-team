---
type: analysis
date: 2026-05-15
phase: 1 (walk-forward) of RTH expansion plan
symbols_evaluated: 8
strategies_evaluated: 27
cells_total: 295
graduation_eligible: 25
runtime_seconds: 378
---

# RTH walk-forward validation — Phase 1 results

**Universe:** 8 symbols × 27 strategies × 2 sides
**Window:** 75/25 chronological split per (strategy, symbol)
**Graduation gates:** n>=25, t>=1.5, E>0.0

## Graduation-eligible cells (25)

These cells cleared all three gates on the OOS slice and are
the candidate pool for Phase 4 staged deployment.

| Strategy | Symbol | Side | OOS n | OOS hit | OOS E (R) | OOS t |
|---|---|---|---|---|---|---|
| gap_fill | ZB | short | 590 | 74% | +1.39 | +22.02 |
| gap_fill | ZN | long | 438 | 75% | +1.11 | +18.47 |
| gap_fill | ZN | short | 394 | 77% | +1.25 | +18.41 |
| gap_fill | ZB | long | 557 | 66% | +1.14 | +16.58 |
| gap_fill | ZF | short | 363 | 71% | +1.11 | +13.85 |
| gap_fill | ZF | long | 377 | 66% | +0.94 | +12.61 |
| support_resistance_bounce | ZB | short | 61 | 38% | +1.63 | +3.33 |
| support_resistance_bounce | ZN | short | 65 | 42% | +1.12 | +3.33 |
| gap_fill | 6E | short | 61 | 54% | +0.56 | +2.93 |
| order_block | ZB | short | 39 | 56% | +0.66 | +2.77 |
| fair_value_gap | MES | long | 81 | 47% | +0.42 | +2.51 |
| gap_fill | NG | long | 30 | 60% | +0.88 | +2.44 |
| vol_spike_fade | ZB | long | 51 | 57% | +0.42 | +2.41 |
| fair_value_gap_tuned | MES | long | 64 | 42% | +0.49 | +2.26 |
| donchian_breakout | MES | long | 62 | 53% | +0.49 | +2.23 |
| support_resistance_bounce | ZF | short | 62 | 32% | +0.81 | +2.22 |
| rsi2_extreme_reversion | CL | long | 118 | 47% | +1.12 | +2.18 |
| order_block_d1 | ZN | short | 58 | 48% | +0.42 | +2.14 |
| gap_fill | NG | short | 32 | 66% | +1.50 | +2.03 |
| order_block | ZF | short | 29 | 52% | +0.55 | +1.95 |
| support_resistance_bounce | ZB | long | 113 | 26% | +0.48 | +1.92 |
| order_block_d1 | ZF | short | 61 | 44% | +0.34 | +1.77 |
| support_resistance_bounce | ZN | long | 121 | 27% | +0.37 | +1.76 |
| order_block_d1 | ZB | short | 73 | 44% | +0.30 | +1.72 |
| liquidity_sweep_tuned | 6E | short | 66 | 38% | +0.33 | +1.55 |

## Top 30 cells by OOS t-stat (all)

| Strategy | Symbol | Side | OOS n | OOS hit | OOS E (R) | OOS t | Eligible |
|---|---|---|---|---|---|---|---|
| gap_fill | ZB | short | 590 | 74% | +1.39 | +22.02 | ✓ |
| gap_fill | ZN | long | 438 | 75% | +1.11 | +18.47 | ✓ |
| gap_fill | ZN | short | 394 | 77% | +1.25 | +18.41 | ✓ |
| gap_fill | ZB | long | 557 | 66% | +1.14 | +16.58 | ✓ |
| gap_fill | ZF | short | 363 | 71% | +1.11 | +13.85 | ✓ |
| range_consolidation_bounce | ZB | long | 3 | 100% | +2.79 | +13.75 |  |
| gap_fill | ZF | long | 377 | 66% | +0.94 | +12.61 | ✓ |
| range_consolidation_bounce | ZN | short | 7 | 100% | +2.56 | +6.28 |  |
| bollinger_mean_reversion | ZB | long | 23 | 87% | +0.90 | +5.29 |  |
| range_consolidation_bounce | ZB | short | 4 | 100% | +2.06 | +3.61 |  |
| support_resistance_bounce | ZB | short | 61 | 38% | +1.63 | +3.33 | ✓ |
| support_resistance_bounce | ZN | short | 65 | 42% | +1.12 | +3.33 | ✓ |
| range_consolidation_bounce | ZN | long | 13 | 77% | +1.73 | +3.32 |  |
| gap_fill | 6E | short | 61 | 54% | +0.56 | +2.93 | ✓ |
| order_block | ZB | short | 39 | 56% | +0.66 | +2.77 | ✓ |
| fair_value_gap | MES | long | 81 | 47% | +0.42 | +2.51 | ✓ |
| gap_fill | NG | long | 30 | 60% | +0.88 | +2.44 | ✓ |
| vol_spike_fade | ZB | long | 51 | 57% | +0.42 | +2.41 | ✓ |
| volume_spike_reversal | CL | long | 10 | 70% | +1.10 | +2.40 |  |
| fair_value_gap_tuned | MES | long | 64 | 42% | +0.49 | +2.26 | ✓ |
| donchian_breakout | MES | long | 62 | 53% | +0.49 | +2.23 | ✓ |
| support_resistance_bounce | ZF | short | 62 | 32% | +0.81 | +2.22 | ✓ |
| rsi2_extreme_reversion | CL | long | 118 | 47% | +1.12 | +2.18 | ✓ |
| order_block_d1 | ZN | short | 58 | 48% | +0.42 | +2.14 | ✓ |
| volume_spike_reversal | ZF | short | 17 | 59% | +0.76 | +2.07 |  |
| gap_fill | NG | short | 32 | 66% | +1.50 | +2.03 | ✓ |
| order_block | ZF | short | 29 | 52% | +0.55 | +1.95 | ✓ |
| support_resistance_bounce | ZB | long | 113 | 26% | +0.48 | +1.92 | ✓ |
| order_block | ZN | short | 24 | 54% | +0.56 | +1.83 |  |
| bollinger_mean_reversion | ZF | long | 19 | 74% | +0.37 | +1.79 |  |

## Errors / skipped (1)

- `narrow_range_break/ZB: ValueError: cannot reindex on an axis with duplicate labels`

## Next: Phase 2 — parameter calibration

For each graduation-eligible cell, sweep strategy parameters
(stop ATR multiplier, target ATR multiplier, lookback) to find
RTH-calibrated values. RTH has higher volume and wider intra-bar
range than Asian; default params likely too tight.

After Phase 2: review with user for sanity check before Phase 4.