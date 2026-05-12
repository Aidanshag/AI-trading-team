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

## 🎯 XFA-readiness checklist (target: ~30 days from 2026-05-12)

User target 2026-05-12: pass Combine in ~1 month, then sustain XFA cash flow. Before XFA transition, all `XFA-readiness: required` items below MUST be resolved. The mistakes that bled tonight (orphan-leg, broker target-fill, stop on wrong side of fill, profit-take gap) must NOT recur in a real-payout context.

### XFA-readiness items (added 2026-05-12 evening)

- [P1] [effort: 60min] [risk: low] [status: open] [autonomous-eligible: yes] [XFA-readiness: required]
  **3:10 PM CT hard time-based flatten** — XFA hard rule. Holding past 3:10 PM CT = rule violation = account closure risk.
  Current state: NOT ENFORCED. `_check_autonomous_rth_window` cuts NEW entries at 14:30 ET = 1:30 PM CT, but existing positions can run through.
  Files: `scripts/live_trader.py` (add `_check_hard_time_flatten`), `hooks/risk_gate.py` (mirror check), tests.
  Acceptance: at 15:05 PM CT (5-min buffer before deadline), all open positions market-closed; new entries blocked from 14:55 PM CT onward.
  Auto-merge: yes once tests cover (a) 15:00 CT scan with open position triggers close, (b) 14:00 CT scan does not, (c) timezone-aware (UTC↔CT conversion).

- [P1] [effort: 90min] [risk: medium] [status: open] [autonomous-eligible: yes] [XFA-readiness: required]
  **Consistency-rule enforcement (50% single-day profit cap)** — currently advisory only per CLAUDE.md `_check_consistency_rule warn-tier`. Today's +$2,948 GC day will trip this in <5 days unless we dilute or cap.
  Why: 50% single-day rule applies to BOTH Combine and XFA. Today's day P&L is 100% of cycle profits → currently failing the advisory check. Need to either: (a) hard-block trades that would push single-day >50% of total cycle, or (b) implement a daily profit-cap that auto-flattens when day P&L exceeds a configured ceiling (e.g., $400-$600 for $50K account per Topstep rules doc).
  Files: `hooks/risk_gate.py:_check_consistency_rule`, `scripts/live_trader.py`, `config/risk_limits.yaml`.
  Acceptance: hard-block (not warn) when projected day P&L > 50% of (cycle_profits + projected_day_pnl). Tests cover edge cases at exactly 50%, just over, and on new cycles.

- [P2] [effort: 45min] [risk: low] [status: open] [autonomous-eligible: yes] [XFA-readiness: required]
  **Widen news-event blackout from ±5min to ±15min** — Topstep doc recommends ±15min around high-impact (NFP/FOMC/CPI).
  Current state: `_check_high_impact_blackout` is ±5min. Code is in `hooks/risk_gate.py`.
  Acceptance: ±15min for HIGH severity, ±5min preserved for MEDIUM. Test verifies a position attempt at -14min before HIGH event is blocked, at -16min is allowed.

- [P2] [effort: 90min] [risk: low] [status: open] [autonomous-eligible: yes] [XFA-readiness: required]
  **Holiday/abbreviated-session schedule check** — Topstep abbreviates hours on some holidays; if 3:10 PM CT flatten isn't adjusted, we'd hold past the real session close.
  Current state: macro brief pipeline fetches some calendar data but no in-trader gate for holiday hours.
  Acceptance: trader's scan_once reads a `holiday_schedule.json` (auto-refreshed daily) and if today is abbreviated, uses the shortened hard-flatten time. Test with mocked schedule.

- [P3] [effort: 60min] [risk: low] [status: open] [autonomous-eligible: yes] [XFA-readiness: required-for-XFA-only]
  **Post-payout MLL recalibration logic** — not needed in Combine. Required immediately upon XFA promotion. Per Topstep docs, MLL resets to $0 after payout, leaving thin headroom.
  Acceptance: on detecting a payout (account balance jumps + MLL reference resets), trader runs `recalibrate_safety_floors()` which logs new headroom, may pause until manual confirmation. Defer build until XFA transition is imminent.

- [P2] [effort: 30min] [risk: low] [status: open] [autonomous-eligible: yes] [XFA-readiness: recommended]
  **Position-protection sweep every scan** — verify each open position STILL has a working broker stop in working_orders. If a stop was cancelled/expired/missing for any reason, either re-place it or emergency-flatten.
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

- [P0] [effort: 45min] [risk: medium] [status: open]
  **Trim live_trader.py: extract snapshot capture to tools/snapshot_writer.py**
  Why: trader at 763 lines as of 2026-05-08 after adding cleanup + Sunday-reopen gates. The capture_snapshot + compute_unrealized block is ~100 lines of "broker state observer" logic that is not core execution. Extract to tools/ keeps the knife focused.
  Files: `scripts/live_trader.py` (lines 131-226 region), NEW `tools/snapshot_writer.py`
  Acceptance: live_trader imports `capture_snapshot` from `tools.snapshot_writer`; all 25 unit tests still pass; dry-run scan output identical to pre-extraction. Trader < 700 lines.
  Auto-merge: false (touches the running trader path; user should review PR)

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

- [P0] [effort: 60min] [risk: low] [status: framework merged 2026-05-08 (cowork); sweep-run still open]
  **Strategy parameter sweep framework — gap_fill robustness sweep**
  Framework SHIPPED by cowork: `scripts/param_sweep.py` (commit `ce495bb`).
  Generic walk-forward sweeper, replaces per-sweep `walk_forward_*.py` pattern.
  **Still TODO**: actually run the gap_fill robustness sweep:
    `python -m scripts.param_sweep --strategy gap_fill \
      --params 'min_gap_atr=0.5,0.75,1.0,1.5;rr_target=1.0,1.25,1.5,2.0' \
      --symbols ZN,ZT,ZB,ZF`
  Output: `vault/research/param_sweeps/gap_fill_<date>.csv`. Goal: find
  params with enough per-trade R to absorb 0.25-0.5 tick slippage.
  Auto-merge: true (offline analysis only)

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
