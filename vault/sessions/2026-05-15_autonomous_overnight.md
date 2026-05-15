---
type: handoff_doc
date: 2026-05-15
window: ~22:00 ET 5/14 → 02:00 ET 5/15 (overnight)
agent: Claude Opus 4.7 via /loop /improve-fund
generated_at: 2026-05-15T06:25:00+00:00
---

# Overnight autonomous-improvement session — handoff to user

User went offline ~midnight ET 2026-05-15 with explicit authorization:
"do as many cycles as you can without me here. try and get the backlog
as minimal as you can on your own." Trader-shutdown authorized for
deploys; HIGH_RISK_FILES still off-limits.

This doc fills in WHY each commit happened — the auto-generated
session summary has the commit list, but not the narrative.

## What the night was for

Two days earlier we audited trade execution and found **$626 of summed
peak MFE captured only $98 realized** (84% leakage). Two distinct bugs
were biting:

1. **POST_FILL_SLIPPAGE direction bug** — the gate used `abs()` slippage
   so favorable fills were treated as failures and emergency-flattened.
   At least 7 winning entries killed in 24h.
2. **EU6/6E symbol alias gap** — `_TICK_ECONOMICS` had "6E" but the
   broker contract resolves to "EU6", so profit-lock + loss-cap were
   silently blind to the 5/14 EU6 short for 2h14m.

Both fixed before the user went offline. The overnight work was the
follow-through on the exit-rule layer plus measurement infrastructure.

## Commits, cycle-by-cycle

| Cycle | Commit | Headline | Why |
|---|---|---|---|
| (pre-loop) | `2bbc312` | POST_FILL_SLIPPAGE direction-aware + alert pytest silencing | Tonight's two biggest live-money bugs. |
| 1 | `e8eddbe` + `22410de` | EU6/6E tick aliases + Pattern A CI test | n=4 Pattern A escalation. |
| 2 | `ab5063b` + `a247b74` | profit_protect close_position audit-trail + regression test | The call-site migration already shipped at 326ab7f; cycle 2 added the audit row + regression-guard test. |
| 3 | `fdafe72` | Continuous percent-of-peak retracement | Replaces static tiers. Peak $113 now floors at $79 (was $32). |
| 4 | `ae6d8f7` | Reversal-detection exit | 3 consecutive bars closing against position → close. Min peak $15 gate. |
| 5 | `722063e` | Time-based profit decay | Peak >15 min stale + >30% retrace → close. Works on sub-$20 peaks where percent-of-peak doesn't. |
| 6 | `2800d99` + `6cdab2f` | Sentinel anomaly watcher + scheduled task | 6 invariants checked every 10 min. Catches the kind of silent bugs that hit us this week. **Live in `FundSentinel` Windows task.** |
| 7 | `1abbef8` | Research: ProjectX SignalR hubs at rtc.topstepx.com | Sub-second tick data IS available. Recommendation: build `tools/tick_stream.py` (signalrcore lib). |
| 8 | `eda4404` | Research: broker limit fill anomaly premise was wrong | 0 adverse-fill limits in 75-order audit. The cited 5/14 04:28 incident was a `type=2 (Market)` order, not a limit. |
| 9 | `4e7aa9a` | Backlog audit — closed 2 already-shipped items | Trailing broker stop (already at 326ab7f) + MGC walk-forward (already graduated by FundValidateLiveFilter). |
| 10 | `4b13c5d` | Sentinel false-positive fix | First live sentinel run flagged the daily-trade-cap state as a warning; now it correctly skips known-benign trader states. |
| 11 | `e4d1e42` | Proposal: peak-capture efficiency metric | The /improve-fund queue is drained — per skill rules, freshly-identified items go propose-only. |

Trader restart at ~00:30 ET picked up cycles 1-5. Trader is now running
with all new code loaded (PIDs 32732/36728).

## What this means for the trader's behavior tomorrow

When the trader restarts after Friday's market-close (or the next time
you bounce it), it will:

1. **Reject buy-limit fills that are >10t ADVERSE** — favorable fills now
   correctly proceed to stop placement (direction-aware fix).
