---
type: reference
purpose: Complete Topstep Trading Combine rules — we are currently in this stage
source: User-provided 2026-05-12 (compiled from Topstep official docs)
last_verified: 2026-05-12
sister_doc: vault/_meta/topstep_rules.md (XFA / Live rules)
---

# Topstep Trading Combine — Complete Rules & Pass Requirements

## Purpose of this document
This file provides every rule, parameter, objective, and constraint for the Topstep Trading Combine (as of May 2026). It is intended for use by an automated/algorithmic trading system. Every rule listed here must be enforced at the code level. Rule violations can permanently disqualify the account from funding. Topstep's official documentation takes precedence over this file if any conflict exists.

---

## What the Combine Is

The Trading Combine is Topstep's monthly-subscription simulated evaluation. You trade a simulated futures account against live market data. Pass the rules below and you automatically advance to an Express Funded Account (XFA) where real payouts begin. There is no minimum or maximum number of days — the Combine runs until you pass, breach, or cancel.

**2025 cohort pass rate: 16.8% per attempt. 51.8% of all participants advance to a funded level across multiple attempts.**

---

## Account Sizes — Parameters

All three account sizes use the same structural rule set. Only the dollar thresholds and contract caps differ.

| Parameter | $50K Combine | $100K Combine | $150K Combine |
|---|---|---|---|
| Profit target | $3,000 | $6,000 | $9,000 |
| Max Loss Limit (MLL) | $2,000 | $3,000 | $4,500 |
| Daily Loss Limit (DLL) | $1,000 | $2,000 | $3,000 |
| Max contracts (minis) | 5 | 10 | 15 |
| Max contracts (micros) | 50 | 100 | 150 |
| Monthly cost (Standard Path) | ~$49/mo | ~$99/mo | ~$149/mo |
| Activation fee (Standard Path) | $149 on pass | $149 on pass | $149 on pass |
| Profit-to-risk ratio | 1.5 : 1 | 1.5 : 1 | 1.5 : 1 |

**Note:** The No Activation Fee Path charges higher monthly fees but waives the $149 activation fee on passing. Math: if you expect to pass in one attempt, No Activation Fee saves money. If you expect multiple months, Standard is cheaper overall.

---

## The Single Rule: Maximum Loss Limit (MLL)

The MLL is the **only hard rule** in the Combine. All other items are objectives. Breaking the MLL is an instant disqualification.

### How it works — INTRADAY TRAILING (critical difference from XFA)
- In the Combine, the MLL trails your **highest live equity balance in real time during the session**, including unrealized (open trade) equity
- It does NOT wait until end-of-day to move — it moves the moment your live equity peaks
- Example ($50K account, $2,000 MLL):
  - Start of day: balance = $50,000 → MLL floor = $48,000
  - You open a position, equity rises to $51,200 → MLL floor immediately rises to $49,200
  - Your position reverses, equity drops to $49,200 → account is **immediately closed**
  - The floor climbed while your position was open — you had less room than you thought

