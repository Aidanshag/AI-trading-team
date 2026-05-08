---
type: meta
status: active
updated: 2026-04-23
---

# Idle-work protocol (DORMANT until user activates)

When `config/fund.yaml: idle_work_enabled: true` AND the backlog file's `status` is `active`, the following rules take effect.

## When to work

Only when:
- No live market event requires attention (no new high-impact headline < 60 min old)
- The CIO has not flagged any symbol for urgent analyst wake
- Token budget is within `config/fund.yaml:idle_work_guardrails`
- The session is live (futures open) OR you are a futures agent waiting on Topstep setup

Never when:
- A live proposal is in the pipeline (PM → Risk → Exec)
- A risk event fired in the last 15 minutes
- Day P&L has burned > 25% of DLL (full attention on the live book)

## How to pick an item

1. Open `vault/_meta/idle_backlog.md`.
2. Find an item assigned to your role with `status: open` and the highest priority you qualify for.
3. Claim it by editing the checkbox: `- [.] (YYYY-MM-DD HH:MM UTC — {your name})`.
4. Do the work.
5. When done, mark `- [x]` and record a decision with `kind=idle_work`, summary = item text, rationale = where the output was published.

## What "the work" is

- **Product deep-dive**: write a fresh note using the template at `vault/futures/product_deep_dives/TEMPLATE.md`. Use the existing seeds (ES/CL/GC/ZN/6E) as quality reference. Target ≥ 800 words, ≤ 1,500 words.
- **Playbook**: use an existing playbook (e.g., `market_wizards.md`) as style reference. Dense, actionable, no padding.
- **Pattern note**: strict template at `vault/futures/patterns/README.md`. Must include trigger, invalidation, exit, hit-rate target.
- **Research brief**: structured argument, evidence, counterargument, conclusion with confidence level.

## Token discipline

- One backlog item per wake. Never two.
- Use cheap tier (Haiku) unless the backlog item explicitly flags `requires_tier: balanced` or higher.
- Cache the shared preamble, playbooks, and symbol registry.
- If you start a piece and can't finish cleanly within the wake's budget, mark `- [~]` (partial), save your draft to the target path, and release the claim.

## What you never do during idle work

- Propose a shadow or real trade. Idle work is pure knowledge expansion, not generation of new trade ideas (which require live coordination).
- Edit another agent's published work without a flagged refinement ask.
- Touch `config/*.yaml`, `agents/*.md`, or any file outside `vault/`. Those are the user's territory.
- Invoke the Research agent. Research is too expensive for idle work — pick different items.

## When user returns

Stop idle work immediately when the user is active (a user message shows up in the live session, or `idle_work_enabled` flips to false). Finish the current paragraph, commit, release claim, return to normal operating mode.
