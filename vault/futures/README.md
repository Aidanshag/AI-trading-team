---
type: index
---

# Futures brain

This is the working brain for the futures desk: product knowledge, pattern library, shadow-trade ledger, watchlists, and daily routines.

## Folders

- **[[product_deep_dives/]]** — one note per tradeable futures product. The single most important long-lived knowledge base. Kept current by the sector analysts.
- **[[patterns/]]** — the pattern library. Recurring setups per sector, each with entry/invalidation/exit criteria.
- **[[watchlists/]]** — live watchlists per sector. Symbols currently being considered, with conviction and state.
- **[[shadow_trades/]]** — shadow-trade ledger. Each day's proposed-but-not-live trades and their counterfactual outcomes.
- **[[routines/]]** — daily and weekly routines. What each agent does, on what cadence.

## Workflow

1. **Analyst wakes** → reads `vault/_meta/team.md`, `vault/_meta/topstep_setup_window.md` (if active), their sector's product deep-dives, today's journal, relevant playbooks.
2. **Analyst observes** → scans news, tape, calendar. Decides if any symbol in coverage has a clean setup today.
3. **Analyst writes** → a thesis (if setup is clean) or a "no-trade update" (if not).
4. **PM receives theses** → sizes, proposes to Risk.
5. **Risk votes** → allow | allow_with_modifications | block. Blocks are explained.
6. **Approved proposals** → become shadow trades today (during setup window) or real orders (once live).
7. **Compliance** → confirms audit trail, flags patterns.
8. **Weekly** → every Sunday, every analyst reviews their week's shadow trades against actual price action. Lessons go to `vault/playbooks/lessons_learned.md`.
