---
type: playbook
category: trading_strategies
applies_to: [analyst_livestock, portfolio_manager, risk_manager]
symbols: [LE, GF, HE]
updated: 2026-04-23
---

# Livestock — trading strategies

Products: [[LE]] live cattle, [[GF]] feeder cattle, [[HE]] lean hogs. See the [[livestock]] analyst prompt and product deep-dives.

**Critical warning**: livestock contracts have daily price limits. A limit move leaves stops unfilled. **Every strategy here assumes one limit move against you is possible; size accordingly.**

## 1. Cattle-on-Feed placement-fade

**One-liner**: After a bullish surprise in the monthly USDA Cattle on Feed report (placements < expected), fade the 2–3 day rally.

**Thesis**: Monthly Cattle on Feed (USDA NASS, Fridays after 3rd of the month) releases three key numbers: on-feed, placements, marketings. A bullish placements print (lower than expected = tighter 4–6 month future supply) produces a 2–3 day rally. But the impact is priced into the deferred contracts (Jun/Aug live cattle), and the front-month often reverses as the algo momentum fades.

**Trigger**:
- Placements print comes in > 1σ below consensus (bullish live cattle).
- Front-month LE rallies > 1.5% in the 2 sessions post-release.
- No concurrent bullish demand catalyst (packer margin, export surprise).

**Invalidation**:
- Packer margin shock (boxed beef cutout breaks to new cycle high).
- USDA revises placements upward in the next monthly print.

**Structure**:
- Short front-month LE (short-stock-only disallowed per firm rules — use bear call spread or long put).
- **Preferred**: bear call spread, DTE 15–30, strikes near resistance.
- Size: 50 bps of equity.

**Exit rules**:
- Target: retrace 50% of the post-release rally.
- Stop: new cycle high in front-month.
- Time stop: 10 sessions.

**Calibration**:
- Expected hit rate: 55%.
- Expected average R: +0.8 to +1.0.
- Historical: works in stable-demand regimes; fails during a beef demand shock year (2014 cycle peak).

**Common traps**:
- Sizing for an outright short — firm rule forbids naked short futures. Options structure only.
- Fading a placement surprise when boxed beef is also rallying — demand-side override kills the trade.
- Holding through next-month's report — placements revisions can reverse the thesis in 30 days.

---

## 2. Feed-cost transmission

**One-liner**: When corn (ZC) rallies > 10% in a month, short feeder cattle (GF) via option structure over 2–4 weeks — feed-cost squeeze on feeder breakevens.

**Thesis**: Feeder cattle are cattle not yet finished on grain feed. Their price is a function of live cattle forward price minus feed cost to finish. A sharp corn rally compresses the feeder breakeven; feedlots reduce placement bids; feeder prices fall over 2–4 weeks as the transmission works through. This is a slow, mechanical relationship — not a sentiment trade.

**Trigger**:
- Corn (ZC) rallies > 10% month-over-month.
- Live cattle (LE) has not rallied proportionally (< 5% MoM).
- Feeder cattle (GF) has not yet priced the compression (< 3% off pre-corn-rally level).

**Invalidation**:
- Corn reverses materially (> 5% down).
- Live cattle breaks out to new highs (offsets feeder breakeven compression).

**Structure**:
- Long GF put spread (defined risk), DTE 30–60, OTM strikes.
- Size: 50 bps of equity max-loss.
- Alternative: short feeder / long corn paired trade by DV01 — but firm rule blocks naked short GF.

**Exit rules**:
- Target: GF drops to feeder-breakeven (calculable from LE forward + new corn price).
- Stop: corn reverses > 5% OR LE rallies > 7%.
- Time stop: 45 sessions.

**Calibration**:
- Expected hit rate: 60%.
- Expected average R: +1.2.
- Historical: reliable during 2012 drought corn rally (feeder-cattle compression played out over 6 weeks, +2.5R).

**Common traps**:
- Timing — feeder doesn't respond to corn in lockstep; give the thesis 10+ sessions before judging.
- Ignoring pasture conditions — if pasture is abundant, some placements go to pasture instead of lot, partially offsetting.
- Limit moves — GF has daily limits; options structure naturally handles this better than outright futures.

---

## 3. Cold Storage divergence

**One-liner**: When Cold Storage report shows protein inventories rising faster than slaughter, position short the relevant deferred protein future.

