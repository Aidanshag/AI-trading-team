---
type: analysis
date: 2026-05-15
phase: universal walk-forward sweep
symbols: 50
strategies: 35
sessions: 4
cells_total: 6792
graduation_eligible: 6
runtime_seconds: 11048
---

# Universal walk-forward — full library × full Topstep universe

**Scope:** 50 symbols × 35 strategies × 4 sessions × 2 sides
**Gates:** n>=25, t>=2.5, E>0.0 (OOS)

## Graduation-eligible cells (6)

| Strategy | Symbol | Session | Side | n | Hit | E (R) | t |
|---|---|---|---|---|---|---|---|
| volume_spike_reversal | ZW | Asian | long | 25 | 80% | +1.32 | +5.41 |
| rsi_divergence_reversal | GMET | Asian | short | 26 | 69% | +0.65 | +2.89 |
| support_resistance_bounce | ZC | Asian | short | 45 | 29% | +2.30 | +2.59 |
| pivot_reversal | MBT | Asian | short | 60 | 50% | +0.50 | +2.56 |
| support_resistance_bounce | ZC | Asian | long | 56 | 29% | +1.58 | +2.51 |
| order_block_d1 | 6S | RTH | short | 28 | 57% | +0.71 | +2.50 |

## Per-session breakdown

- **Asian**: 5 eligible of 1741 cells
- **London**: 0 eligible of 1858 cells
- **RTH**: 1 eligible of 1903 cells
- **PostClose**: 0 eligible of 1290 cells

## Next: stage in shadow mode

`scripts.stage_shadow_cells` reads the JSON and adds each
eligible cell to `state/strategy_validation.json:live_allowlist`
with `experimental: true, shadow_reason: 'universal discovery'`.
Brain emits signals; existing pipeline records to `shadow_trades`
and resolves outcomes nightly. After 2-4 weeks of live data,
`scripts.cell_auto_promote` flags cells whose shadow performance
matches predicted for real-money review.