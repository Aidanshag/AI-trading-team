---
type: analysis
date: 2026-05-15
phase: universal walk-forward sweep
symbols: 50
strategies: 30
sessions: 4
cells_total: 5377
graduation_eligible: 15
runtime_seconds: 6386
---

# Universal walk-forward — full library × full Topstep universe

**Scope:** 50 symbols × 30 strategies × 4 sessions × 2 sides
**Gates:** n>=25, t>=2.0, E>0.0 (OOS)

## Graduation-eligible cells (15)

| Strategy | Symbol | Session | Side | n | Hit | E (R) | t |
|---|---|---|---|---|---|---|---|
| volume_spike_reversal | ZW | Asian | long | 25 | 80% | +1.32 | +5.41 |
| support_resistance_bounce | ZC | Asian | short | 45 | 29% | +2.30 | +2.59 |
| pivot_reversal | MBT | Asian | short | 60 | 50% | +0.50 | +2.56 |
| support_resistance_bounce | ZC | Asian | long | 56 | 29% | +1.58 | +2.51 |
| order_block_d1 | 6S | RTH | short | 28 | 57% | +0.71 | +2.50 |
| vol_spike_fade | ZW | Asian | long | 66 | 56% | +0.38 | +2.44 |
| vol_spike_fade | ZS | London | long | 69 | 55% | +0.36 | +2.38 |
| order_block | ZL | RTH | long | 38 | 53% | +0.58 | +2.33 |
| opening_range_breakout | HO | London | long | 27 | 52% | +0.91 | +2.30 |
| fair_value_gap_tuned | MBT | Asian | short | 49 | 45% | +0.57 | +2.27 |
| vol_spike_fade | ZC | Asian | long | 59 | 56% | +0.36 | +2.21 |
| limit_day_next_fade | ZW | London | short | 32 | 59% | +0.47 | +2.12 |
| liquidity_sweep | MBT | Asian | short | 52 | 48% | +0.44 | +2.11 |
| vol_spike_fade | PL | London | long | 45 | 62% | +0.38 | +2.05 |
| order_block_d1 | ZL | Asian | short | 60 | 47% | +0.39 | +2.00 |

## Per-session breakdown

- **Asian**: 9 eligible of 1385 cells
- **London**: 4 eligible of 1470 cells
- **RTH**: 2 eligible of 1498 cells
- **PostClose**: 0 eligible of 1024 cells

## Next: stage in shadow mode

`scripts.stage_shadow_cells` reads the JSON and adds each
eligible cell to `state/strategy_validation.json:live_allowlist`
with `experimental: true, shadow_reason: 'universal discovery'`.
Brain emits signals; existing pipeline records to `shadow_trades`
and resolves outcomes nightly. After 2-4 weeks of live data,
`scripts.cell_auto_promote` flags cells whose shadow performance
matches predicted for real-money review.