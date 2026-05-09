---
type: index
category: trading_strategies
updated: 2026-04-23
---

# Trading strategies — index

These are the **concrete, testable strategies** the commodity desk trades. Each strategy has a specific trigger, a named invalidation, a defined exit, and a calibration target (expected hit rate + R-multiple).

## Distinction from other playbooks

- **Meta-philosophy** (`market_wizards`, `risk_officer_principles`, `position_sizing`, `psychology_and_discipline`, `macro_framework`, `trend_following`, `quant_principles`): how the fund thinks.
- **Event playbooks** (`fomc_days`, `cpi_nfp_days`, `eia_inventory`, `wasde_days`, `opex_week`, `event_window_procedure`): what to do around specific scheduled events.
- **Strategy playbooks (this folder)**: the actual setups we look for, how we enter, how we exit, how often they work.

## Strategy files

- [[strategies_grains]] — Corn, soybeans, wheat, meal, oil, oats, rice
- [[strategies_livestock]] — Live cattle, feeder cattle, lean hogs
- [[strategies_crude_oil]] — CL (WTI), BZ (Brent), calendar spreads, inter-commodity arbs
- [[strategies_petro_derivatives]] — RB (gasoline), HO (diesel/ULSD), NG (nat gas), crack spreads
- [[strategies_softs]] — Coffee, cotton, sugar, cocoa, OJ, lumber
- [[strategies_metals]] — Gold, silver, copper, platinum, palladium, aluminum

## Conventions across all strategies

Every strategy documented below follows the same template:

```
Name           — short, distinct handle
One-liner      — entry, stop, target in one sentence
Thesis         — why this has edge (structural or behavioral)
Trigger        — the specific, measurable conditions required
Invalidation   — the observation that kills it (close immediately)
Structure      — outright / spread / options; sizing basis
Exit rules     — target R, stop, trailing, time stop
Calibration    — expected hit rate and R; historical bounds
Common traps   — specific ways traders lose money on this
```

## How agents use these

1. On wake, analysts check their sector's strategy file alongside the product deep-dives.
2. A fresh thesis should reference *which* strategy it's running — e.g., "This is a [[strategies_grains#WASDE surprise continuation]] setup."
3. Each strategy has a hit-rate target. After ~30 trades, track realized-vs-expected. Strategies that decay get retired or rewritten.
4. PM sizes per the strategy's guidance within the 50 bps per-trade cap.
5. Risk Manager uses the strategy's invalidation as a soft check: a stop widely outside the strategy's documented invalidation is suspicious.

## Adding a new strategy

If an agent (via the weekly review) identifies a new recurring pattern:
1. Shadow-trade it at half-size for at least 30 occurrences.
2. Measure realized hit rate and average R honestly.
3. If it holds up, propose via a `## Refinement ask` journal entry. The user decides whether to formalize.
4. Once formalized, it goes here with a calibration note: "added 2026-XX-XX, shadow-tested N times before formalization."
