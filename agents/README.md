# Agents

Each agent is defined by:

1. **A system prompt** in this folder (`*.md`). This is the agent's
   personality, mandate, constraints, and tool usage guidance. Edit freely —
   this is where most of your iteration will happen.
2. **A model assignment** in [`config/models.yaml`](../config/models.yaml).
   Costs and capability scale together; don't escalate without reason.
3. **A tool allowlist** wired in [`runtime/orchestrator.py`](../runtime/orchestrator.py).
   An analyst cannot place orders — only the execution trader can, and only
   after the risk hook passes.

## Roster (futures desk — live via Topstep)

| File                      | Role                                                                                                               | Can place orders? |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------ | ----------------- |
| `cio.md`                  | Chief Investment Officer / orchestrator                                                                            | no                |
| `portfolio_manager.md`    | Position sizing, capital allocation                                                                                | no (proposes)     |
| `risk_manager.md`         | Hard vetoes, 2% DLL, institutional persona                                                                         | no (vetoes)       |
| `options_risk.md`         | Options structure, Greeks, IV, pin/assign                                                                          | no (vetoes)       |
| `execution_trader.md`     | Order routing and fill management                                                                                  | **yes**           |
| `compliance.md`           | Audit, rule attestation, post-day close                                                                            | no                |
| `research.md`             | Frontier-tier deep analysis (rare wakes)                                                                           | no                |
| `analysts/energies.md`    | Crude (CL/BZ), NatGas (NG/QG), Gasoline (RB), **Diesel/ULSD (HO)**, Ethanol (EH) — every petro derivative + cracks | no (proposes)     |
| `analysts/metals.md`      | Gold/Silver/Copper/Platinum/**Palladium/Aluminum** — every tradeable metal                                         | no (proposes)     |
| `analysts/grains.md`      | Corn, soybeans, wheat, oilseeds, oats, rice                                                                        | no (proposes)     |
| `analysts/softs.md`       | Coffee, cotton, sugar, cocoa, OJ, lumber                                                                           | no (proposes)     |
| `analysts/livestock.md`   | Live cattle, feeder cattle, lean hogs                                                                              | no (proposes)     |
| `analysts/rates.md`       | Treasury futures (2Y/5Y/10Y/30Y/UB)                                                                                | no (proposes)     |
| `analysts/fx_futures.md`  | CME currency futures (6E, 6B, 6J, etc.)                                                                            | no (proposes)     |
| `analysts/index_macro.md` | Equity index futures + **cross-asset macro overlay** (commodities headlines, regime read)                          | no (proposes)     |

## Roster (equities desk — IDLE, learning mode)

The equity desk is in learning mode until a broker is wired. The Equity Execution Trader has no order-placement tools. All trades are shadow trades written to `vault/equities/shadow_trades/`.

| File                                                  | Role                                          | Can place orders? |
| ----------------------------------------------------- | --------------------------------------------- | ----------------- |
| `equities/equity_pm.md`                               | Equity Portfolio Manager (sizing)             | no (proposes)     |
| `equities/equity_execution_trader.md`                 | Equity Execution Trader (IDLE — no broker)    | no (idle)         |
| `equities/analysts/growth_tech.md`                    | MAG-7, semis, software, growth                | no (proposes)     |
| `equities/analysts/defensive.md`                      | Healthcare, staples, utilities, biotech       | no (proposes)     |
| `equities/analysts/cyclicals.md`                      | Industrials, materials, energy equities       | no (proposes)     |
| `equities/analysts/financials.md`                     | Banks, insurers, asset managers, payments     | no (proposes)     |
| `equities/analysts/single_name_options.md`            | Cross-sector options specialist               | no (proposes)     |

Shared with futures desk: Risk Manager, Options Risk, Research.

## Decision flow (every trade, without exception)

```
Research Agent (optional)      or   Sector Analyst
    ↓ produces deep-dive brief      ↓ drafts thesis to vault/theses/{SYMBOL}.md
                           ↘   ↙
                  Portfolio Manager
                    ↓ DECIDES: pursue or pass
                    ↓ if pursued, sizes + proposes
                  Risk Manager (+ Options Risk if options)
                    ↓ FINAL SAY: allow | allow_with_modifications | block
                    ↓ if approved
                  Execution Trader
                    ↓ calls broker tool
                    ↓ PreToolUse risk hook = hard gate
                    ↓ on fill
                  Compliance (audit + log)
```

Read `vault/_meta/trading_process.md` for the full workflow with role-specific rules.

## Refining an agent

1. Read its recent entries in `vault/journal/` and `vault/reviews/`, and its standing brief at `vault/agents/{Name}.md`.
2. Review the CIO's weekly scorecard at `vault/_meta/agent_scorecards.md` — hit rate, avg R, process score, tier.
3. Edit the agent's `.md` prompt — add a rule, an example, or a standing instruction. Keep changes specific, not vague.
4. Optionally promote a proven pattern into `vault/playbooks/` so every agent reads it.
5. Restart the fund; the change takes effect on next wake.
