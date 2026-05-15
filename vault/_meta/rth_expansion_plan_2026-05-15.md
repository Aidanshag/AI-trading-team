---
type: weekend_plan
date: 2026-05-15
status: draft — awaiting user review
target_window: weekend 2026-05-16 (Sat) → 2026-05-17 (Sun 17:30 ET Globex reopen)
priority: P0 — strategic capacity expansion
---

# RTH strategy expansion — weekend plan

## The diagnosis

Asian session has 14 cells in `live_allowlist`. RTH has 2. This isn't because the strategies don't work in RTH — it's because that's where the historical data lived when each cell was originally walk-forwarded. The graduation criteria (n≥25, t≥1.5, E>0) only fires once enough Asian samples accumulated; RTH bars were never run through the same pipeline.

User is increasingly active during RTH and is the natural in-the-loop reviewer for exit decisions and signal quality calls. Building out RTH coverage now is the single highest-leverage capacity expansion available — it doubles the daily window in which validated cells can fire, without raising per-trade risk.

Current RTH cells:
- `pivot_reversal | MNQ | long` — actively firing (saw it during this session)
- `fair_value_gap | NG | short` — not currently firing

## The plan — four phases, weekend timeline

The autonomous nightly loop is the wrong venue for this. It's a multi-day, multi-decision project that needs user-in-the-loop direction calls on calibration choices and graduation reviews.

### Phase 0 — pre-weekend prep (Friday afternoon, BEFORE 5 PM ET close)

1. **Pull a clean RTH bar history** for each focus-universe symbol. ProjectX `/api/History/retrieveBars` already serves this — need 12-18 months of 1-min RTH bars for: MGC, GC, MNQ, NQ, ES, MES, 6E, ZN, ZB, ZF, CL, MCL, NG, MNG. Cache to `state/bars/<sym>_1m_rth.parquet`.
2. **Lock the trading book.** Whatever's on Friday should close naturally before 5 PM ET. No new entries Friday after 3 PM ET. Trader continues Asian/Europe but RTH is off until Sunday reopen.
3. **Snapshot baseline state** for comparison: `git tag rth-expansion-baseline-<sha>`, snapshot `state/strategy_validation.json` to vault.

### Phase 1 — walk-forward against RTH bars (Saturday morning, ~3-4 hours)

Run `scripts/walk_forward_rth.py` (new, parameterized from existing `walk_forward_firing_strategies.py`) for every strategy × symbol × side combination in `STRATEGY_REGISTRY` × focus universe. Output writes to `state/strategy_validation.json:cells` with keys like `<strategy>|<symbol>|RTH|<side>` and OOS stats (`n, hit, E, t`).

**Cells to evaluate (8 strategies × ~10 symbols × 2 sides = ~160 cells):**
- `fair_value_gap`, `fair_value_gap_tuned`
- `narrow_range_break`, `narrow_range_break_tuned`
- `inside_bar_break`
- `order_block_d1`
- `pivot_reversal`
- `liquidity_sweep_tuned`
- `keltner_breakout`
- `vol_spike_fade`
- `cross_asset_divergence_zn`

Expected output: rank ALL ~160 cells by t-stat. Top 20-30 are the candidate pool. Bottom-N get eliminated immediately.

**User direction call needed at end of Phase 1:** review the ranked-cell report. Cut anything where the math looks suspect (high t but low n, or t high purely from a few outlier days).

### Phase 2 — per-RTH parameter calibration (Saturday afternoon, ~3-4 hours)

For each top-30 candidate from Phase 1, sweep the strategy's parameters against RTH bars specifically. RTH has different microstructure:
- **Higher volume** — wider tolerance for slippage; tighter stops may not get filled before retrace
- **Wider intra-bar range** — N-tick stop buffers calibrated for Asian's quiet tape will fire too easily in RTH's normal noise
- **Event-driven moves** — 8:30 ET data, 10:00 ET data, 10:30 ET oil-inventories Wednesday, Fed minutes 2:00 PM. Pivot/FVG strategies need to either AVOID these windows or use widened parameters
- **Opening volatility** — first 15 minutes after 9:30 ET has dramatically wider bars; signal-quality drops

Output: per-cell calibrated parameters (stop_buffer_ticks, target_buffer_ticks, min_signal_r). Writes to `state/strategy_validation.json:cells[<key>].params`.

**User direction call needed at end of Phase 2:** review the calibration choices. Anything where the parameter swing was wide enough that "calibrated value" feels arbitrary needs your judgment.

### Phase 3 — RTH-specific gates (Sunday morning, ~2-3 hours)

Add infrastructure to handle RTH-specific failure modes:

1. **News-blackout windows** — `tools/regime_signal.py:news_proximity_for(symbol)` already gives a "this symbol is near a known economic release" signal. Wire it into the brain's emit decision so signals near 8:30/10:00/2:00 PM ET releases are suppressed.
2. **Opening-volatility gate** — first 15 minutes after 9:30 ET RTH open has 3-5x normal bar range. Add a `_check_opening_volatility` to the risk gate that blocks new entries in 9:30-9:45 ET.
3. **EOD wind-down gate** — last 30 min of RTH (3:30-4:00 PM ET) has end-of-day positioning noise. Existing `hard_flatten_clock` already handles the 3:10 PM CT (= 4:10 ET) flatten; add a 3:30 PM ET no-new-entries gate.
4. **Symbol-specific event awareness** — oil inventories (Wed 10:30 ET) affects CL/MCL/NG; cattle reports affect LE/HE; treasury auctions affect ZN/ZB/ZF/UB. Wire these into `news_proximity_for`.

