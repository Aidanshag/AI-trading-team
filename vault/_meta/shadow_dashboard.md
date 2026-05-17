---
type: dashboard
date: 2026-05-17
generated_at: 2026-05-17T19:29:50.592637+00:00
auto_generated_by: scripts/shadow_dashboard.py
---

# Shadow trading dashboard

_Auto-generated. Single source of truth for what's currently in shadow + how each cell is performing in real-market conditions. Updated daily via `FundVaultMaintenance`._

## Summary

- **Live cells (real fills):** 17
- **Shadow cells (recording only):** 18
- **Total `shadow_trades` rows in DB:** 6140
- **Resolved (graded):** 6064
- **Signals in last 3 days:** 7

## Cells currently in shadow

Each shadow cell records signals to `shadow_trades` without placing real orders. After 2-4 weeks of positive live data, candidates can be promoted to `experimental:false` (real fills).

| Strategy | Symbol | Session | Side | Source | 30d shadow n | 30d hit | 30d avg R | 30d avg R (friction) |
|---|---|---|---|---|---|---|---|---|
| fair_value_gap_tuned | GC | Asian | short | Combine-phase consistency rule 2026 | 38 | 24% | +0.28 | -0.15 |
| inside_bar_break | GC | PostClose | long | older | 62 | 19% | +0.03 | +0.04 |
| limit_day_next_fade | ZM | Asian | long | universal discovery 2026-05-15 | 0 | - | - | - |
| limit_day_next_fade | ZW | London | short | universal discovery 2026-05-15 | 0 | - | - | - |
| narrow_range_break | 6C | PostClose | long | older | 0 | - | - | - |
| narrow_range_break | GC | Asian | long | Combine-phase consistency rule 2026 | 72 | 17% | +0.05 | -0.13 |
| narrow_range_break | GC | Asian | short | Combine-phase consistency rule 2026 | 80 | 34% | +0.64 | -0.19 |
| order_block | ZL | RTH | long | ag post-fix universal sweep 2026-05 | 0 | - | - | - |
| order_block_d1 | ZL | Asian | short | ag post-fix universal sweep 2026-05 | 0 | - | - | - |
| rsi2_extreme_reversion | MNQ | PostClose | long | older | 0 | - | - | - |
| support_resistance_bounce | ZC | Asian | long | ag post-fix universal sweep 2026-05 | 0 | - | - | - |
| support_resistance_bounce | ZC | Asian | short | ag post-fix universal sweep 2026-05 | 0 | - | - | - |
| support_resistance_bounce | ZN | Asian | long | universal discovery 2026-05-15 | 0 | - | - | - |
| vol_spike_fade | ZC | Asian | long | ag post-fix universal sweep 2026-05 | 0 | - | - | - |
| vol_spike_fade | ZN | Asian | short | universal discovery 2026-05-15 | 0 | - | - | - |
| vol_spike_fade | ZS | London | long | ag post-fix universal sweep 2026-05 | 0 | - | - | - |
| vol_spike_fade | ZW | Asian | long | ag post-fix universal sweep 2026-05 | 0 | - | - | - |
| volume_spike_reversal | ZW | Asian | long | ag post-fix universal sweep 2026-05 | 0 | - | - | - |

## Cells currently live (real fills)

| Strategy | Symbol | Session | Side | Promoted |
|---|---|---|---|---|
| cross_asset_divergence_zn | ZB | Asian | short |  |
| fair_value_gap | 6E | Asian | short |  |
| fair_value_gap | MES | RTH | long | 2026-05-15 |
| fair_value_gap | NG | RTH | short |  |
| fair_value_gap_tuned | MGC | Asian | short | 2026-05-14 |
| fair_value_gap_tuned | MNQ | Asian | long |  |
| inside_bar_break | MGC | PostClose | long | 2026-05-14 |
| keltner_breakout | 6E | Asian | long |  |
| keltner_breakout | 6E | Asian | short |  |
| keltner_breakout | MCL | Asian | long | 2026-05-15 |
| narrow_range_break | MGC | Asian | long | 2026-05-14 |
| narrow_range_break | MGC | Asian | short | 2026-05-14 |
| order_block_d1 | MNQ | Asian | long | 2026-05-15 |
| pivot_reversal | 6E | London | long |  |
| pivot_reversal | MNQ | RTH | long |  |
| vol_spike_fade | 6C | Asian | short |  |
| vol_spike_fade | ZF | Asian | short |  |

## Promotion candidates

Shadow cells with **n≥25** in last 30 days AND **positive avg_ex_r** (friction-adjusted). These cells have enough live data to consider promoting to real fills.

| Cell | n | Hit | Avg R | Avg R (friction) |
|---|---|---|---|---|
| inside_bar_break/GC/PostClose/long | 62 | 19% | +0.03 | +0.04 |

## 7-day pulse (active firing)

Shadow cells that fired in the last 7 days. Quick check on whether the staged cells are actually emitting signals.

| Cell | 7d signals | Hit | Avg R |
|---|---|---|---|
| narrow_range_break/GC/Asian/short | 20 | 100% | +2.85 |
| narrow_range_break/GC/Asian/long | 15 | 13% | -0.33 |
| fair_value_gap_tuned/GC/Asian/short | 9 | 100% | +2.50 |

## Recent cleanup history

- 2026-05-17: removed 28 pre-fix gap_fill / gap_fill_wide cells flagged with `shadow_caveat` (Pattern B inflation). Only post-fix honest cells remain.

## How to read this

- **shadow_reason** tells you why the cell was staged (`universal discovery`, `ag post-fix`, etc.)
- **30d hit** below 30% is normal for trend-followers — look at **avg R** for true edge
- **avg R (friction)** is the realistic number after slippage + fees. Cells with positive `avg_r` but negative `avg_r_friction` are NOT profitable in reality
- Cells in **Promotion candidates** are ready for user review to flip `experimental:false` for real fills

## Source of truth

- `state/strategy_validation.json:live_allowlist` — cell config
- `state/fund.db:shadow_trades` — every signal recorded
- `scripts/cell_auto_promote.py` — auto-promote logic
- `scripts/resolve_shadow_trades.py` — nightly grader