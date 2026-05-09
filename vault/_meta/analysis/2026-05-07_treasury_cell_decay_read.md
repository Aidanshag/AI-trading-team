---
type: analysis
date: 2026-05-07
author: Cowork (Claude)
applies_to: [CIO, Risk Manager, Quant Researcher, Edge Hunter]
sources:
  - vault/research/live_vs_oos/2026-05-07_live_r_comparison.md
  - state/fund.db (orders, risk_events, account_snapshots)
  - state/strategy_validation.json (live_allowlist + live_strategies_filter)
  - vault/_meta/cowork_session_log.md
  - git log since 2026-04-29
confidence: ADVISORY
status: open
---

# Treasury cell decay read — 2026-05-07

## Headline

**The live-vs-OOS tracker is reporting decay on cells that are no longer
allowed to trade live, and the cells that ARE allowed have zero live
data.** This is not a contradiction; it's a sign that the post-lockdown
state is so new that we're operating on theoretical edge with no live
confirmation — and the tracker's UI hasn't yet caught up to the
allowlist change.

## The data

### Live trades placed since Combine start (auto_trader entries)

| Window | Count | Symbols | Strategy mix |
|---|---:|---|---|
| 2026-04-29 | 97 | NG, 6E, GC, ZN, MES | Non-gap_fill (the disaster day; pre-snapshot-pipeline-fix) |
| 2026-05-01 | 2 | 6E, NG | Non-gap_fill |
| 2026-05-04 | 4 | MNQ, GC | Non-gap_fill (pre-profit-lock-disable incident) |
| 2026-05-05 | 5 | MCL, GC, NG | inside_bar_break, narrow_range_break (pre-lockdown) |
| 2026-05-06 | 5 | MCL, GC, NG | narrow_range_break (last fires before 22:24 UTC lockdown) |
| 2026-05-07 | **0** | — | _Lockdown universe = gap_fill on ZN/ZT/ZB/ZF_ |

### Live allowlist (post 2026-05-06 22:24 UTC lockdown)

16 cells, all `gap_fill`, all on Treasury futures: ZN×4, ZT×4, ZB×5,
ZF×3. Per-symbol session/side breakdown in
`state/strategy_validation.json:live_allowlist`.

### Live-vs-OOS tracker contents (today)

13 trades evaluated, 0 of them on the currently-live universe. All 13
are `narrow_range_break` or `inside_bar_break` on GC/MCL/MES/MNQ/NG —
strategies and symbols that were live PRE-lockdown but are shadow-only
NOW.

**Specifically: the two cells flagged `⚠ UNDERPERFORM` today
(`narrow_range_break|GC|Asian|short`, `narrow_range_break|MCL|Asian|long`)
are not in the live allowlist. The flag is a historical observation of
a strategy that was correctly demoted, not a live risk signal.**

## The implication

The fund is in a state where:

1. **Validated edge** (per Tier 3 walk-forward 2026-05-05) is
   `gap_fill` on ZN/ZT/ZB/ZF with OOS t-stats of +7.95 to +11.76 and
   n=240+ per cell.

2. **Live universe** matches the validated edge exactly.

3. **Live data on the live universe** = zero trades, zero observations,
   zero confirmation that the OOS edge transfers.

The tracker's "decay" signals are about strategies the system already
removed. They're informational (those decisions were correct) but they
say nothing about what's actually at risk going forward.

## Why no Treasury gap_fill has fired yet

Two plausible explanations, neither yet confirmed:

**A. Gaps haven't materialized.** `gap_fill` requires
`|open − prior_close| > 0.75 × ATR(14)`. Treasury futures have been
running orderly the past 24h (DGS10 +0.07% / 5d, range regime per the
macro brief). When yields are moving smoothly without overnight news
gaps, the strategy doesn't trigger. This is the strategy working as
designed — it's a conditional edge, not a constant-fire edge.

**B. The risk-gate stack is blocking.** Last 7 days of risk events:
- `daily_fee_budget_exhausted` (block) — n=224
- `thin_tape_regime_block` (info) — n=26
- `globex_reopen_buffer_block` (info) — n=20
- `bracket_oco_misdirected_leg` (breach) — n=9
- `session_cutoff` (block) — n=9
- `daily_trade_count_cost_aware` (block) — n=6
- `daily_target_lock_hard` (block) — n=2

