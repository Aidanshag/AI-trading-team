---
type: analysis
date: 2026-05-15
phase: universal walk-forward sweep
symbols: 1
strategies: 3
sessions: 4
cells_total: 18
graduation_eligible: 2
runtime_seconds: 22
---

# Universal walk-forward — full library × full Topstep universe

**Scope:** 1 symbols × 3 strategies × 4 sessions × 2 sides
**Gates:** n>=25, t>=1.5, E>0.0 (OOS)

## Graduation-eligible cells (2)

| Strategy | Symbol | Session | Side | n | Hit | E (R) | t |
|---|---|---|---|---|---|---|---|
| support_resistance_bounce | ZC | Asian | short | 45 | 29% | +2.30 | +2.59 |
| support_resistance_bounce | ZC | Asian | long | 56 | 29% | +1.58 | +2.51 |

## Per-session breakdown

- **Asian**: 2 eligible of 6 cells
- **London**: 0 eligible of 6 cells
- **RTH**: 0 eligible of 6 cells
- **PostClose**: 0 eligible of 0 cells

## Next: stage in shadow mode

`scripts.stage_shadow_cells` reads the JSON and adds each
eligible cell to `state/strategy_validation.json:live_allowlist`
with `experimental: true, shadow_reason: 'universal discovery'`.
Brain emits signals; existing pipeline records to `shadow_trades`
and resolves outcomes nightly. After 2-4 weeks of live data,
`scripts.cell_auto_promote` flags cells whose shadow performance
matches predicted for real-money review.