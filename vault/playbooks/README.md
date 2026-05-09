---
type: index
---

# Playbooks

Standing procedures for recurring situations. Agents load the relevant playbook on wake. **Edit these freely — the next wake uses the new version.** This is the fastest lever you have for changing fund behavior without touching code.

## Included

**Event playbooks** (what to do around scheduled events):
- [[fomc_days]] — FOMC statements, press conferences, dots, SEP
- [[cpi_nfp_days]] — US CPI and Non-Farm Payrolls
- [[eia_inventory]] — EIA crude + products weekly inventory
- [[wasde_days]] — USDA WASDE and related grain reports
- [[opex_week]] — index options expiration dynamics
- [[event_window_procedure]] — generic protocol for any high-impact release

**Meta-philosophy** (how the fund thinks):
- [[market_wizards]] — distilled Schwager principles
- [[risk_officer_principles]] — buy-side CRO mental models
- [[position_sizing]] — Kelly, vol targeting, pyramiding
- [[psychology_and_discipline]] — biases and emotional discipline
- [[macro_framework]] — regime quadrant, Soros reflexivity
- [[trend_following]] — Seykota, turtles, systematic trend
- [[quant_principles]] — RenTech, Citadel, systematic

**Trading strategies** (concrete setups the desk trades):
- [[strategies_README]] — index of all strategy playbooks
- [[strategies_grains]] — WASDE, South American weather, crush, harvest-low, etc.
- [[strategies_livestock]] — COF placement, feed-cost, cold storage, seasonal, disease fade
- [[strategies_crude_oil]] — EIA, OPEC, Brent-WTI, term structure, geopolitics, SPR
- [[strategies_petro_derivatives]] — RB/HO cracks, 3-2-1, NG storage, summer-blend, cross-Atlantic
- [[strategies_softs]] — weather shocks, ethanol pivot, China cotton, cocoa concentration, lumber
- [[strategies_metals]] — real-yield gold, gold-silver ratio, copper-China, palladium, Pt-Pd ratio, aluminum

## How to add

1. Create `playbooks/{slug}.md` with `type: playbook` frontmatter.
2. Describe: trigger, what agents should check, what they should AVOID, what structures are preferred.
3. Add a link to this README.
4. The agents covering relevant sectors will pick it up on next wake.
