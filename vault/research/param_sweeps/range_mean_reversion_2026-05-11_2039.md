---
type: param_sweep_summary
date: 2026-05-11T20:39:36.820217+00:00
strategy: range_mean_reversion
grid: {'range_period': [10.0, 20.0, 40.0], 'range_max_pct': [0.02, 0.04, 0.06], 'stop_atr_mult': [0.5, 1.0, 1.5]}
symbols: ['ZN', 'MNQ', 'GC', '6E', 'MCL']
---

# Param sweep — range_mean_reversion

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
| ZN | `range_period=10.0, range_max_pct=0.02, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| ZN | `range_period=10.0, range_max_pct=0.02, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| ZN | `range_period=10.0, range_max_pct=0.02, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| ZN | `range_period=10.0, range_max_pct=0.04, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| ZN | `range_period=10.0, range_max_pct=0.04, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| ZN | `range_period=10.0, range_max_pct=0.04, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| ZN | `range_period=10.0, range_max_pct=0.06, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| ZN | `range_period=10.0, range_max_pct=0.06, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| ZN | `range_period=10.0, range_max_pct=0.06, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| ZN | `range_period=20.0, range_max_pct=0.02, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| ZN | `range_period=20.0, range_max_pct=0.02, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| ZN | `range_period=20.0, range_max_pct=0.02, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| ZN | `range_period=20.0, range_max_pct=0.04, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| ZN | `range_period=20.0, range_max_pct=0.04, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| ZN | `range_period=20.0, range_max_pct=0.04, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| ZN | `range_period=20.0, range_max_pct=0.06, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| ZN | `range_period=20.0, range_max_pct=0.06, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| ZN | `range_period=20.0, range_max_pct=0.06, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| ZN | `range_period=40.0, range_max_pct=0.02, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| ZN | `range_period=40.0, range_max_pct=0.02, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| ZN | `range_period=40.0, range_max_pct=0.02, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| ZN | `range_period=40.0, range_max_pct=0.04, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| ZN | `range_period=40.0, range_max_pct=0.04, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| ZN | `range_period=40.0, range_max_pct=0.04, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| ZN | `range_period=40.0, range_max_pct=0.06, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| ZN | `range_period=40.0, range_max_pct=0.06, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| ZN | `range_period=40.0, range_max_pct=0.06, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=10.0, range_max_pct=0.02, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=10.0, range_max_pct=0.02, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=10.0, range_max_pct=0.02, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=10.0, range_max_pct=0.04, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=10.0, range_max_pct=0.04, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=10.0, range_max_pct=0.04, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=10.0, range_max_pct=0.06, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=10.0, range_max_pct=0.06, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=10.0, range_max_pct=0.06, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=20.0, range_max_pct=0.02, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=20.0, range_max_pct=0.02, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=20.0, range_max_pct=0.02, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=20.0, range_max_pct=0.04, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=20.0, range_max_pct=0.04, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=20.0, range_max_pct=0.04, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=20.0, range_max_pct=0.06, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=20.0, range_max_pct=0.06, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=20.0, range_max_pct=0.06, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=40.0, range_max_pct=0.02, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=40.0, range_max_pct=0.02, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=40.0, range_max_pct=0.02, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=40.0, range_max_pct=0.04, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=40.0, range_max_pct=0.04, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=40.0, range_max_pct=0.04, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=40.0, range_max_pct=0.06, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=40.0, range_max_pct=0.06, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| MNQ | `range_period=40.0, range_max_pct=0.06, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=10.0, range_max_pct=0.02, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=10.0, range_max_pct=0.02, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=10.0, range_max_pct=0.02, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=10.0, range_max_pct=0.04, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=10.0, range_max_pct=0.04, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=10.0, range_max_pct=0.04, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=10.0, range_max_pct=0.06, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=10.0, range_max_pct=0.06, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=10.0, range_max_pct=0.06, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=20.0, range_max_pct=0.02, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=20.0, range_max_pct=0.02, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=20.0, range_max_pct=0.02, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=20.0, range_max_pct=0.04, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=20.0, range_max_pct=0.04, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=20.0, range_max_pct=0.04, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=20.0, range_max_pct=0.06, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=20.0, range_max_pct=0.06, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=20.0, range_max_pct=0.06, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=40.0, range_max_pct=0.02, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=40.0, range_max_pct=0.02, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=40.0, range_max_pct=0.02, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=40.0, range_max_pct=0.04, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=40.0, range_max_pct=0.04, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=40.0, range_max_pct=0.04, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=40.0, range_max_pct=0.06, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=40.0, range_max_pct=0.06, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| GC | `range_period=40.0, range_max_pct=0.06, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=10.0, range_max_pct=0.02, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=10.0, range_max_pct=0.02, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=10.0, range_max_pct=0.02, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=10.0, range_max_pct=0.04, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=10.0, range_max_pct=0.04, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=10.0, range_max_pct=0.04, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=10.0, range_max_pct=0.06, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=10.0, range_max_pct=0.06, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=10.0, range_max_pct=0.06, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=20.0, range_max_pct=0.02, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=20.0, range_max_pct=0.02, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=20.0, range_max_pct=0.02, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=20.0, range_max_pct=0.04, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=20.0, range_max_pct=0.04, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=20.0, range_max_pct=0.04, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=20.0, range_max_pct=0.06, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=20.0, range_max_pct=0.06, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=20.0, range_max_pct=0.06, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=40.0, range_max_pct=0.02, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=40.0, range_max_pct=0.02, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=40.0, range_max_pct=0.02, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=40.0, range_max_pct=0.04, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=40.0, range_max_pct=0.04, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=40.0, range_max_pct=0.04, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=40.0, range_max_pct=0.06, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=40.0, range_max_pct=0.06, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| 6E | `range_period=40.0, range_max_pct=0.06, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=10.0, range_max_pct=0.02, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=10.0, range_max_pct=0.02, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=10.0, range_max_pct=0.02, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=10.0, range_max_pct=0.04, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=10.0, range_max_pct=0.04, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=10.0, range_max_pct=0.04, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=10.0, range_max_pct=0.06, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=10.0, range_max_pct=0.06, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=10.0, range_max_pct=0.06, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=20.0, range_max_pct=0.02, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=20.0, range_max_pct=0.02, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=20.0, range_max_pct=0.02, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=20.0, range_max_pct=0.04, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=20.0, range_max_pct=0.04, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=20.0, range_max_pct=0.04, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=20.0, range_max_pct=0.06, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=20.0, range_max_pct=0.06, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=20.0, range_max_pct=0.06, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=40.0, range_max_pct=0.02, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=40.0, range_max_pct=0.02, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=40.0, range_max_pct=0.02, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=40.0, range_max_pct=0.04, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=40.0, range_max_pct=0.04, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=40.0, range_max_pct=0.04, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=40.0, range_max_pct=0.06, stop_atr_mult=0.5` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=40.0, range_max_pct=0.06, stop_atr_mult=1.0` | 0 | — | — | — | — | — | — | — |
| MCL | `range_period=40.0, range_max_pct=0.06, stop_atr_mult=1.5` | 0 | — | — | — | — | — | — | — |

## How to read

- `OOS E (R)` is the per-trade R-multiple — slippage-blind.
- `$@slip=X` is the NET dollar per trade after X ticks/side of round-trip slippage (entry + exit each cost X ticks).
- `breakeven_slip_ticks` is the slippage level at which mean net $ crosses zero. ∞ means the cell stays profitable beyond 2 ticks/side.
- A cell with high R but low `$@slip=0.25` is a trap: paper edge that doesn't survive realistic slippage.
- A cell with low R but high `breakeven_slip_ticks` is robust: the per-trade $ edge is large enough to absorb realistic costs.

Per the slippage-mitigation playbook (`vault/research/slippage_mitigation_playbook.md`) typical Topstep slippage on gap_fill_wide is 0.25-0.5 ticks/side. The `$@slip=0.25` column is the deployment-relevant metric.
