---
type: product_deep_dive
symbol: ZT
sector: rates
analyst: Fund Engineer
updated: 2026-04-25T21:45:00Z
---

# [[ZT]] — CBOT 2-Year Treasury Note

## Contract specs

- **Exchange / product code**: CBOT (CME Group) / ZT
- **Contract size / notional**: $200,000 face value of 6% notional coupon
- **Tick size / tick value**: 1/32 of a point (1 tick = $62.50 per contract)
- **Quote format**: Handles and 32nds (e.g., 104'08 = 104 and 8/32)
- **Contract months**: Quarterly; Mar, Jun, Sep, Dec; active in front 8 quarters
- **Session hours**: RTH 07:20–16:00 CT (pit close). Globex: 17:00 CT Sunday–16:00 CT Friday (23 hours)
- **First notice / last trading day**: First day of delivery month; last trading day is last business day of delivery month
- **Settlement**: Physical delivery of US Treasury 2Y notes with 1.75–2.00 year maturity
- **Margin** (Topstep): ~$1.2K initial, ~$900 maintenance (varies with volatility; confirm live)
- **Contract grade**: Deliverable into ZT are 2Y Treasury notes; CTD (cheapest-to-deliver) note typically carries 10–20 bp invoice yield advantage vs. others

## What it actually is

The 2Y Treasury note futures contract is a leveraged hedge/speculative instrument that mimics owning $200k notional of US 2-year debt maturing in ~24 months. It is the most liquid intermediate-duration US rates contract and sits at the shortest end of the Treasury curve that has a mature, deep futures market (10Y being the other benchmark). The 2Y is operationally critical because:

1. **Fed policy barometer**: The 2Y yield tracks FOMC expectations over the ~2-year window better than any single instrument. Markets price in cumulative Fed moves, inflation, and terminal rate expectations into the 2Y curve.
2. **Shortest-duration hedge**: For fixed-income managers, pension funds, and banks hedging 2–5 year liabilities, ZT is the instrument of choice.
3. **Curve steepening/flattening trades**: Basis traders and macro funds use ZT vs. ZF (5Y), ZB (30Y), and ultra (10Y) to trade curve structure.
4. **Front-running Fed communication**: ZT is often the earliest to react to economic data, Fed speakers, and inflation surprises that would change rate expectations.

## Primary drivers

Ranked by regime impact (2024–2026):

1. **FOMC expectations and terminal rate path**: The single dominant driver. Every FOMC meeting, dot plot revision, or Fed speaker comment moves the 2Y immediately. Forward guidance on the path to neutral/restrictive rates is priced into 2Y yields within 1–2 hours. Current regime (2026): Fed holding near 4.5–5.0%; market is modeling when cuts start and at what pace. Each 25 bp cut expectation shift = ~8–10 bp move in 2Y yield.

2. **Inflation data and real yields**: CPI releases (first Friday of month), PCE core (monthly), PPI (second week), wage data (payrolls first Friday) all move 2Y rapidly. ZT is sensitive to *expectations* of future inflation (not just current). Surprise inflation +0.3% YoY → 2Y yields typically up 5–10 bp intraday. 2Y real yield (yield − inflation expectation) is the "real" anchor; when inflation expectations drop 10 bp, 2Y yield typically falls 10–15 bp.

3. **Risk-off / risk-on sentiment and flight-to-quality**: During equity sell-offs or geopolitical shocks, treasuries rally (yields fall) as capital rotates into safety. ZT sees 10–30 bp rallies on "risk-off" days (e.g., banking crisis March 2023, geopolitical escalations). Conversely, strong earnings and macro optimism weaken 2Y (yields up 5–15 bp).

4. **10Y–2Y curve slope and expectations of future Fed action**: The 2s10s spread is watched obsessively; when it narrows (flattening), it signals either near-term Fed pauses or market pricing of recession. ZT tends to underperform ZF during flattening phases. When spread widens (steepening), ZT outperforms (2Y yields fall relative to 10Y).

5. **International capital flows and USD strength**: Safe-haven inflows from Europe or Japan into US Treasuries bid ZT; capital outflows following geopolitical de-escalation or rally in risk assets reduce demand. Effect is usually 3–5 bp daily, but can be 15–20 bp in crisis scenarios.

## Key correlations

**Positively correlated:**
- [[ZF]] (5Y Note): 0.85–0.95 correlation (very tight). Both are front-end rates; they move together ~90% of the time. Divergence signals curve steepening/flattening interest from traders.
- [[ZB]] (30Y Bond): 0.70–0.80 correlation (strong). Less tight than 2Y–5Y because long rates are more sensitive to inflation expectations and supply; 2Y is more fed-focused.
- [[US 10Y real yields (DFII10)]], inverse: 0.60–0.70 negative correlation. Higher real yields (inflation expectations fall or rates rise hard) → ZT weakness. Lower real yields → ZT strength.
- **DXY (Dollar Index)**: −0.40 to −0.50 correlation (moderate negative). Strong dollar environment typically coincides with Fed tightening (higher rates, lower ZT). Weak dollar = softer rates, higher ZT. Correlation is noisy in the short term but clear over weeks.

**Negatively correlated:**
- [[ES]] / [[NQ]] (Equity index futures): −0.30 to −0.40 during risk-off periods, +0.10 to +0.20 during normal growth conditions (confounded relationship). In a "Goldilocks" environment (moderate growth, no inflation shock), ZT and equities can move together (both weak on rate-hike fears). In acute crises, they decouple sharply (equities plunge, ZT rallies).
- **Breakeven inflation expectations (DFII5)**: When breakevens rise (inflation expectations ↑), real yields can stay flat or fall → ZT weakness. When breakevens fall sharply (deflation fears, demand shock), ZT rallies even if Fed is steady.

**Lead/lag:**
- **CPI release (first Friday, 08:30am ET)** → immediate 2–5 min reaction in ZT. Follow-through over next 1–2 hours if surprise is large (>0.3% miss or beat).
- **FOMC decision days (4–6 per year)**: 14:00 ET announcement → 1–2 min gap, then 15–30 min of chop as markets recalibrate, then trends in one direction for 30–120 min based on dot plot and language changes.
- **Fed speakers (daily)**: Comments move ZT by 3–8 bp over 30–60 min, especially if speaker is voting member and rate path is the topic.
- **Equity sell-offs / VIX spikes** → ZT rallies (flight-to-quality) within 5–10 min. Lead time: minimal, essentially simultaneous.

## Recurring patterns

**Seasonal:**
- **Jan–Feb**: Post-holiday rebalancing; Fed messaging often fresh from December FOMC. Higher volatility. ZT tends to be range-bound but reactive to data.
- **Apr–May**: Tax-loss harvesting and options expiration (monthly/quarterly) can drive consolidation. Typically lower vol, few multi-day trends.
- **June / December**: FOMC decision months (mid-month); elevated vol around the dates. Post-decision, either strong directional move or consolidation.
- **July–Aug**: Summer doldrums; lower trading vol, wider bid-ask in pit. Algo traders dominate; watch for sudden reversals on light volume.
- **Sept–Oct**: Fed balance-sheet runoff (QT) announcements; yield-curve control ends (if applicable). Sept historically volatile (equity vol).
- **Nov–Dec**: Year-end positioning; hedge funds rebalance, option expiry week (Fri before FOMC). High vol; watch for curve trades.

**Event-driven:**
- **FOMC meetings (Tue–Wed, ~8 per year)**: Announcement at 14:00 ET. ZT can move 20–50 bp intraday depending on surprise vs. prior expectations. If dot plot shows earlier cuts than market expected → ZT rallies (yields down). If hawkish surprise → ZT sells off (yields up). Post-meeting volatility often continues through next morning as positioning shakes out.
- **NFP release (first Friday, 08:30am ET)**: Employment data is the Fed's focus; surprise strong → rates up, ZT down. Surprise weak → recession fears → ZT up. Typical move 5–15 bp.
- **CPI/PCE Core (monthly, first Friday and later)**: Inflation surprise; see drivers section. Most impactful for ZT after FOMC.
- **Treasury Department auction announcements** (monthly: 2Y notes typically auctioned early month). Auction concession (bid-ask spread at auction) signals demand; if wide concession, dealers are lukewarm → ZT weakness into the auction. Post-auction, typically stabilizes or rallies.
- **Fed speakers (daily risk)**: Powell, Barr, other voting members' comments can shift 2Y by 5–10 bp if on-topic for rate policy.

**Time-of-day patterns:**
- **Pre-open (07:20–09:30 CT)**: Overnight Globex action carries through; if Europe/Asia had heavy ZT moves overnight, that sets the tone. Typically lighter volume, wider spreads until US data or open.
- **9:30–11:00 ET (Early US session)**: Core time for data releases (CPI 08:30 ET, NFP 08:30 ET). Volatility spike if scheduled data; otherwise consolidation.
- **11:00–14:00 ET**: Slower trade; algo participation. Can be choppy if waiting for FOMC or Fed speakers. Pit volume is moderate.
- **14:00–16:00 CT (Floor close prep / US equity close)**: Risk-on selling into close (equities close at 16:00 ET, Bonds at 16:00 CT). ZT often weakens 5–10 min before pit close. Last 30 min before Globex transition (17:00 CT) has light volume; wide spreads.
- **Overnight Globex (17:00 CT–06:00 CT)**: Lower volume; see overnight European data or Japan opens. Not primary trading session for US directional spec.

**Calendar quirks:**
- **Roll window** (10–15 days before contract expiry, last biz day of contract month): Front contract volume drops sharply; spread widens to 2–4 ticks. ZT rolls in contango most of the time (front month lower yield = front contracts worth more), so rolling is mechanically neutral.
- **Expiration Friday (last biz day of contract month)**: Very thin liquidity; avoid trading the final 30 min of the day.
- **Options expiry (Fridays before 3rd Wednesday of month)**: Long-dated options (Quarterly) can create pin-risk around key strike levels. Watch for gamma-driven reversals on ZT 30–45 min before pit close on expiry Fridays.

## Common setups

1. **Fed Pivot Trade (Duration Longs on Unexpected Rate-Cut Signals)**
   - **Trigger**: FOMC language shift from "higher for longer" to "patient" or "data-dependent"; or CPI surprise -0.2%+ vs. expectations; or Fed speaker hints at earlier-than-expected cuts.
   - **Structure**: Long ZT (either outright or long ZT / short ZF spread to isolate 2Y).
   - **Invalidation**: Fed reiterates hawkish stance within 24 hours; or next data (NFP, CPI) comes in hotter than expectations; or 2Y yields retake 5.00% level after piercing below 4.80%.
   - **Exit**: Take profit at +15 to +25 ticks on outright, or +5 ticks on spread. Or hold if curve steepening thesis is active (ZT outperform ZF).
   - **Context**: Highest hit rate in the 2–4 days post-FOMC. Often runs for 2–5 days before mean-reversion or next catalyst.

2. **Curve Flattener (Short ZT / Long ZF if 2s10s > 1.00%)**
   - **Trigger**: 2s10s spread widens above 1.20%, which is wide vs. historical avg of 0.80–1.00%; market is pricing extended higher-for-longer. Trader shorts duration at front-end, buys 5Y to flatten.
   - **Structure**: Short 2 ZT / long 1 ZF (DV01-weighted, ~1.5:1 ratio). Or outright short ZT if spread is extreme.
   - **Invalidation**: Recession signals → curve re-steepens as long-duration selling hits 5Y. Or Fed cuts faster than priced → curve steepens, trade is wrong.
   - **Exit**: Cover when spread narrows to 0.90% or lower (profit target). Or stop at spread > 1.40% if thesis breaks.
   - **Context**: Works best in late-cycle / overshoot scenarios. Historical hit rate ~55% if entered after at least 2 weeks of widening.

3. **Hedging Long-Duration Fixed-Income Book (Duration Reduction via Short ZT)**
   - **Trigger**: Portfolio manager holds 3–5 year average duration bonds and wants to reduce duration risk by 1–2 years; easiest hedge is short ZT.
   - **Structure**: Short 1 ZT per $500K–$1M notional of portfolio duration (rough rule; depends on exact duration of holdings).
   - **Invalidation**: Doesn't apply; this is a structural hedge, not a trade. Update ratio if rates environment changes significantly.
   - **Exit**: Maintain hedge until rates approach target neutral level or portfolio composition changes.
   - **Context**: Ongoing operational trade for institutional players; not a speculative setup.

## Classic traps

1. **"The Fed will cut soon" trap**: FOMC speaks dovishly (e.g., Powell says "data-dependent"), ZT rallies sharply. Retail traders buy the dip on ZT strength, then next CPI comes in hot, and the Fed re-iterated tightening vs. rate cuts. ZT breaks below the entry, and the trade unwinds at 40 ticks lower. **Lesson**: Don't front-run the Fed; wait for **two** data prints confirming the pivot, not one speech.

2. **Overnight gap risk around data**: ZT opens 08:30 ET with CPI or NFP data. If a trader is short ZT overnight (from Friday close) expecting data to be hot, and it misses by 0.5%, ZT gaps up 8–15 ticks at open, forcing a stop-out. **Lesson**: Size small overnight around known data dates, or don't hold through them.

3. **Roll period liquidity illusion**: Trader thinks ZT is liquid always (it is in the front month), but enters the back month (e.g., Sep ZT when front is Jun) and finds bid-ask is 2–3 ticks wide instead of 1. Slippage eats the edge. **Lesson**: Always trade the front contract in the roll window (first 10 days of delivery month).

4. **Curve trade death by a thousand cuts**: Trader is short ZT / long ZF to flatten the curve, but over 3 days, the curve widens slightly every day (−3 bp / day). After 15 days, the spread has moved 45 bp against the position. Trader takes a −20 tick loss on the structure before curve finally turns. **Lesson**: Curve trades are low-edge, high-friction. Size small. Use a tight stop (±5 ticks on the spread).

5. **Gamma bleed on options expiry**: Trader buys ZT calls (expecting rally) ahead of FOMC. Market stays flat on the move date, and time decay + gamma loss eats 50% of the position value despite no directional move. **Lesson**: Don't hold long-dated (>30 DTE) OTM options on ZT; they decay fast. Use spreads or shorter expirations.

## Liquidity profile

- **Average daily volume (front month)**: ~200–400K contracts (among the most liquid US rates futures). Bid-ask spread: 1–2 ticks in normal sessions, 2–4 ticks in overnight or news-driven scenarios.
- **Open interest trend**: ~700–900K contracts in aggregate across all expirations. Front contract carries 40–50% of total OI.
- **Pre-open (07:20–08:30 CT)**: Light; bid-ask can be 2–3 ticks. Volume under 5K contracts/minute.
- **Core session (09:30–14:00 ET)**: 1.5–2.5K contracts/minute average; spreads 1 tick.
- **Post-close (16:00–17:00 CT)**: Wind-down; 200–500 contracts/minute; spreads widen to 2–3 ticks.
- **Overnight Globex (22:00–06:00 CT)**: 100–300 contracts/minute; spreads 2–4 ticks.
- **Post-FOMC (first 60 min after announcement)**: Very high volatility; bid-ask can spike to 3–5 ticks; volume 5–10K/minute.

## Options (if applicable)

- **Expirations**: Monthly (3rd Friday); Quarterly (Mar/Jun/Sep/Dec 3rd Friday); some weekly on Fridays.
- **Settlement**: American (exercise any time before expiry); settled into futures contract.
- **Typical IV rank range**: 30–70%, with spikes to 80+ around FOMC dates.
- **Greeks behavior**: Delta ≈ futures sensitivity (∆ ≈ 1.0 for ATM calls); gamma is highest near expiration and at-the-money; theta decay accelerates in final 7 days.
- **Pin-risk**: Minimal in Treasury options because assignment is into fungible futures. Exercise/assignment is automatic; no illiquidity or delivery ambiguity.
- **Calendar spread trade**: Long front-month calls / short back-month calls (diagonal) can exploit term-structure; typical payoff in stable yield environments.

## Risk notes

- **Gap risk profile**: ZT is a government security with minimal default risk. Gap risk is *yield* gap (e.g., Fed announcement shifts expectations sharply, yields jump overnight, ZT price falls). Typical overnight gap on FOMC: 5–20 ticks. Rare tail event: 30+ ticks (e.g., March 2020, "Fed bazooka" surprise on both sides).
- **Limit-up / limit-down mechanics**: CBOT ZT does not have hard price limits; it is a contract that trades continuously. Price discovery is efficient.
- **Worst weekly move (last 5 years)**: ~75–80 ticks (vs. ~4,000 tick price, ≈ 2% weekly move). Occurred during March 2020 and March 2023 banking-crisis weeks.
- **Tail-risk events to remember**:
  - **March 2020**: Fed cut rates to zero and announced QE; ZT initially sold off (yields up, as long-duration was expected to suffer), then rallied 60+ ticks intraday as QE support kicked in.
  - **March 2023**: SVB collapse + regional bank stress; 2Y yields crashed 60 bp intraday as investors priced in Fed pause/pivot; ZT rallied ~100 ticks in 24 hours.
  - **June 2022**: Fed raised rates 75 bp (larger hike than expected); ZT sold off ~60 ticks on the day.
  - **Takeaway**: Tail events are Fed-policy-driven or financial-stability-driven. No amount of technical analysis predicts them; size is key.

## References

- **CME ZT contract page**: https://www.cmegroup.com/markets/interest-rates/us-treasuries/2-year-note.contractSpecs.html
- **Federal Reserve calendar**: https://www.federalreserve.gov/monetarypolicy/fomccalendar.htm
- **Treasury Department auction schedule**: https://www.treasurydirect.gov/instit/instit.htm
- **FRED 2Y yield (DGS2)**: Economic data tracking for macro context.
- **Reading**: "The US Treasury Market: Recent Trends and Structural Developments" (Federal Reserve).
