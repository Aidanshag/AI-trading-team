---
name: Silent default = off — load-bearing fields must fail-closed
description: When a safety gate reads a field whose default value (0, None, empty) is indistinguishable from "all good," the gate silently allows. Same pattern hit twice in 6 days.
type: feedback
originSessionId: 66111817-55d9-4a4c-b2ae-864b18030e59
---
When reviewing or writing risk/safety code, **treat any read-default-and-allow
path as fail-closed-needed**. Two real incidents on this fund matched this
exact pattern within 6 days:

- **2026-04-29 DLL breach**: `account_snapshots` table empty → all
  P&L-aware gates received `snap=None` → early-returned to allow → DLL
  breached overnight in thin tape (-$1,013).
- **2026-05-05 NG ride**: `unrealized_pl_usd` hardcoded to `0.0` in
  `auto_trader._capture_account_snapshot` (justified by "orchestrator
  computes it" — but orchestrator dormant) → DLL/TDD/ladder projections
  all read 0 unrealized → blind to a 7-hour bleeding NG short → -$702.

**Why:** The user noted explicitly: "part of the reason the same mistakes
are being made is because there is no memory of them and then the
ensuing fix that is put into place." Without a memory entry that names
the *pattern*, each incident's lesson stays specific to its symptoms,
and the next instance gets misdiagnosed as a new bug.

**How to apply:**
- When auditing or writing a gate that reads a snapshot/config field,
  ask: "If this field were missing/zero/empty, would this gate let a
  bad trade through?" If yes, the gate is silently allowing — fix the
  default, or fail-closed when the field is absent.
- Common offenders: `snap.get("realized_pl_day_usd") or 0.0`,
  `pacing.get("daily_hard_target_usd", 0)`, `if hard > 0 and ...`,
  `return None` paths inside risk hooks.
- For *configuration* fields specifically: a value of 0 or absent
  should mean "still validate" or "log an audit event," NEVER
  "skip this check." This is why `_audit_risk_config_drift` was
  added 2026-05-05 — it's the meta-defense for this pattern.
- When a load-bearing field is intentionally optional (e.g., `unrealized`
  during partial broker outage), distinguish "missing" from "zero" —
  use `None` and explicit checks, not a 0 sentinel.

The fix landed in commit `b6bed39` (loss-tier hard cap + unrealized
compute + audit). The pattern, captured here, is what survives across
sessions.
