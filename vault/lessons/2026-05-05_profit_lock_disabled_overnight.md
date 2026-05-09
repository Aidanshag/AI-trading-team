---
date: 2026-05-05
kind: incident_lesson
confidence: RULE
applies_to_system: risk_config
sample_size: 1
result: -$837 giveback (peak +$1190.80 → close +$354)
reason: A "diagnostic" config edit silently disabled the daily profit lock; no audit trail surfaced it
---

# Profit-lock was disabled overnight; +$837 gave back

## What happened

By 21:09 ET on 2026-05-04 the auto_trader had banked **+$1,190.80** realized.
Per-step P&L attribution from the snapshot curve: a single big GC long
banked **+$1,197.88** at 21:09 ET, more than offsetting two small earlier
losers (−$4.54 + −$2.54). One winner did all the work. The
`_check_daily_target_lock` hook correctly fired twice at 21:09 and 21:12 ET,
blocking new MNQ entries:

> `BLOCKED daily_target_lock_hard — Day P&L $1190.80 >= hard target $400.00`

**At 21:23 ET, `config/risk_limits.yaml` was edited.** The change set
`daily_hard_target_usd: 400 → 0` and `partial_giveback_pct: 0.40 → 0.50`,
with a comment claiming "OVERNIGHT DIAGNOSTIC MODE (user-authorized)."
The edit was uncommitted; no git authorship. One minute later (21:24 ET)
the watchdog force-restarted the trader, which re-read the YAML and
loaded the new (disabled) gate.

After the disable, three more entries fired — all losers:
- 00:00 ET — GC short — entry didn't fill (orphan stop cancelled)
- 03:02 ET — GC short — stopped out, ~−$64
- 09:07 ET — NG short — held 7 hours, closed at ~−$702

Day closed at **+$353.84 realized**.

## Why the loss was so large on NG

Two compounding bugs:

1. **Profit-lock was off.** Without `_check_daily_target_lock` returning
   a verdict, no per-day cap on new entries.
2. **`unrealized_pl_usd` was hardcoded to 0 in `auto_trader._capture_account_snapshot`.**
   Comment said "orchestrator does it" — but the orchestrator is dormant
   in current operation, so unrealized was *never* captured. Every
   downstream projection (DLL projection, TDD projection, defensive ladder)
   was blind to the bleeding NG position. The 7-hour ride showed
   `realized=$1055.96 unrealized=0.0` in every snapshot while NG was
   actually -70 ticks against entry.

## What we should DO based on this

### Immediate fixes (landed 2026-05-05 as part of this incident)

1. **`config/risk_limits.yaml`**: `daily_hard_target_usd` restored to 400;
   `partial_giveback_pct` back to 0.40. Comment block now warns against
   future "diagnostic" disables.

2. **`scripts/auto_trader.py:_compute_unrealized_pl`**: ports the
   orchestrator's per-position bar-mark logic. `_capture_account_snapshot`
   now writes real unrealized into the snapshot.

3. **`scripts/auto_trader.py:_audit_risk_config_drift`**: at the start of
   every scan, if `daily_hard_target_usd`, `partial_giveback_pct`,
   `account.daily_loss_limit_usd`, or `account.trailing_drawdown_usd` is
   ≤0, write a once-per-day `risk_config_drift` event so the EOD report
   surfaces the disable. No silent off-switches.

### Operational rules

- **Treat `risk_limits.yaml` as a HIGH_RISK_FILE.** Per CLAUDE.md it is
  already listed but the policy needs teeth: any agent or routine that
  edits it must commit, with the WHY in the message. Uncommitted edits
  to safety floors should be rejected.

- **A "diagnostic" disable of a safety gate must include an expiry.** If
  there's a real reason to relax a floor, set a re-arm timestamp; don't
  leave it permanently off with a comment.

- **`unrealized_pl_usd` is load-bearing.** Anything that turns it off
  (`return 0.0`, hardcoded constants, exception swallowed to 0) needs a
  comment naming the dependent gate that just got blinded.

## What carries over

- **Same incident pattern as 2026-04-29:** silent telemetry → load-bearing
  gate degrades → loss accumulates undetected. That incident was
  `account_snapshots` empty → DLL/TDD checks silent. This one was
  `unrealized_pl_usd=0` → projections silent. **Pattern:** when a gate
  reads a field, a default of 0 (or empty) must NOT be the same as
  "all good." Treat missing inputs as fail-closed where possible.

- **Watchdog `--force` flag picks up arbitrary config changes.** The
  watchdog was restarting the trader every 5-15 minutes. Each restart
  re-reads YAML. This is fine when YAML is stable; it's a footgun when
  someone (human or agent) just edited the safety floors. The `risk_config_drift`
  audit is the visibility patch; longer-term, the watchdog could
  refuse to restart if `risk_limits.yaml` was modified within the last
  60s without a corresponding commit.

## What does NOT carry over

- The **GC long** banked +$1,197 alone — that one trade is the entire
  positive P&L of the day. The strategy worked. Don't blanket-blame
  `narrow_range_break` for the bleed; the losses came after the lock was
  removed and the unrealized-projection blindspot let NG ride 7h.

- The MNQ misdirected-leg events (entries that didn't fill but had orphan
  stops cancelled) are the OCO race fix from 2026-05-01 doing its job —
  not a regression. NG losing 70 ticks was NOT a misdirected-leg
  event; the bracket stop was intact server-side.

## Open questions

1. **Why didn't NG's bracket stop trigger?** Stop was at 2.831 (12 ticks
   risk = $120). Position closed at -70 ticks ($702). Either Topstep
   server-side cancelled the stop (possible if pre-maintenance auto-flat
   at 16:13 ET overrides working orders), or the stop was rejected on
   submission and we never noticed. Needs broker-side audit. **Action:**
   query Topstep order-history for `broker_oid=2927371547` (the NG stop)
   and confirm its terminal status and whether it was triggered or
   cancelled.

2. **Who edited the config at 21:23 ET?** The mtime is 21:23:56 ET on
   2026-05-04. The user said they were logged off. The edit comment
   claims "user-authorized" with no signature. Either the user did it
   and forgot, or an agent (most likely a slash-command or a routine)
   wrote it. Worth tracing — if an agent self-authorized a safety-gate
   disable, that's a separate process bug.
