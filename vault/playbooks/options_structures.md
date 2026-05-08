---
type: playbook
sector: options
status: active
written: 2026-04-28
author: Fund Engineer
---

# Options structures primer

One-page reference for each allowed options structure used on the fund. Covers Greeks profile, IV regime fit, typical DTE, risk/reward shape, and when to use each.

**Terminology:** All prices, deltas, and Greeks computed via Black-76 (futures options model). Notation: F = futures price, K = strike, T = years to expiry, σ = volatility (annualized), r = risk-free rate (default 5%). Examples use /CL (crude oil) front-month as reference (F=78.50). All Greeks per contract (multiply by 100 for a full position; adjust tick value per product).

---

## Core structures (approved for regular use)

### 1. Long Call
**Use when:** Bullish; you want leveraged upside with defined risk.

**Structure:**
- Buy 1 call at strike K
- Max loss: debit paid
- Max profit: unlimited (technically; liquidity-limited at deep OTM)
- Breakeven: K + debit

**Greeks profile (example: CL 80 call, 30 DTE, vol=22%, F=78.50):**
- Price: $1.33/bbl ≈ $133/contract
- Delta: +0.39 (gains $0.39 for every $1 move up in CL)
- Gamma: +0.077 (delta accelerates as CL rallies)
- Vega: +0.086 (profits if vol rises)
- Theta: −$0.031/day (loses ~$3.10/day to time decay)

**IV regime fit:**
- Best in: Low-to-moderate IV (buying vol is cheaper; theta decay is slower)
- Acceptable in: High IV (vol decay risk, but large moves possible)
- Avoid in: Collapsing IV without a rally (you lose both directions)

**Typical DTE:**
- 21–45 DTE (sweet spot: theta decay is slow, gamma is responsive)
- Avoid <14 DTE (theta accelerates; vega drops; only if directional confidence is very high)
- Avoid >90 DTE (vega bloat; small vol moves hurt; less responsive to spot moves)