### Key implications for automated systems
1. The system must monitor **live equity** (not just closed P&L) against the MLL at all times
2. A profitable open position raises the MLL floor — reducing your buffer while the trade is still open
3. Exiting a profitable trade to lock in gains does NOT raise the MLL further (it's already moved with unrealized gains)
4. A drawdown after a new equity peak can breach the MLL with less total loss than the starting buffer
5. Set internal hard stops well before the MLL — recommended: treat (MLL × 0.7) as the system's internal abort threshold

### What happens when MLL is hit in the Combine
- Account is liquidated for the remainder of that trading day
- Account becomes **ineligible for funding** until reset
- Practice trading remains available
- A Reset Credit can restore the account to starting conditions (one credit per monthly billing cycle)

---

## Objectives to Pass

### 1. Profit Target
- Hit the profit target for your account size (see table above)
- Profits are net of commissions and simulated fees
- Combine profits do NOT transfer to the XFA — the XFA starts at $0 balance
- There is no time limit on reaching the profit target

### 2. Consistency Rule — 50% Best-Day Cap
This is the most commonly failed objective and is critical for automated systems.

**Rule:** Your single highest-profit day must be less than 50% of your total cycle net profit at the moment you hit the profit target.

**Formula:** `Highest single day profit ÷ Total cycle net profit < 50%`

**Examples:**
- Total profit: $3,000, best day: $1,400 → 46.7% → PASS
- Total profit: $3,000, best day: $1,500 → 50.0% → FAIL (must be strictly less than 50%)
- Total profit: $3,000, best day: $1,600 → 53.3% → FAIL

**If you fail consistency:**
- The Combine does NOT close — profits stay in the account
- The system waits for you to add more profitable days to dilute the ratio
- You cannot retroactively reduce the best day's profit — you can only add more days
- Recommended fix: add $150–$400 winning days until the ratio drops below 50%

**Automated system implication:**
- Track `max_single_day_pnl / total_cycle_pnl` in real time
- If this ratio approaches 45%, cap the day's further profit generation (stop trading early, reduce size)
- Spread gains across multiple days — avoid "lottery ticket" single-session blowouts
- Days that close positive but below $150 net still count toward total profit (but not as winning days for XFA qualification later)

### 3. Maximum Position Size
- Fixed at 5/10/15 mini contracts for $50K/$100K/$150K (see table)
- On TopstepX: 10 micros = 1 mini contract (10:1 ratio)
- On Tradovate, NinjaTrader, Rithmic: micros count 1:1 against the limit
- Long and short positions on the same instrument are summed toward the cap
- The cap is set at account purchase and does NOT increase with profit growth
- Orders that exceed the cap are rejected — not a breach, but must be avoided

### 4. Daily Loss Limit (DLL) — Guardrail, Not a Hard Rule
- The DLL is not a rule violation if hit, but triggers session suspension
- Hitting the DLL auto-liquidates all positions and blocks trading for the rest of that session
- The DLL resets at 5:00 PM CT each day
- On TopstepX: DLL is built into the platform and enforced automatically
- On third-party platforms (Tradovate, NinjaTrader): DLL may or may not be auto-enforced — the trader/system is responsible for tracking it
- Burning the DLL wastes a trading day but does not fail the account

**DLL by size:**
- $50K: $1,000 per day
- $100K: $2,000 per day
- $150K: $3,000 per day

**Automated system implication:** Treat the DLL as a hard daily stop. Do not wait for the platform to intervene — build DLL tracking into the system and halt trading before hitting it.

### 5. Trading Hours
- Normal electronic trading hours apply (~23 hours/day for most futures)
- **All positions must be closed by 3:10 PM CT** (or the product's market close, whichever comes first)
- Abbreviated holiday hours exist — check Topstep's holiday calendar before each session
- The system must have a hard time-based flatten that fires at 3:05 PM CT regardless of P&L

---

## Permitted Products and Platforms

### Products
Futures contracts on CME Group products. Most commonly traded:
- Equity index: ES, NQ, YM, RTY (minis) / MES, MNQ, MYM, M2K (micros)
- Energy: CL (crude oil), NG (natural gas)
- Metals: GC (gold), SI (silver)
- FX futures: 6E (Euro), 6B (British Pound), 6J (Japanese Yen)
- Fixed income: ZB, ZN, ZF

Topstep does NOT support forex spot, crypto, or options.

### Platforms (as of April 2026)
- **TopstepX** — Topstep's proprietary platform with built-in TradingView charts, Tilt indicator, integrated risk management. DLL is enforced automatically here.
- **NinjaTrader** — third-party, DLL not auto-enforced
- **Tradovate** — third-party, DLL not auto-enforced

### Critical platform rules
- **VPNs are strictly prohibited.** Any VPN connection triggers Error 403 Forbidden. Topstep's servers detect VPN usage and will close accounts. This applies to all activity: trading, dashboard access, everything.
- **VPS (Virtual Private Servers) and remote access tools are also prohibited** per TopstepX API terms.
- Automated strategies ARE permitted, with caveats:
  - Topstep will not help set up or troubleshoot automated systems
  - No exceptions are made for errant trades or system malfunctions
  - Test on the Practice Account before going live on a Combine account

---

## Passing the Combine — Step by Step

### Step 1: Meet the profit target
- Trade until net P&L (after simulated fees) reaches the profit target for your account size
- Monitor running total daily — the trade report updates in real time

### Step 2: Verify the consistency rule
- At the moment your balance hits the profit target, the dashboard checks if your best day < 50% of total profits
- If consistency passes: account flips to "Passed" status (may take up to 30 minutes to reflect in dashboard)
- If consistency fails: account stays Active — keep trading to dilute the ratio

### Step 3: Activate the Express Funded Account
- You receive an email notification when the Combine passes
- Log in to the Topstep Dashboard and activate the XFA
- Standard Path: pay the $149 activation fee
- No Activation Fee Path: no payment required
- XFA activation takes a few minutes
- If you pass on a Friday after market close, you can pay immediately but the XFA won't be tradeable until the next session (Sunday evening CT for most instruments)

### Step 4: Choose your XFA path (as of February 5, 2026)
At activation, you choose between two XFA variants:
- **Standard Path**: 5 winning days + $5,000 cumulative profit before first payout. No consistency target in XFA.
- **Consistency Path**: 3 winning days + $6,000 cumulative profit before first payout. Adds a 40% consistency target (best day < 40% of total profit since last payout). Faster day count, higher profit threshold.

**This choice is permanent for that account — cannot be changed after activation.**

---

## What Changes Between Combine and XFA

This transition is critical — rules shift in important ways:

| Rule | Trading Combine | Express Funded Account |
|---|---|---|
| MLL trailing method | Intraday (real-time) | End-of-day only |
| MLL consequence | Session liquidation + reset required | Permanent account closure |
| Profit target | Yes ($3K/$6K/$9K) | None |
| Consistency rule | 50% cap to pass | 50% cap (Standard) / 40% cap (Consistency path) |
| Contract limits | Fixed max position size | Dynamic scaling plan (EOD-updated) |
| DLL enforcement | Optional guardrail | Platform-enforced on TopstepX; same optional on others |
| Combine profits | Stay in Combine account | Do NOT transfer to XFA — XFA starts at $0 |
| Payouts | None | Real cash payouts begin |

---

## Automated System — Combine-Specific Rules Checklist

The following must all be implemented before running an automated system on a live Combine:

- [ ] **MLL monitor**: Track live equity (open P&L included) vs. MLL floor in real time. Fire a full flatten if equity approaches MLL minus a safety buffer.
- [ ] **Intraday MLL tracking**: MLL floor moves with unrealized gains during the session. The system must recalculate the floor every tick when positions are open.
- [ ] **DLL tracker**: Calculate running daily P&L and halt trading before hitting the DLL. Do not rely solely on the platform to enforce this.
- [ ] **Consistency ratio monitor**: Track `max_single_day_pnl / total_cycle_pnl` continuously. Reduce or stop daily profit generation when ratio approaches 45%.
- [ ] **Daily profit ceiling**: Set a configurable daily max profit (e.g. $400–$600 for $50K) to prevent any single day from dominating the cycle.
- [ ] **Hard flatten at 3:05 PM CT**: Time-based order to close all positions 5 minutes before the hard 3:10 PM CT deadline. Must fire regardless of P&L.
- [ ] **Holiday calendar check**: Pull Topstep's abbreviated session list and do not trade or reduce position size on those days.
- [ ] **Contract limit enforcement**: Check the account's maximum position size before any order. Sum longs and shorts. Respect the 10:1 micro/mini ratio on TopstepX.
- [ ] **No VPN/VPS**: Ensure all trading and API connections originate from a direct (non-proxied, non-VPN) IP address.
- [ ] **Practice account testing**: Run the system on a Topstep Practice Account before deploying to a live Combine. Verify all flatten logic, DLL stops, and contract limits work correctly.
- [ ] **Malfunction handling**: Build a watchdog that detects system failures and issues a flatten-all order. Topstep makes no exceptions for errant automated trades.
- [ ] **News event filter**: Maintain a calendar of high-impact economic events (NFP, FOMC, CPI, etc.). Reduce position size or halt trading in the window surrounding these events.

---

## Reset Credits

- Each monthly billing cycle grants one Reset Credit
- A Reset Credit resets the Combine back to starting conditions (balance, MLL, everything)
- Useful after a breach or a bad streak — no need to purchase a new account
- Credits are tied to account size and path (a $50K Standard credit can only be used on a $50K Standard account)

---

## Key Rules Summary

| Rule | Value | Consequence of breach |
|---|---|---|
| Max Loss Limit hit | Account-specific | Session liquidation; need reset to continue |
| Profit target | $3K / $6K / $9K | Must reach to pass |
| Consistency (best day) | < 50% of total profit | Blocks pass; keep trading to dilute |
| Max position size exceeded | 5/10/15 minis | Orders rejected; review possible |
| Positions held past 3:10 PM CT | Hard deadline | Rule violation |
| DLL hit | $1K / $2K / $3K | Session suspended until next day |
| VPN use | Zero tolerance | Account closure |
| Multiple Topstep profiles | Zero tolerance | Account closure |

---

## Official Documentation URLs

- Combine parameters: https://help.topstep.com/en/articles/8284197-trading-combine-parameters
- Max Loss Limit: https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit
- Daily Loss Limit: https://help.topstep.com/en/articles/8284207-what-is-the-daily-loss-limit-and-what-happens-if-i-exceed-it
- XFA parameters: https://help.topstep.com/en/articles/8284215-express-funded-account-parameters
- Scaling plan: https://help.topstep.com/en/articles/8284223-what-is-the-scaling-plan
- Program overview: https://www.topstep.com/our-program/

---

*Last updated: May 2026. Topstep reserves the right to update rules at any time without prior notice. Always verify current rules at help.topstep.com before trading.*
