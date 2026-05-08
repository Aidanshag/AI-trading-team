---
type: meta
status: active
applies_to: [all]
updated: 2026-04-29
---

# Economic Health — what the team must clear monthly to be worth running

This document is the firm's economic ground truth. Every agent should be aware: this is not free trading; we have real monthly costs to cover.

## Monthly fixed costs (estimated)

| Line item | Cost | Notes |
|---|---|---|
| **Anthropic API (orchestrator)** | $250 | Active autonomous mode, ~$8/day average. Range $150 (idle) to $450 (max activity) |
| **Claude Pro / Max subscription** | $100 | Claude Max 5× (or Claude Pro at $20). User chooses tier. |
| **Topstep $50K Combine subscription** | $165 | While in Combine evaluation. Drops to ~$135 Performance Account fee once funded. Verify exact pricing on Topstep. |
| **Topstep live market data** | $10 | Optional but recommended. CME + CBOT + NYMEX + COMEX non-pro bundle. Enable when tactical/intraday trading dominates. |
| **Buffer (resets, data, etc)** | $50 | Combine reset fees ($80–200/reset) amortized; misc. |
| **TOTAL MONTHLY COSTS** | **$575** | At active levels. Range $400–700. |

## Breakeven targets (what the team must clear)

| Threshold | Monthly profit | Translation |
|---|---|---|
| **Pure breakeven** | $575 | Cover costs, zero return on time. Floor — anything below is losing money on the operation. |
| **Worthwhile (2× costs)** | $1,150 | Mediocre but defensible. Pays operator ~$0.75/hr at part-time effort. |
| **Comfortable (3× costs)** | $1,725 | Clear return on time + bandwidth. Funds the system + meaningful supplemental income. |
| **Strong (5× costs)** | $2,875 | This is the level to aim for. Justifies the engineering investment. |

## What this means at $50K Combine scale

The $50K Combine has:
- Profit target to pass: **$3,000** (one-time)
- Daily Loss Limit: $1,000 (we use $500 internal cap)
- Trailing drawdown: $2,000

After passing, on a Performance Account:
- 100% of first $5,000 in withdrawals
- Then 90/10 split above

**Realistic monthly net (once funded):**
- Conservative trader: $300–800/month
- Disciplined trader: $1,000–2,500/month
- Skilled / lucky tape: $3,000+/month

**Honest reality check:** ~60% of all Combine attempts fail (industry data). Most successful traders hover around the disciplined-trader range. **Hitting the "comfortable" $1,725/month needs the team to be in the top 30% of funded traders.**

## Operating modes — when to engage which

| Mode | Daily API cost | Daily target | Monthly target | When to use |
|---|---|---|---|---|
| **Hibernate** | $0 (halt active) | $0 | — | Vacation, no edge in tape, between Combines |
| **Observation** | $1–3 (CIO + 1 analyst, manual) | $0 | — | Paper trading or learning regime |
| **Autonomous-light** | $5–8 (current config, low activity day) | $20–50 | $400–800 | Standard operation, average tape |
| **Autonomous-active** | $10–15 (high tick rate, busy tape) | $100–200 | $1,500–3,000 | Profitable streak, want to capture flow |
| **Manual-override** | varies | varies | — | User identifies setup, drives chain manually |

## Cost discipline rules

**For PM and Risk Manager:**
- Every trade must clear costs. If the team makes 20 trades/month and APIcost is $250, then **average trade must clear $12.50 just to break even on API alone**.
- For the team to clear the $575/month total cost target with 20 trades/month: **$28.75 average net per trade** (~3 ticks on micros, less than 1 tick on standard E-minis).
- **R:R discipline aligns with this** — 2:1 R:R with 50% hit rate and average winner = 1R (~$50–250 risk) clears the cost easily IF the discipline holds.

**For all analysts:**
- A "vibes" trade with negative expected value isn't free — it costs roughly $1.50–3 in API to wake the chain even if it ends in NO_TRADE. **Twenty wasted wakes/day = $30/day = $900/month** in pure cost overhead.
- Discipline is profit. Refusing low-quality setups SAVES money even on no-trade days.

**For CIO:**
- Daily session brief should include current month-to-date P&L vs the $575 breakeven, $1,150 worthwhile, $1,725 comfortable thresholds.
- When MTD is below breakeven mid-month, CIO should bias toward higher-conviction setups + tighter stops, not chase volume.
- When MTD is above worthwhile, CIO can authorize slightly more exploratory trades within risk caps.

## What the team should NOT do

- Don't trade just to make the cost back. Forced trades have negative expectancy.
- Don't disable risk gates "because we're behind on the month." The discipline IS the edge.
- Don't escalate to frontier models (Opus) on routine questions — that's a 5–10× cost multiplier.
- Don't run autonomous mode on weekends without explicit reason — costs accrue, no edge in flat markets.

## Monthly profit / loss target tracker

| Month | Costs | Profit | Net | Mode |
|---|---|---|---|---|
| 2026-04 | TBD | TBD | TBD | First month — Combine evaluation |

(This table updates from `state.fund.db` via `scripts/monthly_pnl_report.py` — run weekly at minimum.)
