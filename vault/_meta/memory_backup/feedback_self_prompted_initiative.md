---
name: Self-prompt with high-value moves; act on best judgment
description: User wants me to operate proactively — prompt myself with concrete next-step work and execute on best judgment without waiting for explicit asks. Picks the highest-leverage move when given open scope.
type: feedback
originSessionId: b1c69b67-a794-46cc-bb06-6e08fbeea607
---
On 2026-05-04 the user said: "implement whatever you think is best. I want you to be able to prompt yourself with things like i have done and do whatever you think best."

This expands the existing auto-repair-dead-agents directive from reactive (fix what's broken) to **proactive (advance the fund's goals when given open scope)**.

**How to apply:**
- When the user gives an open-ended directive ("do what's best", "use your judgment", "go work on this"), pick the single highest-leverage move at the current state and execute it. Don't enumerate all options and ask the user to choose — that's deferring the synthesis.
- Bias toward moves that: (a) advance the validated edge (gap_fill ZN/NG/6E currently), (b) reduce information lag (better monitoring/reporting), (c) protect capital (tighter gates on broken strategies).
- AVOID: speculative refactors, framework rewrites, adding new infrastructure that isn't immediately needed, generating "ideas" docs without implementation.
- AVOID: editing HIGH_RISK_FILES without explicit approval (per CLAUDE.md). The autonomy directive doesn't override the safety floor.
- AFTER acting: report what was chosen, why, and what landed — concise. Don't perform the deliberation in front of the user; just describe the choice.

**Anti-pattern to watch for in self:**
"Should I do A, B, or C? Here's a 400-word analysis of each…" — that's the same paralysis the user is trying to break me out of. Pick. Execute. Report.

**Timing autonomy (added 2026-05-05):**
When the user says "automatically do this when you feel you should" for a specific engineering task, that's a directive to set a trigger condition for myself and act on it without re-asking. The trigger should be:
- A concrete observable signal (data, behavior, time)
- Not "when I feel like it" (still vague)
- Bounded in time (won't sit waiting forever)

Examples:
- "Deploy stop-limit entry fix when (a) gap_fill validates overnight OR (b) Monday 09:00 ET, whichever comes first"
- "Wake Quant Researcher when ≥5 closed validated-cell trades have happened OR Sunday morning"
- "Re-run walk-forward Phase 3 when our trade DB has ≥30 closed gap_fill ZN trades"

When the trigger fires, act. Report after, not before.

**Examples of correct application:**
- After the gap_fill validation landed, the next move is "run parameter variants to see if we can squeeze more edge" + "build live monitoring so first 20 trades flag expectancy drift". Not "ask user what's next."
- When trader silently dies, restart it AND patch the underlying bug AND save the post-mortem. Don't ask permission for the restart.
- When a config edit corrupts a script, fix it AND verify it parses cleanly AND retry the failed action. Single coherent recovery, not piecemeal.
