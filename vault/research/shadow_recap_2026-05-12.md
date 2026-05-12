# Shadow-Trade Recap — 2026-05-12

Window: last **7** days. Resolved trades only.

Shadow trades are TRIGGERs the team flagged on tickers outside the
active focus universe (or otherwise unactionable). They cost no
capital. Use this recap to decide whether to PROMOTE a symbol/
strategy combo to the active set.

## Per-(symbol, strategy) performance

`Theo R` = idealized stop-vs-target outcome (research view).
`Exec R` = what production would actually realize after slippage + fees + profit_lock + hard_flatten (see `tools/exec_mirror.py`). Promotion tier uses `Exec R`.

| Symbol | Strategy | n | Wins | HR | Theo R | Exec R | Gap | Tier |
|---|---|---:|---:|---:|---:|---:|---:|:---:|
| NG | inside_bar_break | 158 | 35 | 22% | +0.17 | -0.57 | -0.75 | **RED** |
| GC | narrow_range_break | 152 | 38 | 25% | +0.36 | -0.14 | -0.51 | **RED** |
| ZT | inside_bar_break | 146 | 32 | 22% | -0.09 | -1.78 | -1.69 | **RED** |
| ZN | inside_bar_break | 143 | 26 | 18% | -0.17 | -0.79 | -0.63 | **RED** |
| ZB | inside_bar_break | 141 | 29 | 21% | -0.17 | -0.88 | -0.71 | **RED** |
| ZN | narrow_range_break | 137 | 18 | 13% | -0.29 | -1.08 | -0.79 | **RED** |
| ZT | narrow_range_break | 137 | 25 | 18% | -0.19 | -2.23 | -2.04 | **RED** |
| MCL | inside_bar_break | 133 | 17 | 13% | +0.01 | -0.05 | -0.05 | **RED** |
| ZB | narrow_range_break | 133 | 26 | 20% | -0.17 | -1.18 | -1.02 | **RED** |
| 6E | inside_bar_break | 132 | 14 | 11% | -0.17 | -0.38 | -0.21 | **RED** |
| NG | narrow_range_break | 131 | 9 | 7% | -0.26 | -0.81 | -0.55 | **RED** |
| MES | inside_bar_break | 124 | 25 | 20% | -0.01 | -0.40 | -0.39 | **RED** |
| GC | liquidity_sweep | 121 | 15 | 12% | -0.07 | -0.09 | -0.02 | **RED** |
| 6E | narrow_range_break | 115 | 13 | 11% | -0.13 | -0.37 | -0.24 | **RED** |
| GC | inside_bar_break | 112 | 18 | 16% | -0.04 | -0.04 | -0.00 | **RED** |
| MNQ | inside_bar_break | 111 | 24 | 22% | +0.11 | -0.17 | -0.27 | **RED** |
| MES | narrow_range_break | 110 | 22 | 20% | +0.22 | -0.34 | -0.57 | **RED** |
| MES | liquidity_sweep | 109 | 15 | 14% | -0.05 | -0.46 | -0.41 | **RED** |
| GC | pivot_reversal | 107 | 12 | 11% | -0.10 | -0.06 | +0.04 | **RED** |
| MNQ | narrow_range_break | 107 | 18 | 17% | +0.06 | -0.21 | -0.27 | **RED** |
| 6E | pivot_reversal | 106 | 11 | 10% | -0.12 | -0.37 | -0.25 | **RED** |
| MNQ | liquidity_sweep | 103 | 16 | 16% | -0.05 | -0.22 | -0.17 | **RED** |
| ZF | narrow_range_break | 103 | 12 | 12% | -0.28 | -1.16 | -0.88 | **RED** |
| MCL | narrow_range_break | 99 | 11 | 11% | -0.07 | -0.19 | -0.12 | **RED** |
| ZF | inside_bar_break | 96 | 19 | 20% | -0.12 | -0.72 | -0.60 | **RED** |
| MCL | liquidity_sweep | 95 | 13 | 14% | -0.01 | -0.31 | -0.30 | **RED** |
| 6E | liquidity_sweep | 93 | 10 | 11% | -0.05 | -0.47 | -0.42 | **RED** |
| MES | pivot_reversal | 90 | 20 | 22% | +0.19 | -0.24 | -0.43 | **RED** |
| MNQ | pivot_reversal | 90 | 14 | 16% | -0.06 | -0.21 | -0.16 | **RED** |
| GC | liquidity_sweep_tuned | 89 | 9 | 10% | -0.03 | -0.09 | -0.06 | **RED** |
| NG | fair_value_gap_tuned | 85 | 8 | 9% | -0.11 | -0.47 | -0.36 | **RED** |
| MCL | pivot_reversal | 81 | 6 | 7% | -0.16 | +0.20 | +0.36 | **RED** |
| MES | liquidity_sweep_tuned | 79 | 11 | 14% | +0.01 | -0.48 | -0.49 | **RED** |
| 6E | liquidity_sweep_tuned | 78 | 6 | 8% | -0.10 | -0.44 | -0.34 | **RED** |
| GC | fair_value_gap_tuned | 78 | 13 | 17% | +0.11 | -0.19 | -0.30 | **RED** |
| MNQ | liquidity_sweep_tuned | 76 | 9 | 12% | -0.01 | -0.24 | -0.24 | **RED** |
| NG | liquidity_sweep | 72 | 10 | 14% | -0.03 | -0.33 | -0.30 | **RED** |
| ZB | order_block_d1 | 71 | 6 | 8% | -0.28 | -0.80 | -0.52 | **RED** |
| 6E | fair_value_gap_tuned | 70 | 4 | 6% | -0.20 | -0.32 | -0.12 | **RED** |
| NG | pivot_reversal | 69 | 11 | 16% | +0.10 | -0.45 | -0.55 | **RED** |
| ZN | order_block_d1 | 69 | 8 | 12% | -0.20 | -0.66 | -0.46 | **RED** |
| ZT | order_block_d1 | 69 | 11 | 16% | -0.13 | -2.18 | -2.05 | **RED** |
| MCL | fair_value_gap_tuned | 68 | 7 | 10% | -0.05 | -0.28 | -0.23 | **RED** |
| MCL | liquidity_sweep_tuned | 66 | 10 | 15% | +0.09 | -0.21 | -0.30 | **RED** |
| NG | gap_fill | 64 | 5 | 8% | -0.07 | -1.45 | -1.38 | **RED** |
| NG | order_block_d1 | 64 | 14 | 22% | +0.17 | -0.65 | -0.82 | **RED** |
| GC | order_block_d1 | 63 | 7 | 11% | -0.08 | -0.13 | -0.05 | **RED** |
| ZF | order_block_d1 | 63 | 9 | 14% | -0.10 | -1.03 | -0.93 | **RED** |
| ZF | fair_value_gap_tuned | 60 | 6 | 10% | -0.13 | -0.44 | -0.31 | **RED** |
| MES | order_block_d1 | 58 | 3 | 5% | -0.28 | -0.42 | -0.14 | **RED** |
| 6E | order_block_d1 | 57 | 7 | 12% | -0.05 | -0.42 | -0.37 | **RED** |
| ZB | fair_value_gap_tuned | 56 | 4 | 7% | -0.20 | -0.84 | -0.64 | **RED** |
| MCL | order_block_d1 | 55 | 6 | 11% | +0.02 | +0.09 | +0.07 | **RED** |
| MNQ | fair_value_gap_tuned | 54 | 8 | 15% | +0.00 | -0.27 | -0.27 | **RED** |
| ZB | pivot_reversal | 53 | 7 | 13% | -0.25 | -0.81 | -0.57 | **RED** |
| MES | fair_value_gap_tuned | 52 | 8 | 15% | +0.10 | -0.45 | -0.55 | **RED** |
| NG | liquidity_sweep_tuned | 52 | 6 | 12% | -0.02 | -0.33 | -0.31 | **RED** |
| ZT | fair_value_gap_tuned | 50 | 5 | 10% | -0.11 | -1.58 | -1.47 | **RED** |
| MNQ | order_block_d1 | 46 | 6 | 13% | -0.04 | +0.10 | +0.15 | **RED** |
| ZN | liquidity_sweep | 43 | 8 | 19% | +0.00 | -0.78 | -0.78 | **RED** |
| MNQ | vol_regime_trend | 42 | 8 | 19% | +0.14 | -0.10 | -0.24 | **RED** |
| ZT | liquidity_sweep | 42 | 4 | 10% | -0.07 | -0.93 | -0.86 | **RED** |
| ZN | pivot_reversal | 41 | 4 | 10% | -0.10 | -0.74 | -0.64 | **RED** |
| ZT | pivot_reversal | 40 | 4 | 10% | +0.00 | -1.32 | -1.32 | **RED** |
| ZF | liquidity_sweep | 35 | 4 | 11% | -0.09 | -0.82 | -0.73 | **RED** |
| ZF | liquidity_sweep_tuned | 35 | 2 | 6% | -0.17 | -0.82 | -0.65 | **RED** |
| ZN | fair_value_gap_tuned | 35 | 3 | 9% | -0.21 | -0.62 | -0.40 | **RED** |
| ZB | liquidity_sweep | 34 | 5 | 15% | -0.21 | -0.42 | -0.22 | **RED** |
| MES | vol_regime_trend | 32 | 5 | 16% | +0.22 | +0.26 | +0.04 | **RED** |
| ZN | liquidity_sweep_tuned | 30 | 6 | 20% | +0.20 | -0.58 | -0.78 | **RED** |
| GC | vol_regime_trend | 28 | 7 | 25% | +0.25 | +0.02 | -0.23 | **RED** |
| ZF | pivot_reversal | 26 | 2 | 8% | -0.31 | -0.99 | -0.68 | **RED** |
| ZT | liquidity_sweep_tuned | 26 | 4 | 15% | +0.15 | -0.42 | -0.57 | **RED** |
| MNQ | fair_value_gap | 23 | 13 | 57% | +0.70 | -0.27 | -0.97 | **RED** |
| ZB | liquidity_sweep_tuned | 22 | 4 | 18% | +0.05 | -0.36 | -0.40 | **RED** |
| 6E | vol_regime_trend | 18 | 3 | 17% | +0.17 | +0.33 | +0.16 | **RED** |
| 6B | order_block_d1 | 16 | 6 | 38% | +0.12 | -0.32 | -0.44 | **RED** |
| ZB | vol_regime_trend | 14 | 4 | 29% | +0.14 | -0.83 | -0.97 | **RED** |
| ZN | vol_regime_trend | 13 | 3 | 23% | -0.00 | -0.64 | -0.64 | **RED** |
| ZT | vol_regime_trend | 13 | 2 | 15% | -0.08 | -0.96 | -0.89 | **RED** |
| MCL | keltner_breakout | 11 | 11 | 100% | +2.00 | +4.48 | +2.48 | **GREEN** |
| NG | vol_regime_trend | 11 | 0 | 0% | -0.55 | -0.41 | +0.14 | **RED** |
| ZF | vol_regime_trend | 11 | 2 | 18% | -0.18 | -1.47 | -1.29 | **RED** |
| 6E | keltner_breakout | 5 | 0 | 0% | -1.00 | -0.42 | +0.58 | **YELLOW** |
| MCL | vol_regime_trend | 5 | 0 | 0% | -0.40 | -0.22 | +0.18 | **YELLOW** |
| GC | gap_fill | 3 | 0 | 0% | +0.00 | +2.48 | +2.48 | **YELLOW** |
| MES | gap_fill | 3 | 0 | 0% | +0.00 | +0.00 | +0.00 | **YELLOW** |
| ZF | gap_fill | 3 | 0 | 0% | +0.00 | -2.33 | -2.33 | **YELLOW** |
| ZT | gap_fill | 2 | 2 | 100% | +2.28 | -7.59 | -9.87 | **YELLOW** |
| MNQ | gap_fill | 1 | 0 | 0% | +0.00 | +0.00 | +0.00 | **YELLOW** |

