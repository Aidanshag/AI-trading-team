---
type: product_deep_dive
symbol: ZS
sector: grains
analyst: Fund Engineer
updated: 2026-04-25T23:30:00Z
---

# [[ZS]] — CBOT Soybeans (November Contract)

## Contract specs

- **Exchange / product code**: CBOT (CME) / ZS; equivalent unit = 5,000 bushels per contract
- **Tick size / tick value**: 0.25 cents per bushel; $12.50 per contract
- **Contract months**: Jan, Mar, May, Jul, Aug, Sep, Nov; November is the largest/most liquid; new-crop year cycles Aug→Nov.
- **Session hours**: RTH 09:30–13:15 CT (CBOT pit); Globex: 17:00 CT Sunday–17:00 CT Friday (nearly 24-hour, 15-min gap)
- **First notice / last trading day**: 7th business day of delivery month (Nov contracts expire mid-November); delivery is FOB elevator Chicago/Illinois
- **Settlement**: Physical delivery (soybeans, #1 or #2 yellow; moisture ≤13%) or cash settlement at CBOT settlement price
- **Margin** (Topstep): ~$1.5K initial, ~$1.1K maintenance (varies with IV; confirm live)

## What it actually is

CBOT soybean futures are the primary US price discovery mechanism for field soybeans, the critical oilseed crop that yields both soybean meal (livestock feed) and soybean oil (food + biofuel). One contract = 5,000 bushels (~140 metric tons). The US produces ~120M tonnes of soybeans annually (2nd after Brazil); US soybeans are globally significant (export-driven commodity). The Nov contract (new-crop) and Jan/Mar (old-crop forward) are most liquid. Soybeans compete directly with corn for US acreage — farmers choose between the two crops year-over-year based on relative profitability and expected returns. This acreage competition is central to ZS dynamics. Hedgers (farmers, crushers, food processors) use ZS to manage price risk; speculators trade it for macro exposure to global oilseed demand (China soy protein imports, EU biofuel mandates). The crush spread (ZS price vs. ZL + ZM, soybean oil + meal) is a key monitoring metric: high crush spreads indicate strong demand for the processed products, driving bean demand.

## Primary drivers

Ranked by impact in 2024–2026 regime:

1. **US planting intentions + acreage (USDA March/June)**: Farmers must choose between corn and soybeans. USDA Planting Intentions (mid-March) and Acreage (late June) releases drive the primary ZS moves each year. In recent years, soybeans have been more profitable per acre than corn (higher soybean futures prices relative to crop margins), pulling acreage from corn. Surprises >2% acreage vs. consensus drive 10–25 cent moves. Current acreage trend: 87–90M acres (vs. 84M in 2022).

2. **US crop condition + yield forecasts (weekly/monthly May–Oct)**: Weekly Crop Progress reports (May–Sep) track R1 (beginning bloom), R5 (beginning seed), R7 (beginning maturity), R8 (full maturity). Soybeans are more weather-sensitive than corn in Aug–Sep; heat, hail, or early frost during pod-fill can drastically cut yields. USDA WASDE monthly forecasts estimate yield; 2024 yields averaged ~50 bu/acre (vs. 49 bu/acre in 2023). Drought in key production areas (Iowa, Illinois, Minnesota) is the #1 risk.

3. **China demand + import flows**: China imports ~60–65M tonnes of US soybeans annually (80%+ of US soybean exports). Chinese livestock demand (pork rebuilding post-ASF swine fever, poultry growth) drives meal imports; crush margins in China determine bean demand. Trade wars, tariffs, and China's willingness to buy US beans (vs. Brazil or Argentina) is a major swing factor. 2024–2025 saw modest Chinese buying; any tariff escalation kills US export demand overnight.

4. **South American production (Brazil + Argentina)**: Brazil (global #1 producer, ~140M tonnes/yr) and Argentina (~50M tonnes/yr) compete with US supply. Brazilian harvest (Mar–Apr Southern Hemisphere season) is the primary swing event. Poor Brazilian yields (drought, disease) tighten global supply; strong Brazilian crops soften US soybean prices. Argentina weather (Dec–Feb, early season droughts) sets expectations for planted acreage. US beans often rally when Brazilian/Argentine crops look poor and vice versa.

5. **Soybean meal + oil crush dynamics**: ZS, ZL (soybean oil), and ZM (meal) are linked by the crush (grinding) process. When ZL (oil) rallies on biofuel mandates (EU, US biodiesel blending), the crush margin widens, driving bean demand. Conversely, weak meal demand (poor livestock profitability, weak export demand) narrows the crush, reducing bean value. Weekly EIA biodiesel and soybean oil data feed this dynamic. Monitoring ZL/ZM spreads vs. ZS is critical.

## Key correlations

**Positively correlated:**
- [[ZC]] (Corn): 0.65–0.75 correlation. Both are row crops competing for acreage; both tracked in USDA reports; both hit by weather. Acreage decisions are zero-sum (plant soybeans = less corn). When corn rallies sharply (drought, yield cut), soybeans often rally with it (same weather, same structural support). But in years where farmers favor soybeans (higher crush margins), soybeans can outperform corn.
- [[ZL]] (Soybean Oil) and [[ZM]] (Soybean Meal): 0.5–0.7 correlation (both processed from ZS). ZL is inversely sensitive to crude oil (biodiesel competes with ULSD, hence weak oil pressures ZL). ZM is livestock-feed sensitive (correlated with [[LE]], [[HE]]). When both ZL and ZM rally, ZS is bid up (crush margin widens). When one crashes (e.g., weak meal demand from pork producers), ZS is dragged down.
- [[ZW]] (Wheat): 0.4–0.5 correlation (moderate). All grains respond to global supply tightness and macro demand. But wheat is a distinct market (different geographies, different hedgers); correlation is looser than ZS-ZC.
- [[LE]] (Live Cattle) and [[HE]] (Lean Hogs): 0.25–0.4 correlation (weak-to-moderate). Soybean meal is a primary livestock feed. High ZS (high meal prices) pressures meat producer margins; inverse effect on livestock prices. Lag is 2–6 weeks (feed cost changes ripple through supply chains slowly).
- [[BVSP]] (Brazil Bovespa, proxy for LatAm risk sentiment): 0.3–0.45 correlation. Brazilian soybean harvest success and demand conditions affect Brazilian equities; LatAm crop weakness is bad for Brazilian economy; ZS falls alongside LatAm indices.

**Negatively correlated:**
- **US Dollar Index (DXY)**: −0.25 to −0.35. Stronger USD = cheaper US soybeans for foreign buyers; bearish. Weaker USD = more attractive US exports; bullish. Causal mechanism: USD driven by rates/growth; soybean demand partly driven by export competitiveness.
- **US 2Y real rates**: −0.3 to −0.4. Higher real rates = tighter conditions, lower growth, weaker livestock demand for meal, lower biofuel blending on low macro expectations. Bearish for ZS.
- **Crude oil (weak inverse)**: −0.15 to −0.25. Weak because soybean oil (ZL component) is pro-biofuel (biodiesel is crude-oil substitute). But if crude crashes, overall energy demand expectations fall, macro growth falters, ZL crashes, ZS is dragged down.

**Lead/lag:**
- USDA Planting Intentions (mid-March) → immediate move within 30 min; acreage expectations for soybeans set tone for months.
- USDA Acreage (late June) → second data point; usually lower volatility than March (expectations already set).
- USDA WASDE (monthly ~11am CT) → immediate 5–10 min move; yield revisions ripple for days.
- Brazilian harvest updates (Feb–Apr) → gradual repricing over 1–2 weeks.
- China tariff/purchase announcements → immediate shock; can gap overnight.

## Recurring patterns

**Seasonal:**
- **Spring planting (Apr–May)**: Weather risk on US plantings; delays = bullish. Farmers are deciding ZS vs. ZC acreage based on March prices and crush margins. If ZS has outperformed ZC in Feb–Mar, acreage shifts to soybeans, potentially capping upside in May. Weather in key areas (Iowa) often boosts volatility.
- **Summer pod-fill (Jun–Aug)**: Critical window for soybean yield. Heat stress during Aug pod-fill (90°F+ sustained, low rainfall) cuts yield sharply. USDA forecasts issued in Aug can surprise downward (yield cuts drive rallies). This is the highest-volatility 3 months.
- **Fall harvest (Sep–Oct)**: New-crop soybeans enter market (Brazil harvest ships first; US harvest Sep–Nov). Early harvest supply is bearish. But if Brazil's crop was poor, US beans are premium. Typical pattern: prices fall into US harvest (Sep–Oct weakness), then stabilize Nov when new-crop supply is clear.
- **Winter storage / forward contract (Nov–Mar)**: Old-crop ZS (contracts expiring before harvest) trade on storage/carry. Contango (forward > nearby) reflects storage costs. Winter is typically calmer unless China demand shocks emerge.

**Event-driven:**
- **USDA Planting Intentions (mid-March)**: Largest pre-season ZS event. Acreage surprises >2% move markets 10–25 cents.
- **USDA Acreage (late June)**: Final planted acreage confirmation; less volatile than March (expectations already priced).
- **USDA WASDE (monthly, ~11am CT)**: Yield forecasts issued. Summer WASDEs (Aug especially) can shock if yield is revised sharply.
- **Weekly Crop Progress (Thu evening May–Sep)**: Includes soybean development stages (R1, R5, R7, R8); used by the market to extrapolate yields.
- **Brazil harvest status (Feb–Apr)**: Early reports on Brazilian crop quality/volume; affects global soybean supply picture. Brazil's Jan–Feb weather determines S. America production.
- **China trade/tariff announcements**: Any policy shift affecting US soybean import tariffs can shock ZS overnight (2024 saw tensions; potential 2026 escalation is a tail risk).
- **Crush margin widening (ZL rallies, ZM weak)**: When soybean oil (ZL) rallies on biofuel mandates and meal (ZM) is steady or weak, the crush spread widens, signaling strong bean demand.

**Time-of-day patterns:**
- **Asia close (5:30am CT)**: Overnight Globex driven by China morning trade; if China demand signals emerge (purchase announcements), ZS can gap higher/lower. Most directional moves overnight occur post-China news.
- **9:30–11:30 CT (pit open)**: High volume; good fills. WASDE if released (11am CT) creates the largest single-day moves. First hour reaction to overnight news is reliable.
- **11:30–13:15 CT (pit close)**: Technical plays; lower momentum. Specs covering shorts into close if day has been bullish; possible reversal risk into 13:15.
- **Post-pit close (13:15–17:00 CT)**: Globex thins out; spreads widen to 4–6 cents. Avoid unless size is very small.
- **Overnight Globex (17:00 CT–09:30 next day)**: Very thin; wide spreads. Brazil developments, China announcements, macro shocks can gap markets 10–20 cents overnight.

**Calendar quirks:**
- **Roll window (7–10 days before FND)**: When trading Aug contract and expiry is 7 days away, volume shifts to Sep/Nov. Spreads widen. Contango (Sep > Aug) = pay to roll. Post-harvest (Aug–Oct), contango is normal. Pre-harvest (Mar–Jul), backwardation can appear if demand urgency increases.
- **Brazil harvest (Feb–Apr Southern Hemisphere)**: As Brazilian soybeans hit the global market (export surge Feb–Apr), ZS is typically under pressure; Brazilian production news is a key calendar item for ZS traders.
- **Contract roll into Nov (new-crop)**: In late Aug/early Sep, volume shifts from Aug to Sep to Nov (new-crop contract). This is the transition point where market reprices based on Sep harvest progress and Nov new-crop acreage expectations.

## Common setups

1. **Acreage surprise + structural follow-through (Planting Intentions, Mar 15)**
   - *Trigger*: USDA mid-March Planting Intentions reports soybean acreage. Surprise >2% vs. consensus (e.g., 89M acres expected, 91.5M reported = bullish surprise; less corn acreage pulled). ZS gaps at 11am CT.
   - *Entry*: Long if bullish surprise (more soybeans planted = more supply but also signals farmer preference = higher relative profitability). Entry at 2nd bar close above gap.
   - *Stop*: Gap low. Typical: 5–8 cents.
   - *Target*: Prior resistance (20-day high, round number). Structural moves often extend 15–30 cents over 2–5 days.
   - *Invalidation*: Close back through entry within 30 min = false signal.
   - *Hit rate*: ~60–65% (acreage surprises are binary, directionally reliable).

2. **Brazilian crop weather shock (Feb–Apr)**
   - *Trigger*: Brazilian weather forecast updates show drought/frost risk. ZS rallies in anticipation of lower Brazilian production. Market is long on US supply premium.
   - *Entry*: Short ZS if Brazil weather improves 5–7 days later (drought forecast lifted) after ZS has rallied 20+ cents. Shorts feel overly exposed on Brazil supply concerns now easing.
   - *Stop*: Above the rally high (8–12 cents).
   - *Target*: Entry or prior support; exit on daily close below 20-day MA.
   - *Invalidation*: Brazil weather turns worse again = short stops.
   - *Hit rate*: ~45–55% (Brazil weather fades are unreliable; some rallies are structural if production is truly cut).

3. **Crush spread realignment (ZL diverges from ZS)**
   - *Trigger*: Soybean oil (ZL) rallies sharply (biofuel demand, crude > $75/bbl), but ZS does not keep pace. Crush spread (ZS vs. ZL + ZM) is unusually wide; implied bean value is high relative to crush products.
   - *Entry*: Fade ZL weakness into crush-margin extremes. If ZL rallies 5% but ZS only 1%, short ZL (or buy ZS/sell ZL spread). Crusher demand for beans should equalize the ratio.
   - *Stop*: Above ZL rally high (5–8 cents for ZL).
   - *Target*: Prior ZL baseline or 20-day MA for ZL.
   - *Invalidation*: Crushers report weak margins; demand doesn't materialize; ZS falls.
   - *Hit rate*: ~50–58% (spread mean-reversion is structure-driven but slower to play out).

4. **WASDE yield revision fade (Aug WASDE in particular)**
   - *Trigger*: August WASDE cuts soybean yield forecast (e.g., 50.5 bu/acre → 49.8 bu/acre). ZS rallies 15–25 cents on structural tightness. Specs go long; commercials are sellers (farmers selling forward at higher prices).
   - *Entry*: Fade the rally (short) if price spikes >1% on WASDE and holds near highs 2–4 hours into close. Enter on close or next open at resistance.
   - *Stop*: Above WASDE high (6–10 cents).
   - *Target*: Entry or prior day close; exit on break of entry or on daily close below 20-day MA.
   - *Invalidation*: Yield cut is real; specs stay long; price continues higher next day.
   - *Hit rate*: ~48–55% (WASDE reversion is not automatic; depends on how much was pre-priced).

5. **China demand shock (tariff removal or trade deal)**
   - *Trigger*: US-China negotiations improve; tariff threats ease (or newly announced tariffs are imposed). ZS price reflects the tariff regime. If tariffs remove, US beans become competitive again vs. Brazil; ZS rallies on export demand.
   - *Entry*: Long ZS on trade deal announcement (if tariff removal) or fade ZS on tariff escalation (demand destruction). Entry on close of announcement day or next open if trend is confirmed.
   - *Stop*: Opposite high/low of move. Typical: 10–20 cents (trade shocks are large).
   - *Target*: Structural price level consistent with new tariff regime. Extended moves are common (25–40 cents) over 2–4 weeks.
   - *Invalidation*: Trade deal falls through; tariff reversal = stop.
   - *Hit rate*: ~55–62% (binary events; follow-through is reliable if catalyst is real).

## Classic traps

- **Brazil drought hype vs. late rains**: Market rallies ZS 20–30 cents on Brazilian drought forecasts. Brazil's rainy season extends through March; last-minute rains in Feb–Mar materialize, Brazilian crop survives, ZS collapses. Trap: holding longs too long into Brazilian late-season rains.

- **Crush spread compression illusion**: Soybean oil (ZL) has surged, making the crush spread appear wide and attractive (beans should rally). But ZL weakness is coming (biodiesel demand fades, crude weak). If you buy ZS expecting crush to support it, you get caught as ZL crashes and drags ZS down.

- **China tariff flip-flops**: 2024–2025 saw repeated tariff threats and walk-backs. Traders chase ZS on tariff removal news; then tariffs are re-imposed (just a negotiating tactic). Whipsawed traders exit at losses.

- **Acreage shift overestimation**: Farmers choose ZS over ZC in Mar because ZS crush margins look better. But by May, ZL (oil) has crashed due to weak biofuel demand, crush margins have collapsed, and ZS prices have fallen hard. Longs who bought the acreage shift get stopped.

- **Harvest supply dump**: Come Sep–Oct, Brazilian and US harvests flood the market. New-crop soybeans are abundant; ZS falls sharply. Traders holding summer longs expecting continued bull sentiment get crushed. Sep–Oct are typically the weakest months.

- **Weather forecast overhype (Aug heatwave threat)**: Model shows 95°F+ heat in Aug (critical pod-fill); ZS rallies 20+ cents in anticipation. 5 days later, the heat wave weakens in updated models, rainfall increases; ZS falls 15–20 cents. Trap: buying strength into uncertain weather forecasts.

- **Leverage + stop-hunting**: ZS is ~$12.50 per tick; a 10-contract position is ~$12.5k notional with 5–10x leverage. Overnight Globex can gap 15+ cents; tight stops get washed.

## Liquidity profile

- **Average daily volume** (front month, Nov contract): 180k–400k contracts in normal regime; peak >500k during USDA Acreage or WASDE. Contract-month dependent: Nov (new-crop) is most liquid; Jan (old-crop forward) is lighter but still tradeable.
- **Open interest trend**: ~400k–550k for Nov contract (new-crop); ~200k–300k for Jan (old-crop). Back months negligible for speculator liquidity.
- **Pre-open / post-close behavior**: Globex opens with wide spreads (4–8 cents); 9:30 CT pit open tightens to 1–2 cent spreads. Post-pit close (13:15 CT), Globex widens again (3–6 cents).
- **Best session for fills**: 9:45–13:00 CT (pit hours). Avoid 13:15–17:00 CT and overnight Globex unless size is small or slippage acceptable.
- **Bid-ask spread**: 1–2 cents normal during pit hours; 3–6 cents shoulder hours and Globex (tighter than corn due to soybean's smaller contract size, but good depth nonetheless).

## Options (if applicable)

- **Weekly expirations**: Mondays (expire Friday end of prior week). Popular for weather hedging during Aug pod-fill season.
- **Monthly expirations**: 3rd Friday of month. Lower volume than weeklies; wider spreads. Nov contracts see monthly options activity.
- **Settlement**: 9:30am CT Fridays (weeklies); 9:30am CT on listed expiration date (monthlies).
- **Typical IV rank range**: Planting season (Apr–May): 45–70th percentile. Summer pod-fill (Jun–Aug): 50–75th percentile (most volatile). Fall harvest (Sep–Oct): 30–60th percentile. IV spikes on WASDE or Brazil weather shocks.
- **Pin-risk behavior**: Monthly options near expiry can experience pin risk if strike is near ATM. Aug/Sep options can pin if strike is near WASDE expected level. Avoid short gamma on WASDE days if short calls/puts near-ATM.

## Risk notes

- **Gap risk profile**: Largest gaps occur on USDA data (Planting Intentions, Acreage, WASDE) and Brazil weather shocks. Typical gap: 5–10 cents; extreme gaps (>15 cents) on major acreage surprises or tariff announcements. Overnight Globex gaps to pit open average 1–3 cents unless overnight news (China tariffs, Brazil weather) is significant.

- **Limit-up / limit-down mechanics**: CME allows ZS to move 50 cents/day limit-up or limit-down (from prior settlement). If Brazil crop is destroyed by frost or US drought is catastrophic, ZS can limit-up for 2–3 consecutive days. No way to exit during limit-up; must wait for next day (risk). This is rare but possible.

- **Worst weekly move in last 5 years**: Feb 2022 (Russia-Ukraine invasion, export disruption): ZS rallied from 1350 → 1550 cents (+15%) in 2 weeks (global supply concerns). Aug 2023 (Brazilian drought scare, then rains): ZS gyrated 80+ cents over 3 weeks. Aug 2024 (delayed US plantings, Brazilian wet spring): volatility >100 cents for the month.

- **Tail-risk events to remember**:
  - **2012 Midwest drought**: Yield forecast cut from 42 → 30 bu/acre; ZS rallied from 1100 → 1700 cents (+55%) in 4 months.
  - **2022 Russia-Ukraine invasion (Feb)**: Export concerns; global supply tightens; ZS rallies despite US abundance (export premiums surge).
  - **Brazil freeze events**: Occasional late-season (Mar) frosts in Paraná state (major soy producer) can destroy crops; these are high-impact tail events.
  - **China tariff escalation (2024–2025)**: Trade war threats repeatedly shock ZS 20–30 cents intraday; volatility in tariff regime is a constant background risk.

## References

- **CME ZS contract specs**: https://www.cmegroup.com/markets/agriculture/grains/soybeans.contractSpecs.html
- **USDA NASS Crop Progress**: https://quickstats.nass.usda.gov/ (weekly reports May–Sep; includes R1, R5, R7, R8 development stages)
- **USDA WASDE**: https://www.usda.gov/webdocs/NewsReleases (monthly ~10th, 11am CT; includes yield, production, ending stocks)
- **USDA Planting Intentions**: mid-March report; Acreage report late June.
- **CONAB (Brazil's crop agency)**: https://www.conab.gov.br/ (Brazilian soybean production estimates; harvest timing Mar–Apr)
- **SAGyP (Argentina's agriculture ministry)**: Production estimates for Argentine soybeans.
- **USDA Brazil crop office**: Weekly updates on Brazilian harvest progress and estimates.
- **EIA soybean oil / meal data**: Weekly reports; crush margin calculations.
- **China customs tariff and import data**: Track US soybean export volumes and prices; tariff changes are signaled via policy announcements.
- **CME soybean futures prices/charts**: Real-time via broker; historical at CME Group website.
- **Key calendar dates**: Planting (Apr–May), Acreage (late Jun), WASDE (monthly), Brazil harvest (Feb–Apr), US harvest (Sep–Nov), Nov contract expiry (3rd week Nov).
