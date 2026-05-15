---
type: analysis
date: 2026-05-15
phase: universal walk-forward sweep
symbols: 5
strategies: 27
sessions: 4
cells_total: 565
graduation_eligible: 34
runtime_seconds: 416
---

# Universal walk-forward — full library × full Topstep universe

**Scope:** 5 symbols × 27 strategies × 4 sessions × 2 sides
**Gates:** n>=25, t>=2.0, E>0.0 (OOS)

## Graduation-eligible cells (34)

| Strategy | Symbol | Session | Side | n | Hit | E (R) | t |
|---|---|---|---|---|---|---|---|
| gap_fill | ZC | Asian | short | 321 | 68% | +2.16 | +14.78 |
| gap_fill | ZC | Asian | long | 308 | 68% | +2.14 | +13.43 |
| gap_fill | ZM | Asian | short | 337 | 57% | +1.14 | +10.56 |
| gap_fill | ZM | Asian | long | 316 | 57% | +1.15 | +10.26 |
| gap_fill | ZS | Asian | short | 324 | 56% | +0.96 | +8.87 |
| gap_fill | ZS | Asian | long | 320 | 56% | +0.92 | +8.73 |
| gap_fill | ZC | RTH | long | 133 | 69% | +0.85 | +7.89 |
| gap_fill | ZC | RTH | short | 135 | 66% | +0.77 | +6.98 |
| gap_fill_wide | ZC | Asian | short | 64 | 75% | +1.25 | +6.92 |
| gap_fill | ZS | London | long | 235 | 55% | +0.72 | +6.92 |
| gap_fill | ZS | London | short | 216 | 54% | +0.71 | +6.40 |
| gap_fill_wide | ZC | Asian | long | 56 | 79% | +1.38 | +6.37 |
| volume_spike_reversal | ZW | Asian | long | 25 | 80% | +1.40 | +5.72 |
| gap_fill | ZW | London | long | 144 | 49% | +0.51 | +3.64 |
| gap_fill | ZW | London | short | 154 | 47% | +0.40 | +3.25 |
| gap_fill | ZM | RTH | short | 45 | 60% | +0.70 | +3.25 |
| gap_fill | ZM | RTH | long | 36 | 61% | +0.68 | +2.98 |
| gap_fill | ZL | London | short | 101 | 48% | +0.42 | +2.75 |
| support_resistance_bounce | ZC | Asian | short | 45 | 29% | +2.39 | +2.69 |
| support_resistance_bounce | ZC | Asian | long | 56 | 29% | +1.65 | +2.62 |
| vol_spike_fade | ZW | Asian | long | 66 | 56% | +0.40 | +2.61 |
| order_block_d1 | ZM | London | long | 39 | 54% | +0.62 | +2.54 |
| vol_spike_fade | ZS | London | long | 69 | 55% | +0.38 | +2.50 |
| vol_spike_fade | ZC | Asian | long | 59 | 56% | +0.40 | +2.46 |
| order_block | ZL | RTH | long | 38 | 53% | +0.58 | +2.35 |
| volume_spike_reversal | ZS | Asian | long | 32 | 53% | +0.59 | +2.21 |
| volume_spike_reversal | ZM | London | long | 32 | 53% | +0.59 | +2.21 |
| vol_spike_fade | ZM | RTH | long | 28 | 61% | +0.52 | +2.20 |
| gap_fill | ZL | London | long | 90 | 43% | +0.38 | +2.20 |
| vol_spike_fade | ZM | RTH | short | 32 | 59% | +0.48 | +2.20 |
| vol_spike_fade | ZS | Asian | short | 66 | 53% | +0.33 | +2.10 |
| volume_spike_reversal | ZW | London | short | 26 | 54% | +0.62 | +2.06 |
| order_block_d1 | ZL | Asian | short | 60 | 47% | +0.40 | +2.05 |
| vol_spike_fade | ZC | London | short | 37 | 57% | +0.42 | +2.03 |

## Per-session breakdown

- **Asian**: 16 eligible of 187 cells
- **London**: 11 eligible of 188 cells
- **RTH**: 7 eligible of 190 cells
- **PostClose**: 0 eligible of 0 cells

## Next: stage in shadow mode

`scripts.stage_shadow_cells` reads the JSON and adds each
eligible cell to `state/strategy_validation.json:live_allowlist`
with `experimental: true, shadow_reason: 'universal discovery'`.
Brain emits signals; existing pipeline records to `shadow_trades`
and resolves outcomes nightly. After 2-4 weeks of live data,
`scripts.cell_auto_promote` flags cells whose shadow performance
matches predicted for real-money review.