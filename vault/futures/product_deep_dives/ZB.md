---
type: product_deep_dive
symbol: ZB
sector: rates
analyst: Fund Engineer
updated: 2026-04-25T23:30:00Z
---

# [[ZB]] — CBOT 30-Year Treasury Bond

## Contract specs

- **Exchange / product code**: CBOT (CME Group) / ZB
- **Contract size / notional**: $100,000 face value of 6% notional coupon
- **Tick size / tick value**: 1/32 of a point (1 tick = $31.25 per contract)
- **Quote format**: Handles and 32nds (e.g., 132'16 = 132 and 16/32)
- **Contract months**: Quarterly; Mar, Jun, Sep, Dec; active in front 8 quarters
- **Session hours**: RTH 07:20–16:00 CT (pit close). Globex: 17:00 CT Sunday–16:00 CT Friday (23 hours)
- **First notice / last trading day**: First business day of delivery month; last trading day is last business day of delivery month
- **Settlement**: Physical delivery of US Treasury bonds with 15+ years to maturity (and ≤25.25 years to call). Coupon must be between 4% and 8%.
- **Margin** (Topstep): ~$2.2K initial, ~$1.7K maintenance (varies with volatility; confirm live). Note: roughly 2x ZT margin due to duration.
- **Contract grade**: Deliverable bonds are US Treasury securities maturing or callable in 15–25 years. CTD (cheapest-to-deliver) bond typically carries 20–40 bp invoice yield advantage vs. other deliverable issues.

## What it actually is

The 30-Year Treasury bond futures contract is the longest-dated, most-duration-sensitive US rates instrument traded on CME. It is a leveraged proxy for owning $100k notional of ultra-long-dated US government debt. The 30Y bond is operationally critical because:

1. **Inflation expectations anchor**: The 30Y yield is the market's consensus price for inflation + real returns over 30 years. It is far more sensitive to inflation surprises and regime shifts than the 2Y. A persistent inflation surprise (e.g., +50 bp CPI shock) can move 30Y yields 15–30 bp while 2Y moves only 5–10 bp.
2. **Pension and insurance hedge**: Pension funds and insurance companies manage liabilities 20–40+ years out; ZB is their primary hedge and duration tool.
3. **Curve structure trading**: ZB vs. ZT (30s2s spread) and ZB vs. ZF (30s5s spread) are the classic long-end curve trades. Steepening (30s flatten vs. long duration) and flattening (30s steepen) strategies live here.
4. **Real-yield and breakeven framework**: With inflation expectations (via breakevens), the 30Y yield can be decomposed into real yield + inflation premium. Traders use this to trade inflation vs. real growth.

## Primary drivers

Ranked by regime impact (2024–2026):

1. **Long-duration inflation expectations and breakeven inflation rates**: The dominant driver of 30Y yields. Inflation expectations 10–30 years out are priced into the 30Y breakeven (derived from TIPS spreads). A 25 bp rise in 30-year breakeven inflation expectation → typically 20–30 bp rise in 30Y nominal yield. This is a structural difference from the 2Y, which is dominated by Fed policy; the 30Y is dominated by long-term inflation regime assumptions.

2. **Fed terminal rate expectations (medium-term; 5–10 year horizon)**: While the 2Y prices near-term Fed moves, the 30Y is sensitive to where the market thinks rates will be in the long run. If Fed shifts guidance to "neutral real rates = 1.5%" vs. prior "1.0%", the long-end reprices up 10–20 bp. Current regime (2026): Market is debating whether secular stagnation (low neutral rate) or energy transition inflation (higher neutral rate) prevails; this is the 30Y debate.

3. **Real yield expectations (nominal yield − inflation expectation)**: Demand for real returns on ultra-long capital. In a low-real-yield regime (real yields −1% to 0%), the 30Y becomes a "carry play" (you get paid inflation + a small real carry). In a high-real-yield regime (real yields +2%+), the 30Y is unattractive vs. alternatives. A 25 bp drop in expected real yields → 30Y yields fall 15–25 bp.

4. **Long-dated growth and productivity expectations**: Over 30 years, economic growth assumptions matter. A structural productivity acceleration (e.g., AI capex boom → higher long-term growth) can justify higher real rates and steepen the curve. A recession fear or stagnation assumption → 30Y yields fall. Effect typically 5–15 bp over weeks.

5. **US Government debt supply and issuance**: The Treasury issues ~$4–5 trillion annually. Large supply announcements or auction concessions signal dealer stress; high concession → reduced demand for duration → 30Y yields rise. Conversely, deficit reduction or falling issuance → 30Y yields fall. Effect is usually 3–8 bp but can spike to 20+ bp in supply shocks.

## Key correlations

**Positively correlated:**
- [[ZT]] (2Y Note): 0.70–0.80 correlation (strong but weaker than ZT↔ZF). Both are treasury rates, but they move at different speeds. ZB leads ZT during inflation surprises; ZT leads ZB during Fed-policy-surprises.
- [[ZF]] (5Y Note): 0.85–0.95 correlation (very tight). ZB and ZF move together ~90% of the time. Divergence signals curve steepening/flattening (5s30s spread widening/tightening).
- [[Real yields (DFII30)]], inverse: 0.60–0.75 negative correlation. Lower real yields → higher ZB prices. Real yield expectations are the fundamental driver; when real yields drop 20 bp, ZB typically rallies 12–18 ticks.
- [[Inflation expectations (DFII30 breakeven)]], positive: 0.55–0.70. Higher expected inflation over 30 years → higher nominal yields → ZB weakness. When 30Y breakeven rises 20 bp, ZB typically falls 15–25 ticks.

**Negatively correlated:**
- [[ES]] / [[NQ]] (Equity index futures): −0.40 to −0.60 (moderate to strong negative in risk-off, decoupled in normal growth). In acute crises (e.g., March 2020, 2023 banking stress), equities plunge and ZB rallies sharply (flight-to-quality). In growth optimism, both can weaken (equities sell off on rate-hike fears; ZB also weakens).
- **DXY (Dollar Index)**: −0.25 to −0.35 correlation (weaker than ZT–DXY because long rates are more inflation-driven than policy-driven). Strong dollar can signal global deflation → ZB rallies; weak dollar can signal US inflation risk → ZB weakens.

**Lead/lag:**
- **CPI release (first Friday, 08:30am ET)** → ZB reaction is typically 2–5 min, but follow-through is stronger than ZT. A surprise +0.5% CPI → ZB falls 15–30 ticks intraday vs. ZT falling 5–10 ticks. Lead time: immediate (ZB is more reactive).
- **FOMC decision (14:00 ET)**: ZB reaction lags the initial spike slightly; the pivot/dot-plot language is parsed in ZT first, then ZB responds with larger magnitude. Typical delay: 5–15 min; then 30–90 min of trend.
- **Treasury supply announcements** (monthly): ZB is the most sensitive to supply news. Auction concession or issuance surge can gap yields 5–15 bp within minutes.
- **Equity volatility spikes (VIX >25)**: ZB rallies (flight-to-quality) within 5–10 min, often leading the ZT rally by a few minutes due to its duration sensitivity.

## Recurring patterns

**Seasonal:**
- **Jan–Feb**: Post-holiday rebalancing. Pension funds often rebalance to target duration weights in early January; heavy demand for long-duration hedges. ZB tends to outperform (rally) relative to ZT. Lower vol but trending.
- **Apr–May**: Tax-loss harvesting and Q1 earnings reports. Options expiration (monthly) can drive consolidation. Typically lower vol, few sustained trends.
- **June / December**: FOMC decision months. Post-decision, either strong directional move (especially if dot plot hawkish → ZB sells off hard) or consolidation. June: mid-year rebalance; December: year-end.
- **July–Aug**: Summer doldrums; lower volume, wider spreads. Fed balance-sheet runoff often continues; QT rhetoric can push 30Y yields higher. Algo-driven consolidation.
- **Sept–Oct**: Fiscal year-end for some institutions; rebalancing. Equity volatility often spikes (September effect). ZB typically rallies on risk-off. Fed Powell Jackson Hole speech (late Aug) often sets tone for autumn.
- **Nov–Dec**: Year-end positioning; hedge funds rebalance. Options expiry weeks can create pin-risk. Inflation worries (holiday season demand, supply-chain tightness) can hurt ZB. High vol.

**Event-driven:**
- **FOMC meetings (Tue–Wed, ~8 per year)**: Announcement at 14:00 ET. ZB can move 40–100 ticks intraday depending on dot plot surprise and forward guidance. If dot plot shows higher-for-longer terminal rates (vs. market expecting lower) → ZB sells off hard. If dovish surprise (lower terminal rate) → ZB rallies 50+ ticks.
- **NFP release (first Friday, 08:30am ET)**: Employment surprises don't move 30Y as sharply as 2Y, but strong employment (Fed wants to keep rates high longer) → ZB weakness 10–25 ticks. Weak employment (recession fears) → ZB strength 15–30 ticks.
- **CPI/PCE Core (monthly, first Friday and later)**: Inflation surprise is the #1 driver. Surprise +0.3% YoY → ZB down 15–30 ticks intraday. Surprise −0.2% YoY → ZB up 20–40 ticks. Larger moves than ZT.
- **PPI (Producer Price Index; second week)**: Leading indicator for future CPI; ZB reacts 5–15 bp on surprises.
- **Treasury Department Quarterly Refunding announcements** (mid-month: May, Aug, Nov): Announcements of Treasury issuance plans for next 6 months. If issuance rises sharply → 30Y yields rise 10–20 bp. If falls → yields fall 5–10 bp. Concession (dealer demand at auctions) is the real signal; high concession → yields rise.
- **Fed speakers (daily risk)**: Especially relevant if speaker talks long-term inflation, real rate philosophy, or debt sustainability. Less sensitive than ZT but can move 5–15 bp.

**Time-of-day patterns:**
- **Pre-open (07:20–09:30 CT)**: Overnight Globex action sets tone. European bond moves overnight can cascade. Lighter volume, 2–4 tick spreads. ZB often extends overnight trends from European session.
- **9:30–11:00 ET (Early US session)**: Core time for data releases (CPI 08:30 ET, NFP 08:30 ET). Volatility spike if data surprises. ZB reacts more violently than ZT to inflation data. Pit volume picks up.
- **11:00–14:00 ET**: Moderate vol; consolidation if no event. Dealers manage flow; tight bid-ask (1–2 ticks). ZB often more liquid than ZT in this window.
- **14:00–16:00 CT (FOMC decision window if applicable; else normal closing)**: If no event, typical closing action. Risk-on selling into close can weaken ZB. Last 30 min before Globex transition (17:00 CT) has light volume; spreads 2–3 ticks.
- **Overnight Globex (17:00 CT–06:00 CT)**: Lower volume; European economic data or ECB speakers. ZB can move 5–15 ticks on European surprises, then US session reverses half of it.

**Calendar quirks:**
- **Roll window** (10–15 days before contract expiry, last biz day of contract month): Front contract volume drops sharply; spread widens to 2–4 ticks. ZB rolls in typical contango (front month prices lower), so rolling is mechanically neutral.
- **Quarterly FOMC meetings (8 per year)**: Decision days create spike vol; ZB is more vol-prone than ZT due to duration. Avoid trading final 1 hour on decision days unless you're a volatility specialist.
- **Expiration Friday (last biz day of contract month)**: Very thin liquidity; avoid trading final 30–60 min.
- **Options expiry (3rd Friday of month; Quarterly on 3rd Friday of Mar/Jun/Sep/Dec)**: Long-dated options on ZB can create pin-risk around strike levels ±10 handles. Expect reversals 30–60 min before pit close on expiry days.

## Common setups

1. **Inflation-Proxy Long (Duration Long on Disinflation Signal)**
   - **Trigger**: CPI surprise −0.3% or more; Fed speaker pivots to "inflation is cooling"; breakeven inflation rates drop 15 bp or more; or real yields (TIPS spreads) fall sharply.
   - **Structure**: Long ZB outright, or long ZB / short ZT (curve steepener; isolates the long-duration inflation play).
   - **Invalidation**: Next CPI print hotter than expectations; Fed reiterates sticky-inflation concerns within 24 hours; real yields spike on recession-fear reversal.
   - **Exit**: Take profit at +30 to +50 ticks on outright. Or hold if steepener thesis is active (ZB outperforms ZT).
   - **Context**: Highest hit rate in the 3–10 days following a surprise disinflation print. Runs for 5–15 days before mean-reversion or next catalyst. Real-yield perspective is key; if ZB rallies but real yields widen, the trade may be short-lived.

2. **Curve Steepener (Long ZB / Short ZT or Long ZB / Short ZF)**
   - **Trigger**: 30s2s spread compressed to <250 ticks (narrow vs. historical avg of 300–350 ticks); market is pricing extended higher-for-longer at front-end, but long-end is oversold. Or: curve flattening exhaustion signal (after 4+ weeks of tightening).
   - **Structure**: Long 1 ZB / short 2 ZT (DV01-weighted for flattening protection). Or: long 1 ZB / short 1 ZF if expecting broader steepening.
   - **Invalidation**: Fed surprises hawkish (even longer higher-for-longer) → curve re-flattens as front-end reprices. Or: recession signals + flight-to-quality → entire curve rallies evenly, trade is flat.
   - **Exit**: Cover when 30s2s spread widens to 350+ ticks, or 30s5s widens to 200+ ticks. Or: stop at spread 200 ticks if thesis breaks.
   - **Context**: Works best in late-cycle / Fed-holding-pause scenarios. Historical hit rate ~50–55% if entered after at least 1 week of compression. Requires patience; steepening is slow.

3. **Real-Yield Play (Long ZB if Real Yields Fall Below Neutral)**
   - **Trigger**: Real yields (10Y TIPS yields or 10Y breakeven-adjusted nominal yield) fall below 0.5%; market is pricing near-zero real returns or negative real carry. Structural case: long-term inflation expectations are sticky, but real-rate expectations are collapsing.
   - **Structure**: Long ZB outright (or ZB pairs with 5Y/10Y TIPS if cross-asset play). Hold for weeks to months.
   - **Invalidation**: Real yields spike (productivity optimism, supply shocks reduce inflation, Fed raises rates again); or inflation expectations collapse (major deflation shock).
   - **Exit**: When real yields revert to 1.0%+ (take profit), or hold as structural hedge to long-duration liabilities.
   - **Context**: Lower edge, high noise. Works in regimes where real yields are suppressed (2010–2020, post-March-2023 banking crisis). Requires macro conviction.

4. **Curve-Flattener via Long ZB / Short ZF (If 30s5s Too Wide)**
   - **Trigger**: 30s5s spread widens beyond 200 ticks (ultra-wide, suggesting front-end oversold relative to long-end). Market pricing extended higher-for-longer at 5Y; ZB is relatively cheap.
   - **Structure**: Long 1 ZB / short 1 ZF (DV01-weighted). Isolates long-duration vs. intermediate-duration.
   - **Invalidation**: Fed surprised-hawkish → curve re-flattens as entire front-end reprices. Or: recession fears → flight-to-quality = entire curve rallies, trade is flat.
   - **Exit**: When spread tightens to 170 ticks (profit). Or stop at 230 ticks if thesis breaks.
   - **Context**: Least common of the 4 setups because 30s5s spreads are usually in equilibrium. Useful in extreme over-extension scenarios.

## Classic traps

1. **"ZB is the inflation hedge" trap**: Trader reads that ZB should rally on disinflation, enters long ZB on weak CPI surprise, but within 6 hours realizes the 30Y breakeven expectations anchored higher because Fed guidance shifted to "patient." ZB gives back 20 ticks as real yields revert. **Lesson**: Disinflation alone doesn't rally ZB; you also need Fed pivot signal and real-yield collapse. Wait for two confirms.

2. **Overnight gap risk on supply shocks**: Trader is short ZB, expecting strong data or Fed tightening. Treasury announces $50B issuance surge for next quarter. ZB gaps down 20 ticks at Globex open, forcing stop-out before US session. **Lesson**: Monitor Treasury supply announcements (Tue morning typically); size small overnight if supply cycle is unknown.

3. **Curve trade death by a thousand cuts (extended version)**: Trader is long ZB / short ZT to steepen 30s2s spread. Spread widens 5 ticks/day for 15 days. Trader exits break-even. Next day, Fed surprising dovish → spread widens 40 ticks and the trader left the table early. **Lesson**: Curve trades are high noise, low edge. Size small; use a tight stop (±2 handles on the spread). Don't force exits.

4. **Options gamma bleed on FOMC expiry**: Trader buys ZB calls (expecting rally on dovish surprise). FOMC day is options-expiry Friday. Market stays flat or sells off slightly. Gamma + theta losses erase 70% of premium despite being "right on the direction in the long term." **Lesson**: Never hold OTM options into expirations unless you're a specialist. Use spreads or front-month only.

5. **"ZB is liquid always" trap**: Trader assumes ZB can be sized as large as equities. In reality, front-month ZB averages 50–100K contracts/minute in peak hours; if you're trying to do 500+ contracts, slippage is 2–4 ticks vs. mid-price. Small position loses edge immediately. **Lesson**: ZB is liquid in small/medium sizes (1–20 contracts); for larger positions, scale in over 30+ min or use electronic algos.

6. **Inflation-path trap**: Trader thinks "inflation will be sticky; ZB should underperform." Misses that market is already pricing sticky inflation into breakevens; what matters is whether *actual* inflation surprises higher or lower than priced. If inflation comes in exactly as expected, ZB has no catalysts. **Lesson**: Trade the surprise, not the level. ZB rallies on disinflation *surprises*, not on low absolute inflation.

## Liquidity profile

- **Average daily volume (front month)**: ~80–200K contracts (liquid but less than ZT). Bid-ask spread: 1–2 ticks in normal sessions, 2–4 ticks in overnight or volatile news scenarios.
- **Open interest trend**: ~200–400K contracts across all expirations. Front contract carries 35–45% of total OI.
- **Pre-open (07:20–08:30 CT)**: Light; bid-ask 2–3 ticks. Volume under 2K contracts/minute.
- **Core session (09:30–14:00 ET)**: 0.8–1.5K contracts/minute average; spreads 1 tick.
- **Post-close (16:00–17:00 CT)**: Wind-down; 100–300 contracts/minute; spreads 2–3 ticks.
- **Overnight Globex (22:00–06:00 CT)**: 50–200 contracts/minute; spreads 2–4 ticks.
- **Post-FOMC (first 60 min after announcement)**: Very high volatility; bid-ask can spike to 3–5 ticks; volume 2–5K/minute.

## Options (if applicable)

- **Expirations**: Monthly (3rd Friday); Quarterly (Mar/Jun/Sep/Dec 3rd Friday); some weekly on Fridays (less active than ZT options).
- **Settlement**: American (exercise any time before expiry); settled into futures contract.
- **Typical IV rank range**: 25–65%, with spikes to 75+ around FOMC dates. Generally lower IV than ZT due to longer duration and less event sensitivity.
- **Greeks behavior**: Delta ≈ 0.7–0.8 for ATM calls/puts (due to convexity; ZB is more convex than ZT). Gamma is highest near expiration and at-the-money. Theta decay accelerates in final 7 days.
- **Pin-risk**: Minimal; assignment is into fungible futures. But pin-risk is more pronounced than ZT because long-duration moves create wider deltas; traders more likely to exercise early.
- **Diagonal/calendar spreads**: Long front-month ZB calls / short back-month calls can exploit term-structure; typical payoff in low-vol, stable-yield environments.

## Risk notes

- **Gap risk profile**: ZB is a government security with minimal default risk. Gap risk is *yield* gap (e.g., inflation surprise, supply shock, Fed pivot). Typical overnight gap on FOMC: 20–40 ticks. Rare tail event: 60+ ticks (e.g., March 2020, March 2023, unexpected supply shock).
- **Limit-up / limit-down mechanics**: CBOT ZB does not have hard price limits; continuous price discovery.
- **Worst weekly move (last 5 years)**: ~150–170 ticks (vs. ~130,000 tick price, ≈ 0.13% weekly, but that translates to 4%+ in yield terms). Occurred during March 2020 (Fed shock) and March 2023 (banking-crisis pivot).
- **Tail-risk events to remember**:
  - **March 2020**: Fed shock (cut to zero, QE unlimited). ZB initially sold off 40 ticks (yields up) on shock, then rallied 100+ ticks intraday as QE support became clear.
  - **March 2023**: SVB collapse + Fed pivot expectations. 30Y yields crashed 60+ bp intraday as investors priced in Fed pause. ZB rallied ~120–150 ticks in 24 hours.
  - **June 2022**: Fed raised rates 75 bp (surprise hike). ZB sold off 90+ ticks on the day as real yields spiked.
  - **Nov 2021–Mar 2022**: Inflation shock cycle (CPI prints 7.5%+). ZB sold off 200+ ticks over 4 months as inflation expectations repriced.
  - **Takeaway**: Tail events are inflation-surprises or Fed-pivot surprises. Size is paramount; ZB's leverage amplifies tail shocks.

## References

- **CME ZB contract page**: https://www.cmegroup.com/markets/interest-rates/us-treasuries/30-year-bond.contractSpecs.html
- **Federal Reserve calendar**: https://www.federalreserve.gov/monetarypolicy/fomccalendar.htm
- **Treasury Department auction schedule**: https://www.treasurydirect.gov/instit/instit.htm
- **FRED 30Y yield (DGS30) and TIPS 30Y real yield (DFII30)**: Economic data tracking for macro context.
- **Treasury bond supply and auctions**: https://www.fiscal.treasury.gov/reports-statements/auction-information/index.html
- **Reading**: "Fixed Income Framework" (Federal Reserve); "Long-Duration Bond Trading" (CME research); "Real Yield Analysis and Inflation Expectations" (various macro research).
