---
type: daily_strategy_validation
date: 2026-05-07T19:30:29.811857+00:00
cells_evaluated: 2033
promotions: 3
demotions: 1
live_cells_total: 18
---

# Daily strategy validation — 2026-05-07

Cells evaluated: **2033**  
Promotions: **3**  
Demotions: **1**  
Total live cells: **18**

## PROMOTED to live

| Strategy | Symbol | Session | Side | n_OOS | E_OOS | t_OOS |
|---|---|---|---|---:|---:|---:|
| rsi2_extreme_reversion | MCL | RTH | long | 50 | +0.84 | +1.58 |
| pivot_reversal | GC | Asian | long | 32 | +0.41 | +1.51 |
| fair_value_gap_tuned | 6A | London | short | 25 | +0.54 | +1.52 |

## DEMOTED to shadow

| Strategy | Symbol | Session | Side | n_OOS | E_OOS | t_OOS | Reason |
|---|---|---|---|---:|---:|---:|---|
| fair_value_gap_tuned | MES | London | short | 26 | +0.48 | +1.39 | 3_consecutive_fails |

## Live allowlist snapshot

18 cells currently allowed to place live orders. 
See `state/strategy_validation.json` → `live_allowlist` for the 
machine-readable list the auto_trader consumes.