Many of these blocks are pre-lockdown (the 224 daily_fee_budget hits
mostly cluster around the 4/29 incident period and the pre-lockdown
days). Worth verifying which gates are blocking signals on the CURRENT
allowlist specifically.

## What deserves elevated scrutiny when Treasury gap_fill does fire

The first 5–10 fires on each cell are the highest-information trades
the system will ever see, because they're the first observations after
the lockdown. The system should treat them as a calibration sample,
not as routine.

**Order of expected first-fire by signal mechanic + standing thesis evidence:**

1. **`gap_fill | ZT | Asian | short`** — strongest OOS in the universe
   (E=+1.54R, t=+8.63, n=110). 2Y is most sensitive to Fed-funds
   repricing flow — overnight Asian session is when sovereign hedging
   produces the cleanest gaps. Highest-likelihood first fire.
2. **`gap_fill | ZB | Asian | short`** — second strongest (E=+1.19R,
   t=+8.15, n=145). 30Y reacts to term-premium flow.
3. **`gap_fill | ZN | Asian | short` / `long`** — the original
   walk-forward target (E=+1.10R, t=+11.95, n=256 OOS). Most-tested cell.

When any of these fires, the Risk Manager / Red Team should pay
disproportionate attention. Specifically:
- Was the gap flow-driven (no headline) or information-driven (FOMC
  speaker, geopolitical news, surprise data)? The former is the validated
  regime; the latter is where edge fails.
- Did the trade close at target, stop, or in-between? In-between fills
  carry less calibration signal than clean target/stop hits.
- Did the macro brief that morning flag any caution that turned out to
  matter (or not)? This is the brief's first post-lockdown calibration test.

## Cross-cell correlation flag

Per the standing thesis on [[ZN]], the four Treasury cells are one
trade in aggregate (duration basket). The risk hook's
`correlated_baskets.duration_basket` should cap simultaneous Treasury
positions; verify this is configured and enforced.

If two cells fire same-direction within a short window (e.g.,
`gap_fill|ZN|Asian|long` AND `gap_fill|ZB|Asian|long` both fire at
03:00 UTC), the trader is effectively making one duration bet at 2x
size. The current sizing (1 contract per cell) becomes 2 contracts
of duration risk. Worth confirming the sector cap actually fires in
that scenario.

## Concrete next steps for the system

1. **Fix the live-vs-OOS tracker's display** to either filter out
   non-allowlisted cells or show them in a separate "decommissioned
   strategies" section. Today's report buries the lede.

2. **Add a "no live data yet" placeholder** for the 16 currently-live
   Treasury cells, with the OOS prediction and an estimated trigger
   frequency (from backtest history). When live data arrives, replace
   the placeholder.

3. **Wire the auction calendar's `concession_days` into the
   high-impact-blackout gate** (or surface as a lesson). Tue 5/12 and
   Wed 5/13 are auction days for ZN and ZB — those are exactly the
   days Treasury gap_fill is most exposed to information-driven gaps.
   Currently the macro brief flags this but the gate doesn't act on it.

4. **Set a calibration-window lesson**: "first 10 fires per cell after
   the 2026-05-06 lockdown are calibration-grade — Risk Manager treats
   them with elevated scrutiny." When that lesson reaches RULE tier
   (after 30+ live trades across the universe), retire it.

## Confidence and lifecycle

ADVISORY (n=1 observation, this analysis). Will graduate to PATTERN
once we see the prediction tested: either Treasury gap_fill cells
start firing and live R approximates OOS E (validates the lockdown
choice), or they fire and decay (means the OOS sample didn't generalize
and we need to revisit). Either outcome is a learning observation.

## See also

- [[../theses/ZN]], [[../theses/ZT]], [[../theses/ZB]], [[../theses/ZF]]
- [[../research/live_vs_oos/2026-05-07_live_r_comparison]]
- [[../research/validation/promotion_log]]
- [[../_meta/learning_system]]
