---
type: backlog
purpose: Prioritized queue of fund improvements, consumed by /improve-fund autonomous cycles
---

# Improvement backlog

This file is the work queue for the autonomous-improvement loop. Each entry has explicit priority, effort, risk, and status fields so cycles can pick items mechanically.

## Format

```
- [P0|P1|P2|P3] [effort: Nmin] [risk: low|medium|high] [status: open|in-progress|proposed|merged]
  Title — one-line description
  Why: motivation
  Files: target files (best guess)
  Acceptance: how to know it's done
  Auto-merge: true|false (default false)
```

---

## ⚡ STANDING REFRAME 2026-05-08

User directive: **"close the gap between looks great and actually works
good in production."**

Priority logic going forward:
- Measurement / validation infrastructure > new strategies
- Reduce unknowns > optimize known knowns
- Each change must specify: prediction → measurement plan → variance trigger
- If a P0 item below adds complexity without enabling validation, demote it

## 🆕 Queued 2026-05-14 late — REAL-TIME PRICE FEED (research)

- [P0] [effort: 90min — investigation] [risk: none] [status: open] [autonomous-eligible: yes]
  **Real-time price feed: WebSocket or quote endpoint?** — current in-position polling reads 1-min bar closes via `tools/bar_fetcher.fetch_bars(client, sym, 1, 5)`. That means we have up to ~60s of staleness in the price data even though the poll itself runs every 1s. For exit timing (profit-lock fires when unrealized crosses tier, software take-profit fires when unrealized hits target), this latency matters — tonight 10+ trades had positive peaks but execution slippage cost most of them.
  Investigation steps:
  1. Check ProjectX API for a real-time quote endpoint (single-symbol, sub-second). e.g., `GET /api/MarketData/quote/{contractId}`. Test with a sample call.
  2. Check ProjectX for a WebSocket / SignalR feed for live ticks. Look at `tools/projectx_client.py:_ENDPOINTS` and the API base URL `https://api.topstepx.com` for any streaming endpoint hints.
  3. If a quote endpoint exists: easy swap in `tools/bar_fetcher.py` or a new `tools/quote_fetcher.py` for the in-position path only.
  4. If only WebSocket: more engineering but bigger win. Subscribe-on-open, unsubscribe-on-close, handle reconnects.
  Files: `tools/projectx_client.py`, possibly new `tools/quote_fetcher.py` or `tools/tick_stream.py`. Observation log in `vault/research/analysis/`.
  Acceptance: documented mechanism for getting sub-second price data + recommendation on swap-in path.
  Auto-merge: no — research, not a code change yet. The autonomous routine writes findings; user reviews.
  Mitigation already in place 2026-05-14: in-position polling tightened to 1s (was 2s), and trailing BROKER stop handles execution at native tick speed once the stop is placed correctly. So even with 60s-stale poll data, the broker is the real exit engine — polling is just for updating the trailed stop.

## 🆕 Queued 2026-05-14 — BROKER LIMIT FILL ANOMALY (investigate)

- [P0] [effort: 60min — investigation] [risk: none — just observation] [status: open] [autonomous-eligible: yes]
  **Investigate why buy-limit orders fill at prices above the limit** — concrete incident 2026-05-14 04:28:06: MGC buy limit @ 4698.0 filled at 4709.0 (11 points / 110 ticks ADVERSE slippage on a buy limit). This should be impossible under standard limit semantics (buy limit fills at limit price or BELOW). Either ProjectX has a non-standard "marketable limit" treatment that allows arbitrary slippage, or there's a bug in how we're calling place_order. Investigation steps:
  1. Read ProjectX API docs (or test directly) for `order_type="limit"` behavior at the broker
  2. Check if marketable buy limits act like market orders (= fill at any ask)
  3. Test placing a deliberately non-marketable limit (way below current price) and verifying it sits as working
  4. Check if the issue is a race: did current price actually drop below 4698 momentarily, allowing the buy limit to trigger, but then fill at 4709 because the actual ask at fill time was 4709?
  5. Possibly switch from `order_type="limit"` to a proper `order_type="market"` if marketability is desired (or a true non-marketable limit if price discipline is desired)
  Files: `tools/bracket_placement.py:place_bracket` (entry order section), `tools/projectx_client.py:place_order`, observation log in `vault/research/analysis/`.
  Acceptance: documented understanding of ProjectX limit semantics + recommendation on the right order_type for the trader's intent.
  Auto-merge: no — this is research, not a code change. Autonomous routine writes the analysis; user reviews before any place_order changes.
  Mitigation already in place 2026-05-14: `MAX_FILL_SLIPPAGE_TICKS = 10` in bracket_placement.py — flattens if fill is too far from intended entry. Doesn't fix the broker quirk but prevents trading on the destroyed edge.

## 🆕 Queued 2026-05-14 — EXIT OPTIMIZATION ROADMAP

User direction 2026-05-14: "eventually should all of these be implemented." All 6 exit-optimization options were laid out and the user asked them all to be done at some point. #1 (software take-profit at target) shipped 2026-05-14 0431 UTC. The remaining 5 are queued below in priority order. **Pick from this section first when the autonomous routine fires.**

