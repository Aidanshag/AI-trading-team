---
type: autonomous_investigation
date: 2026-05-11
author: Claude Code (CLI)
trigger: User authorized autonomous overnight validation of gap_fill_wide swap (2026-05-10 evening, post-incident)
status: investigation complete; recommendation: DO NOT SWAP
---

# Autonomous validation: gap_fill_wide as drop-in replacement for gap_fill

## Headline

**Recommendation: do NOT swap `live_strategies_filter` from `gap_fill` to `gap_fill_wide`.**

Two parameter sweeps were run overnight. Neither produced a deployable parameter set meeting the gates (n≥25, t≥1.5, E>0 OOS). On top of that, the validation infrastructure has its own bugs that need fixing before we can trust *any* gap_fill family numbers.

## Why we tried

User noted (correctly) that `gap_fill_wide` was created 2026-05-08 specifically to address the sub-tick-stop bug that caused tonight's $137.89 loss. The variant exists in `tools/backtest/strategies.py` with the right design intent:
- `min_gap_atr` 0.75 → 1.5 (only fire on larger gaps)
- `stop_atr_mult` 0.5 → 1.5 (wider ATR-based stops)
- `min_stop_ticks=3` floor when `tick_size` is provided

But the live config still references plain `gap_fill`. Today's autonomous job was to either validate `gap_fill_wide` for promotion or surface why we can't.

## What ran

Sweep #1: `gap_fill_wide` × {min_gap_atr ∈ [0.5, 0.75, 1.0, 1.25]} × {stop_atr_mult ∈ [1.0, 1.5, 2.0]} × {rr_target ∈ [1.0, 1.25, 1.5]} × {ZN, ZT, ZB, ZF}. 144 combinations.

- Output: `vault/research/param_sweeps/gap_fill_wide_2026-05-11_0400.{csv,md}`
- **Result:** Best variant `ZB min_gap=0.5/stop=1.0/rr=1.5` showed OOS n=54, E=+1.02R, t=+5.79. *Looked* publishable until I noticed:
- **`mean_risk_ticks: 0.00` across all 144 cells.** Stops collapsed to sub-tick.
- Root cause: `scripts/param_sweep.py:run_strategy` calls `backtest_strategy(strategy_fn, bars, symbol, params=params)`. The `params` dict from the grid doesn't include `tick_size`, so `gap_fill_wide` is invoked with `tick_size=None`. Per the strategy code:
  ```python
  min_stop_price = (min_stop_ticks * tick_size) if tick_size else 0
  ```
  With `tick_size=None`, the floor is 0 → `min_stop_ticks=3` is a no-op → backtest stops collapse to whatever `stop_atr_mult × ATR` evaluates to, which on low-vol bars is sub-tick.

So sweep #1's "+1.02R" numbers are not real — they're computed against idealized zero-distance stops.

## What I patched

`scripts/param_sweep.py:run_strategy` — added `inspect.signature(strategy_fn)` check; if the strategy accepts a `tick_size` parameter and the user didn't supply one, the symbol's tick_size from `TICK_ECONOMICS` is injected automatically. Safe: only fires for strategies that explicitly declare `tick_size`.

Sweep #2 ran with the patch active.

## Sweep #2 results (with proper tick_size injection)

- Output: `vault/research/param_sweeps/gap_fill_wide_2026-05-11_0406.{csv,md}`
- **No qualifying variant for any symbol** under the gates (n≥30, t≥1.5).
- Max OOS n across all 144 cells: **5**.
- For comparison: pre-patch sweep showed OOS n up to 222 on the same cell (ZB 0.5/1.0/1.0). With the floor active, that drops to 5. That's a 44× reduction in firings.

Interpretation: with realistic min-stop-ticks=3 enforced, the strategy fires too rarely to validate over a 15-day OOS holdout from 60d of data.

## Deeper finding

`oos_mean_risk_ticks: 0.00` *also* in sweep #2 — even after the patch. The Trade objects returned by `backtest_strategy` don't appear to carry `stop_price` through cleanly, so the param_sweep's `risk_ticks` measurement is unreliable independent of strategy parameterization. This means the t-stats originally quoted for plain `gap_fill` (+7.95 to +11.76) **are also suspect** — they were calculated under the same broken pipeline.

## Recommendation

1. **Keep the current setup** (gap_fill in live_allowlist + `MIN_SIGNAL_R_TICKS=6` gate in `live_trader.py`).
   The gate catches the degenerate signals at the placement layer; observed live tonight, it's working as designed (every Asian-session scan has produced 3-4 blocks per scan, 0 placements).
2. **Fix the backtest engine's Trade.stop_price carry-through** before re-validating ANY gap_fill family variant. Until that's fixed, all walk-forward numbers in this strategy family are not trustworthy.
3. **Once the engine is fixed, re-run sweeps on BOTH variants** with proper stop floors active. Then make the swap decision on real numbers.
4. **Hold off on declaring gap_fill the "validated headline edge"** in CLAUDE.md until step 3 confirms. The 2026-05-04 walk-forward claims may not survive proper stop accounting.

## Files modified tonight

- `scripts/live_trader.py` — added `MIN_SIGNAL_R_TICKS=6`, `signal_passes_min_r_gate()`, `_position_signature()`, `_wait_for_entry_fill()`. Rewired `place_bracket()` to wait-for-fill before placing protective legs. **Both fixes are running live now.**
- `tests/test_live_trader.py` — 11 new tests for the gate + orphan-leg helpers. All pass.
- `scripts/param_sweep.py` — tick_size injection patch (per above).
- Reports saved to `vault/research/param_sweeps/` and `vault/research/analysis/`.

## Live system state at report write-time (2026-05-11 04:10 UTC)

- Trader: PID 33112 (worker) + PID 900 (launcher), alive, scanning every 5 min
- Halt: cleared 03:48 UTC
- Account balance: $49,278.86 (−$137.89 from preflight start, due to overnight orphan-leg incident now fixed)
- Open positions: 0
- Working orders: 0
- Scans since resume: ~6, all surfacing 3-4 gap_fill signals per scan, ALL BLOCKED by the new gate, 0 placements
- Discord alerts wired and tested
