---
type: index
---

# Imported Platform Agent definitions

Drop your existing Anthropic Console Managed Agents' system prompts and instructions here so the local fund's agents can read and incorporate them.

## Workflow

1. In the Anthropic Console at platform.claude.com/workspaces/default/agents, for each agent you've built that covers a role also present in this fund (e.g., macro analyst, options specialist, research):
   - Copy the agent's **system prompt** and any **tool/instruction notes**.
2. Paste into a file here named `{role_slug}.md`. Use the frontmatter below.
3. Our local agent of the matching role reads this folder on wake and layers the instructions into their operation, giving priority to anything explicitly flagged `authoritative: true`.

## File naming (must match local agent roles)

| If your platform agent covers… | Save as… |
|---|---|
| Macro / regime analysis | `index_macro.md` |
| Rates / Treasury curve | `rates.md` |
| Energies / commodities | `energies.md` |
| Metals | `metals.md` |
| Ags / grains / softs | `ags.md` |
| FX / currencies | `fx_futures.md` |
| Equities growth/tech | `growth_tech.md` |
| Equities defensive | `defensive.md` |
| Equities cyclicals | `cyclicals.md` |
| Equities financials | `financials.md` |
| Options specialist | `options_specialist.md` |
| Research / deep analysis | `research.md` |
| Risk management | `risk_manager.md` |
| Portfolio management | `portfolio_manager.md` |
| CIO / orchestrator | `cio.md` |
| Execution / trader | `execution_trader.md` |
| Compliance / audit | `compliance.md` |

If your platform agent doesn't cleanly map to one of the above, save it as `custom_{slug}.md` with a note explaining the role — the CIO will decide which local agent(s) should incorporate it.

## Frontmatter template

```yaml
---
type: platform_agent_import
role: {matching local role}
source_agent_name: {what you called it in the Console}
imported_at: YYYY-MM-DD
authoritative: false     # if true, overrides local prompt on conflict
---
```

Body: the full system prompt / instructions as copied from the Console, verbatim.

## How local agents incorporate these

On wake, a local agent checks for a matching file in this folder:

- **If absent**: proceeds on its own prompt + shared preambles.
- **If present with `authoritative: false`**: treats the imported instructions as **additional context** — useful patterns, vocabulary, checks — to layer onto its own work.
- **If present with `authoritative: true`**: treats the imported instructions as **canonical** and overrides its local prompt where they conflict. Use sparingly; reserve for cases where the platform agent has been validated over time and you want the local agent to behave identically.

## When to update

When you refine a platform agent in the Console, re-export and re-paste to keep the import current. The `imported_at` date in the frontmatter tells the local agent how fresh the instructions are; the CIO will flag imports > 30 days old as stale for review.
