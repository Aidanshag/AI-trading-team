---
type: reference
purpose: Complete Topstep operational rules for automated trading
source: User-provided 2026-05-12 (compiled from Topstep official docs)
last_verified: 2026-05-12
---

# Topstep Funded Account — Complete Context for Automated Trading

## Purpose of this document
This file provides all operational rules, risk limits, payout mechanics, and compliance requirements for trading a Topstep funded account with a near-autonomous / algorithmic trading system. All rules must be enforced at the code level. Violations can result in permanent account closure.

---

## Account Structure Overview

Topstep has 3 stages. Most automated traders will operate in Stage 2 (Express Funded Account).

| Stage | Name | Capital | Payouts |
|---|---|---|---|
| 1 | Trading Combine | Simulated | None — evaluation only |
| 2 | Express Funded Account (XFA) | Simulated | Real cash payouts |
| 3 | Live Funded Account | Real money | Real cash payouts |

**Key stat:** Only 0.71% of XFA traders are called up to Live. Do not design the system to assume Live will happen — focus on XFA longevity and consistent payouts.

---

## Express Funded Account (XFA) — Primary Operating Environment

### Account sizes and hard limits

| Account | Max Loss Limit (MLL) | Daily Loss Limit (DLL) | Starting contracts |
|---|---|---|---|
| $50K | $2,000 below high-water mark | $1,000 | 2 |
| $100K | $3,000 below high-water mark | $2,000 | 3 |
| $150K | $4,500 below high-water mark | $3,000 | 5 |

### Max Loss Limit (MLL) — most critical rule
- The MLL is the **end-of-day trailing** high-water mark in the XFA (different from the Combine, which uses intraday trailing)
- The MLL only moves **up** after session close when a new balance high is set
- If the account balance hits the MLL at any point, the account is **permanently and immediately closed**
- After a payout, the MLL **resets to $0** — this is a critical automated system consideration (see Payout Reset Logic below)
- The system must track live equity vs. MLL in real time and hard-stop before breaching it

### Daily Loss Limit (DLL)
- Hitting the DLL triggers auto-liquidation of all positions and suspends trading for the rest of that session
- This is NOT a rule violation, but wastes a trading day
- The system must respect the DLL as a hard daily stop
- For platforms other than TopstepX, the DLL is enforced by the platform; on TopstepX it is built in

### Scaling Plan (contract limits)
- Contract limits are determined by end-of-day balance and update **once per day** after the trade report resets
- The system cannot increase contract size mid-session even if balance qualifies
- Exceeding the scaling plan limit for more than 10 seconds is a rule violation that can trigger account review or closure
- On TopstepX: 10 micro contracts = 1 mini contract (1:10 ratio)
- On Tradovate/NinjaTrader/Rithmic: micros count 1:1 against the plan

#### Scaling Plan tiers (example — $50K account)
| Balance | Max contracts |
|---|---|
| $0 to $1,499 | 2 |
| $1,500 to $1,999 | 3 |
| $2,000+ | 5 |

*Verify exact tiers in your Topstep Dashboard before coding — tiers can change.*

