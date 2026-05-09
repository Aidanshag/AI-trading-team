---
name: Autonomous AI hedge fund
description: Multi-agent Topstep futures trading system on the Claude Agent SDK
type: project
originSessionId: 0fb1ece1-0ed0-47f7-9c25-6b7ec073a6ec
---
Building an autonomous team of Claude-powered agents that function like a hedge fund trading CME futures and futures options on Topstep.

**Scope (confirmed, phase 1):**
- Single venue: **Topstep** (prop firm; CME futures only; automation allowed)
- Asset classes: CME futures + futures options, covering:
  - Energies (/CL, /NG, /RB, /HO, micros)
  - Metals (/GC, /SI, /HG, micros)
  - Ags/softs (/ZC, /ZS, /ZW, /KC, /CT, /SB, /CC)
  - Equity index futures (/ES, /NQ, /RTY, /YM, micros) — as macro expression, not equity-picking
  - Rates (/ZN, /ZB, /ZF, /ZT)
  - **FX futures** (/6E, /6B, /6J, /6A, /6C, /6S, micros M6E/M6B) — these are Topstep's "FX"; no spot FX
- Execution: paper (Topstep Combine) first → funded account → real capital
- Data: internet (news, web search, market-data vendors). Bloomberg/BLPAPI was considered earlier and **dropped** — do not reintroduce unless user asks.
- Cadence: continuous during each contract's trading hours (most CME futures trade ~23h/day)

**Explicitly OUT of scope (for now):**
- Equities, equity options, spot FX, crypto (can add later with a separate broker MCP)

**Agent roster:**
- CIO / Orchestrator
- Portfolio Manager
- **Risk Manager** — hard veto via PreToolUse hook; 2% DLL; Citadel/Jane-Street institutional voice; can escalate to Research (frontier tier) for novel structures
- **Options Risk Agent** — dedicated; Greeks, IV, pin/assignment risk, naked-short check
- **Research** — frontier-tier deep analyst, rarely invoked, high token cap, gated by CIO; `frontier` slot in models.yaml updates when Anthropic releases new models
- Execution Trader
- Compliance / Audit
- Futures sector analysts: energies, metals, ags, rates, FX futures, **Index/Macro (cross-covers commodity headlines)**
- **Equities desk (idle, learning mode)**: Equity PM, Equity Execution Trader, Growth/Tech, Defensive, Cyclicals, Financials analysts, Single-Name Options specialist. Shares Risk Manager + Options Risk.

**Non-negotiables:**
- **No naked short positions** — enforced at risk-hook level, not prompt level
- **Every order, no exceptions, routes through the Risk Manager agent** before the execution trader is permitted to call the broker. Enforced at workflow (orchestrator) AND tool (PreToolUse hook) levels.
- **Daily loss limit = 2% of current equity.** When Topstep's USD DLL is tighter, Topstep's number wins. `effective_dll = min(pct*balance, topstep_usd_cap)`.
- **Per-trade risk cap: 50 bps of equity** max worst-case loss.
- **Risk Manager persona** is a buy-side institutional risk officer (Citadel / Jane Street voice). Terse, quantitative, non-negotiable.
- API cost conservation: Haiku default; Opus only for hard reasoning; prompt caching; event-driven, not polling

**Why:** User is building toward real-money autonomous futures trading via Topstep. Single-venue/single-asset simplification was chosen to nail safety, auditability, and Combine-rule compliance before expanding.

**How to apply:** Every order gates through risk manager (general + options-specific) before the Topstep API tool executes. Shared state store tracks positions, Topstep account-level metrics (trailing DD, daily P&L vs limit), and an append-only decision log. When a contract's session is closed, the agents covering it idle.

**Vault brain structure** (all in Obsidian, user-editable):
- `vault/_meta/` — team culture, conventions, regime framework, Topstep setup window, idle-work protocol + backlog (user-gated)
- `vault/playbooks/` — trader wisdom (Market Wizards, risk officer, sizing, psychology, macro, trend, quant), event playbooks (FOMC, CPI, EIA, WASDE, opex), lessons learned
- `vault/futures/` — product deep-dives (seed: ES/CL/GC/ZN/6E; rest in idle backlog), patterns, shadow trades, routines, watchlists
- `vault/equities/` — learning-mode material; watchlists, theses, shadow trades, reviews
- `vault/regime/` — current regime read, updated weekly
- `vault/news_imports/` — user's manual summaries of paywalled content (WSJ, Bloomberg, etc.) — high-signal path
- `vault/social/` — Twitter watchlist + ingested feed (when X API enabled)
- `vault/platform_agents/` — bridge folder for output from user's Anthropic Console Managed Agents
- `vault/reading_list/` — curated books/podcasts/RSS
- `vault/research/` — Research agent's deep-dive outputs

**Subscription access reality:**
- User has WSJ, Bloomberg, CNBC, X subscriptions. Most consumer subs ban programmatic access. Do NOT scrape wsj.com / bloomberg.com / barrons.com / ft.com — gets user's account banned.
- Legit paths: RSS (free), paid licensed APIs (NewsAPI/Benzinga/Dow Jones Newswires/X API Basic $100mo), user manual imports.
- Bloomberg Terminal via BLPAPI only if user is running on a Terminal-logged-in box; academic license has redistribution limits.