## Promotion recommendations

**GREEN — promote to active focus** (1 combos):
- `MCL` / `keltner_breakout` (11 trades, 100% win, +2.00 avg R)

**YELLOW — keep shadow-tracking** (7 combos):
- `6E` / `keltner_breakout` (5 trades, 0% win, -1.00 avg R)
- `MCL` / `vol_regime_trend` (5 trades, 0% win, -0.40 avg R)
- `GC` / `gap_fill` (3 trades, 0% win, +0.00 avg R)
- `MES` / `gap_fill` (3 trades, 0% win, +0.00 avg R)
- `ZF` / `gap_fill` (3 trades, 0% win, +0.00 avg R)
- `ZT` / `gap_fill` (2 trades, 100% win, +2.28 avg R)
- `MNQ` / `gap_fill` (1 trades, 0% win, +0.00 avg R)

**RED — drop from shadow scan** (82 combos):
- `NG` / `inside_bar_break` (158 trades, 22% win, +0.17 avg R)
- `GC` / `narrow_range_break` (152 trades, 25% win, +0.36 avg R)
- `ZT` / `inside_bar_break` (146 trades, 22% win, -0.09 avg R)
- `ZN` / `inside_bar_break` (143 trades, 18% win, -0.17 avg R)
- `ZB` / `inside_bar_break` (141 trades, 21% win, -0.17 avg R)
- `ZN` / `narrow_range_break` (137 trades, 13% win, -0.29 avg R)
- `ZT` / `narrow_range_break` (137 trades, 18% win, -0.19 avg R)
- `MCL` / `inside_bar_break` (133 trades, 13% win, +0.01 avg R)
- `ZB` / `narrow_range_break` (133 trades, 20% win, -0.17 avg R)
- `6E` / `inside_bar_break` (132 trades, 11% win, -0.17 avg R)
- `NG` / `narrow_range_break` (131 trades, 7% win, -0.26 avg R)
- `MES` / `inside_bar_break` (124 trades, 20% win, -0.01 avg R)
- `GC` / `liquidity_sweep` (121 trades, 12% win, -0.07 avg R)
- `6E` / `narrow_range_break` (115 trades, 11% win, -0.13 avg R)
- `GC` / `inside_bar_break` (112 trades, 16% win, -0.04 avg R)
- `MNQ` / `inside_bar_break` (111 trades, 22% win, +0.11 avg R)
- `MES` / `narrow_range_break` (110 trades, 20% win, +0.22 avg R)
- `MES` / `liquidity_sweep` (109 trades, 14% win, -0.05 avg R)
- `GC` / `pivot_reversal` (107 trades, 11% win, -0.10 avg R)
- `MNQ` / `narrow_range_break` (107 trades, 17% win, +0.06 avg R)
- `6E` / `pivot_reversal` (106 trades, 10% win, -0.12 avg R)
- `MNQ` / `liquidity_sweep` (103 trades, 16% win, -0.05 avg R)
- `ZF` / `narrow_range_break` (103 trades, 12% win, -0.28 avg R)
- `MCL` / `narrow_range_break` (99 trades, 11% win, -0.07 avg R)
- `ZF` / `inside_bar_break` (96 trades, 20% win, -0.12 avg R)
- `MCL` / `liquidity_sweep` (95 trades, 14% win, -0.01 avg R)
- `6E` / `liquidity_sweep` (93 trades, 11% win, -0.05 avg R)
- `MES` / `pivot_reversal` (90 trades, 22% win, +0.19 avg R)
- `MNQ` / `pivot_reversal` (90 trades, 16% win, -0.06 avg R)
- `GC` / `liquidity_sweep_tuned` (89 trades, 10% win, -0.03 avg R)
- `NG` / `fair_value_gap_tuned` (85 trades, 9% win, -0.11 avg R)
- `MCL` / `pivot_reversal` (81 trades, 7% win, -0.16 avg R)
- `MES` / `liquidity_sweep_tuned` (79 trades, 14% win, +0.01 avg R)
- `6E` / `liquidity_sweep_tuned` (78 trades, 8% win, -0.10 avg R)
- `GC` / `fair_value_gap_tuned` (78 trades, 17% win, +0.11 avg R)
- `MNQ` / `liquidity_sweep_tuned` (76 trades, 12% win, -0.01 avg R)
- `NG` / `liquidity_sweep` (72 trades, 14% win, -0.03 avg R)
- `ZB` / `order_block_d1` (71 trades, 8% win, -0.28 avg R)
- `6E` / `fair_value_gap_tuned` (70 trades, 6% win, -0.20 avg R)
- `NG` / `pivot_reversal` (69 trades, 16% win, +0.10 avg R)
- `ZN` / `order_block_d1` (69 trades, 12% win, -0.20 avg R)
- `ZT` / `order_block_d1` (69 trades, 16% win, -0.13 avg R)
- `MCL` / `fair_value_gap_tuned` (68 trades, 10% win, -0.05 avg R)
- `MCL` / `liquidity_sweep_tuned` (66 trades, 15% win, +0.09 avg R)
- `NG` / `gap_fill` (64 trades, 8% win, -0.07 avg R)
- `NG` / `order_block_d1` (64 trades, 22% win, +0.17 avg R)
- `GC` / `order_block_d1` (63 trades, 11% win, -0.08 avg R)
- `ZF` / `order_block_d1` (63 trades, 14% win, -0.10 avg R)
- `ZF` / `fair_value_gap_tuned` (60 trades, 10% win, -0.13 avg R)
- `MES` / `order_block_d1` (58 trades, 5% win, -0.28 avg R)
- `6E` / `order_block_d1` (57 trades, 12% win, -0.05 avg R)
- `ZB` / `fair_value_gap_tuned` (56 trades, 7% win, -0.20 avg R)
- `MCL` / `order_block_d1` (55 trades, 11% win, +0.02 avg R)
- `MNQ` / `fair_value_gap_tuned` (54 trades, 15% win, +0.00 avg R)
- `ZB` / `pivot_reversal` (53 trades, 13% win, -0.25 avg R)
- `MES` / `fair_value_gap_tuned` (52 trades, 15% win, +0.10 avg R)
- `NG` / `liquidity_sweep_tuned` (52 trades, 12% win, -0.02 avg R)
- `ZT` / `fair_value_gap_tuned` (50 trades, 10% win, -0.11 avg R)
- `MNQ` / `order_block_d1` (46 trades, 13% win, -0.04 avg R)
- `ZN` / `liquidity_sweep` (43 trades, 19% win, +0.00 avg R)
- `MNQ` / `vol_regime_trend` (42 trades, 19% win, +0.14 avg R)
- `ZT` / `liquidity_sweep` (42 trades, 10% win, -0.07 avg R)
- `ZN` / `pivot_reversal` (41 trades, 10% win, -0.10 avg R)
- `ZT` / `pivot_reversal` (40 trades, 10% win, +0.00 avg R)
- `ZF` / `liquidity_sweep` (35 trades, 11% win, -0.09 avg R)
- `ZF` / `liquidity_sweep_tuned` (35 trades, 6% win, -0.17 avg R)
- `ZN` / `fair_value_gap_tuned` (35 trades, 9% win, -0.21 avg R)
- `ZB` / `liquidity_sweep` (34 trades, 15% win, -0.21 avg R)
- `MES` / `vol_regime_trend` (32 trades, 16% win, +0.22 avg R)
- `ZN` / `liquidity_sweep_tuned` (30 trades, 20% win, +0.20 avg R)
- `GC` / `vol_regime_trend` (28 trades, 25% win, +0.25 avg R)
- `ZF` / `pivot_reversal` (26 trades, 8% win, -0.31 avg R)
- `ZT` / `liquidity_sweep_tuned` (26 trades, 15% win, +0.15 avg R)
- `MNQ` / `fair_value_gap` (23 trades, 57% win, +0.70 avg R)
- `ZB` / `liquidity_sweep_tuned` (22 trades, 18% win, +0.05 avg R)
- `6E` / `vol_regime_trend` (18 trades, 17% win, +0.17 avg R)
- `6B` / `order_block_d1` (16 trades, 38% win, +0.12 avg R)
- `ZB` / `vol_regime_trend` (14 trades, 29% win, +0.14 avg R)
- `ZN` / `vol_regime_trend` (13 trades, 23% win, -0.00 avg R)
- `ZT` / `vol_regime_trend` (13 trades, 15% win, -0.08 avg R)
- `NG` / `vol_regime_trend` (11 trades, 0% win, -0.55 avg R)
- `ZF` / `vol_regime_trend` (11 trades, 18% win, -0.18 avg R)

## Action items

- CIO: review GREEN list at next session brief; add to focus universe
  via `config/focus_universe.yaml` if backtest-aligned.
- Quant Researcher: cross-check GREEN combos against literature
  priors in `tools/strategy_performance.py` before promotion.
- Edge Hunter: continue shadow-tracking YELLOW; deprioritize RED.

_Generated by `scripts/shadow_trade_recap.py` at 2026-05-12T14:43:39+00:00._
