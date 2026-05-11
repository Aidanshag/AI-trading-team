---
type: autonomous_investigation
date: 2026-05-11
author: Claude Code (CLI)
trigger: User authorized autonomous overnight validation of gap_fill_wide swap (2026-05-10 evening, post-incident)
status: investigation complete; recommendation: DO NOT SWAP, AND demote gap_fill itself
revision: 2026-05-11 04:50 UTC - fixed typo in param_sweep risk_ticks measurement (t.stop_price → t.stop), re-ran sweeps, conclusions strengthened
---

# Autonomous validation: gap_fill_wide as drop-in replacement for gap_fill

## Headline

**Two recommendations:**

1. **Do NOT swap to `gap_fill_wide`.** It doesn't validate under any of 144 tested parameter combinations.
2. **Plain `gap_fill` also doesn't validate** under the corrected pipeline. The "validated edge" cited as the fund's primary alpha (t-stats +7.95 to +11.76) was a product of three compounding bugs in the validation pipeline. Under realistic stop floors enforced in both backtest AND live, neither variant produces a deployable parameter set on 60 days of treasury data.

This is a foundational finding — the fund's strategic narrative (gap_fill as the validated headline edge on ZN/ZT/ZB/ZF, locked-in 2026-05-06) is materially compromised. **User decision required:** demote gap_fill family from live_allowlist; reopen the strategy-discovery question.

## Timeline

### Night of 2026-05-10 → 11
- 20:32 ET: 2 long signals (ZN/ZT) placed via live_trader. Stop distances 0.1-0.5 ticks.
- 20:37 ET: 2 short signals (ZB/ZF) placed. Same sub-tick stop pattern.
- 20:38 ET: I halted the trader after diagnosing calibration issue.
- 20:40 ET: ZB protective stop fired alone (entry-limit never filled), opened unintended LONG. Flatten closed it at −$137.89.
- 20:50 ET: Shipped trader-side fixes: MIN_SIGNAL_R_TICKS=6 gate + orphan-leg fix (wait-for-fill before placing protective legs). Tests pass. Trader restarted with fixes active.
- 21:21 ET: Trader resumed under halt; subsequent Asian scans confirmed gate working (3-4 degenerate signals per scan, all blocked, 0 placements).
- 23:48 ET: User cleared halt for live observation.
- 00:13 UTC: First param sweep on gap_fill_wide. *Looked good* (best ZB E=+1.02R, t=+5.79) but `mean_risk_ticks=0.00` smelled wrong.
- 00:25 UTC: Identified missing tick_size injection in param_sweep. Patched. Re-ran sweep — drastically fewer qualifying cells.
- 04:30 UTC: User authorized step-1 strategy fix + further autonomous work.
- 04:35 UTC: Patched `gap_fill` strategy with min_stop_ticks/tick_size params. Patched daily_strategy_validation to inject tick_size. Added tests.
- 04:42 UTC: Found the actual root cause of `mean_risk_ticks=0.00`: typo in param_sweep (`t.stop_price` vs `t.stop`). Fixed.
- 04:43 UTC: Re-ran gap_fill_wide sweep with full corrected pipeline. Risk_ticks now median=3.0 (floor enforced). Still no qualifying variant.
- 04:48 UTC: Re-ran plain gap_fill sweep with corrected pipeline. **Plain gap_fill also fails to validate.** Max OOS n=5.

## What I fixed and shipped

### Live trader (running now, PID 33112)
- `scripts/live_trader.py:MIN_SIGNAL_R_TICKS = 6` + `signal_passes_min_r_gate()` — rejects sub-buffer signals at trader layer. 11 unit tests.
- `place_bracket()` rewired — wait for fill before placing protective stop/target. `_position_signature()` + `_wait_for_entry_fill()`. 6 unit tests covering helpers.
- `find_latest_signal(symbol=...)` — injects tick_size to strategies that declare it. 3 unit tests. (Not yet active in running trader — pending restart on user review.)

### Strategy library
- `tools/backtest/strategies.py:gap_fill()` — added `min_stop_ticks=3` + `tick_size: float | None = None` params. When tick_size is supplied, the strategy refuses to emit sub-floor stops. Backwards-compatible: tick_size=None means old behavior. 3 unit tests.

### Validation pipeline
- `scripts/param_sweep.py:run_strategy()` — fixed `t.stop_price` → `t.stop` typo (Trade dataclass attribute is `.stop`). Added `inspect`-based tick_size injection for strategies that declare it.
- `scripts/daily_strategy_validation.py:collect_trades()` — added `_tick_size_for_symbol()` lookup + same inspect-based injection. Future preflight runs will validate gap_fill family with stop floors active.

