---
date: 2026-05-08
kind: slippage_sensitivity_grid
scope: 21 strategies × 10 symbols × 60d × 4 slippage levels
total_signals: 73,531
output_csv: (in scripts/backtest_full_grid_slippage.py output)
---

# Slippage sensitivity grid — only `gap_fill_wide` survives realistic slippage

## Headline finding

The current `live_allowlist` (`gap_fill` on ZB/ZF/ZN/ZT) is highly vulnerable
to slippage. At realistic 0.25 tick/side, the strategy's +$81k 60-day edge
flips to **-$113k**. Edge survives only at near-zero slippage.

**Only `gap_fill_wide`** maintains positive expectancy across all tested
slippage levels (0.0 / 0.25 / 0.5 / 1.0 ticks per side).

## Strategy-level table

| Strategy | n | 0.0 slip | 0.25 slip | 0.5 slip | 1.0 slip |
|---|---|---|---|---|---|
| **gap_fill_wide** | 106 | **+$12,785** | **+$9,840** | **+$6,895** | **+$1,006** |
| pullback_in_trend | 5 | +$262 | +$180 | +$99 | -$63 |
| range_mean_reversion | 8 | +$270 | +$83 | -$103 | -$476 |
| volatility_breakout | 7 | +$168 | +$15 | -$138 | -$444 |
| rsi2_extreme_reversion | 1649 | +$15,963 | **-$7,080** | -$30,124 | -$76,210 |
| **gap_fill** (allowlist) | 4206 | **+$81,414** | **-$113,171** | -$307,756 | -$696,925 |
| (others) | | various | progressively worse | catastrophic | catastrophic |

## Top per-cell candidates at realistic 0.25 ticks/side slippage

These cells maintain edge AFTER slippage. Most are NOT currently in the
live_allowlist.

| Cell | n | Clean 60d | Realistic 60d (0.25 slip) |
|---|---|---|---|
| `rsi2_extreme_reversion \| CL` | 128 | +$25,396 | **+$24,006** |
| `rsi2_extreme_reversion \| ES` | 242 | +$19,007 | +$15,501 |
| `gap_fill \| 6E` | 59 | +$7,260 | +$6,367 |
| `rsi2_extreme_reversion \| NG` | 250 | +$8,558 | +$5,608 |
| `gap_fill \| NG` | 120 | +$7,893 | +$5,053 |
| `gap_fill \| ES` | 36 | +$5,035 | +$4,629 |
| `gap_fill_wide \| ZT` | 31 | +$2,175 | +$1,058 |

## Implications for Sunday's deployment

The Sunday Globex reopen run is now critical primarily as a **slippage
measurement**, not a profit-prediction. Three possible outcomes:

1. **Actual broker slippage ~0**: gap_fill works as backtested. Combine math holds.
2. **Actual slippage 0.10–0.25**: gap_fill marginal; switch to gap_fill_wide cells.
3. **Actual slippage > 0.25**: current allowlist broken. Need wider-stop strategies.

## What's already happening to address this

- `scripts/slippage_tracker.py` is in place — will populate
  `vault/research/live_slippage/<date>_per_cell.md` after Sunday fills land.
- Cowork backlog P0: parameter sweep framework includes gap_fill robustness
  variants. If gap_fill_wide validates with bigger n, it becomes the primary
  candidate.
- Cowork backlog P0: auto-promote/demote cells from live evidence will
  surface which cells actually work in live vs which decay due to slippage.

## Decision: do NOT change live_allowlist before Sunday

Reasoning:
- Sunday IS the slippage measurement. Changing allowlist now means we lose
  the controlled experiment.
- gap_fill_wide produces only 106 trades over 60d → very few Sunday signals
  to learn from.
- Brain's validation pipeline correctly hasn't promoted slippage-resistant
  cells (small samples). Trusting validation remains the right call.

## Action items for Monday morning analysis

1. Run `scripts/slippage_tracker.py` — measure actual per-cell slippage
2. Compare to this grid's predictions
3. If actual ≥ 0.25 ticks/side: open PR to swap allowlist toward
   gap_fill_wide cells + rsi2 cells (conditional on cowork's auto-promote
   landing first)
4. If actual < 0.10 ticks/side: keep current allowlist, scale up trade caps
