---
type: reference
status: ACTIVE
updated: 2026-05-15
purpose: Single canonical reference for what fires when on profit-taking + loss-cap exits. Read this before changing any exit-rule code.
---

# Exit ladder — what fires when, in order

The trader's `tools/profit_protect.check_and_close` runs every ~1-10 seconds on each open position. It evaluates rules in PRIORITY ORDER — the first rule to fire executes a close via `client.close_position()`, and subsequent rules are skipped for that scan.

## The ladder (top to bottom — first match wins)

| # | Rule | When it fires | Source |
|---|---|---|---|
| 0 | **Software target hit** | `unrealized >= _target_usd_by_contract[cid]` (set by `bracket_placement.place_bracket` at fill from `signal['target']`) | `profit_protect.py` ~700 |
| 1 | **Time-based profit decay** | Peak hit > `TIME_DECAY_MINUTES_STALE` (15) min ago AND `current < peak * (1 - TIME_DECAY_RETRACE_FRACTION)` (current < 70% of peak) | `_is_profit_stale()` |
| 2 | **Reversal-detection exit** | Peak ≥ `REVERSAL_MIN_PEAK_USD` (15) AND last `REVERSAL_BARS_REQUIRED` (3) consecutive 1-min closes form a strict descent (long) or ascent (short) | `_detect_reversal()` |
| 3 | **Percent-of-peak floor** | Peak ≥ `MIN_PEAK_FOR_FLOOR_USD` (20) AND `current < max($20, peak * (1 - RETRACE_CAP_FRACTION))` (30% retrace default) | `_compute_active_floor()` |
| 4 | **decide() trailing-tier** | `RUNNER_ZONE_TIERS` for peaks > $750 (mechanical backstop for big winners — uncapped) | `decide()` |
| 5 | **Hard loss cap** | `unrealized <= -LOSS_TIER_HARD_CAP_USD` ($150) | `decide()` |
| 6 | **Broker-side stop order** | Server-side; fires on price touch. Trailed UP as peak grows via `_trail_broker_stop_to_floor()` (cancel + replace). | place_bracket entry path |

Rules 0-3 are post-fill, software-side, and tick-stream-driven (sub-second). Rule 4 is the runner-zone backstop. Rule 5 is the loss-cap insurance. Rule 6 is the OS-level safety floor.

## Why the ordering matters

- **Software target before everything else** — if strategy says "take profit at +$30," we honor that even if a tighter rule would have fired first
- **Time decay before reversal** — stale peaks are a stronger signal than a single reversal pattern; we'd rather close a tired trade than wait for 3 lower closes
- **Reversal before percent-of-peak** — structural signal (3 bars-against) outranks mechanical retrace
- **Percent-of-peak before runner tiers** — for mid-size peaks ($20-$750), the continuous retrace cap is tighter than the runner-zone tiers

## Tick stream interaction (2026-05-15)

All these rules now read `current` from the SignalR tick cache (`tools/tick_stream.py`) when fresh (<30s old). Falls back to 1-min bar close polling if cache stale. **Latency for rule evaluation dropped from 0-60s to ~50-200ms.**

## Parameter calibration — what the data says

From the 2026-05-15 counterfactual replay (`scripts/replay_exits.py`) against this week's 27 trades:

| Run | Counterfactual P&L | vs Actual (−$128.50) |
|---|---|---|
| Actual realized | −$128.50 | baseline |
| Default new rules | +$49.50 | +$178 |
| **Calibrated rules** | **+$153.50** | **+$282** |

Calibration sweep winners (`scripts/tune_exits.py`):

| Parameter | Default | Tuned | Reason |
|---|---|---|---|
| `RETRACE_CAP_FRACTION` | 0.30 | 0.40 | Let trades retrace more before exit fires |
| `MIN_PEAK_FOR_FLOOR_USD` | $20 | $30 | Don't apply floor to small peaks; they should run |
| `REVERSAL_BARS_REQUIRED` | 3 | 4 | Be more sure of reversal before triggering |
| `REVERSAL_MIN_PEAK_USD` | $15 | $10 | Fire reversal on smaller wins too |
| `TIME_DECAY_MINUTES_STALE` | 15 | 20 | Wait longer for time-decay to fire |
| `TIME_DECAY_RETRACE_FRACTION` | 0.30 | 0.15 | Tighter retrace once stale |

**Tuned values are NOT in the running code.** 27 trades is a small sample with heavy overfit risk. Live shadow validation (Phase 4 — measure peak_pct_captured weekly via sentinel) will confirm direction. After 2-4 weeks of live data, promote tuned values or revert.

The pattern in the data: **let winners run longer (higher peak thresholds, more retrace allowed), but be tighter when we DO act (smaller retrace on time-decay).**

## Measurement loop (added 2026-05-15)

Every profit_lock close now records `peak_pct_captured` in the decisions audit trail. The sentinel `check_peak_capture_weekly` aggregates this into a single weekly health metric:

- **≥30%** = healthy (info-level finding)
- **<30%** = warn-level finding; exit rules underperforming OR signals are stop-firing before peaks develop

This closes the "did the rebuild work?" loop — we'll know within 7 days of live data whether the new rules deliver in production what they did in replay.

## Files that touch the exit ladder

| File | Role |
|---|---|
| `tools/profit_protect.py` | All the rule logic + parameters |
| `tools/bracket_placement.py` | Places entry, registers software target, post-fill slippage check |
| `tools/tick_stream.py` | Sub-second price feed; `check_and_close` reads from this cache |
| `tools/sentinel.py` | `check_peak_capture_weekly` measures effectiveness |
| `scripts/live_trader.py` | Calls `check_and_close()` every scan |
| `state/strategy_validation.json` | Per-cell `walkforward_oos` + `shadow_history` (not yet wired to per-cell exit params; future) |

## Open work (post-weekend)

1. **Per-cell exit parameter overrides** — different cells may want different `RETRACE_CAP_FRACTION`. Implement via `live_allowlist[i].exit_params` JSON object that overrides global defaults.
2. **Phase 4: broker target leg re-test** — `SKIP_TARGET_LEG=True` since 5/11 anomaly. Test if lifted with a small trade Sunday.
3. **Walk-forward exit params per cell** — once we have ≥2 weeks of live capture data, run the tune_exits sweep per (strategy, symbol, session) cell.
