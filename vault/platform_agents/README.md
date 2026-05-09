---
type: index
---

# Platform Agents bridge

The bridge between Anthropic Console **Managed Agents** (at [platform.claude.com/workspaces/default/agents](https://platform.claude.com/workspaces/default/agents)) and this local fund.

## Why a bridge

Managed Agents run in Anthropic infrastructure on a cron. They're great for:

- Scheduled pre-open briefs before your computer is awake
- Post-close recaps written while you sleep
- Weekly meta-reviews
- Long-running research dives you don't want to pay Opus tokens for locally

But they can't:

- Place orders (no broker access)
- See the local SQLite state or the vault directly

So we use a copy-paste (or file-sync) bridge.

## Workflow

1. Configure a Managed Agent in the Console. Give it the same `vault/_meta/team.md` preamble as the local agents, so it shares culture.
2. Have it output a markdown file in a predictable format (below).
3. Copy-paste or script-sync the output into this folder, named `YYYY-MM-DD_{agent_slug}.md`.
4. The local fund's CIO reads this folder on its wake. High-priority entries (tagged `priority: high`) get surfaced to the daily brief; everything else is searchable context.

## Expected output format (please standardize your Managed Agents to this)

```yaml
---
type: platform_agent_output
agent: pre_open_brief | weekly_review | etc.
produced_at: ISO timestamp
priority: high | med | low
symbols: [CL, ES, ...]
---
```

Body:

- **TL;DR** — one paragraph.
- **Key signals** — bulleted, each with source.
- **What this implies for the desk** — a short list of asks/flags.

## Suggested Managed Agents to build in the Console

1. **Pre-open brief** — fires at 05:30 CT each trading day. Reads the prior day's close, overnight news, economic calendar for today, dealer positioning if available. Produces a brief aimed at the CIO's morning wake.
2. **Post-close recap** — fires at 16:30 CT. Reads the day's closing moves, after-hours data, key headlines. Produces a digest for evening consumption.
3. **Weekly meta-review** — fires Sunday 18:00 CT. Reads the week's journal and reviews (you'd need to paste or rsync them up). Produces a critical review of process, hit rates, and areas to sharpen.
4. **Research dive** — on-demand. A question-answering agent with web search, to cover topics the local Research agent might skip for cost reasons.

## If you want tighter integration

- **Option A — Hosted HTTP endpoint**: Managed Agents can call webhooks. Host a small Flask/FastAPI endpoint on your VPS that accepts agent output and writes it to this folder. Then the sync is fully automatic.
- **Option B — Invoke-as-tool**: our local fund can (in principle) call a Managed Agent via HTTPS as an MCP tool. Requires: Managed Agent exposed as an API, our local MCP wrapper that handles auth and maps requests/responses. I can build this if you share access details.

For now, manual copy-paste works and has zero infrastructure cost.
