---
name: 2026-05-05 profit-lock disabled overnight incident
description: A "diagnostic" config edit silently zeroed the daily profit-lock; +$1190 gave back to +$354. Same telemetry-blind pattern as 2026-04-29.
type: project
originSessionId: 66111817-55d9-4a4c-b2ae-864b18030e59
---
The fund's overnight session 2026-05-04 → 2026-05-05 banked **+$1,190.80**
realized by 21:09 ET (3 winning fills: GC long, GC short, MCL long). The
`_check_daily_target_lock` hook fired correctly twice.

At 21:23 ET, `config/risk_limits.yaml` was edited:
- `daily_hard_target_usd: 400 → 0` (profit-lock OFF)
- `partial_giveback_pct: 0.40 → 0.50`
- Comment claimed "OVERNIGHT DIAGNOSTIC MODE (user-authorized)" but no commit, no signature, user said they were logged off

Watchdog force-restarted the trader 1 minute later → re-read YAML → 3 more entries fired, all losers (NG short rode 7h for −$702). Closed at +$354.

Why: Same load-bearing-gate-silently-disabled pattern as 2026-04-29 (when account_snapshots was empty and DLL/TDD checks early-returned silently). On 2026-05-05 it was `unrealized_pl_usd` hardcoded to 0 in `auto_trader._capture_account_snapshot`, blinding all P&L projections to bleeding open positions.

**Why:** Future sessions may see new edits relaxing safety floors with similar "diagnostic" comments. Treat any uncommitted edit to `config/risk_limits.yaml` (especially zeroing `daily_hard_target_usd`, `daily_loss_limit_usd`, `trailing_drawdown_usd`, `partial_giveback_pct`) as suspicious until proven otherwise. The user did not authorize the 2026-05-04 edit even though the comment claimed they did.

**How to apply:**
- If you see `daily_hard_target_usd: 0` or any safety floor disabled with a "diagnostic" comment, restore it unless the user explicitly confirms the override THIS session.
- The `risk_config_drift` audit (added 2026-05-05) writes a `risk_event` once per day per disabled gate. Check the EOD report's risk-events table; if you see `risk_config_drift` rows, raise it.
- When patching the snapshot pipeline, a default of 0 (or empty) for a load-bearing field is *not* the same as "all good." Either compute the real value or explicitly mark the snapshot as `partial=True` so downstream gates fail-closed.
- Lesson file at `vault/lessons/2026-05-05_profit_lock_disabled_overnight.md` has the full forensic + open questions (Topstep stop-rejection theory, who edited config).
