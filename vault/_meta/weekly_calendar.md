---
type: calendar
status: ACTIVE
purpose: Queue of upcoming user-present work items. Read each morning. Scheduled Discord reminders fire when items come due.
updated: 2026-05-17
---

# Weekly calendar — queued work needing user presence

This is the single source of truth for upcoming tasks that need the user's active attention. The `FundWeeklyReminder` scheduled task reads this file every Saturday 09:00 ET and pings Discord with anything due in the next 7 days. **Schedule compressed 2026-05-17** — moved most items up by 1-2 weeks per user direction.

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

## 2026-05-19 — Tuesday

- [2026-05-19] [open] **Add 3-5 mean-reverting strategies for ranging regimes**
  Why: current 28-strategy library is heavy on trend/breakout (only ~5 mean-revert variants). Ranging regime cells fire less often than they could. Trend regime filter shipped 5/17 only helps if we have strategies for BOTH regimes.
  Action: pair with me to design + implement. Candidates: keltner channel mean-revert, fade-the-50EMA-touch, bollinger-band-pinch, RSI-divergence reversal, donchian-channel-fade.
  Est: 1.5-2 hrs user attention (with my implementation in parallel — was 3-4 hrs but parallelizable).

## 2026-05-20 — Wednesday

- [2026-05-20] [open] **Per-cell regime calibration round 1**
  Why: trend_regime + vol_regime can be combined per cell. Right now we have either/or. Some cells want "trending + high vol" or "ranging + low vol." Don't need 2 weeks of forward data — use the 6064 historical shadow trades to do an initial pass.
  Action: review my regime×outcome breakdown across historical cells, configure top candidates.
  Est: 1 hr user attention.

## 2026-05-22 — Friday

- [2026-05-22] [open] **Universal sweep with regime gating + first promote review**
  Why: by Friday we'll have 5 days of regime-gated live data on the 35 cells. Run the sweep, compare hit rates to baseline, see if regime gating delivered.
  Action: kick off sweep (or wait for `FundUniversalSweep` Sun 5/24), review comparison + flip first promotion candidate to live if criteria met.
  Est: 30 min user attention.

## 2026-05-23 — Saturday

- [2026-05-23] [open] **IB Phase 2 — historical data backfill**
  Why: once IB Gateway is connected (today, 5/17), Phase 2 uses IB's 10+ year history to do MULTI-REGIME walk-forward. Solves the "60-day overfit" problem from the universal sweep on ProjectX bars.
  Action: pair with me to design IB historical pull cadence + storage.
  Est: 2-3 hrs user attention.

## Items without specific dates (do when ready)

- **Promote `keltner_breakout/MCL/Asian/long` and `order_block_d1/MNQ/Asian/long`** — already live; monitor performance
- **Consistency-rule enforcement** (P1 backlog item) — needs HIGH_RISK file approval for hooks/risk_gate.py edit
- **Equities desk reactivation** — deferred until post-Combine + IB Phase 2 ready

## How reminders work

`FundWeeklyReminder` (Sat 09:00 ET) parses this file, finds items with `due_date` in the next 7 days where `status: open`, and posts a Discord summary. Update the dates as items shift; mark `done` when complete and they drop out of the rotation.

For tighter cadence (mid-week reminders): consider adding `FundMidweekReminder` (Wed 09:00 ET) by editing `scripts/install-vault-maintenance-tasks.ps1` or as a one-off `schtasks /create`.
