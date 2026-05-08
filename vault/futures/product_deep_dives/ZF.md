---
type: product_deep_dive
symbol: ZF
sector: rates
analyst: Fund Engineer
updated: 2026-04-25T03:15:00Z
---

# [[ZF]] — CBOT 5-Year Treasury Note

## Contract specs

- **Exchange / product code**: CBOT (CME Group) / ZF
- **Contract size / notional**: $100,000 face value of 6% notional coupon
- **Tick size / tick value**: 1/32 of a point (1 tick = $31.25 per contract)
- **Quote format**: Handles and 32nds (e.g., 108'16 = 108 and 16/32)
- **Contract months**: Quarterly; Mar, Jun, Sep, Dec; active in front 8 quarters
- **Session hours**: RTH 07:20–16:00 CT (pit close). Globex: 17:00 CT Sunday–16:00 CT Friday (23 hours)
- **First notice / last trading day**: First day of delivery month; last trading day is last business day of delivery month
- **Settlement**: Physical delivery of US Treasury 5Y notes with 4.75–5.25 year maturity
- **Margin** (Topstep): ~$2.0K initial, ~$1.5K maintenance (varies with volatility; confirm live)
- **Contract grade**: Deliverable into ZF are 5Y Treasury notes; CTD (cheapest-to-deliver) note typically carries 15–30 bp invoice yield advantage vs. others
- **Notional vs. ZT**: ZF is exactly half the contract size of ZT ($100K vs. $200K face value). This is by design — it provides intermediate duration exposure with tighter risk control.

## What it actually is

The 5-Year Treasury note futures contract is the intermediate-duration hub of the US Treasury curve, occupying the critical "sweet spot" between short-term Fed policy expectations (2Y) and long-term inflation/growth expectations (10Y+). The 5Y is the most-watched part of the yield curve because it embodies the market's view of the *normalized* policy environment after the current cycle. 

Why the 5Y matters:

1. **The "mid-cycle" barometer**: The 5Y reflects both near-term Fed policy (first 2 years) and medium-term normalcy (years 3–5). It's the contract traders use when they want to express a view that is **not** betting on immediate Fed action but rather on where rates will settle once the current tightening/easing cycle matures.

2. **Curve positioning hub**: Most curve trades (2s5s, 5s30s, 2s10s) pivot around the 5Y. Traders flatten by shortening ZF, steepen by buying ZF. The 5Y is the fulcrum.

3. **Options-heavy product**: ZF has a deep, liquid options market. Structured products (caps, collars, straddles) for real money investors are typically struck on 5Y yields, not 2Y or 10Y.

4. **Institutional hedging benchmark**: Pension funds and insurance companies hedging 3–7 year liabilities use ZF as their primary duration hedge. It's the "commercial grade" contract.

5. **Liquidity bridge**: ZF is less liquid than ZT but more liquid than ZB; it's the contract many traders use when ZT is congested or when they want intermediate risk exposure at a better fill.

## Primary drivers

Ranked by regime impact (2024–2026):

1. **FOMC expectations through the 2–5 year window**: Like ZT, the 5Y is highly sensitive to Fed policy guidance, but with a slightly longer duration. Surprise cuts signal → 5Y yields fall 10–20 bp. Surprise hikes → yields up 15–25 bp. The reaction is slightly muted vs. ZT because the market is pricing some "bounce-back" at the long end of the cycle.

2. **Term premium and duration appetite**: The 5Y sits at the sweet spot where institutional investors (pension funds, insurance, corporates) have active demand. When duration demand is strong (i.e., investors are risk-averse and willing to lock in yield), 5Y spreads tighten relative to the curve and ZF outperforms ZB. When duration is being sold (yield-seeking environment), 5Y yields spike relative to 2Y and 10Y, and ZF underperforms both.

3. **Inflation expectations (medium-term)**: While the 2Y is dominated by near-term inflation surprises, the 5Y is more sensitive to expectations about the *sustained* inflation level after the current cycle. PCE 5Y5Y breakeven (5-year inflation expectation, 5 years forward) is a key driver. If market reprices inflation higher for 2026–2031, 5Y yields will outperform (move higher faster than 2Y).

4. **Curve structure trades (2s5s, 5s30s spreads)**: When the 2s5s is wide (ZF weaker than ZT), curve traders buy ZF to flatten. When 5s30s is steep, traders short ZF to reduce long-duration duration. These relative-value trades create supply/demand imbalances in ZF that aren't purely driven by yield or Fed expectations.

5. **Foreign central bank action and USD carry trade flows**: Similar to ZT, but with a slightly longer duration window. ECB tightening or BOJ easing affects the carry-trade attractiveness of USD 5Y rates. Inflows from Japanese investors into 5Y US Treasuries can move ZF 5–10 bp. Outflows during risk-on rallies in JPY can move it similarly in the opposite direction.

## Key correlations

**Positively correlated:**

- [[ZT]] (2Y Note): 0.90–0.98 correlation (extremely tight). ZT and ZF move together 95%+ of the time. Divergence signals curve flattening/steepening interest from specialized traders.
- [[ZB]] (30Y Bond): 0.75–0.85 correlation (strong). ZF and ZB are both front-end relative to the full curve; they co-move on broad "risk sentiment" shifts. Less tight than ZT–ZF because long rates are exposed to longer-term inflation and supply shocks.
- [[US 5Y real yields (DFII5)]], inverse: 0.65–0.75 negative correlation. Higher real yields (inflation expectations drop or Fed is seen as restrictive long-term) → ZF weakness. Lower real yields → ZF strength.
- **DXY (Dollar Index)**: −0.35 to −0.50 correlation (moderate negative). Strong dollar reflects higher US real yields; weak dollar reflects lower yield differentials with G10. Effect is slightly less pronounced on ZF than ZT because ZF is intermediate-duration and less rate-sensitive.

**Negatively correlated:**

- [[ES]] / [[NQ]] (Equity index futures): −0.25 to −0.35 during risk-off periods, +0.05 to +0.15 during growth-optimistic regimes (confounded). ZF is duration; duration usually suffers when equities rally hard (risk-on, rates expected to rise). In crises, ZF rallies sharply as capital rotates into safety.
- **Commodity prices (CRB Index)** & breakeven inflation: When commodity prices spike (oil, grains, metals), inflation expectations rise, 5Y real yields can fall even if nominal yields rise → mixed effect on ZF. But historically, the correlation is mild (0.20 to 0.35) because commodity inflation is often transitory, and the Fed eventually offsets it with tightening.

**Lead/lag:**

- **CPI release (first Friday, 08:30am ET)** → immediate 2–5 min reaction in ZF. 5Y is more muted than ZT to CPI surprises because much of the CPI surprise is priced as transitory; longer-duration is more concerned with sustained inflation.
- **FOMC decision (4–6 per year)**: 14:00 ET announcement → immediate 1–3 min gap, then 15–45 min of repositioning as traders rebalance curve positions. ZF typically trades in 15–25 tick range on FOMC days (vs. ZT's 20–50 ticks).
- **Fed speakers**: ZF is slightly less reactive to speakers than ZT. A speaker discussing near-term policy is more important for ZT; a speaker discussing medium-term equilibrium rates is more important for ZF.
- **5Y inflation breakeven revisions**: When market reprices 5Y5Y inflation expectations, ZF can lead ZT by 30–60 min, especially on data where term premium shifts.

## Recurring patterns

**Seasonal:**

- **January**: Post-holiday rebalancing; pension funds and insurance companies adjust duration allocations. ZF often sees heavy flows (either buyers or sellers, depending on prior year's P&L).
- **March / June / September / December**: FOMC decision months. ZF volatility clusters around mid-month announcement dates.
- **April**: Tax-loss harvesting window; some fixed-income managers rebalance long-duration positions. Mild vol increase.
- **July–August**: Summer doldrums; lighter trading, but curve trades (2s5s, 5s30s) can still offer tactical edges.
- **September–October**: Fiscal year-end positioning for real-money investors (Jul 1 start for many US institutions); month-end rebalancing. Often see curve positioning shifts.
- **November–December**: Year-end; holiday trading thin, but dealer hedge ratios shift ahead of year-end financial reporting. Watch for gamma-driven reversals around key yields (e.g., 4.00%, 4.50%).

**Event-driven:**

- **FOMC meetings (Tue–Wed, ~8 per year)**: Announcement 14:00 ET. ZF can move 15–30 ticks depending on surprise. If dot plot shows earlier cuts → ZF rallies. If hawkish surprise → ZF sells off. Post-FOMC volatility is typically lower than ZT because curve traders are also recalibrating 2s5s and 5s30s spreads simultaneously.
- **NFP release (first Friday, 08:30 ET)**: Similar to ZT, but magnitude is 5–12 ticks on ZF vs. 10–20 on ZT. 5Y is less sensitive to near-term employment surprises.
- **CPI/PCE (monthly)**: Inflation surprise. ZF reaction is typically −0.5 to −1.0 times the size of ZT reaction, because term premium shifts more for intermediate duration than short duration.
- **5Y Treasury auction (monthly, early in month)**: The government auctions $32–38B of 5Y notes monthly. Auction concession (bid-ask spread) signals demand. Wide concession → weak demand → ZF weakness. Tight concession → strong demand → ZF strength. Post-auction, typically stabilizes.
- **Fed balance-sheet guidance (QT rate announcements, typically quarterly)**: If Fed signals faster runoff or changes, term premium adjusts → ZF can gap 5–15 ticks.

**Time-of-day patterns:**

- **Pre-open (07:20–09:30 CT)**: Overnight Globex action sets the tone. European yields often move during Asian hours; if European 5Y equivalent (Bunds) rallied overnight, ZF typically opens soft.
- **9:30–11:00 ET (Early US session)**: Data release window (CPI 08:30 ET, NFP 08:30 ET). ZF reaction is typically 5–15 ticks on surprises.
- **11:00–14:00 ET (Mid-session)**: Consolidation; algo trading dominates. Bid-ask spreads tighten to 1 tick. Lower intraday vol.
- **14:00–16:00 CT (Afternoon into pit close)**: If FOMC or major data is due, volatility picks up 30–45 min before announcement. Otherwise, slower trade. Equities close at 16:00 ET; often see 5–10 tick weakness in ZF into US equity close.
- **Overnight Globex (17:00 CT–06:00 CT)**: Very light volume; spreads 2–4 ticks. Asian and European economic data can move ZF 3–8 ticks overnight.

**Calendar quirks:**

- **Roll window (10–15 days before contract expiry)**: Front contract volume drops sharply; spread widens to 2–3 ticks. ZF typically rolls in slight contango (front month cheaper).
- **Expiration Friday**: Thin liquidity; avoid final 30 min. Options expiry (Fridays before 3rd Wednesday) can create gamma-driven reversals around key strikes.
- **Monthly auction days**: Government typically auctions on Monday–Thursday early in the month. Pre-auction, bid-ask can widen 1–2 ticks as dealers hedge.

## Common setups

1. **Flattener Trade (Short ZF / Long ZB if 5s30s > 1.50%)**
   - **Trigger**: 5s30s spread widens beyond 1.60–1.80%, signaling that intermediate and long duration are overvalued relative to history (avg is 1.20–1.50%). Trader believes this is cyclical and will compress.
   - **Structure**: Short 2 ZF / Long 1 ZB (roughly DV01-balanced). Or trade the outright if conviction is high.
   - **Invalidation**: Steep curve rally (equities plunge, flight-to-quality) → curve re-steepens as investors dump long bonds. Or economic data comes in surprisingly weak → Fed cuts faster → long duration outperforms.
   - **Exit**: Cover when spread compresses to 1.30% or lower (target). Stop at 2.10% if thesis breaks.
   - **Context**: Most reliable in late-cycle when yield curve is historically steep and 5–30 year rates are seen as overextended. Historical hit rate ~50–60% if entered after spread has been >1.70% for 3+ weeks.

2. **Curve Steepener (Long ZF / Short ZT if 2s5s < 0.40%)**
   - **Trigger**: 2s5s spread compresses below 0.35%, which is historically tight. Market is either pricing near-term Fed cuts (2Y outperforming) or is risk-averse. Trader buys intermediate, sells short-end.
   - **Structure**: Long 2 ZF / Short 1 ZT (DV01-weighted, ~2:1 ratio) to isolate the curve position. Or trade 5Y vs. 2Y in Treasury cash if more precise.
   - **Invalidation**: Fed re-iterates hawkish stance → 2Y outperforms again, spread re-compresses. Or recession signal → both 2Y and 5Y rally, curve stays flat.
   - **Exit**: Unwind when spread widens to 0.60%+ (target). Or stop at spread < 0.25% if thesis breaks.
   - **Context**: Works best in mid-cycle after curve has already flattened significantly (spread <0.50%). Typical edge is small (3–5 ticks profit on modest size).

3. **Duration Play on Fed Pivot (Long ZF on Surprise Dovish Signal)**
   - **Trigger**: FOMC signals more flexibility on cuts; or inflation data comes in meaningfully below expectations (−0.3% YoY surprise); or Fed Chair comments are notably less hawkish than prior guidance.
   - **Structure**: Long ZF outright. Or long ZF / short ZT spread if want to isolate the pivot (ZF rallies more than ZT on curve-steepening expectations).
   - **Invalidation**: Next data (NFP, CPI) comes in hotter than expected; Fed re-emphasizes hawkish tilt; 10Y yields blow out higher on supply concerns.
   - **Exit**: Take profit at +8 to +15 ticks (outright) or +3 to +6 ticks (spread). Or hold if curve-steepening thesis is active and durable.
   - **Context**: High probability in the 3–5 days immediately post-FOMC if announcement was dovish surprise. Often runs 5–15 ticks before mean-reversion or next catalyst.

4. **Institutional Hedging (Short ZF to Hedge Long Fixed-Income Portfolio)**
   - **Trigger**: Portfolio manager holds 3–7 year average-duration bonds; wants to reduce duration risk by 1–2 years. ZF is the natural hedge.
   - **Structure**: Short 1 ZF per $400K–$600K notional of portfolio duration.
   - **Invalidation**: Portfolio composition changes; rates approach desired neutral level.
   - **Exit**: Maintain until thesis is satisfied or rates environment fundamentally changes.
   - **Context**: Operational, ongoing trade for institutional players.

## Classic traps

1. **"Goldilocks" curve expectations trap**: Market is pricing soft landing + eventual Fed cuts. Both ZF and ZB rally together. Trader buys the dip on ZF expecting curve to steepen (5s30s to widen), but then economic data is mixed, and the Fed holds steady longer than expected. 5s30s doesn't widen; ZF underperforms ZB. Position shows −2 to −3 ticks loss despite directionally correct bet that yields should fall.  **Lesson**: Directional + curve-structure bets require two confirmations (not one). Don't assume curve will steepen just because yields fall.

2. **Auction concession whipsaw**: Heavy 5Y Treasury auction is announced; dealer concessions widen (bid-ask at auction is 2–3 ticks). Trader shorts ZF ahead of the auction expecting weakness post-auction. Auction results are strong; dealers buy the merchandise quickly; ZF rallies 5 ticks 30 minutes after auction. **Lesson**: Auction weakness is priced in 1–2 hours before. Shorting into the auciton is fighting institutional demand. Trade the post-auction bounce, not the pre-auction dip.

3. **Curve trade death by liquidity**: Trader enters short ZF / long ZB to flatten the 5s30s, but ZF is less liquid than ZT (smaller notional), and the trader's bid-ask slippage on entry is 1.5 ticks (vs. 1 tick on ZT). Spread doesn't move for 4 days, costing the trader −0.5 ticks per day in bid-ask bleed. After 3 days, the trade is underwater −1.5 ticks before it even starts working. **Lesson**: ZF is liquid, but not as liquid as ZT or ZB. For small accounts, trading 2s5s or 5s30s with ZF requires tight entry/exits. Use the cash market (STRIPS or Treasury bills) if available.

4. **Fed speaker misinterpretation on 5Y**: Fed Chair comments on near-term policy "patience" and ZT rallies 15 ticks. Trader assumes ZF should rally more (curve steepens on confidence in medium-term cuts) and buys ZF aggressively. But ZF only rallies 8 ticks because the market reprices term premium higher (longer uncertainty = premium demanded). Curve actually flattens, not steepens. **Lesson**: ZF and ZF move together, but ZF has an additional term-premium overlay. A short-term dovish surprise doesn't automatically steepen the curve; need explicit guidance on medium-term path.

5. **Roll-period slippage**: Trader is long ZF in Sep contract with 10 days until expiry. Bid-ask widens from 1 tick to 3 ticks. Trader tries to roll to Dec; Dec is liquid, but the bid-ask on Dec is also 2–3 ticks. Rolling costs 2–3 ticks (bid-ask on exit + entry). Over a year of monthly rolling, this accumulates to significant drag. **Lesson**: If planning to hold ZF positions over multiple months, roll proactively (not in the final roll window). Or trade ZB (higher notional, even better liquidity) if holding multi-month positions.

## Liquidity profile

- **Average daily volume (front month)**: ~150–250K contracts (strong, but notably lower than ZT's 200–400K). This is by design; ZF is smaller notional ($100K vs. ZT's $200K).
- **Bid-ask spread (normal session)**: 1–2 ticks in core hours (09:30–14:00 ET); 2–3 ticks in pre-open or post-close.
- **Open interest trend**: ~400–600K contracts in aggregate across all expirations. Front contract carries 35–45% of total OI.
- **Pre-open (07:20–08:30 CT)**: Light; 2–3 tick spreads. Volume <3K contracts/minute.
- **Core session (09:30–14:00 ET)**: 1K–1.5K contracts/minute; 1-tick spreads.
- **Post-close (16:00–17:00 CT)**: Wind-down; 150–300 contracts/minute; 2–3 tick spreads.
- **Overnight Globex (22:00–06:00 CT)**: 50–150 contracts/minute; 2–4 tick spreads.
- **Post-FOMC (first 60 min after announcement)**: High volatility; spreads 2–4 ticks; volume 3–5K/minute.

## Options (if applicable)

- **Expirations**: Monthly (3rd Friday); Quarterly (Mar/Jun/Sep/Dec 3rd Friday); weekly on some Fridays.
- **Settlement**: American (exercise any time before expiry); settled into futures contract.
- **Typical IV rank range**: 25–65%, with spikes to 75+ around FOMC dates. Slightly lower IV than ZT because ZF has lower yield sensitivity per tick.
- **Greeks behavior**: Delta ≈ futures sensitivity (∆ ≈ 1.0 for ATM calls); gamma peaks at expiration and ATM; theta decay is moderate (ZF options are slightly cheaper to hold than ZT options because notional is half).
- **Pin-risk**: Minimal in Treasury options; assignment is into fungible futures, no ambiguity.
- **Practical structure**: Long call / short call spread (bull call spread) is common for traders who want to express moderate upside with defined risk on 5Y curve steepening bets.

## Risk notes

- **Gap risk profile**: ZF is government-backed with minimal default risk. Gap risk is *yield* gap (Fed policy surprise overnight, yields reprice sharply). Typical overnight gap on FOMC: 5–15 ticks. Tail event: 25+ ticks (e.g., March 2020, March 2023 banking crisis).
- **Limit-up / limit-down mechanics**: CBOT ZF does not have hard price limits. Price discovery is continuous.
- **Worst weekly move (last 5 years)**: ~55–65 ticks (vs. ~11,000 tick price, ≈ 0.6% weekly move). ZF moves are typically 60–70% of ZT move size (because of lower yield sensitivity) and 40–50% of ZB move size (because ZB is longer duration).
- **Tail-risk events**:
  - **March 2020**: Fed cut rates aggressively + QE. ZF sold off initially (higher rates expected), then rallied ~50 ticks intraday as QE support materialized.
  - **March 2023**: SVB collapse + regional bank stress. ZF rallied ~65 ticks in 24 hours as investors repriced to expect Fed pause.
  - **June 2022**: Fed raised 75 bp (surprise size). ZF sold off ~40 ticks on the day.
  - **Takeaway**: Tail moves are Fed or financial-stability driven. Position size is critical for survival. Monitor Treasury auctions and debt ceiling events (wild cards).

## References

- **CME ZF contract page**: https://www.cmegroup.com/markets/interest-rates/us-treasuries/5-year-note.contractSpecs.html
- **Federal Reserve calendar**: https://www.federalreserve.gov/monetarypolicy/fomccalendar.htm
- **Treasury Department auction schedule**: https://www.treasurydirect.gov/instit/instit.htm
- **FRED 5Y yield (DGS5)**: Economic data for macro context.
- **5Y5Y inflation breakeven (T5YIFR)**: Key driver of 5Y real yields.
- **Reading**: "Duration and Term Premium in Sovereign Yields" (BIS Quarterly Review).
