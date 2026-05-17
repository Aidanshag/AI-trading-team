---
type: calendar
status: ACTIVE
purpose: Queue of upcoming user-present work items. Read each morning. Scheduled Discord reminders fire when items come due.
updated: 2026-05-17
---

# Weekly calendar — queued work needing user presence

This is the single source of truth for upcoming tasks that need the user's active attention. The `FundWeeklyReminder` scheduled task reads this file every Saturday 09:00 ET and pings Discord with anything due in the next 7 days.

To add a new queued item: append under the appropriate week, set `due_date`, `status: open`, and a one-line summary.

When a task is done: change `status: open` → `status: done` and append the completion date.

## Format

```
- [DATE] [STATUS] short title
  Why: motivation
  Action: what the user should do
  Est: 30min / half-day / weekend
```

## 2026-05-18 — Monday

- [2026-05-18 06:00 ET] [scheduled-task] **FundMondayRegimeSweep**
  Auto-runs universal walk-forward with regime gating active.
  Action: review `vault/_meta/shadow_dashboard.md` after 06:30 ET; Discord-pinged on completion.
  User work: ~5 min review.

## 2026-05-23 — Saturday

- [2026-05-23] [open] **Add 3-5 mean-reverting strategies for ranging regimes**
  Why: current 28-strategy library is heavy on trend/breakout (only ~5 mean-revert variants). Ranging regime cells fire less often than they could.
  Action: pair with me to design + implement. Candidate strategies: keltner channel mean-revert, fade-the-50EMA-touch, bollinger-band-pinch, RSI-divergence reversal.
  Est: 3-4 hours user attention (with my implementation in parallel).

- [2026-05-23] [open] **Per-cell regime calibration round 1**
  Why: trend_regime + vol_regime can be combined per cell. Right now we have either/or. Some cells want "trending + high vol" or "ranging + low vol."
  Action: review the 2-week shadow data, pick cells where regime combo would help, configure.
  Est: 1-2 hours user attention.

## 2026-05-30 — Saturday

- [2026-05-30] [open] **Re-run universal walk-forward with regime gating**
  Why: confirm regime filters lift hit rates as predicted (vs Monday baseline).
  Action: kick off sweep, review comparison with the 5/18 results.
  Est: 30min user attention (mostly compute time).

- [2026-05-30] [open] **Promote first true "graduated" cell to live**
  Why: by 5/30 the 9 ag cells staged 5/17 will have 2 weeks of live shadow data. The ones with positive friction-adjusted P&L are real candidates.
  Action: review shadow_dashboard.md "Promotion candidates" section; pick top 1-2 to flip experimental:false.
  Est: 30min user attention.

## 2026-06-06 — Saturday

- [2026-06-06] [open] **Phase 2 of IB integration — historical data backfill**
  Why: once IB Gateway is connected (today, 5/17), Phase 2 is using IB's 10+ year history to do MULTI-REGIME walk-forward. Solves the "60-day overfit" problem from the universal sweep.
  Action: pair with me to design the IB historical pull cadence + storage.
  Est: 2-3 hours user attention.

## Items without specific dates (do when ready)

- **Promote `keltner_breakout/MCL/Asian/long` and `order_block_d1/MNQ/Asian/long`** — already live; monitor performance
- **Consistency-rule enforcement** (P1 backlog item) — needs HIGH_RISK file approval for hooks/risk_gate.py edit
- **Equities desk reactivation** — deferred until post-Combine + IB Phase 2 ready

## How reminders work

`FundWeeklyReminder` (Sat 09:00 ET) parses this file, finds items with `due_date` in the next 7 days where `status: open`, and posts a Discord summary. Update the dates as items shift; mark `done` when complete and they drop out of the rotation.
