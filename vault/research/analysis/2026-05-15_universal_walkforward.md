---
type: analysis
date: 2026-05-15
phase: universal walk-forward sweep
symbols: 1
strategies: 2
sessions: 4
cells_total: 16
graduation_eligible: 1
runtime_seconds: 18
---

# Universal walk-forward — full library × full Topstep universe

**Scope:** 1 symbols × 2 strategies × 4 sessions × 2 sides
**Gates:** n>=25, t>=2.0, E>0.0 (OOS)

## Graduation-eligible cells (1)

| Strategy | Symbol | Session | Side | n | Hit | E (R) | t |
|---|---|---|---|---|---|---|---|
| fair_value_gap | MES | RTH | long | 81 | 47% | +0.42 | +2.51 |

## Per-session breakdown

- **Asian**: 0 eligible of 4 cells
- **London**: 0 eligible of 4 cells
- **RTH**: 1 eligible of 4 cells
- **PostClose**: 0 eligible of 4 cells

## Next: stage in shadow mode

`scripts.stage_shadow_cells` reads the JSON and adds each
eligible cell to `state/strategy_validation.json:live_allowlist`
with `experimental: true, shadow_reason: 'universal discovery'`.
Brain emits signals; existing pipeline records to `shadow_trades`
and resolves outcomes nightly. After 2-4 weeks of live data,
`scripts.cell_auto_promote` flags cells whose shadow performance
matches predicted for real-money review.