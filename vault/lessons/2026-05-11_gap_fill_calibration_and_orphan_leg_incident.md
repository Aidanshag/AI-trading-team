---
date: 2026-05-11
tier: RULE
status: encoded
loss_usd: 137.89
symbols_affected: [ZN, ZT, ZB, ZF]
strategies_affected: [gap_fill]
sessions_affected: [Asian]
trigger_window: Sunday-Monday overnight 2026-05-10/11
related_lessons:
  - 2026-05-01 bracket OCO orphan-leg (supposedly fixed; this incident shows the fix is incomplete)
  - 2026-04-29 empty account_snapshots DLL breach (telemetry-blind safety floor)
---

# 2026-05-11 — gap_fill calibration breakdown + orphan-leg regression

## What happened

First Sunday-night live run of `live_trader.py`. Trader started 17:06 ET, scanned cleanly through the Sunday-reopen blackout (17:00-17:30 ET) and the PostClose session. At 20:32 ET (00:32 UTC Monday), session rolled to Asian, and the trader fired the first real trades of the night.

Pattern observed:
- 4 signals fired in two consecutive 5-min scans (00:32 + 00:37): ZN long, ZT long, ZB short, ZF short
- All from `gap_fill` strategy in Asian session
- Stop distances were 0.1–0.5 ticks after rounding (sub-tick)
- Targets were 1 tick from strategy entry
- The trader's marketable-limit buffer is 5 ticks

Within ~5 minutes of the ZB SHORT placement, the broker's BUY-stop leg (priced at 113.3125, supposed to close a hypothetical short position) triggered standalone — because the ZB SHORT entry-limit at 113.125 had never filled. The stop opened an unintended LONG at 113.3125. Price ran against it, closed manually via `scripts/flatten.py` at a loss of $137.89 net.

## Two failure modes — both reproducible, both encoded

### Failure mode A — calibration breakdown in low-vol regimes

The `gap_fill` strategy computes `stop = entry ± 0.5 × ATR(14)` on 5-minute bars. In Sunday Asian session, ATR on treasury futures collapses to ≤1 tick. After `_round_to_tick`, stop and entry round to the SAME PRICE — degenerate stop.

In the strategy code, the rr-check `(entry - target) / max(entry - stop, 1e-9) >= rr_target` then divides by 1e-9 → ratio is enormous → **every signal passes**, no matter the actual R-distance. The strategy emits these degenerate signals as "high-conviction."

The trader then applies a 5-tick marketable-limit buffer (slippage allowance). When the strategy's stop-distance is < 5 ticks, the buffer DOMINATES the strategy's intended risk frame. Any fill at the marketable limit is immediately past the target.

**Why backtest didn't catch this:** the same sub-tick stops produce idealized R-multiples in the backtest engine (because exit-at-stop hits at zero loss when stop == entry). The originally-cited t-stats of +7.95 to +11.76 for gap_fill on treasuries are calibrated against this broken pipeline. They aren't lies — they're correctly computed values of a meaningless metric.

→ **encoded** (live, defense-in-depth):
- `scripts/live_trader.py:MIN_SIGNAL_R_TICKS = 6` — gate at trader layer rejects any signal whose stop OR target distance is < 6 ticks (above the 5-tick buffer). 11 unit tests in `tests/test_live_trader.py`.
- `tools/backtest/strategies.py:gap_fill()` — added `min_stop_ticks=3` + `tick_size` params. When tick_size is provided, the strategy itself refuses to emit sub-floor signals. 3 unit tests in `tests/test_strategies.py`. Backwards-compatible (no tick_size = old behavior).
- `scripts/daily_strategy_validation.py:collect_trades()` — injects tick_size from `_tick_size_for_symbol()` lookup for strategies that declare the parameter. Future preflight runs validate gap_fill with the floor active.
- `scripts/param_sweep.py:run_strategy()` — same inspect-based injection for the parameter-sweep harness.

### Failure mode B — orphan-leg regression

`scripts/live_trader.py:place_bracket()` placed entry-limit + stop-limit + target-limit as three SEPARATE broker orders, back-to-back. ProjectX has no native bracket OCO linkage on this account; the orders are independent.

When the ZB SHORT entry-limit at 113.125 never filled (price didn't rally to it), the protective BUY-stop at 113.3125 continued to "protect" a position that didn't exist. Price rose to 113.3125, the stop triggered, and instead of closing a non-existent short, the BUY *opened* an unwanted LONG.

The "fix" recorded in project history (2026-05-01) was supposed to address this. Tonight's incident shows that fix was incomplete or had regressed — the protective legs were placed regardless of entry fill.

→ **encoded:**
- `scripts/live_trader.py:place_bracket()` — rewired. Now:
  1. Snapshot baseline position signature for the contract (`_position_signature`).
  2. Place entry-limit.
  3. Poll for signature change up to 30 seconds (`_wait_for_entry_fill`).
  4. If filled: place stop + target. If timeout: cancel entry; protective legs NOT placed.
- 6 unit tests in `tests/test_live_trader.py` covering the helpers.

## How to apply / future detection

**For every NEW strategy added to the registry:**
- Does it set stops as a multiple of ATR or volatility? → must accept `tick_size` + `min_stop_ticks` kwargs and floor the stop distance.
- Has it been validated with a per-symbol tick_size injection? → if no, the validation may be unreliable.

**For every change to live_trader's `place_bracket` or signal pipeline:**
- Are protective legs placed before entry confirmation? → fail.
- Is there a poll-for-fill or equivalent mechanism? → required.

**Whenever t-stats look "too good":**
- Check the per-trade risk_ticks metric. If close to zero, the metric is unreliable.
- The backtest engine's `Trade.stop_price` carry-through is suspected broken; see `vault/research/analysis/2026-05-11_gap_fill_wide_validation_attempt.md`. Until that's fixed and re-validated, treat any gap_fill family edge claim as provisional.

## Open items (for user review)

1. **Wire live_trader to pass tick_size to strategy_fn** (`find_latest_signal`). Currently the strategy patch is dormant in live (still relies on the trader-layer gate for safety). Architecturally cleaner to move the floor into the strategy.
2. **Fix backtest engine `Trade.stop_price` carry-through.** This is the load-bearing fix for re-validating any strategy in the gap_fill family.
3. **Decide whether to keep `gap_fill` in live filter at all.** If post-fix validation shows it doesn't survive realistic slippage, demote and look elsewhere.