- [P0] [effort: 90min] [risk: low] [status: open] [autonomous-eligible: yes] [exit-roadmap-step: 2]
  **Percent-of-peak retracement (replaces tier table)** — current static tiers leave too much give-back (peak $113 → exit $29 = $84 give-back overnight 2026-05-14). User wants a continuous rule: "never give back more than X% of peak above $20." e.g., 30% retrace cap means peak $100 → exit at $70 max. Replace `TRAILING_PROFIT_TIERS` with a continuous function `floor_for_peak(peak_usd) -> float` returning `max(20, peak * (1-X))` for peak above $20. Add a regression test: at peak $100, retrace to $69 closes; retrace to $71 holds. Calibrate X via walk-forward analysis on historical fills (start with X=0.30 = 30% retrace cap).
  Files: `tools/profit_protect.py` (replace `_compute_active_floor`, keep `decide()` signature). Tests: extend `tests/test_profit_protect.py`.
  Acceptance: peak $100 close happens at >= $70 unrealized (vs current $40 floor from (80,40) tier).
  Auto-merge: yes if tests pass.

- [P1] [effort: 120min] [risk: medium] [status: open] [autonomous-eligible: yes] [exit-roadmap-step: 5]
  **Re-test broker target legs (5/11 anomaly may have lifted)** — currently `SKIP_TARGET_LEG = True` due to broker auto-filling target limits at next-available market. Test: place a target leg with limit ~10pts away from current price on a small MGC trade. Monitor for ~5 min. If it stays "working" without filling → broker is fixed, can re-enable target legs as a redundant exit layer (alongside the software take-profit added 2026-05-14). If it auto-fills → keep SKIP_TARGET_LEG=True, document the persisting anomaly.
  Files: `scripts/live_trader.py:SKIP_TARGET_LEG`, observation log in `vault/research/analysis/`.
  Acceptance: test result documented; SKIP_TARGET_LEG flipped to False ONLY if broker target legs behave correctly.
  Auto-merge: no — requires manual observation of broker behavior. Autonomous routine should write the observation but leave the flag flip to a human.

- [P1] [effort: 90min] [risk: low] [status: open] [autonomous-eligible: yes] [exit-roadmap-step: 4]
  **Reversal detection exit** — if 3 consecutive 1-min bars close AGAINST a position's direction, market-close. Captures "momentum has died" patterns the tier rules can't see. For a long: 3 lower closes in a row → exit. Implementation in `tools/profit_protect.check_and_close` — after computing unrealized, fetch last 3 1-min bars, check direction. Add a min-peak gate (only fire if peak crossed $15 — otherwise too many false exits on noisy small wins).
  Files: `tools/profit_protect.py`, tests with synthetic bars.
  Acceptance: synthetic 3-bar reversal triggers close at any unrealized > $0; <3 bars of reversal doesn't trigger.
  Auto-merge: yes if tests pass.

- [P2] [effort: 150min] [risk: medium] [status: open] [autonomous-eligible: yes] [exit-roadmap-step: 3]
  **Volatility-aware tier tightening** — adjust the retrace cap based on recent realized vol. High vol → wider tolerance (move could resume); dying vol → tighter (move likely over). Use 1-min ATR vs 14-bar baseline. Multiplier: floor = base_floor × (1 - 0.3 × low_vol_signal). Needs calibration via backtest.
  Files: `tools/profit_protect.py` + new `tools/regime_signal.py` helper.
  Acceptance: when realized vol drops below 50% of trailing baseline, profit-lock floor tightens by ~20%. Backtest shows reduced give-back without hurting hit rate.
  Auto-merge: no — calibration choice needs human review. Autonomous routine implements + runs backtest; user reviews calibration.

- [P2] [effort: 60min] [risk: low] [status: open] [autonomous-eligible: yes] [exit-roadmap-step: 6]
  **Time-based profit decay** — if peak hit > N minutes ago AND current is still below peak by Y%, market-close. Stale-profit rule. Defaults: N=15 min, Y=30%. Implementation: track `_position_peak_ts` alongside `_position_high_water` in profit_protect.
  Files: `tools/profit_protect.py`, tests.
  Acceptance: peak hit 20 min ago at $80, current $50 (37% below peak) → close fires. Peak hit 5 min ago at $80, current $50 → hold (within time window).
  Auto-merge: yes if tests pass.

---

## 🆕 Queued 2026-05-14 late-night — HIGHEST PRIORITY (autonomous monitoring)

