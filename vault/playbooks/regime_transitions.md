---
type: playbook
sector: macro
status: active
written: 2026-04-25
author: Fund Engineer
---

# Regime transition playbook

How to recognize and trade regime pivots. Applies to all sectors. Updated framework drawing from 2008–2020 historical case studies.

---

## What is a regime transition?

A regime is a persistent market state defined by:
- **Price structure** — trending vs. mean-reverting, directional momentum vs. chop
- **Volatility regime** — high/low/term structure shape
- **Correlation structure** — which assets move together and which don't
- **Macro anchor** — what macroeconomic state is pricing in (growth, stagflation, disinflation, deflation, financial stress, etc.)

A **regime transition** is when one or more of these dimensions shift structurally, not tactically. Examples:
- Fed pivot from hiking to cutting (2023) → equities re-price, duration outperforms
- China stimulus surprise (2023 midyear) → commodities spike, cyclicals re-rate
- Energy supply shock (2022) → inflation regime shift, term structure inverts
- Financial stress event (March 2023 banking) → safe-haven flows, curve flattens

**What regime transitions are NOT:**
- A 2–3% intraday swing in SPX
- A single data print that misses expectations
- A central banker saying something hawkish in a speech

Regime transitions have staying power (≥2–4 weeks) and repricing ripples across the entire market structure.

---

## Framework: Five steps to recognize a transition

### 1. Identify the macro anchor shift (the root cause)

Track five macro dimensions continuously:

| Dimension | Inputs | Signal of shift |
|-----------|--------|-----------------|
| **Growth** | ISM, jobless claims, PMI, corporate guidance, credit growth | PMI below 50 for 2+ months; ISM surprise -10 pts in one month |
| **Inflation** | CPI/PPI, wages, commodity prices, breakevens (DFII10, DFII5), expectations surveys | Breakevens rise 20+ bps; wage growth surprise +50 bps YoY |
| **Fed policy** | Fed funds target, dot plot, speech tone, QT/QE | Chair's Jackson Hole speech mentions "pause"; taper announced |
| **Financial stress** | Credit spreads (HY OAS, TED spread), USD VIX, TLT/IEF ratio, equity VIX | HY OAS widens 150+ bps in one week; VIX spike > 30 |
| **Geopolitical** | Conflict escalation, supply disruption, sanctions risk | Oil supply shock ≥1M barrels; sanctions announced on major economy |

**Rule: A regime transition candidate emerges when TWO of these dimensions shift in the same direction within 3–5 trading days.**

Examples:
- 2023-03-10: Banking stress (financial) + Fed pivot signal (policy) → transition candidate
- 2022-02-24: Geopolitical (Russia/Ukraine) + energy supply shock (commodity) → transition candidate
- 2023-08-20: China stimulus (growth anchor) + commodity rebound (macro theme) → transition candidate

### 2. Check price structure for confirmation (the market vote)

Once a macro anchor shift candidate emerges, check whether the *price structure* has begun to move. A price structure change requires:

**Equity indices (SPX, NQ, Russell):**
- Prior 20-day high/low broken with authority (>1% move through range)
- Intraday volatility spike (VIX ≥2 standard deviations above recent mean)
- Volume spike on directional days (>20% above 20-day average)

