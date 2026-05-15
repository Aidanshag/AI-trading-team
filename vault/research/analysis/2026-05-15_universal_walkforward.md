---
type: analysis
date: 2026-05-15
phase: universal walk-forward sweep
symbols: 7
strategies: 3
sessions: 4
cells_total: 55
graduation_eligible: 2
runtime_seconds: 37
---

# Universal walk-forward — full library × full Topstep universe

**Scope:** 7 symbols × 3 strategies × 4 sessions × 2 sides
**Gates:** n>=25, t>=1.5, E>0.0 (OOS)

## Graduation-eligible cells (2)

| Strategy | Symbol | Session | Side | n | Hit | E (R) | t |
|---|---|---|---|---|---|---|---|
| limit_day_next_fade | ZW | London | short | 32 | 59% | +0.48 | +2.20 |
| limit_day_next_fade | ZM | Asian | long | 34 | 56% | +0.40 | +1.84 |

## Per-session breakdown

- **Asian**: 1 eligible of 17 cells
- **London**: 1 eligible of 16 cells
- **RTH**: 0 eligible of 22 cells
- **PostClose**: 0 eligible of 0 cells

## Next: stage in shadow mode

`scripts.stage_shadow_cells` reads the JSON and adds each
eligible cell to `state/strategy_validation.json:live_allowlist`
with `experimental: true, shadow_reason: 'universal discovery'`.
Brain emits signals; existing pipeline records to `shadow_trades`
and resolves outcomes nightly. After 2-4 weeks of live data,
`scripts.cell_auto_promote` flags cells whose shadow performance
matches predicted for real-money review.