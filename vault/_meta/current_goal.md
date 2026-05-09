---
type: canon
status: ACTIVE
priority: TOP
read_on_first_wake: ALL
---

# 🎯 CURRENT GOAL — read this BEFORE anything else

## Pass the Topstep $50K Combine. As fast as safely possible.

That's the only goal right now. **It is above all other priorities** — above monthly net P&L, above strategy R&D, above polish. Until the Combine is passed, every decision the team makes is judged by one question:

> *Does this move us closer to the $3,000 cumulative profit target without breaching DLL, TDD, or the 50% consistency rule?*

If the answer is no, don't do it.

## What "passing" means (Topstep $50K Combine specifics)

| Requirement | Threshold | Source |
|---|---|---|
| Cumulative profit | **+$3,000** | Topstep |
| Daily Loss Limit | never breach **−$1,000** in any single day | Topstep |
| Trailing Drawdown | never go **$2,000 below peak EOD balance** | Topstep |
| Consistency rule | **no single day > 50% of total profit at submission** | Topstep |
| Minimum trading days | **≥ 5 days with at least one trade** | Topstep |
| Submit + payout | request payout once eligible | Topstep |

## What "as fast as safely possible" means

- **Win small, win consistently.** Even +$100/day passes in 30 trading days. Even +$200/day passes in 15. The game is repetition, not heroics.
- **Cap each day at ~$200 net** to satisfy the consistency rule by submission time. A single great $1,000 day forces 4 more $250+ days to balance — and one bad day in there breaks the chain.
- **Survival > speed.** A day with no trade is fine. A day with a -$300 loss is not. The math: 1 day of -$300 takes 2 days of +$150 to recover, plus the cumulative $40 fixed-cost burn. You don't make it back.
- **Phase 1 (now): Climb to $3,000.** Phase 2 (after): Maintain. Most Combines are lost in Phase 2, not Phase 1 — keep that in mind even while climbing.

## What is DEPRIORITIZED until the Combine is passed

- Strategy R&D / new strategies (use what works, don't experiment)
- Monthly NET P&L optimization (still tracked, but not the KPI driving decisions)
- Vault expansion / deep-dives that don't directly serve a Combine trade
- Equities desk (already dormant — keep it dormant)
- Anything that costs API spend without a clear path to a passing trade

The fund's monthly cost (~$575) still matters — but only as the lower bound. After passing the Combine and getting the funded account, monthly profitability becomes the primary KPI. Until then, **the Combine is the only KPI.**

## Per-role implications

**CIO**: every session brief opens with Combine progress: cumulative $X / $3,000 target (Y% there), days logged, distance to consistency-cap headroom, distance to DLL/TDD walls. Wake the analyst whose sector is most likely to produce a small clean trade today. Skip exploratory wakes.

**Portfolio Manager**: every accepted proposal must answer "does this fit Combine math?" — small risk, high probability, defined invalidation. Reject heroic R:R proposals during Phase 1. Cap each accepted trade at $250 worst-case (already enforced) and prefer $100-150 risk on micro contracts.

**Risk Manager**: tighten any trade that would push the day past +$200 realized. If today is already +$200, only allow defensive / closing trades. The 50% rule is a hard ceiling, not a soft suggestion.

**Edge Hunter / Quant Researcher**: bias toward micro-contract, intraday, mean-revert-after-extension setups during RTH only. Skip overnight. Skip event windows. The strategies that work for the Combine are NOT the same strategies that maximize monthly P&L on a funded account — they're more conservative.

**Compliance**: every EOD report leads with: cumulative_profit, days_logged, max_single_day, consistency_ratio, distance_to_DLL, distance_to_TDD. If any of those numbers is concerning, escalate to user via the loss-alerter webhook.

## Source of truth

- **This doc** is the current goal — agents read this on first wake.
- `risk_limits.yaml:account.profit_target_usd` and `combine_pacing.*` are the encoded rules.
- `vault/_meta/economics.md` retains the longer-term equation; agents reference it for "after the Combine."
- `fund.yaml:current_phase` is the programmatic flag.

When this goal is reached (cumulative profit ≥ $3,000 sustained), update this doc to point at the next phase and update `fund.yaml:current_phase` accordingly.