**Bond yields (10Y, 2Y, 5Y):**
- 20+ bps move in one direction in ≤3 days AND the move **sticks** (doesn't reverse next day)
- Curve shape change (2s10s or 5s30s narrows/widens by ≥10 bps)

**Commodities (CL, NG, GC, ag complex):**
- Sector breaks recent 30-day range with >2% daily move
- Stops getting run: buy-side/sell-side orders that held for 2+ weeks get trampled

**Dollar (DXY via 6E/6B/6J):**
- >1.5% move in ≤3 days
- Term structure inverts (far contracts move more than near) = structural shift

**Correlation:**
- Assets that were positively correlated for months turn negative (or vice versa)
  - Example: Tech (NQ) and bonds (ZB) normally move together in cutting cycles; if they invert, regime has shifted
  - Check SPX-TLT correlation; if flips from +0.3 to -0.5, regime candidate is real

**Confirmation rule:** If macro anchor shift is present AND price structure shows 2+ of the above, regime transition is 75%+ likely.

### 3. Project the new regime's character (what trades?)

Once you've confirmed a transition, define what the new regime likely looks like. Use historical analogs.

**Example regime transitions and their price mechanics:**

| Transition | Price Character | Trades Favored |
|------------|-----------------|-----------------|
| **Hiking cycle → Cutting cycle** | Yields fall, duration rallies, growth re-prices higher | Long TLT, buy dips in growth (NQ), reduce commodity hedges |
| **Stag → Disinflation** | Yields fall, equities chop, cyclicals underperform | Long bonds, short commodities, reduce size overall |
| **Deflation shock (financial crisis)** | Flight to safety, yield collapse, widening spreads, VIX spike persist for weeks | Long duration, avoid risk assets, size down dramatically, tight stops |
| **Inflation surprise** | Yields jump, term structure steepens, commodities lead, real assets outperform | Long commodities (CL, GC), short duration, reduce equity exposure |
| **China stimulus cycle** | Commodities spike, reflation trade, cyclical outperform, EM currencies firm | Long raw materials (copper, iron), long cyclical industrials, thin stops if growth revises down |

**Don't memorize all cases.** Instead: In the first 5 trading days of a transition, **identify which asset class is repricing fastest**. That's your leading indicator of the regime's character.

- Equities repricing fastest? → Growth/inflation expectation shift
- Bonds repricing fastest? → Real-rate or term-premium shift.
- Commodities repricing fastest? → Supply/demand or geopolitical shift.
- FX repricing fastest? → Rate-differential or risk-sentiment shift.

### 4. Size your entry (position trading, not day trading)

In a confirmed regime transition, **sizing follows a three-wave rule:**

**Wave 1 (Days 1–3 after confirmation):** 25% of intended size
- Regime transition is confirmed but price structure hasn't fully re-equilibrated
- Risk of false signal still ~25%
- Entry levels haven't found sustainable support/resistance yet

**Wave 2 (Days 4–10 after confirmation):** 50% of intended size
- New price levels hold; related assets are following (correlation moving as expected)
- Invalidation threshold is now clear; risk of wrong-regime-call has dropped to ~10%

**Wave 3 (Days 11–30 after confirmation):** 25% of intended size (optional)
- Only add if new regime is deepening (price structure extending, correlations staying inverted, macro anchor holding firm)
- If price structure shows exhaustion, skip Wave 3 and don't add

**Stops:**
- Wave 1 stop: Tightest — regime-confirmation invalidation level (e.g., if 2s10s curve inversion reverses 15+ bps, curve-flattening thesis dies)
- Wave 2 stop: Medium — break of the 20-day high/low in the direction opposite to your trade
- Wave 3 stop: Widest — break of the 50-day extreme in the opposite direction

**Position limit:**
- Regime transitions are structural bets, not tactical fades. Max position = 2–3R per side per sector
- If the bet goes to 2R profit, hold and let 1R ride; don't take it all off immediately

### 5. Invalidation: When to exit (regime didn't stick)

A regime transition is **invalid** when any of the following happen:

**Macro anchor reverts:**
- Fed re-signals hawkishness after 10 days of "cutting" pricing
- Inflation number comes in hot after deflationary data
- Geopolitical risk event resolves (e.g., OPEC supply cut canceled unexpectedly)
- China stimulus fades (no follow-up actions within 2–3 weeks)

**Price structure reverses:**
- The new price levels reverse by >50% without making a new extreme
- Correlation inversion flips back to pre-transition direction
- Volatility collapses suddenly (often a dead-cat-bounce warning)

**Related markets don't follow:**
- If equities transition to "growth rally" but commodities don't follow, regime is suspect; size down
- If bonds transition to "falling yields" but credit spreads widen, credit is front-running a growth problem; risk signal

**Exit rule:**
- If invalidation threshold is hit, exit the entire position **immediately**. Don't wait for Wave 2 or 3.
- If the regime transition fails in the first 5 days, take the loss and move on. False signals in regime transitions are expensive (can blow through stops fast).

---

## Case study: 2023 banking panic → pivot (March 10–April 15)

### Macro anchor shift (March 8–10)
- SVB fails (Friday, March 10)
- Credit Suisse deposit flight accelerates
- **Signal:** Financial stress widening + Fed policy scrutiny (is hiking stopping early?)

### Price structure confirmation (March 10–13)
- VIX spikes from 18 to 28 (Wednesday)
- SPX breaks 10-day lows by 2%; volume +40%
- TLT rallies 200 bps in 3 days (duration repricing)
- 2s10s curve flips from flat to +50 bps steepness
- **Confirmation:** Regime transition to "Fed pivot + financial stress" is live

### Regime character (March 13+)
- Bonds (TLT) lead; equities chop; growth sectors (NQ) underperform
- Dollar weakens (DXY -2.5% over 3 weeks)
- Commodity weakness (CL, NG fall)
- **Implied regime:** Cutting cycle + slowdown risk

### Trades (sized per three-wave rule)
- **Day 1–3:** Buy TLT 1R, short SPX 0.5R (size small; regime not settled)
- **Day 4–10:** Add to TLT long (+0.5R), hold short SPX, watch credit spreads
- **Day 10+:** Credit spreads stabilized by April 5; Fed signaled patience; **reverse to neutral**, take TLT profits, cover SPX shorts
- **Outcome:** 2R gain on TLT long; 0.8R loss on SPX short (closed early when regime signal weakened); net +1.2R

---

## Regime transitions by frequency and reliability

| Regime Transition Type | Frequency | Reliability | Time-to-resolution |
|---|---|---|---|
| **Fed policy pivot** (hiking → cutting or vice versa) | 1–2x per year | 90% | 4–6 weeks |
| **Geopolitical shock** (supply, conflict) | 1–3x per year | 75% (resolution uncertain, but repricing is real) | 2–8 weeks |
| **Financial stress event** (credit, systemic) | 0–1x per year | 80% | 3–6 weeks |
| **China stimulus** | 1–3x per year | 70% (often fades; government commitment varies) | 3–8 weeks |
| **Inflation/deflation pivot** | 0–1x per year | 85% | 6–12 weeks |
| **Sector supply shock** (energy, agriculture) | 2–4x per year | 60% (short-lived, reversal risk high) | 2–4 weeks |

**Lesson:** Fed pivot and financial stress regimes are your most reliable regime trades. Commodity supply shocks are noisier; size them half of policy-based trades.

---

## Rules for regime transition trading

1. **Never enter a regime transition trade without TWO macro anchors AND price structure confirmation.** One-anchor trades are speculation, not regime reads.

2. **The first 5 days are the most violent.** If your thesis is right, you'll feel pain but have conviction. If you're wrong, you'll know by Day 5. Don't hold losers past the invalidation threshold.

3. **Regime transitions are position trades, not day trades.** Hold winners for 2–4 weeks minimum. If you're day-trading regime bets, you're cutting profits short.

4. **Regime transitions reveal themselves in correlation flips.** Watch what didn't move yesterday move today. That's your confirmation.

5. **Related markets must follow for the regime to be real.** If one asset class reprices but others don't, the regime is fake or incomplete. Downsize.

6. **On invalidation, exit the entire position immediately.** Regime trades that fail can accelerate into your stop before you react. Be mechanical.

7. **During regime transitions, tighten stops and watch correlations live.** New regimes often flip hard in the first week as market positioning whipsaws.

---

## See also

- [[macro_framework]] — macro inputs and how they flow through the portfolio
- [[risk_officer_principles]] — position sizing and risk controls in regime transitions
- [[dealer_gamma]] — how dealer hedging accelerates regime moves
- [[position_sizing]] — how to size regime transition trades