**Pros:**
- Simple, directional, defined downside (debit paid)
- Gamma works for you in winning trades (position gets bigger as you're right)
- Scalable: buy 1 for $133 or 10 for $1,330

**Cons:**
- Theta works against you every day (you're paying for time)
- Requires the move to happen before expiry; wrong timing kills the thesis
- Max profit requires deep ITM (high gamma, hard to get there)

**Exit rules:**
- Take profit at 2R: sell at double your debit paid
- Stop: 50% debit loss (theta + adverse move is your stop)
- If underlying stalls below strike past 7 DTE: close and redeploy capital

---

### 2. Long Put
**Use when:** Bearish; you want leveraged downside with defined risk.

**Structure:**
- Buy 1 put at strike K
- Max loss: debit paid
- Max profit: K − debit (exercised at zero)
- Breakeven: K − debit

**Greeks profile (example: CL 77 put, 30 DTE, vol=22%, F=78.50):**
- Price: $1.29/bbl ≈ $129/contract
- Delta: −0.37 (loses $0.37 for every $1 move up in CL; gains $0.37 for every $1 down)
- Gamma: +0.076 (delta accelerates as CL falls; becomes more negative)
- Vega: +0.084 (profits if vol rises)
- Theta: −$0.031/day (loses ~$3.10/day)

**IV regime fit:**
- Best in: Low-to-moderate IV (cheaper entry, slower theta decay)
- Acceptable in: High IV (more profitable if put finishes ITM, but decay is steeper)
- Avoid in: Rising-IV environment without a clear bearish catalyst (you're fighting vol expansion working for short volatility, not your side)

**Typical DTE:**
- 21–45 DTE (same as long calls: theta is manageable, gamma is reactive)
- Avoid <14 DTE unless the move is imminent
- Avoid >90 DTE (same vega bloat as long calls)

**Pros:**
- Defined risk (debit paid = max loss)
- Clean short exposure without margin concerns
- Profit accelerates (gamma) if thesis plays out

**Cons:**
- Theta decay is relentless; you're paying for time
- Requires downside move to materialize; timing risk high
- Deep ITM is profit ceiling, not infinite profit

**Exit rules:**
- Same as long call: take 2R profit, 50% debit stop
- Close after 7 DTE if move hasn't materialized (theta burns too fast)

---

### 3. Bear Put Spread (Defined-Risk Bullish Income)
**Use when:** Mildly bullish; you want to collect premium with defined risk; entry point is elevated.

**Structure:**
- Sell 1 put at strike K₁ (higher, closer to F)
- Buy 1 put at strike K₂ (lower, protection)
- Width: K₁ − K₂ = defined max profit and max loss
- Max profit: credit received (happens if underlying stays above K₁ at expiry)
- Max loss: (K₁ − K₂) − credit (you're short the spread; capped at width)
- Breakeven: K₁ − credit

**Greeks profile (example: Sell 79 put, Buy 76 put, 30 DTE, vol=22%, F=78.50):**
- Short 79 put: −$2.23, delta −0.53, vega −0.089
- Long 76 put: +$0.94, delta +0.29, vega +0.077
- **Net:** credit $1.29, net delta −0.24, net vega −0.012
- (The net short vega means you profit if vol collapses; most spreads are short vol structures)

**IV regime fit:**
- Best in: High IV (credit is larger; vol likely to collapse post-expiry)
- Acceptable in: Moderate IV (still profitable; just smaller credit)
- Avoid in: Rising IV (the short side loses as vol expands; your max loss widens on paper)

**Typical DTE:**
- 30–60 DTE (sweet spot: credit is meaningful, theta decay accelerates into expiry)
- 21–30 DTE works if IV rank is >50th percentile

**Pros:**
- Positive theta: you earn money every day (if underlying cooperates)
- Defined risk: you know max loss upfront (width − credit)
- High win rate: underlying just needs to stay above short strike
- Credit can be 50–80% of the spread width (very efficient)

**Cons:**
- Assignment risk: if short put goes ITM, you're assigned shares (or contracts long) at K₁
- Negative delta: you have a mild short bias (you want underlying to stay above K₁)
- Vol expansion (IV rank rising) hurts your credit size and max profit

**Management:**
- Exit at 50% of max profit (half your credit target)
- If underlying drops to short strike: evaluate — close the spread for a loss or hold if still bullish
- At 7 DTE: close regardless of P&L; theta acceleration is too fast; assignment risk is real

**Exit rules:**
- Take profit at 50% of credit (half the max profit)
- Stop: spread width − credit (full width loss)
- Hard stop: 7 DTE close if not at 50% profit yet (theta acceleration risks forcing assignment)

---

### 4. Bear Call Spread (Defined-Risk Bearish Income)
**Use when:** Mildly bearish or neutral; you want to collect premium with capped risk; underlying is elevated.

**Structure:**
- Sell 1 call at strike K₁ (lower, closer to F)
- Buy 1 call at strike K₂ (higher, protection)
- Width: K₂ − K₁ = max loss and max profit
- Max profit: credit received (underlying stays below K₁ at expiry)
- Max loss: (K₂ − K₁) − credit
- Breakeven: K₁ + credit

**Greeks profile (example: Sell 80 call, Buy 82 call, 30 DTE, vol=22%, F=78.50):**
- Short 80 call: −$1.33, delta −0.39, vega −0.086
- Long 82 call: +$0.61, delta +0.22, vega +0.060
- **Net:** credit $0.72, net delta −0.17, net vega −0.026

**IV regime fit:**
- Best in: High IV (credit is larger; vol likely to collapse)
- Acceptable in: Moderate IV
- Avoid in: Low IV or rising IV (credit is small; vol expansion hurts you)

**Typical DTE:**
- 30–60 DTE (sweet spot for theta decay and credit size)
- 21–30 DTE if IV rank is elevated (>60th percentile)

**Pros:**
- Positive theta: earn money if underlying sits still or falls
- Defined max loss: you know the worst upfront
- High-probability trade: underlying just needs to not rally hard
- Short vol structure: profits if IV rank falls (typical post-earnings, post-event)

**Cons:**
- Negative delta: you're short a mild amount (you want underlying to fall or stay flat)
- Max profit is credit (can be <50% of spread width, depending on IV)
- Assignment risk if short call goes ITM near expiry

**Management:**
- Exit at 50% of credit (half max profit)
- If underlying rallies toward short strike: reassess — close spread for a loss or adjust by rolling short strike higher
- At 7 DTE: close; theta acceleration is dangerous; assignment on short call is likely if ITM

**Exit rules:**
- Take profit at 50% of credit
- Stop: spread width − credit
- Hard stop: 7 DTE close if not at 50% profit

---

### 5. Bull Put Spread (Defined-Risk Bullish Income)
**Use when:** Bullish; you want premium income with defined risk; you have a specific target support level.

**Structure:**
- Sell 1 put at strike K₁ (lower, closer to downside risk)
- Buy 1 put at strike K₂ (even lower, protection)
- Width: K₁ − K₂ = max loss and profit boundaries
- Max profit: credit received (underlying stays above K₁ at expiry)
- Max loss: (K₁ − K₂) − credit
- Breakeven: K₁ − credit

**Greeks profile (example: Sell 76 put, Buy 74 put, 30 DTE, vol=22%, F=78.50):**
- Short 76 put: −$0.94, delta −0.29, vega −0.077
- Long 74 put: +$0.50, delta +0.15, vega +0.050
- **Net:** credit $0.44, net delta −0.14, net vega −0.027

**IV regime fit:**
- Best in: High IV (credit is larger)
- Acceptable in: Moderate IV
- Avoid in: Rising IV (expansion hurts max profit)

**Typical DTE:**
- 30–60 DTE (standard theta decay window)

**Pros:**
- Positive theta: earn daily if underlying cooperates
- Defined risk: know your max loss upfront
- Directional flexibility: can be sized smaller than long calls for same risk
- Efficient use of buying power (spreads are cheaper capital-wise than outright directional bets)

**Cons:**
- Negative delta: mild short bias (less bullish than a long call)
- Credit is small (can be <30% of spread width)
- Assignment risk on short put if underlying falls through K₁

**Exit rules:**
- Take profit at 50% of credit
- Stop: spread width − credit
- Hard stop: 7 DTE close

---

### 6. Bull Call Spread (Defined-Risk Bullish Leverage)
**Use when:** Bullish; you want directional leverage with capped risk; you don't have unlimited capital for long calls.

**Structure:**
- Buy 1 call at strike K₁ (lower, closer to F)
- Sell 1 call at strike K₂ (higher, cap on upside)
- Width: K₂ − K₁ = max profit and max loss boundaries
- Max profit: (K₂ − K₁) − debit paid
- Max loss: debit paid
- Breakeven: K₁ + debit

**Greeks profile (example: Buy 78 call, Sell 80 call, 30 DTE, vol=22%, F=78.50):**
- Long 78 call: +$1.61, delta +0.42, vega +0.087
- Short 80 call: −$1.33, delta −0.39, vega −0.086
- **Net:** debit $0.28, net delta +0.03, net vega +0.001 (vega-neutral; good)

**IV regime fit:**
- Best in: Moderate IV (lower entry cost; less theta drag than long call alone)
- Acceptable in: All IV regimes (not vol-sensitive due to vega neutrality)
- Neutral to high IV: short call offsets long call's vol benefit, but spreads are cheaper

**Typical DTE:**
- 21–45 DTE (sweet spot: vega-neutral, gamma-reactive)

**Pros:**
- Much cheaper than long call alone (short call funds half or more of long call)
- Vega-neutral: vol moves don't hurt or help much (focus is spot movement)
- Gamma still works for you: delta accelerates as you're right
- Wider risk/reward is more efficient than long call

**Cons:**
- Capped upside: max profit is (K₂ − K₁) − debit, not infinite
- If underlying rallies past K₂, you leave money on table (short call is capped)
- Still has theta drag (long call losses more than offset by short credit)

**Exit rules:**
- Take profit at 2R: sell spread for double the debit paid
- Stop: 50% debit loss
- If underlying breaks K₂ and stalls: hold (short call is capped) or close to collect full width profit

---

## Advanced structures (approved for experienced traders; requires PM escalation)

### 7. Iron Condor (Short Vol, Range-Bound Bet)
**Use when:** Neutral outlook; underlying is choppy; IV is elevated and expected to collapse; you want high-probability premium collection.

**Structure:**
- Sell 1 OTM call at strike K₃
- Buy 1 OTM call at strike K₄ (higher, protection)
- Sell 1 OTM put at strike K₁
- Buy 1 OTM put at strike K₂ (lower, protection)
- Structure is "collared": short two strikes (call and put), long two outer strikes (protection)
- Max profit: total credit received (if underlying stays between K₁ and K₃ at expiry)
- Max loss: larger of the two spreads' widths minus total credit (capped on both sides)

**Greeks profile (example: Sell 80 call, Buy 82 call, Sell 76 put, Buy 74 put, 30 DTE, vol=22%, F=78.50):**
- Call spread: net debit −$0.72 (short call credit exceeds long call debit)
- Put spread: net credit $0.44
- **Net:** credit ~$0.20 (after combining both spreads)
- Net delta ≈ 0 (balanced long and short deltas)
- Net vega ≈ −0.05 (short vol structure; benefits from vol collapse)

**IV regime fit:**
- Best in: High IV (credit is largest; vol collapse is expected)
- Acceptable in: Moderate-high IV (still profitable; smaller credit)
- Avoid in: Low IV or rising IV (credit is minimal; vol expansion kills you)

**Typical DTE:**
- 30–45 DTE (standard range-bound window)

**Pros:**
- High probability of profit: underlying just needs to stay within two ranges (most do, most of the time)
- Balanced delta: neutral to market direction
- Positive theta: earn money daily from time decay
- Short vol: profits if vol collapses (typical 2–4 weeks after vol spikes)
- Two-sided protection: losses are capped on both sides

**Cons:**
- Complex: four legs to manage; assignment risk on two sides
- Small credit: max profit can be 20–30% of max loss (unfavorable risk/reward in low-IV environments)
- Whipsaw risk: if underlying moves fast in one direction, you lose on that side; can lead to assignment
- Gamma works against you: delta accelerates if underlying breaks a sold strike

**Management:**
- Close at 50% of max profit (half the credit)
- If underlying breaks toward one side: consider closing that side of the spread to salvage credit on other side
- Hard stop: spread width × 1.5 or time-based at 14 DTE (close the whole trade)

**Exit rules:**
- Take profit at 50% of credit
- Stop: larger spread width minus credit
- Hard stop: 14 DTE close (theta acceleration + gamma risk becomes dangerous)

**When to escalate to PM:** Condors are approval-required because they tie up capital on both sides and can require two separate assignment negotiations. Use sparingly; size smaller than directional spreads.

---

### 8. Iron Butterfly (Short Vol, Narrow Range, High Probability)
**Use when:** Neutral; underlying is expected to stay flat; IV is high; you want maximum probability of profit (but narrower range than condor).

**Structure:**
- Sell 1 ATM call at strike K (center)
- Buy 1 OTM call at strike K + W (higher, protection)
- Sell 1 ATM put at strike K (center, same strike as short call)
- Buy 1 OTM put at strike K − W (lower, protection)
- Butterfly is "tight": both sold strikes are at the same level (center), wings are equal distance out

**Greeks profile (example: Sell 78 call & 78 put, Buy 80 call & 76 put, 30 DTE, vol=22%, F=78.50):**
- Net delta ≈ 0 (perfectly balanced; ATM shorts are delta-neutral)
- Net vega ≈ −0.08 (short vol structure; benefits if vol collapses)
- Net gamma ≈ 0 (ATM short gamma offsets long leg gamma; mostly flat)
- Max profit: credit (typically 30–50% of wing width)
- Max loss: wing width − credit (happens if underlying moves beyond either wing at expiry)

**IV regime fit:**
- Best in: High IV (credit is meaningful; vol collapse expected)
- Acceptable in: Moderate IV
- Avoid in: Rising IV (you're paying for vol expansion)

**Typical DTE:**
- 21–30 DTE (tighter window than condor; butterfly is more sensitive to timing)
- Avoid >45 DTE (gamma decay is too slow; vega bloat makes it expensive)

**Pros:**
- Highest probability of profit: underlying needs to stay within a narrow range
- Vega-short: benefits if vol collapses post-event
- Balanced delta: neutral; works in all directions (as long as underlying stays put)
- Efficient capital use: max loss is only the wing width

**Cons:**
- Very narrow profit zone: underlying moves >1–2% often violates the trade
- Small credit: max profit is often 25–35% of max loss (risk/reward is unfavorable)
- Gamma risk at expiry: if underlying is near a strike, assignment risk is high; could be assigned on both short legs
- Pin risk: if underlying is exactly at short strike at expiry, assignment is ambiguous (could be assigned or not)

**Management:**
- Close at 75% of max profit (three-quarters of credit target); don't hold to expiry
- If underlying moves toward a wing: decide whether to close the whole trade or roll the threatened wing higher/lower
- Hard rule: never hold a butterfly to expiry (pin risk and assignment ambiguity are too high)

**Exit rules:**
- Take profit at 75% of credit (well before expiry)
- Stop: wing width − credit
- Hard stop: 7 DTE close (pin risk and gamma explosion)

**When to escalate to PM:** Butterflies are narrow-bet structures. Size them smaller than spreads (1–2 contracts max on a $500K account). PM sign-off required.

---

### 9. Calendar Spread (Long Volatility, Long Time)
**Use when:** You expect a period of high volatility followed by a collapse; you want to profit from vol expansion, not direction; setup is neutral.

**Structure:**
- Sell 1 near-term call/put at strike K (e.g., 30 DTE)
- Buy 1 far-term call/put at strike K (e.g., 60 DTE), same strike
- Profit source: theta on short leg expires faster than long leg; at expiry of short, long still has time value
- Also profits if underlying is near K at short expiry (gamma profit from rolling short higher/lower)

**Greeks profile (example: Sell CL 78 call 30 DTE, Buy CL 78 call 60 DTE, vol=22%, F=78.50):**
- Short 30 DTE call: −$1.61, theta $0.031/day (positive; decay is fast)
- Long 60 DTE call: +$2.10, theta −$0.018/day (slower decay)
- **Net:** debit $0.49, positive theta (trades earn money daily if underlying stays at strike)
- Vega: long is higher (more vol-sensitive); short loses; **net slightly short vega** (you want vol to rise, not fall)

**IV regime fit:**
- Best in: Low IV expanding to moderate (profit from vol expansion; short leg decays faster)
- Acceptable in: Stable IV (still profitable from time decay differential)
- Avoid in: Collapsing IV (vol compression kills long leg value; short leg doesn't decay fast enough)

**Typical DTE:**
- Sell 21–30 DTE; buy 45–60 DTE (14–30-day calendar window)
- Avoid narrower calendars (<7 days between legs) — too choppy
- Avoid wider calendars (>60 days) — too much capital tied up

**Pros:**
- Profits from three sources: short theta, vol expansion (if long bought when IV is low), and gamma roll profits (short leg can be re-sold at higher strike as underlying moves)
- Capital-efficient: debit paid is small (50–70% of outright option premium)
- Directionally neutral: works if underlying is flat or moves slightly
- Can be rolled: if short expires, re-sell at new strike; keep collecting theta

**Cons:**
- Theta profit is modest: you're paying for time, but earning less than you pay
- Vega is tricky: if vol rises, long gains but short also gains (net vega is slightly negative or neutral) — requires vol expansion + spot move to be profitable
- Gamma risk: as short approaches expiry, gamma explodes; underlying move away from strike can hurt
- Requires active management: can't be set and forgotten (rolling decisions matter)

**Management:**
- Monitor short expiry closely (last 5 days); decide whether to re-sell at new strike or close
- If underlying moves away from strike: let short decay; theta still works; long is still worth money
- If underlying moves toward strike: take profit on short; consider adjusting long or letting it ride
- Close if short moves deeply ITM/OTM and vol collapses (long position loses value; short isn't profitable)

**Exit rules:**
- Take profit at 50% of debit (short expires profitably; you've earned the theta differential)
- Stop: 100% of debit paid (vol collapses; long leg loses value faster than short decays)
- Time stop: 5 days before short expiry (close or roll to avoid gamma explosion)

**When to escalate to PM:** Calendars are longer-term structures requiring active management. Escalate if calendar debit exceeds $500 per contract.

---

### 10. Diagonal Spread (Leveraged Directional, Multiple Expirations)
**Use when:** Bullish (or bearish); you want leveraged direction with defined risk; you plan to manage the position actively; you want to reduce entry cost vs. outright long call/put.

**Structure:**
- Buy 1 long-dated call/put at strike K₁ (e.g., 90 DTE) — the core position
- Sell 1 near-term call/put at strike K₂ (e.g., 30 DTE) — collect premium to offset long cost
- K₂ is typically higher (for call diagonals) or lower (for put diagonals) than K₁ — you're selling OTM premium
- As near-term expires, you can re-sell the next month at the same or higher strike; keep rolling

**Greeks profile (example: Buy CL 76 call 90 DTE, Sell CL 78 call 30 DTE, vol=22%, F=78.50):**
- Long 90 DTE call: +$2.90, delta +0.45, vega +0.095, theta −$0.018/day
- Short 30 DTE call: −$1.33, delta −0.39, vega −0.086, theta +$0.031/day
- **Net:** debit $1.57, net delta +0.06, net vega +0.009, net theta +$0.013/day

**IV regime fit:**
- Best in: Low-to-moderate IV (you want to buy long-dated leg at reasonable price; collect short-term premium)
- Acceptable in: High IV (short premium is good; but long cost is also high — mixed)
- Avoid in: IV collapse (long leg value drops; short doesn't decay fast enough)

**Typical DTE:**
- Buy 60–90 DTE; sell 21–30 DTE; roll sold leg monthly
- Creates a rolling, multi-month position if managed correctly

**Pros:**
- Directionally leveraged: positive net delta; makes money if underlying rises
- Debit is lower than outright long call: short premium offsets long cost by 40–60%
- Theta-positive if managed: rolling the short leg collects premium monthly
- Flexible: can adjust strikes on short leg rolls to either collect more premium or give more upside

**Cons:**
- Complex: requires active management (monthly rolling decisions)
- Assignment risk on short leg: if it goes ITM, you're assigned (in futures, you're assigned the underlying contract)
- Vega exposure: positive vega means you want vol to rise (profits if IV increases); but if vol collapses, the short leg loses less than it should
- Gamma risk: short leg can move fast against you late in month; requires adjustment or closure

**Management:**
- Monitor short expiry; decide to re-sell, roll up, or close
- If underlying rallies past short strike: can close short to lock profits; keep long for upside
- If underlying falls: let short expire worthless; hold long; prepare to re-sell next month at lower strike
- If vol drops: long loses value; consider closing entire diagonal and redeploying

**Exit rules:**
- Take profit on the "roll": collect >75% of max possible short premium across 3+ rolls (i.e., over 3 months)
- Stop on long: 50% of long debit (underlying has moved against thesis and vol has collapsed)
- Hard stop: 5 days before short expiry if it's ITM and vol is low (assignment is imminent)

**When to escalate to PM:** Diagonals require active management and rolling discipline. Size smaller than spreads (1–2 contracts); escalate if total debit on diagonal exceeds $500.

---

## Structure selection matrix

| Outlook | IV Regime | Setup | Use Structure | DTE | Max P&L |
|---------|-----------|-------|---------------|----|---------|
| **Bullish** | Low | Spot support, catalysts | Long call | 21–45 | Unlimited (practical limit: liquidity) |
| **Bullish** | Moderate | Support level clear | Bull call spread | 21–45 | Spread width − debit |
| **Bullish** | High, expected collapse | Mild bullish, harvest premium | Bear put spread | 30–60 | Credit received |
| **Bullish, leveraged** | Low–Moderate | Multi-month, active mgmt | Diagonal call spread | 60–90 | Spread width − debit (rolled) |
| **Bearish** | Low | Spot resistance, downside catalyst | Long put | 21–45 | Unlimited (practical) |
| **Bearish** | Moderate | Resistance level clear | Bear call spread | 21–45 | Spread width − debit |
| **Bearish** | High, expected collapse | Mild bearish, harvest premium | Bull put spread | 30–60 | Credit received |
| **Neutral, range-bound** | High | IV elevated, collapse expected | Iron condor | 30–45 | Credit received |
| **Neutral, tight range** | High | Maximum probability play | Iron butterfly | 21–30 | Credit (small) |
| **Neutral, volatility expected** | Low expanding | Vol expansion expected | Calendar spread | Rolling monthly | Debit − theta earnings |

---

## Rules of structure selection

1. **Match the thesis to the structure.** Don't force a bearish thesis into a bull call spread. Thesis → structure → Greeks, not the reverse.

2. **IV regime determines profitability.** In high IV, short vol (spreads, condors, sells). In low IV, long vol (long calls, long puts, calendars). Wrong regime = fighting the probabilities.

3. **DTE matters more than you think.** <14 DTE: gamma is violent, theta is extreme, vega collapses. Avoid unless move is imminent. >90 DTE: vega bloat makes small changes hurt; capital is tied up. Sweet spot: 21–60 DTE.

4. **Greeks must align with your thesis.** Long call thesis (bullish) = positive delta, positive gamma. Bear put spread thesis (mildly bullish income) = negative delta, short vega. If Greeks don't match, structure is wrong.

5. **Risk/reward must be ≥2:1.** On spreads, max profit must be ≥50% of max loss. On long options, target profit must be ≥2× debit. Lower ratio = pass.

6. **Theta and vega work together or against you.** Positive theta structures (spreads) are short vol; they profit when vol collapses and underlying stays put. Negative theta (long options) profit when underlying moves big. Know which you're fighting.

7. **Escalate to PM for advanced structures.** Iron condors, butterflies, diagonals require sign-off. PM must approve sizing and rolling plan upfront.

8. **Always have an exit plan before entry.** Profit target (50–75% of max profit). Loss stop (50–100% of max loss or spread width). Time stop (7 DTE close on spreads, 5 DTE on short premium). No exceptions.

---

## Common mistakes

**Mistake 1: Buying long calls in high-IV environments.**
- Vol is expensive; you're fighting theta decay from day one. Better to sell spreads or wait for vol to collapse.

**Mistake 2: Selling spreads in low IV.**
- Credit is tiny; risk/reward is bad (risking 3 to make 1). Pass until IV rank >50th percentile.

**Mistake 3: Holding spreads past 7 DTE.**
- Gamma acceleration, theta explosion, assignment risk, and vega blow-up are all at their worst. Close and move on.

**Mistake 4: Letting assignment happen by surprise.**
- Monitor your short legs closely in the final week. If ITM, either close or roll. Don't let a broker assignment create a forced position you didn't plan for.

**Mistake 5: Over-sizing complicated structures.**
- Butterflies and iron condors are high-probability but low-profit trades. Size them 50% of a simple spread. Complexity should reduce size, not increase it.

**Mistake 6: Chasing vol in the wrong direction.**
- Long options in collapsing vol, short options in rising vol. Fighting vol is expensive. Always be short vol in high-IV environments, long vol when IV is depressed.

**Mistake 7: No Greeks discipline.**
- Know your net delta, vega, gamma, theta before entry. If you can't explain why the Greeks are what they are, the structure is probably wrong.

---

## See also

- [[iv_regime_fit]] — which structures fit which IV percentiles (expanded matrix coming)
- [[pin_and_assignment]] — assignment risk protocols and pin-risk mechanics
- [[options_risk_principles]] — broader risk framework for options book
- [[pre_trade_checklist]] — Greeks questions (Q8–Q10) must be answered before PM approval
- Pricing tools: `compute_greeks()`, `compute_implied_vol()`, `compute_structure_greeks()`
