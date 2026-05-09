---
type: meta
status: active
applies_to: [all]
priority: PRIMARY_GOAL
updated: 2026-04-29
---

# Topstep Combine Pass Strategy — the firm's #1 goal

**This is the primary objective of the trading team.** Everything else (cost discipline, edge research, autonomous infrastructure) is in service of one outcome: **pass the Topstep $50K Combine and get seeded with real trading capital**, then earn meaningful cash on the funded account.

Read this document on your first wake of every session. Refresh your understanding of the rules.

## The pass criteria (Topstep $50K Combine)

| Requirement | Threshold | Failure mode |
|---|---|---|
| **Profit target** | **$3,000 net profit** | Until hit, you're still in evaluation |
| **Daily Loss Limit (DLL)** | **−$1,000** intraday from prior EOD balance | Single breach = account failed |
| **Trailing Drawdown (TDD)** | **$2,000** from highest EOD balance ever reached | Single breach = account failed |
| **Minimum trading days** | **5 days** with at least one trade | Submitted with < 5 days = pending |
| **Consistency rule** | **No single day ≥ 50%** of total profit | Submitted with breach = denied |
| **Max position** | **5 contracts total open** at any time | Hard cap |
| **End-of-day flat** (verify) | Often required on Combine | Carry overnight = potential disqualification |

**Verify these against Topstep's current rules at https://www.topstep.com/rules.** This document captures our understanding as of 2026-04-29 — terms may have changed.

## What "passing" actually requires — strategic mindset

Most retail traders fail the Combine because they focus on the WRONG number. They aim for $3,000 in profits. **Wrong frame.**

The right frame: **don't lose $1,000 in any one day, don't give back $2,000 from peak, accumulate profit slowly and consistently across multiple sessions.**

If you average **+$300/day with no DLL breaches**, you pass in 10 trading days.
If you average **+$100/day with no DLL breaches**, you pass in 30 trading days.
**Both work.** Time is on your side as long as you don't blow the account.

The fail mode is almost always: trader has a great morning (+$800 day P&L), gets greedy, takes oversized afternoon trades, gives back to −$200 (DLL margin from peak: $1,000), then takes one more revenge trade and breaches. **Account gone in one session.**

## The "consistency rule" nobody respects

Topstep's consistency rule says: **no single day can be more than 50% of total profit at submission time.**

Concrete: if you have $4,000 in total profits but $2,500 came from one explosive day, that day is 62% of total — **denied.** You'd have to keep trading until other days bring the ratio back under 50%.

Implication: **don't try to pass in one big day.** Aim for 4–8 modestly profitable days. The pass is more about not-losing than about big wins.

## Trailing Drawdown is the silent killer

The TDD locks in your highest EOD balance and follows you up — but never down. So if you reach $52,000 EOD ($2K above start), your TDD floor is $50,000 (not $48,000 anymore). You can lose anything down to $50K but no further.

If you reach $53,000 EOD, the TDD floor is $51,000.

**This caps how much you can give back.** Once you've made progress, the TDD is much tighter than $2,000 from current. **Most blow-ups happen because traders forget the TDD anchored to a peak weeks ago.**

We track running peak in our state DB; Risk Manager monitors this.

## Combine-mode trading rules (firm-wide, ENFORCED by Risk Manager)

These are non-negotiable while in Combine evaluation:

| Rule | Threshold | Why |
|---|---|---|
| Internal DLL ceiling | **−$500** (50% of Topstep $1,000) | 100% safety buffer absorbs slippage + correlation surprise |
| Per-trade risk cap | **$250** (50bp of $50K) | One trade ≤ 25% of internal DLL ceiling |
| Defensive ladder triggers | −$150 alert / −$300 restrict / −$500 lockdown / −$750 emergency | Progressive tightening as drawdown deepens |
| Naked short *options* | Always blocked | Unbounded loss profile — categorical block |
| Naked short *futures* | Permitted (2026-04-29) | Allowed with stop + $250 cap + ladder backstops |
| Defined risk required | Always | Working stop OR structured max-loss |
| Max contracts | **5** total open | Topstep cap |
| **Daily profit cap (NEW)** | **$700** (cap on logged daily P&L for consistency) | If a day is running >$700, scale down or stop — you're risking the consistency rule |
| **Weekly loss cap (NEW)** | **−$300/week** | If a week is net −$300, halt for review |

