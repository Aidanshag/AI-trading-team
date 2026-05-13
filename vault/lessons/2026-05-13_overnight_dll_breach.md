---
date: 2026-05-13
kind: incident_lesson
confidence: RULE
applies_to_system: live_trader_risk_gates
sample_size: 1
result: -$1,005.72 day (Topstep canTrade=0; account locked at $51,569)
reason: live_trader simplification left two safety floors behind — no upper bound on signal R, and dll_breached read the wrong config key
---

# Overnight DLL breach — wide GC stop + wrong-key DLL gate

## What happened

Overnight 2026-05-12 → 2026-05-13. Trader had been in shadow mode all of
5/12 with `trading_halt_until=2026-05-13T01:35:53Z`. The halt **expired
at 21:35 ET** (5/12). At 21:46 ET the trader fired its first live order
of the night. Three brackets fired in 46 minutes; Topstep flipped
`canTrade=0` at 23:32 ET.

| UTC | ET | Event | Day P&L |
|---|---|---|---|
| 01:46 | 21:46 | GC long: entry filled 4716.5, broker stop placed at 4710.1 — **64-tick / $640 stop** | $0 |
| 02:02 | 22:02 | GC stopped out (per-trade cap fired at −$210 unrealized but didn't exit fast enough; broker stop caught it at −$644) | −$644 |
| 02:02 | 22:02 | MNQ bracket fires immediately. Entry filled higher than expected; broker stop correctly placed below fill. Geometry was actually fine. | −$644 |
| 02:07 | 22:07 | MNQ closed | −$681 |
| 02:32 | 22:32 | **3rd bracket fires — GC short — at day P&L −$683**, deep past what the user expected the internal floor to be. | −$683 |
| 03:32 | 23:32 | 3rd stopped out; Topstep flips canTrade=0 | **−$1,006** |
| 07:13 | 07:13 (5/13) | Snapshot writer dies — last DB heartbeat | frozen |

The Windows-update reboot at **07:20 ET (5/13)** is a SEPARATE fault.
KB5087051 / KB5089549 / KB5092762 forced a reboot that killed the python
process. This explains the 5.6h of stale snapshots but did NOT cause the
bad trades — the trades fired BEFORE update activity began at 21:53 ET.

## Root causes

**Pattern B — wide-stop / no-upper-bound:**
The strategy ([narrow_range_break](../../tools/backtest/strategies.py) GC
Asian long, per live_allowlist) returned a 6.4-point native stop. The
trader placed it unchecked. `MIN_SIGNAL_R_TICKS=6` exists to reject
**too-narrow** stops; there was no symmetric defense against **too-wide**
stops. 64 ticks × $10/tick × 1 ct = $640 risk on a single trade — bigger
than the internal $250 DLL on entry alone. Pattern B because calibration
was wrong-context: the strategy's stop sizing assumed regime conditions
where 64 ticks was reasonable; thin Asian-tape ATR made it the entire
account.

**Pattern A — wrong-config-key DLL gate:**
`scripts/live_trader.dll_breached` read
`account.daily_loss_limit_usd` (default `1000` = Topstep's hard limit)
instead of `account.internal_dll_target_usd` (configured `250` after the
4/29 incident). At −$683 day P&L the gate returned `False` because
`−683 > −1000`, allowing the 3rd bracket to fire. The internal soft DLL
that the user explicitly set ("agents target THIS, not Topstep's") was
silently ignored. Same shape as 4/29 (empty `account_snapshots` → all
gates silent) and 5/5 (`unrealized_pl_usd` hardcoded to 0 → all
projections blind).

**Compound — per-trade cap is scan-tick bounded:**
`PER_TRADE_LOSS_CAP_USD=150` fires from `tools/profit_protect.check_and_close`,
which is only called on the 5-min scan tick. Thin overnight tape moved
GC from +$70 peak to −$210 within a single scan window; the next scan
saw it past the cap and force-closed via market-IOC, but the broker stop
at 4710.1 had already fired by then. The "$150 cap" is functionally
bounded above by `scan_interval × tape_velocity + slippage`, not by the
$150 number.

**Operational — watchdog gap:**
`FundTraderWatchdog` was Disabled at the OS level (last run 5/8 17:31)
as part of the 5/10 "detection-first" alerting refactor. The active
revive path is `FundLiveTraderEnsureRunning`, which only fires Sun 17:00
+ Mon-Fri 06:30 ET. When today's Windows reboot killed the trader at
07:20 ET, nothing was scheduled to revive it for ~23 hours.

## How the trader regressed on its own lessons

The 4/29 incident's encoded defenses lived in `scripts/auto_trader.py`
(2,900 LOC). The **"knife" simplification** on 2026-05-11 evening cut
auto_trader down to `live_trader.py` (~1300 LOC). Three encoded defenses
got dropped on the floor in that move:

1. The **internal soft DLL** read (auto_trader correctly read
   `internal_dll_target_usd`; live_trader's reimplementation didn't).
2. The **defensive ladder** (`_check_combine_defensive_ladder` —
   progressive size-reduction at −$150/−$300/−$500) — lives in
   `hooks/risk_gate.py` only; doesn't run in the live_trader path.
3. The **per-trade risk cap** (`per_trade_risk_pct_of_equity: 0.005` —
   still in `config/risk_limits.yaml` but unread by any current code).

This is a meta-lesson: **when you simplify a system, audit which encoded
defenses live in the part you're cutting, and re-encode them in the
replacement.** A code-review checklist asking "what gates from the prior
version are NOT present in this one?" would have caught all three.

## Fixes landed 2026-05-13

1. **`scripts/live_trader.MAX_SIGNAL_RISK_USD = 150`** + new gate
   `signal_passes_max_risk_gate()`. Rejects any signal whose
   `stop_ticks × tick_value × qty > 150` BEFORE the order leaves the
   trader. Wired into `scan_once` after the existing min-R gate.
   Default-denies on missing `tick_value` (Pattern A defense).

2. **`scripts/live_trader.dll_breached`** rewritten to read
   `internal_dll_target_usd` first, fall through to Topstep's
   `daily_loss_limit_usd` only if internal is missing or zero. Treats
   `0` / `None` / missing as "not configured" so a wiped value can't
   silently disable the gate.

3. **`scripts/trader_watchdog._revive()`** redirected from the disabled
   legacy `FundAutoTraderDaily` task to the active
   `restart-live-trader-if-dead.ps1` launcher (which is idempotent and
   duplicate-safe). Same module also got a docstring update.

4. **`tools/trader_utils._tick_value`** added — pure helper reading
   `tick_value` from `config/symbols.yaml`, parallel to existing
   `_tick_size`.

5. **`tests/test_pattern_regressions.py`** extended with 4 new tests
   under the n=3 escalation surface — oversized-stop rejection, sane-
   stop passes, internal-DLL primary read, Topstep fallback. Per the
   CLAUDE.md n=3 rule: any pattern that recurs gets a build-failing CI
   test.

6. **`tests/test_live_trader.py::test_dll_not_breached`** updated to use
   −$100 (under the $250 internal target) rather than −$500 (which now
   correctly fires the internal gate).

7. **Watchdog daemon process started in the background** as a stopgap
   (`python -m scripts.trader_watchdog --daemon --interval 90`). Survives
   until reboot. **Pending user action:** re-enable
   `FundTraderWatchdog` from elevated PowerShell:
   `schtasks /Change /TN "FundTraderWatchdog" /ENABLE`.

## Operational rules

- **Every signal must pass a max-risk gate, not just a min-R gate.**
  A stop being "too tight" and a stop being "too wide" are both
  signal-rejection conditions. Don't ship one without the other.

- **`internal_dll_target_usd` is the agents' target.** Live code must
  read this field FIRST, not `daily_loss_limit_usd`. The latter is the
  Topstep server-side floor and exists as the OUTER backstop, not the
  agent-facing one.

- **Simplifications must inventory encoded defenses.** When refactoring
  a risk-critical module, dump the list of every gate, every read, and
  every default in the OLD version, and check each one is either
  preserved in the NEW version or explicitly justified as removed.

- **Per-trade caps that depend on scan cadence are not actually caps.**
  A $150 cap that fires on a 5-min tick is a $150-plus-slippage-plus-
  five-minutes-of-tape-velocity cap. Either move the cap to a tighter
  poll, or place an additional broker-side stop tighter than the
  strategy stop. (Pending — Tier 2 fix.)

## What carries over

- **3rd recurrence of the silent-default pattern** (4/29 → 5/5 → 5/13).
  Every time it has been a different field reading wrong: empty
  account_snapshots, hardcoded `unrealized_pl_usd=0`, wrong key for
  DLL. The fix shape is identical each time: fail closed on the missing
  signal, log loudly on the read path. Worth a once-per-quarter audit
  of every gate's default value, asking "what does this do if the field
  it reads is missing or zero?"

- **Calibration scope must follow the deployment scope.** GC
  `narrow_range_break` Asian long had OOS stats from a sample that
  presumably included nights similar to this one — but the strategy's
  stop sizing isn't session-aware. The trader's gates need to encode
  the "what's the worst single trade could be" constraint independent
  of what the strategy thinks is appropriate. (Pattern B encoded
  defense.)

- **Windows updates can kill the trader silently.** Tonight's reboot
  was at a benign time (07:20 ET, account locked anyway). A reboot
  during active overnight trading would be a different story. Worth
  configuring Windows Update active-hours to overlap the trading
  window, OR adding a system-resume hook that re-launches the trader.

## What does NOT carry over

- The **MNQ "inverted stop"** in the DB was a red herring. The strategy's
  original stop level was stored, not the broker-side recalculated stop.
  The broker had the stop correctly below the actual fill. The DB-write
  bug is real but didn't cause loss this incident. (Tier 3 fix — write
  broker-side stop, not strategy stop.)

- The **Windows update did not cause the trades.** The bad trades fired
  21:46–22:32 ET; updates began staging 21:53 ET. The trades came first.

## Open follow-ups (deferred)

- **Per-trade cap latency.** Move `tools/profit_protect.check_and_close`
  off the 5-min scan tick into a separate ~30s polling loop. OR place a
  broker-side stop at the cap distance in addition to the strategy stop.

- **Defensive ladder in live_trader.** Port a minimal version of
  `_check_combine_defensive_ladder` from `hooks/risk_gate.py`. Currently
  the live_trader has only a single DLL trigger, not a graded one.

- **`orders.ts_filled` not being written since 2026-05-11.** Either the
  live_trader deployment broke a reconcile path or there isn't one.
  Telemetry blind — no broker-side audit possible without it.

- **`daily_pl` table empty since 2026-05-01.** Find the call site and
  re-wire from the nightly path or live_trader's daily-close.

- **`FundTraderWatchdog` re-enablement.** Needs admin PowerShell.
  Daemon-mode stopgap running but won't survive reboot.
