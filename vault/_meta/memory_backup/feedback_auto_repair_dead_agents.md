---
name: Auto-fix silently-dead agents in the moment
description: When the trader, runtime, or any agent is detected dead/silent, immediately diagnose and patch — do not ask permission. Days with zero trading are unacceptable bleed.
type: feedback
originSessionId: b1c69b67-a794-46cc-bb06-6e08fbeea607
---
When a status check, recap, or any tool call reveals that the auto_trader, runtime/orchestrator, scheduled task, or any other fund agent has silently died, stopped logging, or is otherwise non-functional, **fix it in the same turn — do not ask the user for permission first.**

This includes (non-exhaustive):
- Process not running but PID file present (stale lock)
- Logs ending hours before market close with no exit reason
- Scheduled task fired but child process is gone (e.g., post-reboot)
- Snapshot pipeline gone stale (>5 min old during RTH)
- Any agent in the chain throwing repeated exceptions and not producing output
- Crash loops where preflight passes but trader exits within minutes

The "fix" includes whatever is needed to restore live trading: relaunching the trader, clearing stale locks, patching the launcher, adding self-heal triggers to scheduled tasks, fixing the underlying bug, etc.

**Why:** Each silent-death day costs ~$26 in fixed subscription bleed PLUS the opportunity cost of zero shots taken. The 2026-05-04 day burned a full session because Windows force-rebooted at 07:10 ET and the scheduled task never re-fired. The user explicitly told me on 2026-05-04 "whenever the trader or any other agent silently dies i want you to automatically fix it in the moment ... you must be able to patch these issues in real time and on your own."

**How to apply:**
- The HIGH_RISK_FILES restriction in CLAUDE.md (no editing `risk_gate.py`, `db.py`, `schema.sql`, `topstep.py`, `projectx_client.py`, `risk_limits.yaml.hard_rules`) still stands — those need explicit approval before edits. But operational repair (scheduled tasks, launcher scripts, stale locks, restart commands, env config) does NOT need approval.
- After fixing, briefly report what was wrong and what was patched. Don't narrate the diagnosis at length.
- If the underlying root cause is a HIGH_RISK_FILES bug, restore liveness with a workaround AND flag the deeper fix needing approval.
- Treat over-caution here as a slow loss, exactly like the cost-urgency feedback memory.
