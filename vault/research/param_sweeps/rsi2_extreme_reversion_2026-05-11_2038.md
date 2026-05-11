---
type: param_sweep_summary
date: 2026-05-11T20:38:16.344479+00:00
strategy: rsi2_extreme_reversion
grid: {'rsi_buy_below': [5.0, 10.0, 15.0], 'rsi_exit_above': [60.0, 70.0, 80.0]}
symbols: ['ZN', 'MNQ', 'GC', '6E', 'MCL']
---

# Param sweep — rsi2_extreme_reversion

## Best variant per symbol — slippage-adjusted (OOS, n≥30, t≥1.5)

Ranked by `mean_net_usd_at_slip_0.25` (typical live slippage).

| Symbol | Best params | OOS_n | OOS_E (R) | OOS_t | $@slip=0.25 | $@slip=0.5 | $@slip=1.0 | breakeven_slip_ticks | mean_risk_ticks |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 6E | _(no qualifying variant)_ |  |  |  |  |  |  |  |  |
| GC | _(no qualifying variant)_ |  |  |  |  |  |  |  |  |
| MCL | _(no qualifying variant)_ |  |  |  |  |  |  |  |  |
| MNQ | _(no qualifying variant)_ |  |  |  |  |  |  |  |  |
| ZN | _(no qualifying variant)_ |  |  |  |  |  |  |  |  |

## All combinations — slippage-adjusted dollars (OOS only)

