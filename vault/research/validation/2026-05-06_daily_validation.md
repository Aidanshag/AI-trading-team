---
type: daily_strategy_validation
date: 2026-05-06T20:04:34.283646+00:00
cells_evaluated: 1601
promotions: 2
demotions: 2
live_cells_total: 11
---

# Daily strategy validation — 2026-05-06

Cells evaluated: **1601**  
Promotions: **2**  
Demotions: **2**  
Total live cells: **11**

## PROMOTED to live

| Strategy | Symbol | Session | Side | n_OOS | E_OOS | t_OOS |
|---|---|---|---|---:|---:|---:|
| narrow_range_break | MNQ | London | long | 38 | +0.47 | +1.52 |
| inside_bar_break | MES | RTH | long | 32 | +0.43 | +1.67 |

## DEMOTED to shadow

| Strategy | Symbol | Session | Side | n_OOS | E_OOS | t_OOS | Reason |
|---|---|---|---|---:|---:|---:|---|
| inside_bar_break | GC | Asian | short | 56 | +0.23 | +1.23 | 3_consecutive_fails |
| inside_bar_break | 6A | Asian | short | 51 | +0.24 | +1.39 | 3_consecutive_fails |

## Live allowlist snapshot

11 cells currently allowed to place live orders. 
See `state/strategy_validation.json` → `live_allowlist` for the 
machine-readable list the auto_trader consumes.