### Position closing deadline — HARD REQUIREMENT
- **All positions must be closed by 3:10 PM CT** (or the product's market close, whichever comes first)
- The system must have a hard time-based flatten mechanism that fires regardless of P&L or open trades
- Abbreviated holiday hours exist — the system must check Topstep's holiday calendar
- No exceptions. Open positions after market close will trigger rule violations

### Consistency rule (carries over from the Combine)
- No single winning day can account for **50% or more** of total cycle profits
- An autonomous system must track this ratio continuously
- Avoid strategies that produce occasional massive wins and many small wins — this will fail the consistency check
- Recommended: cap daily profit targets to avoid inadvertently concentrating too much profit on one day

### Positions that breach limits during the session
- If a position moves against you and approaches the MLL intraday, the system must close before the MLL is hit
- The MLL is calculated on **open equity**, not just closed P&L

---

## Payout Mechanics

### Qualifying for a payout
- A "winning day" requires **at least $150 net profit** after commissions and fees
- Standard path: need **5 winning days** before first payout request
- Consistency path (as of Feb 5, 2026): **3 winning days**, but different payout caps apply
- After the first payout, subsequent payouts require being profitable since the last payout (net P&L > $0)

### Payout amounts
- First payout ($50K account): capped at **$5,000**
- Subsequent payouts (all sizes): capped at **$6,000 per request**
- Minimum payout request: **$125**
- Profit split: **90% trader / 10% Topstep** (for accounts created on or after Jan 12, 2026)

### Payout methods and fees
| Method | Timing | Fee |
|---|---|---|
| ACH / Aeropay (US only) | Next business day / real-time | No fee |
| Wise | 24–48 hours | $20 |
| Wire transfer | Up to 10 days | $20 |

- Submit requests in the **morning ET** to hit the same-day processing queue
- After submission, copy-trading connections on the account are suspended until payout clears

### CRITICAL — Payout Reset Logic for automated systems
When a payout is processed:
1. The Max Loss Limit **resets to $0**
2. Your available trading room shrinks back to the original MLL buffer
3. If your system is sized to trade near the MLL, a payout can make the account dangerously close to termination on the very next trade
4. **The system must recalculate safe position sizing and stop-loss levels immediately after any payout**
5. Never auto-request a payout without checking whether post-payout MLL headroom is sufficient to survive normal drawdown

---

## Trading Hours and Market Access

- Normal electronic trading hours apply (nearly 23 hours/day for futures)
- **Hard flatten: 3:10 PM CT daily**
- Abbreviated holiday hours — check Topstep's site before each session
- All positions must be flat before market close regardless of strategy

---

## News Events

- Topstep does not prohibit news trading, but all risk from slippage, volatility, and DLL violations is the trader's responsibility
- For automated systems: consider disabling or reducing position size around high-impact events (NFP, FOMC, CPI)
- Recommend building a news filter that flags scheduled events and reduces max size or pauses trading in the window before/after

---

## Rule Violations — What Closes an Account Instantly

| Violation | Result |
|---|---|
| Balance hits Max Loss Limit | Permanent account closure |
| Exceeding contract limit >10 seconds | Account review, potential closure |
| Holding positions past 3:10 PM CT | Rule violation |
| Any single day = 50%+ of total profits | Consistency failure |
| Conviction for financial fraud/felony | Account closure |

---

## Back2Funded (XFA recovery option)

If the account is lost **before the first payout**:
- 7-day window to reactivate after account loss
- Pay the reactivation fee for your account size
- Only available on TopstepX in the new Topstep Dashboard
- Once any payout has been taken, Back2Funded is no longer available — a new Combine is required

---

## Live Funded Account (Stage 3) — If Called Up

*This stage involves real capital. Rules are stricter.*

- **Only 20% of your eligible XFA balance** is available at call-up; 80% is held in reserve
- Reserve unlocks in $15,000 increments for every $6,000 net profit milestone
- Winning days from the XFA **do not carry over** — you start the 30-day counter fresh in Live
- 5 benchmark days ($150+ profit each) required between each payout
- First 30 benchmark days: payouts capped at **50% of your share**
- After 30 benchmark days: up to **100% daily payouts** allowed (but 100% withdrawal closes the account)
- Copy trading is **not available** in Live accounts
- Contract sizing uses **Dynamic Live Risk Expansion (DLRE)** — not the fixed scaling plan
  - DLRE expands DLL and contract limits as net profit grows
  - DLRE contracts limits if equity drops or volatility increases
  - Requires 10 active trading days at each tier before DLL increases

### Live DLL by account size
| Account | Daily Loss Limit |
|---|---|
| $50K | $2,000 |
| $100K | $3,000 |
| $150K | $4,500 |
| Any (if balance ≤ $10,000) | $2,000 (tightened) |

---

## Recommended Automated System Guardrails

These are not Topstep rules — they are engineering recommendations for keeping the account alive:

1. **Hard MLL buffer**: Set an internal stop at 80% of the MLL — never let the system approach the actual limit
2. **Daily P&L ceiling**: Cap daily profits to stay under the 50% consistency threshold (e.g. $400–$600/day on a $50K account)
3. **Time-based flatten**: Fire a close-all-positions order at 3:05 PM CT (5 minutes before the hard deadline)
4. **Post-payout recalibration**: After any payout approval, recalculate MLL headroom and reduce position sizing if margin is thin
5. **Scaling plan check at session open**: Pull end-of-day balance and confirm max contract limit before placing any order
6. **News event filter**: Maintain a calendar of high-impact events and reduce size or halt trading in ±15 min windows
7. **Micro/mini contract awareness**: If using TopstepX, track micros at 10:1 ratio; on other platforms track at 1:1
8. **Payout eligibility tracker**: Count winning days ($150+ net), track P&L since last payout, flag when payout becomes eligible
9. **Concurrent account management**: Up to 5 XFAs can be active — if running multiple, track MLL and payout reset independently per account
10. **Holiday schedule check**: Pull Topstep's abbreviated session calendar and skip or reduce trading on those days

---

## Key URLs

- Official rules: https://www.topstep.com/express-funded-account-rules/
- Live account rules: https://www.topstep.com/live-funded-account-rules/
- Payout policy: https://help.topstep.com/en/articles/8284233-topstep-payout-policy
- Account parameters: https://help.topstep.com/en/articles/8284215-express-funded-account-parameters
- Scaling plan: https://help.topstep.com/en/articles/8284223-what-is-the-scaling-plan

---

*Last updated based on Topstep rules as of May 2026. Rules are subject to change at any time without notice — Topstep's official documentation takes precedence over this file.*