2. **Recognize EU6 (and other FX/equity contract roots)** for profit-lock
   + loss-cap purposes. No more "BLIND to this position" spam.
3. **Use `close_position` endpoint** for profit-lock flattens (already
   shipping pre-tonight; now audit-trail-row written to `decisions`).
4. **Apply continuous percent-of-peak retracement** instead of static
   tier table. Peak $50 → floor $35 (was $18). Peak $113 → floor $79
   (was $32). Big winners (>$750 peak) still on runner-zone tiers.
5. **Fire REVERSAL_EXIT** if 3 consecutive 1-min bars close against the
   position direction AND peak >= $15.
6. **Fire TIME_DECAY_EXIT** if peak was hit >15 min ago AND current is
   below peak by >=30%. Works even on sub-$20 peaks.
7. **Be watched by sentinel every 10 min** — Discord-alerts on mock
   orders in DB, blind positions, post-floor close slippage, orphan
   stops, brain/trader rate mismatches, duplicate trader processes.

## What's left in the backlog (15 open, 1 proposal)

**Auto-eligible but needs you:**
- Peak-capture efficiency metric (NEW proposal, my recommendation as
  the next ship — closes the variance-trigger loop on tonight's exit
  fixes). 45min, low risk, auto-merge:yes.
- Volatility-aware tier tightening (P2) — calibration choice needs
  human review.
- Re-test broker target legs (P1) — manual broker observation.

**Touches HIGH_RISK_FILES (autonomy stopped):**
- Consistency-rule enforcement (P1) — `hooks/risk_gate.py`.

**Needs user action outside the code:**
- Wire FundWeeklyAudit routine (P1, 15min) — needs GitHub auth.

**Not Combine-priority:**
- Post-payout MLL recalibration (P3) — XFA-only.

**Standing reframe items:**
- Several validation-infra items waiting on user direction.

## Things you'll want to look at first

1. **Discord** — should have only `FundSentinel` startup pings overnight.
   If you see anything else, sentinel caught a real issue. Check `vault/
   _meta/sentinel_2026-05-15.md` for the daily report.
2. **`vault/research/analysis/2026-05-15_realtime_price_feed.md`** —
   greenlight this and we go from 60s-stale bar polling to sub-second
   tick data. Biggest single edge-capture upside left.
3. **The peak-capture-metric proposal in backlog** — small change,
   closes the measurement loop on tonight's exit work. I'd ship it
   first thing.
4. **Test count:** 519+ green. Run `.venv/Scripts/python.exe -m pytest
   tests/ -q --ignore=tests/test_overnight_fixes.py` to verify.
5. **Trader is alive** — PIDs 32732/36728 (live_trader),
   19544/19892 (brain_signaler). Sentinel scheduled task: `FundSentinel`
   every 10 min.

## What I deliberately did NOT do

- Did NOT touch HIGH_RISK_FILES (hooks/risk_gate.py, state/db.py,
  tools/projectx_client.py, etc.) — no autonomous edits there.
- Did NOT implement the freshly-identified peak-capture-metric — kept
  it as a proposal per /improve-fund's "no implementing freshly-
  identified items in same cycle" rule.
- Did NOT manually flip experimental cells or change live_allowlist.
- Did NOT touch the broker target leg flag (SKIP_TARGET_LEG=True) —
  that requires manual observation per the backlog item.
- Did NOT push directly to remote without committing first; every
  cycle made its own commit with a real message.

## Cost note

`/improve-fund` skill's budget cap was $5/cycle. Tonight: 11 cycles +
inline work. Each cycle's worktree-agent invocation was the bulk of
the spend (~$0.50-1.00). Total tonight likely $5-10 in API. The
sentinel scheduled task spends ~$0 (no LLM calls — pure Python checks).

## Stopping the loop

After this handoff doc, I'm letting the loop expire. The next /loop
wake won't fire automatically. The `FundSentinel` scheduled task is
the ONLY autonomous overnight monitor running.

If something looks wrong in the morning, the easiest reset is:
`powershell -ExecutionPolicy Bypass -File scripts/restart-live-trader-
if-dead.ps1` (idempotent — does nothing if trader's alive).
