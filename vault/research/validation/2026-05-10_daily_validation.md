---
type: daily_strategy_validation
date: 2026-05-10T20:52:38.632430+00:00
cells_evaluated: 2024
promotions: 3
demotions: 3
live_cells_total: 18
---

# Daily strategy validation — 2026-05-10

Cells evaluated: **2024**  
Promotions: **3**  
Demotions: **3**  
Total live cells: **18**

## PROMOTED to live

| Strategy | Symbol | Session | Side | n_OOS | E_OOS | t_OOS |
|---|---|---|---|---:|---:|---:|
| fair_value_gap | MNQ | RTH | long | 45 | +0.40 | +1.77 |
| liquidity_sweep | MNQ | London | long | 33 | +0.46 | +1.71 |
| liquidity_sweep_tuned | MNQ | London | long | 29 | +0.57 | +1.73 |

## DEMOTED to shadow

| Strategy | Symbol | Session | Side | n_OOS | E_OOS | t_OOS | Reason |
|---|---|---|---|---:|---:|---:|---|
| narrow_range_break | MNQ | London | long | 36 | +0.09 | +0.39 | 3_consecutive_fails |
| inside_bar_break | 6A | London | long | 33 | +0.21 | +0.93 | 3_consecutive_fails |
| fair_value_gap_tuned | 6A | London | short | 24 | +0.60 | +1.66 | 3_consecutive_fails |

## Live allowlist snapshot

18 cells currently allowed to place live orders. 
See `state/strategy_validation.json` → `live_allowlist` for the 
machine-readable list the auto_trader consumes.

