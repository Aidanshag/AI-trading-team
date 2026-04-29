---
type: journal
date: {{YYYY-MM-DD}}
author: fund
---

# Journal — {{YYYY-MM-DD}}

## Cost ledger (fill this in FIRST every session)

| Metric | Today | MTD | Notes |
|---|---|---|---|
| Gross trading P&L | $0 | $0 | from `account_snapshots` |
| Topstep fees | $0 | $0 | from `orders` × fee schedule |
| API spend | $0 | $0 | from `costs` table |
| **Net** | **$0** | **$0** | **the only KPI that matters** |
| Trades placed | 0 | 0 | |
| Per-trade NET (avg) | $0 | $0 | |

**MTD pace vs targets** (see `_meta/economics.md`):
- Break-even ($575): X% reached, $Y to go, Z days remaining
- Worth-doing ($1,150): X% reached

A flat day is a -$20 day (fixed costs). Neutrality isn't free.

## Daily brief — CIO

- Regime: risk-on | risk-off | neutral | transitioning | event-driven | thin
- Liquidity: normal | thin | affected by [event]
- Top themes:
  1. …
  2. …
  3. …
- Events to watch (next 12h): …
- Strategies appropriate today: …
- Strategies blocked today (and why): …
- Analyst wake plan: …

## Setups taken

For each: symbol / strategy / entry-stop-target / conviction / expected NET / actual outcome / NET realized.

## Setups skipped (equally important)

The "didn't trade" decisions. Patience IS a trade.

## Risk events today

From `risk_events`. Note any blocks — were they correct (saved a bad trade) or false-positive?

## Lessons (if any)

If a pattern emerged 3+ times, draft to `vault/lessons/YYYY-MM-DD_<slug>.md` with confidence tier.

## EOD posture for tomorrow

- internal_dll: $250 (post-incident) / $500 (normal)
- daily_fee_budget: $15 (autonomous) / $30 (supervised)
- autonomous_mode: on/off
- Strategies on probation / suspended

## Timestamped entries (appended by agents through the day)
