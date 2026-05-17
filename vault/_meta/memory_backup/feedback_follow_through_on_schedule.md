---
name: feedback-follow-through-on-schedule
description: "User flag 2026-05-14 — when something is queued/scheduled for \"later\" or \"tomorrow,\" it MUST land in the improvement_backlog with explicit auto-merge eligibility OR a hard schedule. User will forget; the system has to remember."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b979f9ba-f40d-4fdc-8d30-1f25c42d62e2
---

# When you defer something, schedule it concretely

**Rule:** any time I tell the user "I'll do that later" or "queueing for
tomorrow" or "P0 in backlog" — the deferred item MUST be either:

1. Written into `vault/_meta/improvement_backlog.md` with **explicit**:
   - Priority (`[P0|P1|P2|P3]`)
   - Effort estimate
   - Risk level
   - `autonomous-eligible: yes|no` flag
   - `auto-merge: yes|no` flag (only `yes` if it doesn't touch HIGH_RISK_FILES)
   - Acceptance criteria
   - Files to touch
2. OR scheduled as a remote Claude routine via the `schedule` skill with
   a cron / `run_once_at`.

**Never** "I'll remember" — I will not. Future-Claude in a new session
won't either. The user explicitly stated 2026-05-14: *"I have asked you
to schedule future things before and I want to make sure you remember
that ... I will likely forget about it otherwise."*

**Why this matters:** the user's mental model is that the system
improves autonomously. If I say "queued" and don't write a backlog
entry, the work never happens and the user loses trust that the
system is improving without their direct attention.

## How to apply

When a turn ends with deferred work:

1. Open `vault/_meta/improvement_backlog.md`.
2. Add an entry under the most recent "Queued YYYY-MM-DD" section
   (or create a new dated section at the top).
3. Use the format from `vault/_meta/improvement_backlog.md` header.
4. If autonomous-eligible AND non-HIGH_RISK: `auto-merge: yes` so the
   daily Cloud routine (`trig_011w6DUmXbojsfkjKtCaJfBa`, 09:00 UTC)
   picks it up.
5. If risky / requires user judgment: `autonomous-eligible: no` —
   surface in the next session-open recap.
6. Also save a one-line entry in MEMORY.md or update a relevant
   project memory so future-me sees what's pending.

## Counter-pattern to watch for

Saying "I'll schedule this overnight" or "tomorrow morning" verbally
without actually writing the entry. This was the failure shape today:
multiple "I'll schedule the audit" statements that needed user prompt
to actualize. Eliminate that gap.

Related: [[feedback-save-every-session]],
[[project-weekly-audit-routine]].