### Tests
- 14 new unit tests across `tests/test_live_trader.py` + `tests/test_strategies.py`. Full suite: **305 → 319 passing**.

## The compounding bugs that hid the truth

**Bug 1: missing tick_size in validation calls.**
`gap_fill_wide` was created 2026-05-08 with a `min_stop_ticks=3` floor (only active when `tick_size` is provided). The validation pipeline never passed tick_size, so the floor never fired. Backtest stops were free to collapse to whatever `0.5×ATR` evaluated to — sub-tick in low-vol sessions.

**Bug 2: typo in risk_ticks measurement.**
`param_sweep.py` line 184 read `t.stop_price`, but the Trade dataclass attribute is `t.stop`. AttributeError was silently caught by a broad `except Exception: pass`, so the `risk_ticks` metric was always 0 across every sweep ever run. We had no way to notice that stops were collapsing.

**Bug 3: silent default in the rr-check ratio.**
The strategy code has `(target - entry) / max(entry - stop, 1e-9) >= rr_target`. When stop collapsed to entry, `max(0, 1e-9) = 1e-9` → ratio is enormous → every signal "passes" rr_target check regardless of actual R. Combined with bug 1, the strategy emitted degenerate signals as "high-conviction." Combined with bug 2, we couldn't detect them.

These three bugs together produced gap_fill's reported t-stats of +7.95 to +11.76 over n=240+ trades. Under the corrected pipeline, those numbers vanish.

## Final sweep results (corrected pipeline)

### gap_fill (currently live)
- 64 cells tested. No cell meets n≥30 AND t≥1.5.
- Max OOS n: 5
- Best E across all cells: ZF at +0.40R (n=5)
- Best $-net at 0.25-tick slip: +$5/trade (ZF)
- Output: `vault/research/param_sweeps/gap_fill_2026-05-11_0443.{csv,md}`

### gap_fill_wide
- 144 cells tested. No cell meets n≥30 AND t≥1.5.
- Max OOS n: 5
- Same pattern as gap_fill — the wider stops just mean fewer signals.
- Output: `vault/research/param_sweeps/gap_fill_wide_2026-05-11_0440.{csv,md}`

### Why so few trades?
60 days × 4 sessions × 4 symbols × stops floored at 3 ticks = the natural firing frequency just isn't there at this data window. This MIGHT be a data-window issue (1-year window could give n≥30), or it might be that the gap_fill class of edge is fundamentally weak after stop-floor enforcement. Distinguishing the two requires re-running with a longer history — yfinance only ships 60d of 5m intraday data so we'd need an alternative source.

## Recommendations (user review required)

### Immediate (can do tonight on user approval, no further investigation needed)
1. **Empty the gap_fill family from `live_strategies_filter`.** Currently `state/strategy_validation.json` has gap_fill on ZN/ZT/ZB/ZF locked in. With no validated edge, leaving it live means: every scan emits degenerate signals → gate blocks them → zero trades and zero revenue. Cleaner to make the no-trade state explicit.
2. **Restart live_trader** to pick up the strategy patch + find_latest_signal wiring. After restart, the strategy itself won't emit degenerate signals; trader logs will be cleaner.

### Strategic (require user judgment)
1. **Get a longer data series** to fairly re-validate. yfinance 60d is too short. Options: Polygon, IBKR historical, Topstep tick data. Re-validate gap_fill + gap_fill_wide on a 1+ year window before drawing a final conclusion.
2. **Reopen strategy discovery.** If gap_fill doesn't survive on longer data either, the fund needs a new source of edge. The Quant Researcher agent's prior `cross_asset_divergence_zn` proposal could be revisited.
3. **CLAUDE.md edit:** the "Strategic focus — gap_fill on ZN/NG/6E (validated 2026-05-04)" section materially misstates current reality. Should be flagged with a 2026-05-11 correction note pending re-validation on real data.

### Don't do
- **Don't restart trader to remove the gate.** The MIN_SIGNAL_R_TICKS=6 gate at the trader layer is the safety net even when the strategy patch is wired. Defense-in-depth.
- **Don't drop gap_fill_wide from the strategy library.** It's correct code; just doesn't have validated parameters. Worth keeping for future re-validation.

## Live system state (write-time 04:50 UTC)

- Trader: PID 33112 (worker), alive, scanning every 5 min
- Halt: cleared
- Account balance: $49,278.86
- Open positions: 0
- Working orders: 0
- Trades placed since resume: 0 (gate blocking all signals)
- Tests: 319/319 passing

The trader is safe; it's just not making money tonight. That's the honest state.