**Thesis**: Monthly Cold Storage (USDA NASS, late month) reports ending inventories of beef, pork, and other proteins in refrigerated storage. A build in cold storage without a proportional rise in slaughter signals weak demand (distributors can't move product). This tends to weigh on the deferred contract as the excess inventory has to clear before new-production prices can rise.

**Trigger**:
- Pork or beef cold storage build > 5% MoM.
- Weekly slaughter is not rising proportionally (< 2% MoM).
- Export sales for the same protein are not surging.

**Invalidation**:
- Export data surges in the next weekly print (external demand clears inventory).
- Cold storage report is revised downward next month.

**Structure**:
- Short via long-put or bear-call-spread in the deferred contract (Jul/Aug for pork, Aug/Oct for cattle).
- DTE 45–75.
- Size: 50 bps of equity max-loss.

**Exit rules**:
- Target: price retraces to pre-build level.
- Stop: cold storage reverses in next monthly print.
- Time stop: 60 sessions.

**Calibration**:
- Expected hit rate: 55–60%.
- Expected average R: +1.0 to +1.3.
- Historical: reliable in post-COVID normalization period (2022–23).

**Common traps**:
- Ignoring holiday-demand seasonality — hams build before Easter, clear by Mar; not a bearish signal in Feb.
- Shorting the front-month instead of deferred — front-month moves on current slaughter, not inventory.
- Missing a concurrent disease outbreak reducing supply unexpectedly.

---

## 4. Grilling-season seasonal long

**One-liner**: Long live cattle (LE) via call spread entering mid-April, targeting Memorial Day through July 4 demand window.

**Thesis**: US retail beef demand peaks around the grilling-season holidays (Memorial Day, July 4th, Labor Day). The seasonal strength is well-documented; LE tends to rally into late May / early June historically. It's most actionable when combined with tight beef inventory (low boxed-beef cutout inventory ratio).

**Trigger**:
- Mid-April: boxed beef cutout ≥ 95% of 5-year high for the week.
- Cold storage beef inventory below 5-year range.
- LE has not yet broken out to new 30-day high.

**Invalidation**:
- Consumer spending or restaurant-traffic data weakens sharply.
- Retail beef prices signal demand destruction at the case.

**Structure**:
- Long LE call spread, DTE 60, strikes ATM/OTM.
- Size: 50 bps of equity max-loss.

**Exit rules**:
- Target: first week of July or +2R, whichever first.
- Stop: cutout weakens 10% from peak.
- Time stop: July 4th.

**Calibration**:
- Expected hit rate: 55%.
- Expected average R: +1.2.
- Historical: consistent 2015–2021; muted 2022–23 during inflation-driven demand softening.

**Common traps**:
- Entering too early (March) — April weakness on placements is normal pre-rally.
- Ignoring demand data — if retail is tightening, grilling rally doesn't materialize.
- Holding past July 4th — demand plateaus, supply catches up.

---

## 5. Disease-headline fade

**One-liner**: After a confirmed disease outbreak spike in livestock prices, fade the second-day rally via option structure — headlines compress faster than supply shock.

**Thesis**: Disease outbreaks (African Swine Fever, avian flu spillover, foot-and-mouth) produce immediate panic spikes. But actual herd impact takes months to show in slaughter data. The market routinely overshoots the first-day headline, then retraces 40–60% within 5–10 sessions as the immediate panic recedes and traders wait for supply confirmation.

**Trigger**:
- Confirmed outbreak headline drives a 5%+ spike day-1.
- Day-2 rally continues but volume fades by end-of-day.
- No follow-up confirmation of larger herd impact.

**Invalidation**:
- Second outbreak in a different region (escalation, not isolation).
- USDA issues a herd-size revision downward.

**Structure**:
- Bear call spread on the affected protein, DTE 21–30, sold above the day-2 close.
- Size: 50 bps of equity max-loss.

**Exit rules**:
- Target: 50% retrace of the outbreak-spike move.
- Stop: price makes a new high post-day-2.
- Time stop: 15 sessions.

**Calibration**:
- Expected hit rate: 60% (most outbreaks don't materially change supply in the near-term).
- Expected average R: +1.0.
- Historical: worked in 2014 PED virus (pork), 2022 avian flu headline.

**Common traps**:
- Fading a confirmed multi-region outbreak — that's a real supply shock, not a headline spike.
- Structuring as outright short (firm forbids).
- Ignoring the news flow after entry — escalation signals mean exit immediately.

---

## 6. Hog-corn ratio mean reversion

**One-liner**: Fade the hog-corn ratio when it's > 20 (super-profitable for producers) or < 12 (super-squeezed), targeting mean reversion to 14–16.

**Thesis**: The hog-corn ratio (HE price × 100 / ZC price, approximately) is a classic livestock-economics indicator. Historically oscillates 12–20. High ratios signal incentives for herd expansion (which produces more supply in 6–9 months = bearish hogs); low ratios signal herd liquidation (future supply tightness = bullish hogs). The cycle is slow but reliable.

**Trigger**:
- Ratio > 20: position for hog weakness (options structure) + corn strength.
- Ratio < 12: position for hog strength 6–9 months out (deferred hog longs).
- Confirm with producer-sow-herd reports (quarterly USDA).

**Invalidation**:
- Structural shock (disease, export ban) overrides cycle.
- Ratio breaks outside 10–24 range.

**Structure**:
- Paired or deferred hog options (HE deferred call spreads when positioning long, deferred put spreads when short).
- Size: 50 bps of equity.

**Exit rules**:
- Target: ratio back to 14–16.
- Stop: ratio extends beyond 10 or 24.
- Time stop: 90 sessions.

**Calibration**:
- Expected hit rate: 55%.
- Expected average R: +1.2.
- Historical: reliable in normal-demand regimes; fails during major shocks (Smithfield purchase, ASF pulse years).

**Common traps**:
- Ignoring the long cycle — this is a 2–4 month trade, not an intraday.
- Ignoring futures structure — front-month HE vs 3-month-out HE behave differently during cycle turns.
- Over-sizing — livestock is volatile enough that the slow cycle trade needs room.
