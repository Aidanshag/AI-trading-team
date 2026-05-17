---
name: project-weekly-audit-routine
description: "User wants a weekly Sunday-evening audit of trader+brain code for duplicate logic, dead code, Pattern A/B bugs, and bloat. Instructions live in vault/_meta/weekly_audit.md. Routine creation blocked on GitHub App connection."
metadata: 
  node_type: memory
  type: project
  originSessionId: b979f9ba-f40d-4fdc-8d30-1f25c42d62e2
---

# Weekly trader+brain audit routine

**Status (2026-05-14):** Instructions written, routine creation blocked.

**Motivation:** User read an article about a Claude-built app where the
hired engineer found the codebase a mess — duplicate functionality,
brittle coupling, fix-one-break-two. User wants proactive prevention.

**What's in place:**
- Full audit playbook: `vault/_meta/weekly_audit.md`
- Backlog entry to create the remote routine once GitHub is connected:
  see `vault/_meta/improvement_backlog.md` 2026-05-14 entry

**What's pending:**
- User needs to connect GitHub App at
  https://claude.ai/code/onboarding?magic=github-app-setup
- Then create routine: cron `0 22 * * 0` (Sun 18:00 ET = 22:00 UTC),
  repo `https://github.com/Aidanshag/AI-trading-team`,
  prompt: "Read vault/_meta/weekly_audit.md and execute the weekly audit."

**Why:** Same failure mode user described in the article — left
unchecked, ~3-5 sessions of additive changes per week compound into
mess. The audit dedupes, kills dead code, keeps live_trader <600 lines,
flags Pattern A/B regressions before they cause incidents.

**Related:** [[feedback-continuous-trader-trim]],
[[feedback-brain-owns-decisions]].
