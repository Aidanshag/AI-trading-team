---
type: playbook
applies_to: [all]
---

# Lessons learned

Running list of hard-won lessons. When a post-trade review surfaces a pattern that recurs, promote the lesson here. When a lesson here is violated across many trades, promote it into a hard rule in `agents/risk_manager.md` or `config/risk_limits.yaml`.

## Format

`- YYYY-MM-DD — [[SYMBOL]] — one-sentence rule — link to review.`

## Seed entries (user can edit)

- 2026-04-23 — General — Every thesis must name the specific observation that would invalidate it; if you can't, the thesis isn't real.
- 2026-04-23 — General — Stops inside recent 20-bar ATR are fake stops.
- 2026-04-23 — General — Correlated longs across sectors are one trade for sizing purposes, not three.

## Entries from production (agents append)
