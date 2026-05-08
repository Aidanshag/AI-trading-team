---
date: 2026-05-08
kind: full_grid_backtest
scope: 21 strategies × 10 symbols × 24 hour-of-day buckets
data: 60d 5m bars (yfinance)
total_signals: 73,361
output_csv: vault/research/backtests/2026-05-08_full_grid.csv
---

# Full grid backtest — strategy × symbol × hour-of-day

## Headline

Of 21 strategies tested, **only 3 show real edge**:

| Strategy | n | Hit% | Total 60d | Notes |
|---|---|---|---|---|
| `gap_fill` | 4,206 | 61% | **+$81,414** | The workhorse — large n, robust hit rate |
| `rsi2_extreme_reversion` | 1,645 | **9%** | +$12,923 | Tail-driven (rare big wins) — needs cell-level investigation |
| `gap_fill_wide` | 106 | 67% | +$12,785 | Selective high-conviction variant of gap_fill |

The other 18 strategies range from marginal losers to **catastrophic** at default params:
- `narrow_range_break`: -$616k (n=14,832, 27% hit) — must NEVER fire live
- `inside_bar_break`: -$562k (n=14,872, 31% hit) — same
- `fair_value_gap`: -$142k (n=9,308, 34% hit) — already demoted, default params confirmed bad
- `opening_range_breakout`: -$120k — bad as configured

These 4 collectively cost -$1.44M over 60d in this simulation. The brain's validation pipeline already screens them out of `live_allowlist`, but they remain in `STRATEGY_REGISTRY` for parameter-tuned re-entry.

## Hour-of-day P&L profile (best strategy per hour)

| Hour ET | Best strategy | n | Total 60d |
|---|---|---|---|
| 0 (8pm) | rsi2_extreme_reversion | 71 | +$8,425 |
| 1 (9pm) | rsi2_extreme_reversion | 60 | +$8,902 |
| 5 (5am) | gap_fill | 99 | +$6,881 |
| **6 (6am)** | **gap_fill** | 95 | **+$10,040** |
| 7 (7am) | rsi2_extreme_reversion | 96 | +$9,317 |
| **9 (9am — RTH open)** | **rsi2_extreme_reversion** | 90 | **+$12,352** |
| **18 (6pm — PostClose)** | **gap_fill** | 225 | **+$12,998** |
| 19 (7pm) | gap_fill | 459 | +$8,394 |
| 22 (10pm) | gap_fill | 393 | +$8,353 |
| **23 (11pm)** | **rsi2_extreme_reversion** | 63 | **+$14,535** |
| 11–14 (RTH lunch) | (marginal) | small | small |

**Two peak edge corridors:**
- **PostClose → Asian start (18:00–01:00 ET)** — gap_fill + rsi2 alternating, ~$50k of total edge
- **Pre-RTH → RTH open (06:00–09:00 ET)** — gap_fill into rsi2, ~$30k of total edge

**RTH lunch (11:00–14:00 ET) is dead** — confirms session-bucketed analysis. RTH dead zone for treasury-focused strategies.

## Deeper finding: gap_fill on NG and 6E

Both were in the original 2026-05-04 validated set per CLAUDE.md but got demoted in subsequent walk-forward runs (samples thinned). This grid confirms they retain edge over 60d:

- `gap_fill|NG|hour=18` = +$3,551 (n=26, 50% hit)
- `gap_fill|6E|hour=18` = +$3,104 (n=21, 48% hit)
- `gap_fill|6E|hour=22` = +$3,475 (n=91, 48% hit, total all sessions)

**Brain status**: still in shadow — samples too thin to clear `n>=20 + t>=1.5` promotion threshold in the validation pipeline. **Do NOT manually promote.** Let shadow trades organically accumulate; brain will promote when statistically warranted (this is Pattern B "wrong-context validation" defense from CLAUDE.md).

## rsi2_extreme_reversion: tail-driven edge — needs investigation

- 1,645 trades, 9% hit rate, +$12,923 total
- Wins are rare but huge (+$140 to +$3,200/trade)
- Asymmetric risk: a 10% degradation in tail behavior could turn this strongly negative
- Concentrated in specific cells: ES @ hour 9 (n=5, +$3,222/trade) — almost certainly tail outliers

**Quant Researcher action item**: drill into the 1,645 trades. Identify the 5-10 cells driving the +$12.9k. Determine whether the tail edge is structural (extreme oversold bouncing) or sample-luck. If structural, propose a `rsi2_*` parameter sweep to find robust cells.

## What's already encoded vs gap

**Already encoded (correct):**
- Brain's `STRATEGY_CELL_ALLOWLIST` filters to gap_fill on validated treasury cells
- Validation pipeline keeps shadow cells out until n≥20 + t≥1.5
- Catastrophic strategies (narrow_range, inside_bar, etc.) never enter `live_allowlist`

**Open gaps (low priority, for follow-up):**
1. No `STRATEGY_DENYLIST` exists — catastrophic strategies could in principle re-enter via daily validation if a freak window matched their thresholds. Belt-and-suspenders: hardcode them out.
2. No "lunch dead zone" gate — could skip new entries 11:00–14:00 ET. Brain change, low value (most cells aren't RTH anyway).
3. No dollar-volume-weighted ranking — current grid uses raw P&L; a Sharpe-like or risk-adjusted metric would deprioritize tail-driven cells.

## Files

- Raw cell-level data: `vault/research/backtests/2026-05-08_full_grid.csv`
- Backtest script: `scripts/backtest_full_grid.py` (idempotent, can re-run as data refreshes)
