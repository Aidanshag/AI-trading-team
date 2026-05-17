---
type: analysis
date: 2026-05-15
phase: universal walk-forward sweep
symbols: 1
strategies: 5
sessions: 4
cells_total: 40
graduation_eligible: 0
runtime_seconds: 31
---

# Universal walk-forward — full library × full Topstep universe

**Scope:** 1 symbols × 5 strategies × 4 sessions × 2 sides
**Gates:** n>=25, t>=1.0, E>0.0 (OOS)

## Graduation-eligible cells (0)

_None._

## Per-session breakdown

- **Asian**: 0 eligible of 10 cells
- **London**: 0 eligible of 10 cells
- **RTH**: 0 eligible of 10 cells
- **PostClose**: 0 eligible of 10 cells

## Next: stage in shadow mode

`scripts.stage_shadow_cells` reads the JSON and adds each
eligible cell to `state/strategy_validation.json:live_allowlist`
with `experimental: true, shadow_reason: 'universal discovery'`.
Brain emits signals; existing pipeline records to `shadow_trades`
and resolves outcomes nightly. After 2-4 weeks of live data,
`scripts.cell_auto_promote` flags cells whose shadow performance
matches predicted for real-money review.