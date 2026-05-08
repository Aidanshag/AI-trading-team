"""Restore the -$750 emergency_flatten level in the defensive ladder.

The user temporarily disabled this level on 2026-04-29 evening. This
script auto-restores it. Idempotent: if the level is already active,
it's a no-op.

Triggered by the 'FundRestoreEmergencyFlatten' Windows Task Scheduler
task, scheduled for 9 AM the morning after the user disabled it.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
RISK_LIMITS = HERE / "config" / "risk_limits.yaml"


COMMENTED_BLOCK = """    # ── TEMPORARY 2026-04-29 (USER OVERRIDE) ──
    # The -$750 emergency_flatten level is DISABLED for the rest of tonight's
    # session per user directive. Topstep's $1000 DLL remains the broker-side
    # hard backstop. The -$500 lockdown above still blocks new entries.
    # RESTORE BEFORE NEXT SESSION:
    #   - threshold_usd: -750
    #     action: "emergency_flatten"
    #     description: "Flatten at market immediately. Trading halted for session."
"""

ACTIVE_BLOCK = """    - threshold_usd: -750         # 75% of Topstep DLL — approaching breach
      action: "emergency_flatten"
      description: "Flatten at market immediately. Trading halted for session."
"""


def main() -> int:
    if not RISK_LIMITS.exists():
        print(f"ERROR: {RISK_LIMITS} not found", file=sys.stderr)
        return 1

    text = RISK_LIMITS.read_text(encoding="utf-8")

    if "action: \"emergency_flatten\"" in text and "TEMPORARY 2026-04-29" not in text:
        print("emergency_flatten already active. No change needed.")
        return 0

    if COMMENTED_BLOCK not in text:
        print("ERROR: Could not find the commented-out block. "
              "Restore manually by editing config/risk_limits.yaml",
              file=sys.stderr)
        return 2

    new_text = text.replace(COMMENTED_BLOCK, ACTIVE_BLOCK)
    RISK_LIMITS.write_text(new_text, encoding="utf-8")
    print(f"[{datetime.now(tz=timezone.utc).isoformat(timespec='seconds')}] "
          "Restored -$750 emergency_flatten level in defensive ladder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