| Symbol | Params | OOS n | OOS E (R) | OOS t | $@0 | $@0.25 | $@0.5 | $@1.0 | breakeven |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ZN | `rsi_buy_below=5.0, rsi_exit_above=60.0` | 60 | -0.29 | -2.13 | -10 | -18 | -26 | -41 | 0.00 |
| ZN | `rsi_buy_below=5.0, rsi_exit_above=70.0` | 27 | -0.52 | -2.37 | -30 | -37 | -45 | -61 | 0.00 |
| ZN | `rsi_buy_below=5.0, rsi_exit_above=80.0` | 4 | +0.08 | +0.08 | -35 | -43 | -51 | -66 | 0.00 |
| ZN | `rsi_buy_below=10.0, rsi_exit_above=60.0` | 60 | -0.29 | -2.13 | -10 | -18 | -26 | -41 | 0.00 |
| ZN | `rsi_buy_below=10.0, rsi_exit_above=70.0` | 27 | -0.52 | -2.37 | -30 | -37 | -45 | -61 | 0.00 |
| ZN | `rsi_buy_below=10.0, rsi_exit_above=80.0` | 4 | +0.08 | +0.08 | -35 | -43 | -51 | -66 | 0.00 |
| ZN | `rsi_buy_below=15.0, rsi_exit_above=60.0` | 60 | -0.29 | -2.13 | -10 | -18 | -26 | -41 | 0.00 |
| ZN | `rsi_buy_below=15.0, rsi_exit_above=70.0` | 27 | -0.52 | -2.37 | -30 | -37 | -45 | -61 | 0.00 |
| ZN | `rsi_buy_below=15.0, rsi_exit_above=80.0` | 4 | +0.08 | +0.08 | -35 | -43 | -51 | -66 | 0.00 |
| MNQ | `rsi_buy_below=5.0, rsi_exit_above=60.0` | 224 | -0.04 | -0.36 | -0 | -1 | -1 | -1 | 0.00 |
| MNQ | `rsi_buy_below=5.0, rsi_exit_above=70.0` | 191 | -0.05 | -0.33 | -2 | -2 | -2 | -3 | 0.00 |
| MNQ | `rsi_buy_below=5.0, rsi_exit_above=80.0` | 151 | -0.12 | -0.94 | -1 | -1 | -1 | -2 | 0.00 |
| MNQ | `rsi_buy_below=10.0, rsi_exit_above=60.0` | 229 | -0.08 | -0.69 | -1 | -1 | -1 | -2 | 0.00 |
| MNQ | `rsi_buy_below=10.0, rsi_exit_above=70.0` | 195 | -0.07 | -0.52 | -2 | -2 | -2 | -3 | 0.00 |
| MNQ | `rsi_buy_below=10.0, rsi_exit_above=80.0` | 153 | -0.19 | -1.83 | -1 | -1 | -1 | -2 | 0.00 |
| MNQ | `rsi_buy_below=15.0, rsi_exit_above=60.0` | 235 | -0.11 | -1.14 | +0 | -0 | -0 | -1 | 0.17 |
| MNQ | `rsi_buy_below=15.0, rsi_exit_above=70.0` | 198 | -0.12 | -1.06 | -2 | -2 | -3 | -3 | 0.00 |
| MNQ | `rsi_buy_below=15.0, rsi_exit_above=80.0` | 154 | -0.19 | -1.81 | -3 | -3 | -3 | -4 | 0.00 |
| GC | `rsi_buy_below=5.0, rsi_exit_above=60.0` | 148 | -0.02 | -0.14 | +66 | +61 | +56 | +46 | ∞ |
| GC | `rsi_buy_below=5.0, rsi_exit_above=70.0` | 127 | +0.02 | +0.13 | +90 | +85 | +80 | +70 | ∞ |
| GC | `rsi_buy_below=5.0, rsi_exit_above=80.0` | 94 | +0.10 | +0.58 | +156 | +151 | +146 | +136 | ∞ |
| GC | `rsi_buy_below=10.0, rsi_exit_above=60.0` | 154 | -0.04 | -0.39 | +52 | +47 | +42 | +32 | ∞ |
| GC | `rsi_buy_below=10.0, rsi_exit_above=70.0` | 132 | +0.00 | +0.02 | +77 | +72 | +67 | +57 | ∞ |
| GC | `rsi_buy_below=10.0, rsi_exit_above=80.0` | 95 | +0.08 | +0.44 | +136 | +131 | +126 | +116 | ∞ |
| GC | `rsi_buy_below=15.0, rsi_exit_above=60.0` | 158 | -0.02 | -0.22 | +44 | +39 | +34 | +24 | ∞ |
| GC | `rsi_buy_below=15.0, rsi_exit_above=70.0` | 134 | -0.01 | -0.10 | +70 | +65 | +60 | +50 | ∞ |
| GC | `rsi_buy_below=15.0, rsi_exit_above=80.0` | 95 | +0.06 | +0.35 | +118 | +113 | +108 | +98 | ∞ |
| 6E | `rsi_buy_below=5.0, rsi_exit_above=60.0` | 138 | -0.16 | -1.50 | -2 | -5 | -8 | -14 | 0.00 |
| 6E | `rsi_buy_below=5.0, rsi_exit_above=70.0` | 92 | -0.08 | -0.51 | +1 | -2 | -5 | -12 | 0.07 |
| 6E | `rsi_buy_below=5.0, rsi_exit_above=80.0` | 60 | +0.05 | +0.22 | +6 | +2 | -1 | -7 | 0.44 |
| 6E | `rsi_buy_below=10.0, rsi_exit_above=60.0` | 139 | -0.15 | -1.41 | -1 | -4 | -7 | -14 | 0.00 |
| 6E | `rsi_buy_below=10.0, rsi_exit_above=70.0` | 93 | -0.06 | -0.38 | +2 | -1 | -4 | -11 | 0.16 |
| 6E | `rsi_buy_below=10.0, rsi_exit_above=80.0` | 60 | +0.05 | +0.22 | +5 | +2 | -1 | -7 | 0.42 |
| 6E | `rsi_buy_below=15.0, rsi_exit_above=60.0` | 140 | -0.09 | -0.69 | +0 | -3 | -6 | -12 | 0.01 |
| 6E | `rsi_buy_below=15.0, rsi_exit_above=70.0` | 94 | +0.04 | +0.21 | +4 | +1 | -3 | -9 | 0.30 |
| 6E | `rsi_buy_below=15.0, rsi_exit_above=80.0` | 60 | +0.05 | +0.22 | +5 | +2 | -1 | -7 | 0.42 |
| MCL | `rsi_buy_below=5.0, rsi_exit_above=60.0` | 142 | +0.04 | +0.37 | -1 | -1 | -2 | -3 | 0.00 |
| MCL | `rsi_buy_below=5.0, rsi_exit_above=70.0` | 127 | +0.12 | +0.84 | +2 | +1 | +1 | -0 | 0.85 |
| MCL | `rsi_buy_below=5.0, rsi_exit_above=80.0` | 79 | -0.09 | -0.52 | +2 | +1 | +1 | -0 | 0.87 |
| MCL | `rsi_buy_below=10.0, rsi_exit_above=60.0` | 149 | +0.33 | +1.05 | -1 | -1 | -2 | -3 | 0.00 |
| MCL | `rsi_buy_below=10.0, rsi_exit_above=70.0` | 132 | +0.44 | +1.24 | +2 | +1 | +1 | -0 | 0.92 |
| MCL | `rsi_buy_below=10.0, rsi_exit_above=80.0` | 81 | +0.46 | +0.81 | +2 | +2 | +1 | +0 | 1.15 |
| MCL | `rsi_buy_below=15.0, rsi_exit_above=60.0` | 152 | +0.25 | +0.83 | -1 | -1 | -2 | -3 | 0.00 |
| MCL | `rsi_buy_below=15.0, rsi_exit_above=70.0` | 134 | +0.37 | +1.04 | +2 | +1 | +1 | -0 | 0.92 |
| MCL | `rsi_buy_below=15.0, rsi_exit_above=80.0` | 83 | +0.42 | +0.78 | +2 | +2 | +1 | +0 | 1.23 |

## How to read

- `OOS E (R)` is the per-trade R-multiple — slippage-blind.
- `$@slip=X` is the NET dollar per trade after X ticks/side of round-trip slippage (entry + exit each cost X ticks).
- `breakeven_slip_ticks` is the slippage level at which mean net $ crosses zero. ∞ means the cell stays profitable beyond 2 ticks/side.
- A cell with high R but low `$@slip=0.25` is a trap: paper edge that doesn't survive realistic slippage.
- A cell with low R but high `breakeven_slip_ticks` is robust: the per-trade $ edge is large enough to absorb realistic costs.

Per the slippage-mitigation playbook (`vault/research/slippage_mitigation_playbook.md`) typical Topstep slippage on gap_fill_wide is 0.25-0.5 ticks/side. The `$@slip=0.25` column is the deployment-relevant metric.
