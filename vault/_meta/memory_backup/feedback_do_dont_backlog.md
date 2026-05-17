---
name: feedback-do-dont-backlog
description: "When user logs off / overnight / weekend, do high-priority items DIRECTLY instead of adding to backlog. Backlog growth is itself the problem."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 01330334-e95e-4182-b81f-d9cbbd00f2f1
---

When the user is stepping away — logging off a session, going to sleep, or starting a weekend — DO the high-priority backlog items directly instead of queuing them.

**Why:** As of 2026-05-15 the cloud `/improve-fund` routine that was supposed to consume the backlog has produced ~0 commits in a week. The backlog has grown to 25 open items (~32 hours of work) while real autonomous throughput is near zero. The user surfaced this directly: "instead of putting new things in the backlog, you do them directly when I'm logging off of a session or at nights when I log off. That lets things that need immediate attention get addressed overnight rather than sitting in the backlog."

**How to apply:**
- When the user signals they're stepping away, ask whether to kick off an autonomous `/loop /improve-fund` cycle for the duration
- During interactive sessions: when you discover an actionable issue, default to **fixing it in-session** rather than writing a backlog entry. Backlog is for items that genuinely need future research, calibration, or human review
- Reserve the backlog for: research items, items requiring human decision (auto-merge:false), items deferred because they need a maintenance window
- Lower-priority items can still queue for weekend `/loop` runs
- HIGH_RISK_FILES (per CLAUDE.md: `hooks/risk_gate.py`, `state/db.py`, `state/schema.sql`, `tools/topstep.py`, `tools/projectx_client.py`, `risk_limits.yaml.hard_rules`) still need explicit approval — autonomy stops at the safety floor
- Commit each item separately so the user can revert any one without losing the rest

Related: [[feedback-autonomous-overnight-fixes]] (pre-committed responses to 8 known issue patterns), [[feedback-self-prompted-initiative]] (pick highest-leverage move when given open scope), [[feedback-refinement-queue-authorized]] (standing auth for refinement queue when conditions are right).