- [P0] [effort: 180min] [risk: low] [status: open] [autonomous-eligible: yes]
  **Sentinel — continuous autonomous anomaly watcher** — user direct quote 2026-05-14: "nothing improves unless I directly work on it." Multiple bugs tonight (tests writing 24 mock orders to production DB, MGC missing from `_TICK_ECONOMICS`, peak reporting glitch, profit-lock that fired but with $49 slippage from polling latency) all went undetected until the user manually flagged them. The system has watchdog (process-death) and Discord (some events) but no behavior-level monitoring.
  Build `tools/sentinel.py` + `FundSentinel` scheduled task running every 10 min that:
  1. Scans the orders table for `broker_order_id LIKE 'mock_%'` → critical Discord alert (= tests are polluting production)
  2. Scans for open positions where `_resolve_tick_economics` returns (0,0) → critical alert (= profit-lock is blind)
  3. For each closed trade today: check `realized_pl_usd` vs the profit-lock floor that should have fired. If close happened with >$10 slippage past the floor, warn → indicates broker latency or polling miss
  4. Cross-check: any `customTag` in working orders that has no matching position → orphan flag (should be cleaned by cleanup_orphan_brackets, but verify)
  5. Check that brain emit rate matches trader scan rate ratio (brain emits 60s, trader scans every 5min — should see N signals consumed where N = # emissions ÷ 5)
  6. Check live_trader process tree: if >1 live_trader python process running, alert (= duplicate from kill/restart race, causes double-firing)
  Each finding posts to Discord with severity. Report saved daily to `vault/_meta/sentinel_YYYY-MM-DD.md`.
  Why: replaces the "user manually catches problems" pattern with system-catches-problems. The bugs that hit tonight would have been auto-flagged within 10 min.
  Acceptance: 6 invariants checked every 10 min, Discord alert fires on any violation, daily report written.

## 🆕 Queued 2026-05-14 evening — HIGH PRIORITY

- [P0] [effort: 180min] [risk: medium] [status: open] [autonomous-eligible: yes]
  **Trailing broker stop — replace software-polled profit-lock with broker-side trailing stop** — user 2026-05-14 explicitly asked for this ("logic-based system, not just tiers; letting a trade go from $100 to $30 still sucks"). Currently `tools/profit_protect.check_and_close` polls every 10s and submits a market-IOC when peak retraces below floor. Two failure modes: (a) fast-tape slippage past the cap before the next poll, (b) broker stop is at the wider strategy-stop level so worst-case is bounded by the strategy stop, not the floor. The fix: as peak crosses each tier, MODIFY the broker stop UP to the floor-equivalent price. Broker enforces it server-side, instantly.
  Why: tier (80, 40) means a $100 peak retraces to $39 before closing = $61 give-back. User finds this excessive. Trailing broker stop makes the broker enforce the floor at the broker level — when peak hits $100, broker stop sits at $40-equivalent price (= entry ± 40-ticks-of-MGC). When current touches that, broker fires INSTANTLY.
  Files: `tools/profit_protect.py` (add the modify-broker-stop call after computing active_floor), `tools/bracket_placement.py` (export a helper to compute broker-stop-price for a given floor), `tools/projectx_client.py` (verify modify_order signature, or use cancel+replace if modify isn't supported). Tests in `tests/test_profit_protect.py` should add cases for "peak crosses tier → modify_order called with new stop price."
  Acceptance: when running with an open position and unrealized crosses each tier threshold, broker working-order's stopPrice MUST be updated to the floor-equivalent. Verify via `client.get_working_orders` showing the new stopPrice after each tier crossing. Existing software polling stays as belt-and-suspenders.
  Auto-merge: yes if tests pass and no HIGH_RISK_FILES touched. (`tools/projectx_client.py` IS HIGH_RISK — if modify_order isn't already there, file a sub-item requesting user approval instead of editing.)
  Also tighten tier table while you're in there: user is flagging $100→$30 as too much give-back. Consider:
    - (80, 50) instead of (80, 40) → $100 peak → $50 floor → $50 give-back
    - Or add (90, 55) → $100 peak → $55 floor → $45 give-back
    - Or the proper answer: % retrace cap. e.g., "never give back >40% of peak above $50."
  Recommend exploring the % retrace option since it's truly logic-based vs tier-based.

## 🆕 Queued 2026-05-14 evening

- [P1] [effort: 15min] [risk: none] [status: open] [autonomous-eligible: no — needs user GitHub auth]
  **Wire FundWeeklyAudit as a remote Claude routine** — instructions are written in `vault/_meta/weekly_audit.md`. Tried to create the routine 2026-05-14 but Anthropic's GitHub App isn't connected for Aidanshag/AI-trading-team yet. Once user connects GitHub at https://claude.ai/code/onboarding?magic=github-app-setup or runs /web-setup, the routine can be created with `cron_expression: "0 22 * * 0"` (= Sun 18:00 ET = Sun 22:00 UTC), repo `https://github.com/Aidanshag/AI-trading-team`, model `claude-sonnet-4-6`, and the prompt: "Read vault/_meta/weekly_audit.md for full instructions and execute the weekly audit. Working directory: repo root."
  Why: prevents the "Claude codebase becomes a mess" failure mode (the article the user mentioned 2026-05-13 about Claude code that accumulated duplicate logic + brittle coupling). The audit dedupes, kills dead code, flags Pattern A/B bugs, keeps `scripts/live_trader.py` under the 600-line ceiling.
  Acceptance: routine exists at https://claude.ai/code/routines, fires every Sun 22:00 UTC, writes `vault/_meta/weekly_audit_YYYY-MM-DD.md`, posts Discord summary.

## 🆕 Queued 2026-05-13 evening

- [P1] [effort: 120-180min] [risk: low] [status: open] [autonomous-eligible: yes]
  **Walk-forward validation of MGC cells** — 4 MGC shadow cells were added to `state/strategy_validation.json:live_allowlist` 2026-05-13 evening (narrow_range_break long/short, fair_value_gap_tuned short — all Asian; inside_bar_break long PostClose). They mirror existing GC cells and currently have `experimental: true` (shadow mode, no real fills). Need walk-forward OOS stats on MGC bars to graduate them out of shadow.
  Why: tonight's GC fair_value_gap_tuned short emitted a 95-tick ($951) stop — over the $150 max-risk gate, so blocked. MGC tick value is 1/10 of GC ($1 vs $10), so the same strategy on MGC produces a $95 risk profile that fits inside the cap. Adds capacity without raising risk per trade. But: the existing OOS stats are from GC bars, not MGC — MGC has different liquidity, gappier bar shapes, lower volume. Pattern B says re-validate before deploying.
  Files: pick the most relevant `scripts/walk_forward_*.py` and either parameterize for MGC or fork an MGC-specific copy. Bars come from ProjectX via `tools/bar_fetcher.fetch_bars(client, "MGC", ...)`. Output writes to `state/strategy_validation.json:cells` under keys `<strategy>|MGC|<session>|<side>` with `last_oos: {n, hit, e, t}` populated.
  Acceptance: each MGC cell in live_allowlist has a `last_oos` entry. For cells meeting n≥25 AND t≥1.5 AND E>0, flip `experimental: false` to graduate to real fills. Failing cells stay shadow or get removed from allowlist.
  Auto-merge: yes — backtest math only, no broker IO, no risk-config edits. Touches `state/strategy_validation.json` which the autonomous loop already updates.

---

## 🎯 XFA-readiness checklist (target: ~30 days from 2026-05-12)

User target 2026-05-12: pass Combine in ~1 month, then sustain XFA cash flow. Before XFA transition, all `XFA-readiness: required` items below MUST be resolved. The mistakes that bled tonight (orphan-leg, broker target-fill, stop on wrong side of fill, profit-take gap) must NOT recur in a real-payout context.

### XFA-readiness items (added 2026-05-12 evening)

- [P0] [effort: 60min] [risk: low] [status: merged 2026-05-12 (claude_code)] [autonomous-eligible: yes] [Combine-required: YES]
  **3:10 PM CT hard time-based flatten** — SHIPPED 2026-05-12 evening. `tools/hard_flatten_clock.py` + 14 unit tests + wired into `scripts/live_trader.py:scan_once` BEFORE signal-fire logic. Window logic: 2:55-3:04 CT blocks new entries, 3:05-3:29 CT proactive flatten + cancel working orders, 3:30+ CT overnight session resumes. DST-aware via `zoneinfo`.
  Current state: NOT ENFORCED. `_check_autonomous_rth_window` cuts NEW entries at 14:30 ET = 1:30 PM CT, but existing positions can run through to 3:10 PM CT and beyond. The trader operates 24/5 — a position opened in any earlier session can span into the 3:10 PM CT cutoff if not closed.
  Files: `scripts/live_trader.py` (add `_check_hard_time_flatten`), `hooks/risk_gate.py` (mirror check), tests.
  Acceptance: at 3:05 PM CT (5-min buffer before deadline), all open positions market-closed; new entries blocked from 2:55 PM CT onward. Must handle DST timezone correctly.
  Auto-merge: yes. Tests cover (a) 3:00 CT scan with open position triggers close, (b) 12:00 CT scan does not, (c) UTC↔CT conversion, (d) holiday schedule integration.

- [P1] [effort: 90min] [risk: medium] [status: open] [autonomous-eligible: yes] [XFA-readiness: required]
  **Consistency-rule enforcement (50% single-day profit cap)** — currently advisory only per CLAUDE.md `_check_consistency_rule warn-tier`. Today's +$2,948 GC day will trip this in <5 days unless we dilute or cap.
  Why: 50% single-day rule applies to BOTH Combine and XFA. Today's day P&L is 100% of cycle profits → currently failing the advisory check. Need to either: (a) hard-block trades that would push single-day >50% of total cycle, or (b) implement a daily profit-cap that auto-flattens when day P&L exceeds a configured ceiling (e.g., $400-$600 for $50K account per Topstep rules doc).
  Files: `hooks/risk_gate.py:_check_consistency_rule`, `scripts/live_trader.py`, `config/risk_limits.yaml`.
  Acceptance: hard-block (not warn) when projected day P&L > 50% of (cycle_profits + projected_day_pnl). Tests cover edge cases at exactly 50%, just over, and on new cycles.

- [P2] [effort: 45min] [risk: low] [status: merged 2026-05-12 (claude_code)] [autonomous-eligible: yes] [XFA-readiness: required]
  **Widen news-event blackout from ±5min to ±15min** — SHIPPED 2026-05-12 evening. `config/risk_limits.yaml:high_impact_blackout_minutes` changed from 5 to 15. Code path unchanged (already configurable). NFP/FOMC/CPI windows now properly buffered.

- [P2] [effort: 90min] [risk: low] [status: merged 2026-05-12 (claude_code)] [autonomous-eligible: yes] [XFA-readiness: required]
  **Holiday/abbreviated-session schedule check** — SHIPPED 2026-05-12 evening. `tools/holiday_schedule.py` (static 2026 CME calendar) + integration in `tools/hard_flatten_clock.py:current_window`. Memorial Day 2026-05-25 abbreviated 12:00 CT close active. Christmas + Good Friday treated as full-close (no trading). 8 unit tests covering edge cases.

- [P3] [effort: 60min] [risk: low] [status: open] [autonomous-eligible: yes] [XFA-readiness: required-for-XFA-only]
  **Post-payout MLL recalibration logic** — not needed in Combine. Required immediately upon XFA promotion. Per Topstep docs, MLL resets to $0 after payout, leaving thin headroom.
  Acceptance: on detecting a payout (account balance jumps + MLL reference resets), trader runs `recalibrate_safety_floors()` which logs new headroom, may pause until manual confirmation. Defer build until XFA transition is imminent.

- [P2] [effort: 30min] [risk: low] [status: merged 2026-05-12 (claude_code)] [autonomous-eligible: yes] [XFA-readiness: recommended]
  **Position-protection sweep every scan** — SHIPPED 2026-05-12 evening. `tools/position_protection.py` + 7 unit tests + wired into `scripts/live_trader.py:scan_once`. Runs after `enforce_loss_cap`. Checks each open position for a matching `live_<cid>_stop` working order. If missing AND past 90s grace period, emergency-flattens.
  Why: tonight's MNQ incident revealed a stop can fail to land. The verify-at-placement check now catches placement failures. A periodic sweep catches LATER cancellations (broker session-end, server cleanup, etc.).
  Files: `scripts/live_trader.py` (add to scan_once next to enforce_loss_cap).
  Acceptance: every scan, for each open position, query working orders, verify a stop with matching `customTag` pattern exists. If not → log critical + emergency-flatten.

### XFA-readiness summary table

| Item | Priority | Effort | Auto-mergeable | Trigger to ship |
|---|---|---|---|---|
| 3:10 PM CT hard flatten | P1 | 60min | ✓ | anytime |
| Consistency rule hard-block | P1 | 90min | ✓ | anytime (today is already advisory failing) |
| News blackout ±15min | P2 | 45min | ✓ | anytime |
| Holiday schedule | P2 | 90min | ✓ | anytime |
| Post-payout recalibration | P3 | 60min | ✓ | defer until XFA transition imminent |
| Position-protection sweep | P2 | 30min | ✓ | anytime |

---

## P0 — critical (do first)

- [P2] [effort: 90min] [risk: medium] [status: open] [autonomous-eligible: when triggers met]
  **Win/loss-conditional cooldown** — replace flat `SAME_SYMBOL_COOLDOWN_MIN=45`
  with outcome-aware cooldown table per user direction 2026-05-11 evening.
  Why: today's GC trades (+$2,616 then +$380) suggest trending symbols benefit
  from tighter re-entry after winners. Flat 45-min blocks follow-on
  opportunities. After losses, keep 45-min anti-tilt window (4/29 lesson).
  Proposed table:
    after_win:       15-20 min   (allow follow-on momentum)
    after_breakeven: 30 min
    after_loss:      45 min      (anti-tilt, current default)
  Files: `scripts/live_trader.py`, `tools/trade_state.py`, `tests/test_live_trader.py`
  Acceptance: 3 unit tests covering each branch + `recent_thesis_for(symbol)`
  returns the outcome-appropriate window. Auto-merge ok once triggers met.
  Triggers for autonomous ship (ALL must be true):
  1. Orders.ts_filled / avg_fill_price reliably populated (broken per cowork
     2026-05-06; without it we can't read realized P&L per symbol).
  2. ≥10 live trades accumulated with mixed outcomes (need baseline data
     before relaxing safety) — currently at ~6 trades total.
  3. GC has fired ≥3 times with consistent positive expectancy under the
     new SKIP_TARGET_LEG architecture (the user's specific motivation).

- [P0] [effort: 90min] [risk: low] [status: merged 2026-05-08 (cowork)]
  **Auto-promote/demote cells from live evidence** — SHIPPED by cowork
  `scripts/cell_auto_promote.py` (commit `834852f`) + 17 unit tests (commit `b3a1f75`).
  Atomic JSON writes; honors user pin (live_strategies_filter); audit log
  to `vault/research/cell_promotion_log.md`. Will surface meaningful
  decisions after Sunday's fills accumulate to n≥10.
  Remaining: wire into `scripts/preflight.py` as step 9 (CLI agent task).

- [P0] [effort: 45min] [risk: medium] [status: merged (already done — verified 2026-05-12)] [autonomous-eligible: yes]
  **Trim live_trader.py: extract snapshot capture to tools/snapshot_writer.py** — ALREADY SHIPPED. `tools/snapshot_writer.py` exists and is imported at `scripts/live_trader.py:132` (`from tools.snapshot_writer import capture_snapshot`). Backlog status was stale.

- [P1] [effort: 4h] [risk: low] [status: open — DEMOTED 2026-05-08 from P0]
  **Strategy R&D: target >50% hit rate at heavy slippage**
  Reframe note: demoted from P0 because new strategies = new unknowns,
  before current `gap_fill_wide` deployment is validated against
  predictions. Re-promote to P0 after we have at least 2 weeks of live
  data showing actual-vs-backtest variance is low (<20%) on existing
  cells.
  Why: user directive 2026-05-08 — at >50% hit rate with positive R-mult, profitability is statistically nearly guaranteed because the win:loss arithmetic compounds in our favor independent of slippage. Current `gap_fill_wide` has ~67% hit but few signals; we need 2-3 strategies with both high cadence AND high hit rate.
  Approach (multiple candidates to evaluate in parallel):
    1. **Bollinger band 2σ + RSI extreme + reversal candle**: fade extremes when 3 conditions align. Wide stop = 1.5×ATR beyond extreme. Target = 1.5×ATR. Expected hit rate 65-75%.
    2. **Failed breakout pattern**: 20-bar high/low test that fails to follow through. Stop above failed level, target = 1.5× attempted move. Expected hit rate 55-65%.
    3. **Multi-timeframe confluence**: only fire when 5m, 15m, 1h trend agree. Wide stop based on 1h ATR. Expected hit rate 60-70% but rare signals.
    4. **Volume-weighted reversal**: extreme volume (>2× MA) at price extreme + reversal bar. Wide stop. Expected hit rate 60%.
    5. **Previous-day-level fade**: test of previous day high/low with multiple touches → reversal. Expected hit rate 60-70%.
  Validation criterion: each candidate must show:
    - OOS n ≥ 50 over 60d
    - OOS hit rate ≥ 55%
    - At 0.5 tick/side slippage: positive expectancy
    - At 1.0 tick/side slippage: positive expectancy
  Acceptance: at least 2 candidates pass criterion; results in `vault/research/high_hit_rate_strategies/`. Best candidate(s) registered in STRATEGY_REGISTRY for live validation.
  Auto-merge: false (touches strategy library; needs review)

- [P1] [effort: 60min] [risk: low] [status: open]
  **Run param sweep with slippage-adjusted dollar metrics**
  Why: cowork's `param_sweep.py` reports R-multiples but doesn't model slippage in dollars. The 2026-05-08 finding showed that R-multiple ≠ slippage-resistance. Need a sweep that runs each param combo through `model_strategy_returns_with_slippage.py`-style logic.
  Files: extend `scripts/param_sweep.py` to accept `--slippage-levels 0,0.25,0.5,1.0` and `--metric dollar` mode; OR create wrapper that takes sweep output and applies slippage modeling.
  First sweep: gap_fill on (min_gap_atr × stop_atr_mult × min_stop_ticks) — find slippage-optimal parameter combo.
  Acceptance: writes `vault/research/param_sweeps/gap_fill_dollars_slippage_<date>.csv` with per-combo P_pass at each slippage level.
  Auto-merge: true (offline analysis)

- [P1] [effort: 90min] [risk: low] [status: open]
  **New strategy: wide_session_drive — designed for slippage tolerance**
  Why: only gap_fill_wide currently survives realistic slippage in our registry. We need 2-3 slippage-tolerant strategies as a portfolio, not a single point of failure. Wide-stop strategies with wide targets absorb slippage as a small fraction.
  Logic: at each session boundary, define opening range (30 min), enter on break with stop = ±1.0 × range, target = ±2.5 × range. Per-trade R-multiple ~2.5; per-trade $ edge $200-800; hit rate target 35-45%.
  Files: NEW entry in `tools/backtest/strategies.py` registered in `STRATEGY_REGISTRY`; integration into `scripts/daily_strategy_validation.py:ALL_STRATEGIES`.
  Acceptance: backtest on 60d 5m bars across treasuries + NG + 6E + ES; slippage sensitivity at 0/0.25/0.5/1.0 ticks per side; demonstrate positive expectancy at 0.25 slippage on n≥30 trades. If passes, walk-forward validation auto-runs.
  Auto-merge: false (touches strategy library)

- [P1] [effort: 120min] [risk: medium] [status: open]
  **Passive entry orders (post-only / limit-at-bid)**
  Why: largest single slippage reduction lever (-50% on entry slippage). Currently using marketable-limit at +5 ticks which crosses the spread. Post-only would rest at the favorable side and only fill when market comes to us.
  Files: `scripts/live_trader.py:place_bracket` — change entry from marketable-limit to post-only-limit. Add a fill-timeout (e.g., 5 min) after which we cancel and try again or skip the signal.
  Acceptance: backtest with post-only fills (estimated fill rate 40-60%) shows net P&L improvement after accounting for missed fills. Live data confirms entry slippage reduction.
  Auto-merge: false (touches order placement code path)

- [P0] [effort: 60min] [risk: low] [status: merged 2026-05-11 (claude_code) — sweep run + revealed broken pipeline]
  **Strategy parameter sweep framework — gap_fill robustness sweep** — SHIPPED 2026-05-11 night. Multiple sweeps run on gap_fill + gap_fill_wide; output in `vault/research/param_sweeps/`. The sweep run REVEALED a deeper bug: param_sweep wasn't passing tick_size to the strategy. Patched (also surfaced the t.stop_price typo bug). After fixes, NEITHER gap_fill NOR gap_fill_wide qualified — leading to gap_fill removal from `live_strategies_filter` and a diversified 23-cell deployment of non-gap_fill strategies. See `vault/research/analysis/2026-05-11_gap_fill_wide_validation_attempt.md`.

### Cowork shipped 2026-05-08 (status: merged)

- `scripts/cell_auto_promote.py` (commit `834852f`) + tests (`b3a1f75`)
- `scripts/param_sweep.py` (commit `ce495bb`) — framework only, sweep run pending
- `scripts/regime_classifier.py` (commit `729c1fb`) — vol/trend/news regime tags
- `scripts/cost_ledger.py` (commit `1ed3b4e`) — daily NET P&L automation

## P1 — high (Phase 2 work)

- [P1] [effort: 30min] [risk: low] [status: merged 2026-04-30]
  **Real-time loss alerter (Discord webhook)** — DONE
  Implemented `scripts/loss_alerter.py` with thresholds at -$100/-$200/-$400/canTrade=false.
  Wired into `auto_trader.scan_once` after each snapshot. `--test` flag fires synthetic alert.
  Activates when user adds `DISCORD_WEBHOOK_URL` to .env.

- [P1] [effort: 45min] [risk: low] [status: merged 2026-04-30]
  **Per-strategy auto-demote on negative-EV streak** — DONE
  Implemented `_strategy_recent_streak` and `_strategy_is_demoted` helpers.
  When a strategy hits 5 consecutive stop-outs in 4h, auto-suspends for the rest of UTC day
  via `risk_events.rule='strategy_demoted_today'`.

- [P1] [effort: 60min] [risk: medium] [status: open]
  **Setup confluence requirement**
  Why: lone signals fired in noisy tape today. A signal confirmed by ≥1 of: volume above 1.5× MA, ATR expansion, or another strategy showing same direction is more reliable
  Files: `scripts/auto_trader.py:find_latest_signal` or new wrapper
  Acceptance: signals not confirmed by at least one confluence factor are skipped under autonomous mode
  Auto-merge: false (touches hot path)

## P2 — medium

- [P2] [effort: 30min] [risk: low] [status: open]
  **Cost ledger in CIO daily brief**
  Why: agents need to feel the cost burn every session. CIO's brief already exists; it just needs the cost ledger pulled in.
  Files: `agents/cio.md` (prompt update), `scripts/_session_brief.py` (if it exists), or new helper
  Acceptance: every CIO session brief opens with "MTD: gross +$X, fees -$Y, API -$Z, net +$W"

- [P2] [effort: 20min] [risk: low] [status: merged 2026-05-01]
  **Lessons → strategy_blacklist auto-promotion** — DONE
  Script existed but used yaml.safe_dump which strips comments (same bug
  fixed in halt.py). Replaced with targeted text-only edit. Two tests
  added (`tests/test_auto_promote_lessons.py`) — comment preservation +
  idempotency. RULE-tier lessons now auto-encode without destroying the
  hand-curated explanations in risk_limits.yaml.

- [P2] [effort: 45min] [risk: medium] [status: open]
  **Regime classifier (live vol/volume metric)**
  Why: today's blanket 21:00–04:00 ET rule is crude. A live regime classifier ("ATR/avg over recent N bars below threshold → choppy → block mean-reversion") would be more precise
  Files: new `tools/regime_classifier.py`, plumb into auto_trader
  Acceptance: regime_classifier.current_regime() returns one of {trending, choppy, event, thin}; auto_trader respects it

- [P2] [effort: 30min] [risk: low] [status: merged 2026-04-30]
  **`fund halt` and `fund resume` CLI commands** — DONE
  Implemented `scripts/halt.py` with `4h` / `30m` / `next-open` / `clear` /
  `status` subcommands. Targeted text-edit (preserves YAML comments).
  Wired into `fund.ps1` as `fund halt` and `fund resume` verbs.

## P3 — long-term

- [P3] [effort: 90min] [risk: medium] [status: open]
  **Remote kill switch (HTTP endpoint, password-protected)**
  Why: kill from your phone when you see a bleed. Tiny Flask/FastAPI endpoint, password auth, sets `trading_halt_until`
  Files: new `scripts/remote_kill.py` + service install script
  Acceptance: POST to `http://localhost:PORT/halt?duration=4h` (with bearer token) writes the halt
  Note: medium risk — requires opening a port. User must approve network exposure model.

- [P3] [effort: 2h] [risk: high] [status: open]
  **A/B test new strategies in shadow mode**
  Why: new strategies should accumulate outcomes in `shadow_trades` table for N days before going live
  Files: `tools/backtest/strategies.py` (mark which are validated), `scripts/auto_trader.py` (only fire validated for live)
  Acceptance: a `validated_after: YYYY-MM-DD` field on each strategy gates whether it can fire live or only shadow
  Auto-merge: false

- [P3] [effort: 60min] [risk: low] [status: merged 2026-04-30]
  **Documentation: CLAUDE.md update with new config blocks** — DONE
  Created `CLAUDE.md` at project root with: top-level orientation, read-first
  order, layout map, full risk-floor architecture (all 23 hook checks listed),
  two-trading-paths note, operational scripts, autonomous infra, recent
  history. New Claude sessions discover this on attach.

---

## Strategy ideas to implement (user-supplied)

This section is the user's idea inbox for new price-action / mathematical
strategies. Drop notes, descriptions, screenshots, links, or rough sketches
here. The autonomous-improvement loop (cloud routine
`trig_011w6DUmXbojsfkjKtCaJfBa`) will pick items from this section, code
them up against the existing strategy protocol in
`tools/backtest/strategies.py`, register them in `STRATEGY_REGISTRY` and
`STRATEGY_ROSTER`, add literature priors to `tools/strategy_performance.py`,
write tests, and submit a PR.

**Strategic focus:** price-action / microstructure / mathematical. FVG is
the lead strategy. Classical TA additions go straight to P3 unless the
user explicitly asks for one.

**Format for entries:**

```
- [strategy_name] [status: idea|proposed|implemented]
  Description: what is the pattern, in plain English
  Source: where this came from (friend, book, paper, link, intuition)
  Trigger conditions: candle/structure rules
  Entry/Stop/Target: rough idea
  Symbols of interest: which markets it should run on
  Notes: any extra context
```

**Examples (currently empty — drop ideas below):**

<!-- USER: ADD IDEAS HERE -->

## Research backlog for next Quant Researcher wake (2026-05-05)

- [extended_data_validation] [status: idea]
  Description: Re-run walk_forward_phase2.py on 90+ days of intraday data once available to confirm the 7 cells deployed today don't deteriorate
  Symbols of interest: 6E, MCL, NG, GC, MES, ZN
  Notes: yfinance limits to 60d for 5m bars. Need a different data source for longer history (firstrate_csv source already wired)

- [param_sweep_gap_fill_ZN] [status: idea]
  Description: gap_fill ZN at default params shows OOS E=+1.10R t=+11.95. Earlier sweep showed min_gap_atr=1.25 hits +2.74R OOS but small n. Sweep min_gap_atr ∈ {0.5, 0.6, 0.75, 1.0, 1.25} × rr_target ∈ {1.0, 1.5, 2.0, 2.5} on more data. Find optimal cell.
  Trigger conditions: rerun walk_forward_extensions.py with extended params

- [confluence_strategies] [status: idea]
  Description: Do confluence-of-signals filters add edge? E.g., "only fire gap_fill ZN Asian when also RSI < 30 (oversold)" or "only fire pivot_reversal 6E RTH short when DXY rallying"
  Trigger conditions: design + walk-forward each combination

- [time_of_day_micro_buckets] [status: idea]
  Description: Current sessions are 4 buckets (Asian/London/RTH/PostClose). Try finer 2-hour buckets (e.g., 02:00-04:00 vs 04:00-06:00 inside Asian) to find tighter edge windows
  Notes: Risk of overfitting; require n>=30 per bucket and walk-forward

- [order_flow_microstructure] [status: idea]
  Description: Investigate whether ProjectX provides bid/ask spread or depth data. If yes, add features: imbalance, micro-price drift, sweep detection
  Source: ProjectX API docs

- [anti_strategy_research] [status: idea]
  Description: narrow_range_break has aggregate -0.09R t=-3.93. The INVERSE direction would have aggregate +0.09R. Test "fade NRB" as an explicit strategy with proper walk-forward
  Notes: only useful if t>2 OOS; avoid building on known-losing strategies

## Old example template (kept for format reference)

- [example_template] [status: idea]
  Description: (your description)
  Source: (your source)
  Trigger conditions: (your rules)
  Entry/Stop/Target: (rough sketch)
  Symbols of interest: (which markets)
  Notes: (anything else)

---

## How items get added

- Failed sessions / new bugs → P0 or P1 with a `lesson_ref:` link to the journal/lesson file
- Audit findings during `/improve-fund` cycles → `proposed` status until user approves
- User requests → directly added at requested priority

## How items get removed

When merged, change `status: merged` and add `merged_in:` git SHA. Keep the row for ~30 days as a record, then archive to `vault/_meta/archive/improvement_backlog_YYYY-MM.md`.
