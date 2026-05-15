---
type: analysis
date: 2026-05-15
phase: universal walk-forward sweep
symbols: 7
strategies: 30
sessions: 4
cells_total: 639
graduation_eligible: 9
runtime_seconds: 858
---

# Universal walk-forward — full library × full Topstep universe

**Scope:** 7 symbols × 30 strategies × 4 sessions × 2 sides
**Gates:** n>=25, t>=2.0, E>0.0 (OOS)

## Graduation-eligible cells (9)

| Strategy | Symbol | Session | Side | n | Hit | E (R) | t |
|---|---|---|---|---|---|---|---|
| volume_spike_reversal | ZW | Asian | long | 25 | 80% | +1.32 | +5.41 |
| support_resistance_bounce | ZC | Asian | short | 45 | 29% | +2.30 | +2.59 |
| support_resistance_bounce | ZC | Asian | long | 56 | 29% | +1.58 | +2.51 |
| vol_spike_fade | ZW | Asian | long | 66 | 56% | +0.38 | +2.44 |
| vol_spike_fade | ZS | London | long | 69 | 55% | +0.36 | +2.38 |
| order_block | ZL | RTH | long | 38 | 53% | +0.58 | +2.33 |
| vol_spike_fade | ZC | Asian | long | 59 | 56% | +0.36 | +2.21 |
| limit_day_next_fade | ZW | London | short | 32 | 59% | +0.47 | +2.12 |
| order_block_d1 | ZL | Asian | short | 60 | 47% | +0.39 | +2.00 |

## Per-session breakdown

- **Asian**: 6 eligible of 183 cells
- **London**: 2 eligible of 185 cells
- **RTH**: 1 eligible of 271 cells
- **PostClose**: 0 eligible of 0 cells

## Next: stage in shadow mode

`scripts.stage_shadow_cells` reads the JSON and adds each
eligible cell to `state/strategy_validation.json:live_allowlist`
with `experimental: true, shadow_reason: 'universal discovery'`.
Brain emits signals; existing pipeline records to `shadow_trades`
and resolves outcomes nightly. After 2-4 weeks of live data,
`scripts.cell_auto_promote` flags cells whose shadow performance
matches predicted for real-money review.