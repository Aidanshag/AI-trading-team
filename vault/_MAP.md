---
type: moc
updated: 2026-04-23
---

# Fund brain — Map of Content

Top-level index. Every subfolder has its own README; this ties them together so Obsidian's graph view reveals the full structure.

## Culture and process

- [[_meta/team|Team culture]] — who we are and how we collaborate.
- [[_meta/trading_process|Trading process]] — the front-office workflow (CIO → Research/Analysts → PM → Risk → Execution).
- [[_meta/conventions|Vault conventions]] — frontmatter, wikilinks, file naming.
- [[_meta/symbol_registry|Symbol registry]] — wikilink targets for every tradeable symbol.
- [[_meta/topstep_setup_window|Topstep setup window]] — current 4–5 day learning sprint.
- [[_meta/idle_protocol|Idle-work protocol]] — rules when agents are autonomously expanding the brain.
- [[_meta/idle_backlog|Idle backlog]] — queue of expansion tasks.

## Playbooks — the trader-wisdom library

- [[playbooks/market_wizards|Market Wizards]] — distilled principles from Schwager's interviews.
- [[playbooks/risk_officer_principles|Risk officer principles]] — buy-side CRO mental models.
- [[playbooks/position_sizing|Position sizing]] — Kelly, vol targeting, pyramiding.
- [[playbooks/psychology_and_discipline|Psychology and discipline]] — biases and emotional discipline.
- [[playbooks/macro_framework|Macro framework]] — regime quadrant, Soros reflexivity.
- [[playbooks/trend_following|Trend following]] — Seykota, turtles, systematic trend.
- [[playbooks/quant_principles|Quant principles]] — what RenTech/Citadel/Two Sigma do.
- Event playbooks: [[playbooks/fomc_days|FOMC]] · [[playbooks/cpi_nfp_days|CPI/NFP]] · [[playbooks/eia_inventory|EIA]] · [[playbooks/wasde_days|WASDE]] · [[playbooks/opex_week|Opex]] · [[playbooks/event_window_procedure|Event window generic]]
- [[playbooks/lessons_learned|Lessons learned]] — running list, promoted from reviews.

## Trading strategies — the desk's setup library

Every thesis names which of these strategies it's running. Calibration targets (hit rate, avg R) are documented inside each file.

- [[playbooks/strategies_README|Strategies index]] — overview + conventions.
- [[playbooks/strategies_grains|Grains strategies]] — WASDE surprise, South American weather, crush, planting-progress, harvest-low, wheat-corn, export pace.
- [[playbooks/strategies_livestock|Livestock strategies]] — COF placement fade, feed-cost transmission, cold storage, grilling seasonal, disease fade, hog-corn ratio.
- [[playbooks/strategies_crude_oil|Crude oil strategies]] — EIA surprise, OPEC+ directional, Brent-WTI arb, term structure, geopolitical decay, SPR fade.
- [[playbooks/strategies_petro_derivatives|Petro derivative strategies]] — summer RB crack, winter HO crack, 3-2-1 margin, NG storage, heating-season, summer-blend, cross-Atlantic diesel.
- [[playbooks/strategies_softs|Softs strategies]] — weather supply shocks, ethanol-sugar pivot, cotton China pulse, cocoa concentration, lumber-housing.
- [[playbooks/strategies_metals|Metals strategies]] — real-yield gold pivot, gold-silver ratio, copper China credit, palladium supply shock, Pt-Pd ratio, aluminum energy cost.

## Futures desk

- [[futures/|Futures brain]] — landing page.
- [[futures/routines/daily_routine|Daily routine]]
- [[futures/routines/weekly_review|Weekly review]]
- [[futures/product_deep_dives/|Product deep-dives]] — one note per contract.
- [[futures/patterns/|Pattern library]]
- [[futures/shadow_trades/|Shadow trades]]
- [[futures/watchlists/|Watchlists]]

## Equities desk (learning mode — no broker yet)

- [[equities/|Equities brain]]
- [[equities/watchlists/|Watchlists]]
- [[equities/shadow_trades/|Shadow trades]]
- [[equities/theses/|Theses]]
- [[equities/reviews/|Reviews]]

## Regime and macro

- [[regime/current|Current regime read]] — updated weekly by CIO / Index-Macro.

## Inputs (news, social, research)

- [[news_imports/|News imports]] — user's manual summaries of paywalled content.
- [[social/twitter_watchlist|Twitter watchlist]] — curated accounts for X API polling.
- [[platform_agents/|Platform Agents bridge]] — outputs from Anthropic Console Managed Agents.
- [[research/|Research agent output]] — frontier-tier deep-dives.

## Daily operations

- [[journal/|Journal]] — one note per day, all agents append.
- [[reviews/|Reviews]] — post-trade + daily compliance summaries.

## Learning resources

- [[reading_list/|Reading list]] — books, podcasts, RSS, papers.
- [[agents/|Agent standing briefs]] — each agent's evolving notebook.

## Market structure (future expansion)

- [[market_structure/|Market structure]] — TBD; session mechanics, auction mechanics, option expiry details.

---

## How the graph looks

Open the Obsidian graph view (Ctrl+G). You'll see:
- **Playbooks** densely cross-linked to each other and to theses.
- **Product deep-dives** as spokes off the sector analysts.
- **Symbol wikilinks** resolving to the symbol registry so every `[[CL]]` lands somewhere.
- **Journal notes** connecting every decision back to its source thesis.

If you see orphan notes (no inbound links), it's a prompt to connect them — either add backlinks or reconsider whether the note should exist.
