---
type: meta
updated: 2026-04-23
---

# Vault conventions

## Frontmatter

Every agent-written note starts with YAML frontmatter. Minimum fields:

```yaml
---
type: thesis | journal | review | playbook | brief
updated: ISO 8601 timestamp
author: agent name (or "human" if user-edited)
---
```

Thesis frontmatter additionally includes:

```yaml
symbol: TICKER
sector: energies | metals | ags | rates | fx_futures | index_macro
conviction: low | med | high
direction: long | short | flat
timeframe: intraday | swing
```

## Wikilinks

Always wikilink symbols: `[[CL]]`, `[[ES]]`. The symbol registry in `_meta/symbol_registry.md` gives every symbol its own stub note so links resolve.

For sectors: `[[energies]]`, `[[rates]]`, etc.

For events: `[[FOMC]]`, `[[WASDE]]`, `[[EIA]]`.

## File naming

- Theses: `theses/{SYMBOL}.md` (one per symbol; overwrite on update).
- Journal: `journal/YYYY-MM-DD.md` (one per day; agents append blocks).
- Reviews: `reviews/YYYY-MM-DD.md` (one per day; agents append blocks).
- Playbooks: `playbooks/{slug}.md` — user-curated.
- Agent briefs: `agents/{agent_name}.md`.

## Tone

Brief, numerical, specific. No hedging language ("might", "could", "perhaps"). State the view and the evidence, or don't state it.
