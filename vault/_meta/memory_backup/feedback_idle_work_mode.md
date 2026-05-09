---
name: Idle-work mode is user-gated
description: Agents never self-activate autonomous brain expansion; user flips the flag explicitly
type: feedback
originSessionId: 0fb1ece1-0ed0-47f7-9c25-6b7ec073a6ec
---
The fund has an idle-work mode where agents pull from a backlog (`vault/_meta/idle_backlog.md`) to expand the Obsidian brain when no live work is pending. This mode is **user-gated**, not self-activating.

**Why:** The user said explicitly "do not tell them to do this until I am not actively on claude." The idle-work mode is infrastructure for the user to turn on when they step away from active development — not a default behavior. If agents self-activated, they would burn tokens during times the user might not expect.

**How to apply:**
- Activation requires two steps: `config/fund.yaml:idle_work_enabled: true` AND `vault/_meta/idle_backlog.md:status: active`. Both gates matter — belt and suspenders.
- Activation scripts are `.\scripts\idle-mode-on.ps1` and `.\scripts\idle-mode-off.ps1`.
- The orchestrator reads the flag in `_team_preamble()` and only prepends the idle protocol to agent prompts when active.
- When activated, agents operate under tighter guardrails (`idle_work_guardrails` in `config/fund.yaml`): forced cheap tier, lower per-wake token caps, max daily wakes, and halt-on-live-event.
- When the user returns (interactive session detected, or flag flipped back), agents cease idle work, finish the paragraph, commit output, release claim.
- Do NOT casually recommend turning idle mode on. It's a deliberate "I'm stepping away — you keep working" move.