### Phase 4 — staged deployment (Sunday afternoon, before 6 PM ET Globex reopen)

**Critical principle: don't go from "2 cells live" to "10 cells live" in one step.** Each cell starts `experimental: true` (shadow mode, signals emit but no real fills), accumulates 2-3 weeks of LIVE OOS stats, then graduates one at a time.

Sunday afternoon: pick the TOP 3-5 cells from Phase 2 calibration. Set `experimental: true` in live_allowlist. Trader will shadow-fire them starting Sunday 6 PM ET reopen. exit_reasoner (already in shadow_mode) will produce HOLD/CLOSE decisions for these cells too — that data accumulates in `agent_exit_vetoes` for review.

**User direction call needed for Phase 4:** approve the specific 3-5 cells before Sunday close. After 2 weeks of live shadow data, review and graduate one cell at a time.

## What needs to be NEW code

- `scripts/walk_forward_rth.py` — fork of `walk_forward_firing_strategies.py` parameterized for `session="RTH"`. ~100 lines.
- `tools/regime_signal.py:opening_volatility_active(now)` — pure function returning True during 9:30-9:45 ET RTH. ~20 lines + test.
- `hooks/risk_gate.py:_check_opening_volatility` — gate that blocks new entries in the window. **This touches HIGH_RISK_FILES — needs your explicit approval before edit.**
- `hooks/risk_gate.py:_check_rth_eod_wind_down` — blocks new entries 3:30-4:00 PM ET RTH. **Also HIGH_RISK — needs approval.**

## What needs to be USER decisions

1. **Calibration trade-offs** at Phase 2 end — when a parameter sweep doesn't have a clear winner, you pick the conservative choice.
2. **Cell-graduation approvals** at Phase 4 — which 3-5 cells go live first; which stay in shadow.
3. **Approval on HIGH_RISK_FILE edits** — opening-volatility gate + EOD wind-down gate touch `hooks/risk_gate.py`; I can't merge these autonomously.
4. **Capacity question** — current daily trade cap is 15. If RTH adds 3-5 cells, daily volume could double. Do we raise the cap to 25, or stay disciplined at 15 (cells compete for slots)?

## Risks + mitigations

- **Risk: overfitting** to recent RTH data. Mitigation: walk-forward with rolling 6-month in-sample → 1-month out-of-sample windows. Reject cells where in-sample/out-of-sample t-stat ratio is >2x.
- **Risk: news-release surprise** invalidates calibration. Mitigation: news-blackout windows are gate-level, not strategy-level. If the gate fires, no entry regardless of cell.
- **Risk: trader fee budget blown** if RTH cells fire often + lose. Mitigation: each cell starts experimental (no real fills) for 2+ weeks. Real fills only after positive E and t in live shadow.
- **Risk: exit_reasoner overload** if 10+ cells fire concurrently. Mitigation: agent already has rate-limiting (3 consecutive holds max, 30-min max hold). Should scale fine to 10-15 simultaneous positions.

## Total weekend effort estimate

- Phase 0 (Friday prep): 1-2 hours
- Phase 1 (walk-forward): 3-4 hours (mostly compute; user-review at end)
- Phase 2 (calibration): 3-4 hours (compute + user direction calls)
- Phase 3 (gates): 2-3 hours (CODE + tests)
- Phase 4 (staged deploy): 1-2 hours

**Total: 10-15 hours wall-clock, of which 3-4 hours need active user attention** (review calls + HIGH_RISK approvals). The rest is compute + my implementation work.

## What success looks like

By Sunday 5:30 PM ET (just before Globex reopen):
- 3-5 new RTH cells added to `live_allowlist` with `experimental: true`
- Each has documented OOS stats (n, hit, E, t) on RTH bars
- News-blackout + opening-vol + EOD-windown gates active in risk_gate.py
- `state/strategy_validation.json` snapshot committed; baseline tag preserved for rollback
- Trader restarted with new code, shadow-firing the new cells starting 6 PM ET Sunday

After 2-3 weeks of live shadow data:
- One cell at a time graduates `experimental: false`
- RTH coverage matches Asian's ~10-14 cells
- Combine pass happens with RTH cells materially contributing

## Open questions for you before kickoff

1. **Weekend availability** — are you around Saturday day + Sunday day? The 3-4 user-direction calls cluster at phase boundaries.
2. **HIGH_RISK approvals** — pre-approve the two gate additions (opening-vol + EOD wind-down) in writing now, OR review them per-PR Sunday?
3. **Cell selection bias** — any specific RTH strategies you want me to prioritize or DE-prioritize? E.g., if you've watched MNQ pivot_reversal RTH work well by eye, that's a strong prior.
4. **Calibration philosophy** — bias conservative (tighter stops, smaller targets, lower fire rate) or bias aggressive (looser params, more signals)?
5. **Daily-trade-cap policy** — keep at 15 or raise?

## Open questions for me to answer in Phase 0

- How much historical RTH data do we actually have stored? Need 12-18mo for walk-forward.
- Does `walk_forward_firing_strategies.py` actually parameterize cleanly to `session="RTH"`, or does it have Asian assumptions baked in?
- Are there RTH-specific bar gaps (RTH closes 4 PM, gap-jump on Sunday 6 PM reopen) that the strategy code needs to handle differently?

---

**Status:** awaiting your review. Once you sign off on phasing + answer the 5 open questions, I can pre-prep Phase 0 (data pull + baseline snapshot) anytime Friday afternoon.