The **$700 daily profit cap** isn't a Topstep rule but a **firm-imposed ceiling to protect the consistency rule**. If the team has a runaway profitable day, banking it past $700 risks making that day disproportionate to total profit.

## Pass-mode strategy (what kinds of trades to favor)

Tactical bias while in Combine:

**FAVOR:**
- High-probability mean-reversion setups (RSI2, BB pullback, range MR) — high hit rate, smaller R:R OK
- Defined-risk options structures — bounded max loss
- Liquid CME products (ES, MES, NQ, MNQ, CL, MCL, GC, MGC, ZN, 6E, M6E, M6B) — tight spreads, predictable fills
- Validation-grade trades for chain testing (limited risk)
- Single-position trades (not stacking correlated exposure)

**AVOID:**
- Counter-regime trades without strong evidence
- Low-liquidity products that can gap (some softs, thinly-traded contracts) — even if they were on Topstep, slippage hurts more than the edge
- Multi-position correlated exposure that compounds adverse moves
- Holding positions through known high-impact data releases (FOMC, NFP, CPI, EIA crude release) — risk of single-bar 4% move
- Options expiration weeks for short-DTE structures
- "Make-it-back" trades after a loss

## Pass-progress tracking (state.fund.db + Topstep account)

The team should track:
1. **Current Combine balance** vs starting $50,000
2. **Cumulative P&L** (= balance − $50,000)
3. **Days since Combine start** (calendar)
4. **Days WITH at least 1 trade** (trading days for min 5 requirement)
5. **Highest EOD balance ever** (TDD anchor)
6. **Largest single-day P&L** (consistency ratio numerator)
7. **Day P&L distribution** (verify no day > 50% of total)

These get computed by `scripts/combine_progress_report.py`. CIO reads this on every session-open wake.

## After passing — Performance Account mode

Once the Combine is passed and Topstep funds you on a Performance Account (PA):
- Same DLL/TDD rules
- 100% of first $5,000 in net profits
- 90/10 split (you get 90%) above $5,000

**Withdrawal threshold:** typically need to be at least $X above starting (verify) and meet trading-day minimums to withdraw.

In PA mode, the firm's strategy can shift slightly:
- Discipline still primary, but the consistency rule no longer applies the same way (verify Topstep's current PA rules)
- Goal becomes monthly withdrawal targets aligned with the Economic Health document ($1,725/mo "comfortable" target)
- Can run autonomous mode at higher activity if profit history justifies

## What every agent should do differently

**CIO**: every daily session brief opens with a Combine-progress section: "Day 14/min 5; balance $51,200 (+$1,200/+$3K target = 40% to pass); largest day +$340 (consistency 28%); next milestone: hit $52K to advance TDD anchor."

**Sector Analysts (Energies, Metals, Grains, etc.)**: when proposing setups, explicitly note whether the setup has the **risk profile** that fits Combine mode — small risk per trade, high-probability hit rate, no overnight gap risk for short-DTE.

**Edge Hunter / Quant Researcher**: prioritize setups with R:R ≥ 2:1 AND hit rate ≥ 50% (per backtest data). This combination is the most reliable Combine-pass profile.

**PM**: every proposal is sized so that worst case ≤ $250 AND best case ≤ $700/day. If a trade could hit $700+ alone, **reduce size**. Save the upside for tomorrow.

**Risk Manager**: treat the $700 daily profit cap and the consistency rule as additional gates beyond the existing 13. If today's P&L would push past the consistency-safe ratio, BLOCK or modify down.

**Compliance**: end-of-day audit verifies (1) DLL not breached, (2) TDD not breached, (3) consistency ratio still safe, (4) at least one trading day logged.

**Book Monitor**: alert immediately if running peak − current P&L approaches −$1,500 (within $500 of TDD breach).

## The user's stated goal

> "the main goal: be able to get trading cash from topstep and be profitable"

That's the frame. **Pass the Combine → get funded → start earning real cash → generate enough monthly to clear the $575 cost baseline and build toward the $1,725 comfortable target.**

Every wake, every decision, every refusal — orient toward this one goal.
