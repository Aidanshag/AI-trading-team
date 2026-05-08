---
type: index
updated: 2026-04-23
---

# Fund brain

This Obsidian vault is the fund's qualitative brain. Operational state (positions, orders, P&L) lives in SQLite under `state/`; this vault holds the thinking.

## How to navigate

- **Theses** — `[[theses/]]` — one note per symbol or theme. Analysts write these; PM reads them. Latest revision is the active view.
- **Playbooks** — `[[playbooks/]]` — standing procedures. User-curated. Agents load relevant ones on wake. Edit these to change agent behavior without touching code.
- **Journal** — `[[journal/]]` — one note per day. Agents timestamp their observations, decisions, and hand-offs here.
- **Reviews** — `[[reviews/]]` — post-trade reviews and daily compliance summaries.
- **Agents** — `[[agents/]]` — each agent's standing brief. Lessons learned accumulate here.
- **Meta** — `[[_meta/]]` — conventions, symbol registry, glossary.
- **Templates** — `[[_templates/]]` — note templates the agents fill in.

## Editing rules

- Agents treat **everything in `playbooks/`** as authoritative. Edit a playbook and the next wake picks it up.
- Agents treat **everything in `_meta/`** as stable reference. Don't rewrite it mid-day.
- Humans curate; agents append. If a human edits a thesis, the agent treats the human version as truth and only layers on top if new information warrants.
- All notes use YAML frontmatter for machine-readable tags (symbol, sector, type, conviction, etc.).
- Wikilinks (`[[Crude Oil]]`) are the primary connective tissue. Use them liberally.
