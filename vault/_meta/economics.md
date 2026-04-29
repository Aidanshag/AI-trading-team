---
type: canon
status: active
read_on_first_wake: [CIO, Portfolio Manager, Risk Manager, Edge Hunter, Quant Researcher, Compliance]
purpose: "Make the entire team feel the cost-burn every day. A flat day is NOT a free day."
---

# Trading economics — the only KPI that matters

## The equation

```
NET MONTHLY P&L  =  gross trading profit  −  Topstep fees  −  Claude API spend  −  subscriptions
```

That's the number. Win rate, R:R, Sharpe — those are inputs. **NET MONTHLY P&L is the output, and the only one this fund is judged on.**

## Monthly fixed costs (the burn rate)

| Item | Monthly cost |
|---|---|
| Topstep $50K Combine subscription | ~$175 |
| Claude Premium subscription | ~$100 |
| Anthropic API credits (agents) | ~$250 |
| Misc / buffer | ~$50 |
| **Monthly fixed cost (break-even)** | **~$575** |

That's **~$20 per trading day** before a single trade. **A flat day is a -$20 day.** A day with no trades is still -$20. There is no such thing as "neutral."

## Profitability tiers

| Tier | Monthly NET P&L | What it means |
|---|---|---|
| Breakeven | $575 | Costs covered. No profit. |
| Worth doing | $1,150 | $20/day net profit. The minimum for the fund to make sense. |
| Comfortable | $1,725 | $40/day net profit. Pays for itself + buys time. |
| Combine pass + payout | $3,000+ | Hits the Topstep target, eligible for funded account. |

## The math every team member must internalize

### Per-trade economics
- **Micro contract round-trip fee**: $1.50 (Topstep schedule)
- **Full-size contract round-trip fee**: $5.00
- **Required reward / fee ratio**: 3x (`risk_limits.yaml:fee_decision.min_reward_to_fee_ratio`)
- **Minimum reward per trade**: $30 USD (`MIN_REWARD_USD` in auto_trader)

### Per-day economics
- **Fixed cost**: ~$20/day (subscriptions amortized)
- **Daily fee budget**: $30/day under supervised, $15/day under autonomous
- **Practical minimum NET to be profitable today**: $30 ($20 fixed + ~$10 fees)
- **A day that nets $30 takes the fund from -$20 (flat) to +$10 (small green)**

### Per-month economics
- **Days needed at $30 net to break even**: 19 trading days (one full month)
- **Days needed at $50 net to be "worth doing"**: 23 days
- **Days needed at $100 net to be "comfortable"**: 17 days

## What this means for trade decisions

### Edge Hunter / Quant Researcher / Analysts
- Before publishing a thesis, compute its expected NET dollar profit:
  `(hit_rate × reward) − ((1−hit_rate) × loss) − round_trip_fee`
- If the expected NET is < $5, **do not publish the thesis.** It's noise.
- 30 trades that net $1 each don't beat 5 trades that net $20 each, when fees are equal.

### Portfolio Manager
- Reject any proposal whose NET expected P&L is too small to justify the slot.
- A "winning" trade that nets $5 after fees is barely worth the API cost of the agent wakes that proposed it.

### Risk Manager
- The cost ledger is part of the risk calculation. A strategy with positive gross EV but negative net (after fees) gets blocked.
- Daily fee burn approaching the budget = early warning, even if no individual trade was bad.

### CIO daily session brief
- ALWAYS open with: *"MTD: gross +$X, fees -$Y, API -$Z, net +$W. Break-even needs $V more by Day N. We're [ahead/on track/behind]."*
- If MTD net is negative past Day 10, escalate to "tighten" mode (PM proposes smaller, Risk veto threshold lowers).

### Compliance
- End-of-day audit reports NET P&L (not gross). The journal entry's headline number is always the net.
- Track per-strategy fee burn — strategies whose fee burn exceeds their gross profit get demoted regardless of "win rate."

## What a profitable day looks like

| Day | Gross | Fees | API | Net | Cumulative MTD | State |
|---|---|---|---|---|---|---|
| Day 1 | +$80 | -$15 | -$8 | **+$57** | +$57 | green |
| Day 2 | +$0 | $0 | -$8 | **-$8** | +$49 | green (no-trade day still costs API) |
| Day 3 | +$120 | -$25 | -$10 | **+$85** | +$134 | green |
| Day 4 | -$30 | -$10 | -$8 | **-$48** | +$86 | yellow (one bad day) |
| Day 5 | +$60 | -$12 | -$8 | **+$40** | +$126 | green |

**5-day total: +$126 net. Pace = $25/day = $525/mo. Below "worth doing" tier — needs improvement to net +$50/day.**

## What today (2026-04-29) looked like

| Item | Value |
|---|---|
| Gross trading P&L | -$610 (estimated) |
| Topstep fees | -$403 |
| API spend | ~-$8 |
| **Net** | **-$1,021** |
| Trades placed | 97 (across 5 symbols) |
| Effective per-trade cost (fees alone) | $4.16 |
| Average reward per trade | < $0 (negative-EV churn) |

**Lesson encoded permanently**: the fee bleed alone (-$403) is more than half the total drawdown. Every gate added in the 2026-04-29 incident response (`daily_fee_budget_usd`, `per_symbol_trade_count_block`, regime gate, RTH-only autonomous) targets this directly.

## How to use this doc

- **CIO**: read on first wake every session. Pull the cost ledger into the brief.
- **Portfolio Manager / Risk Manager**: reject any setup that doesn't clear the per-trade NET threshold.
- **Analysts**: include expected NET dollar profit in every thesis (not just R:R).
- **Compliance**: update this doc's "today" section in the EOD audit, append a per-day row to the table.
- **User**: this is the canonical answer to "is the fund profitable?". Look here, not at the trading P&L alone.
