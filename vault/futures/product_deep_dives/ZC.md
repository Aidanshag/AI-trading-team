---
type: product_deep_dive
symbol: ZC
sector: grains
analyst: Fund Engineer
updated: 2026-04-25T19:45:00Z
---

# [[ZC]] — CBOT Corn (December Contract)

## Contract specs

- **Exchange / product code**: CBOT (CME) / ZC; equivalent unit = 5,000 bushels per contract
- **Tick size / tick value**: 0.25 cents per bushel; $12.50 per contract
- **Contract months**: Mar, May, Jul, Sep, Dec; December is the largest/most liquid; new-crop year cycles Sep→Dec.
- **Session hours**: RTH 09:30–13:15 CT (CBOT pit); Globex: 17:00 CT Sunday–17:00 CT Friday (nearly 24-hour, 15-min gap)
- **First notice / last trading day**: 7th business day of delivery month (Dec contracts expire mid-December); delivery is FOB elevator Chicago/Illinois
- **Settlement**: Physical delivery (corn, #2 yellow; 0.5% maximum foreign material allowed) or cash settlement at CBOT settlement price
- **Margin** (Topstep): ~$1.3K initial, ~$950 maintenance (varies with IV; confirm live)

## What it actually is

CBOT corn futures are the primary US price discovery mechanism for field corn (animal feed, ethanol, industrial feedstock). The Dec contract (new-crop year) and Mar/May (nearby) are the most liquid. One contract = 5,000 bushels (~140 metric tons). The US is the world's largest corn producer (~370M tonnes/yr); corn is fundamental to US agriculture economics, livestock costs (beef, pork, poultry), ethanol fuel blending (10% of US gasoline supply), and export markets (China, Mexico, Japan as top buyers). Speculators trade it for macro agricultural risk exposure and mean-reversion in yield/acreage cycles. Hedgers (farmers, feedlots, ethanol plants, food processors) lock in input costs and output prices. Corn's price moves directly affect feeder cattle (GF), live cattle (LE), and lean hogs (HE) profitability via feed costs.

## Primary drivers

Ranked by impact in 2024–2026 regime:

1. **US planting intentions + acreage (USDA March/June)**: In March, USDA releases Planting Intentions survey (farmers report intended acres for corn, soybeans, wheat). June brings Acreage report (actual planted). These are the single largest corn events each year. Surprises of >2% acreage vs. consensus drive 5–15 cent moves. Post-2022 dynamics: farmers reduced corn acreage to plant soybeans (soy more profitable post-Ukraine). Expect acreage to range 85–90M acres (vs. 91M in 2021 peak).

2. **USDA crop condition + yield forecasts (weekly/monthly 2026–2027)**: Weekly Crop Progress reports (May–Sep) track planting %, silking %, maturity %, drydown %. Monthly WASDE forecasts (issued 10 days after month-end) estimate yield, production, ending stocks. Poor crop condition (droughts, flooding, disease) → lower yield → lower ending stocks → higher prices. 2024 saw robust yields (~172 bu/acre); drought risk heightens volatility May–Aug.

3. **Global supply-demand balance (ending stocks worldwide)**: If global corn ending stocks fall below 100M tonnes (4-yr low territory), markets price in structural tightness. China inventory changes, Black Sea supply disruptions (Ukraine), and Argentine production shifts move global prices. USDA's WASDE 10-day forecasts of world production/stocks are the primary data point.

4. **Crude oil and energy complex spillover**: Corn is 10% of US gasoline via ethanol mandate (E10 + E15 seasonal blend); crude oil near $70/bbl incentivizes ethanol crush margins. When crude rallies sharply, corn often rallies with a 1–3 day lag as ethanol demand/profitability rises. Weak oil caps corn upside (ethanol economics deteriorate).

5. **Macro demand signals (China growth, food inflation expectations)**: Recessions reduce livestock feed demand; deflationary macro pressures corn prices down. China represents ~20% of global corn demand; stimulus cycles or trade deals (US-China ag purchases) create demand swings. Post-Covid, China's demand for Brazilian corn substitution reduced US exports.

## Key correlations

**Positively correlated:**
- [[ZS]] (Soybeans): 0.65–0.75 correlation. Both are row crops competing for acreage, both tracked in USDA reports, both hit by weather/yield changes. In years of drought, both rally in sync. Soybean meal is livestock feed; when ZS rallies (meal up), ZC often rallies on feed-cost expectations.
- [[ZW]] (Wheat): 0.45–0.55 correlation (moderate). Both grains, both sensitive to weather. But wheat has separate supply dynamics (winter vs. spring, different geographies). Wheat is a global commodity; corn is more US-focused.
- [[LE]] (Live Cattle) and [[HE]] (Lean Hogs): 0.3–0.5 correlation (weak-to-moderate). Corn is a major input cost for feedlots (60%+ of finishing ration) and hog producers. High corn prices → lower profitability for meat producers; they hedge by shorting corn. But lag is 2–4 weeks (feed costs take time to flow through). Reverse causality: if LE rallies (demand surge), feedlots build inventory, increasing feed demand; corn rallies with lag.
- [[CL]] (Crude): 0.25–0.4 correlation (weak-to-moderate). Oil > $70 supports ethanol crush; corn rallies. Oil < $50 kills ethanol economics; corn is pressured.
- [[DXY]] (US Dollar Index): −0.2 to −0.3 (weak negative). Stronger dollar = cheaper US corn for foreign buyers; bearish. But correlation is loose because commodity prices and USD are driven by overlapping macro forces (rates, real yields), not direct causation.

**Negatively correlated:**
- **US 2Y real rates (DGS2 − inflation breakeven)**: −0.3 to −0.4. Higher real rates = tighter financial conditions, lower growth expectations, reduced feedlot demand. Corn is pro-cyclical.
- **US equity indices (SPX, NDX) during recession signals**: −0.15 to −0.25 (weak). In severe recessions (2008, 2020), livestock demand and biofuel blending drop; corn crashes. But in bull markets, the correlation is near-zero because commodity and equity drivers diverge.

**Lead/lag:**
- USDA Planting Intentions report (mid-March) → move within 30 min; effects ripple 2–3 days as specs adjust.
- USDA June Acreage → similar impact.
- USDA WASDE (10 days after month-end at 11am CT) → immediate 5–10 min move, extended impact through week.
- Weather forecasts (6–10 day outlooks May–Aug) → gradual repricing 2–4 days ahead.

## Recurring patterns

**Seasonal:**
- **Spring planting (Apr–May)**: Weather risk peaks. Delayed plantings (wet fields) boost bull sentiment; rain rallies the market. Cool, wet springs in Iowa/Illinois cause anxiety. Historically, April–May see highest intraday volatility.
- **Summer growing season (Jun–Aug)**: Kernel development (pollination + grain fill). Droughts or floods during this window → yield destruction → sharp rallies. Weather forecasting models (6–10 day outlooks) are critical. Heat stress during pollination (late Jun/early Jul) is most dangerous.
- **Fall harvest (Sep–Oct)**: New-crop supply enters market; bearish pressure. Yields realized. Dec contract (new-crop) typically is cheaper than Dec of prior year if yields are good.
- **Winter storage (Nov–Mar)**: Farmer/elevator selling ramps down; commercial stocks drawn. Price typically reflects storage costs + carry (contango). Old-crop vs. new-crop spread reflects storage economics.

**Event-driven:**
- **USDA Planting Intentions (mid-Mar)**: Largest pre-season event. Acreage estimates for corn, soybeans set market direction for months.
- **USDA Acreage report (late June)**: Final acreage report; more accurate than March intentions but lower vol (expectations already priced).
- **USDA WASDE (monthly, ~11am CT)**: Weekly Crop Progress (Thu evenings May–Sep) = market-moving; includes yield forecasts mid-season.
- **Ethanol crush spreads (corn vs. ethanol + DDGS)**: When ethanol rallies (energy demand), crush spreads widen; corn demand surges. CNH Industrial (Case, New Holland) demand for farm equipment can indirectly signal farmer sentiment.
- **China trade flows and tariff changes**: 2024–2025 have seen US-China agri tensions. Tariff announcements → sudden demand shock.

**Time-of-day patterns:**
- **Asia close (5:30am CT)**: Globex overnight trades driven by Asian demand signals; minimal direct US impact; wide spreads.
- **9:30–11:30 CT (pit open + first hour)**: High vol, good fills. Often reverses overnight action or reacts to WASDE if released.
- **11:30–13:15 CT (pit close approach)**: Technical support/resistance plays; less directional momentum. Volume drops near pit close (13:15).
- **Post-pit close (13:15–17:00 CT)**: Globex only; wider spreads; lower volume. Not primary trading window.
- **Overnight Globex (17:00 CT–09:30 CT next day)**: Very thin; wide spreads (3–5 cents); if news drops, overnight Globex can see sharp gaps.

**Calendar quirks:**
- **Roll window (7–10 days before FND of nearby month)**: If trading Mar contract and expiry is 7 days away, volume/interest shifts to May. Spreads widen. Contango (May > Mar) = pay to roll; backwardation (May < Mar) = get paid to roll. Post-harvest (Sep–Dec), contango is normal (carry costs). Pre-harvest, backwardation can appear if supply concerns emerge.
- **Harvest-driven supply (Sep–Nov)**: New-crop corn floods market; Dec contract sees selling pressure from farmers + elevators taking delivery on old-crop, selling new-crop forward. Typical pattern: Sep–Oct are the weakest months.

## Common setups

1. **USDA acreage surprise + month continuation**
   - *Trigger*: USDA Planting Intentions or Acreage report shows acres >2% vs. consensus (e.g., 87M expected, 89M reported = bullish surprise). Price gaps at 11:00am CT.
   - *Entry*: Long if surprise is bullish (fewer acres = less supply) and price holds above gap by 2nd 5-min bar. Short if bearish (more acres).
   - *Stop*: Gap low/high. Typical: 4–8 cents.
   - *Target*: First technical resistance (often prior daily close, 20-day MA, or next round number); 1:2 to 1:4 RR typical.
   - *Invalidation*: Close back through entry within 30 min (reversal of surprise sentiment).
   - *Hit rate*: ~58–62% in 2023–2024 samples. Acreage surprises are structural; follow-through is reliable.

2. **Weather rally fade (8–4 days before heat event)**
   - *Trigger*: Extended forecast shows drought or heat stress window (late Jun/early Jul, kernel-fill stage); ZC rallies 15+ cents over 3 days on fear.
   - *Entry*: Sell (short) if price shows exhaustion intraday (Bollinger Band touch, divergence on MACD). Setup often develops Tue–Wed with heat expected Fri–Sun.
   - *Stop*: Above the high of the rally. Typical: 6–10 cents.
   - *Target*: Recent baseline (before rally); exit on daily close below 20MA.
   - *Invalidation*: Forecast updated to show even worse heat = short stops.
   - *Hit rate*: ~45–52% (fades often fail; requires discipline; weather can shift; some rallies are structural). More reliable if rain forecast also increases likelihood of cooling.

3. **Post-WASDE reversion (yield revisions)**
   - *Trigger*: WASDE releases; USDA cuts yield forecast (e.g., 170 bu/acre → 168 bu/acre). Market rallies on the cut, then fades next day as specs lock in.
   - *Entry*: Fade the rally (short) if price spikes >1% on WASDE and holds near highs into close. Enter on close or next open.
   - *Stop*: Above WASDE high (5–8 cents typical).
   - *Target*: Prior day close or recent support; exit on break of entry.
   - *Invalidation*: Market continues higher on second day = yield cut was structural.
   - *Hit rate*: ~48–55% (reversion is not guaranteed; some WASDE cuts are real catalyst changes).

4. **Crush spread positioning (corn vs. ethanol)**
   - *Trigger*: Ethanol rally (crude > $75/bbl, E-d spread widens, crush margin >$2/bushel profit); feed demand surges; ZC should trade rich to fundamentals.
   - *Entry*: Long ZC on weakness within an uptrend (20-day MA above 50-day MA) if crush margin signals >$1.50 opportunity.
   - *Stop*: Below 20-day MA. Typical: 5–8 cents.
   - *Target*: Recent resistance or macro high; hold as long as crush margin >$1/bushel.
   - *Invalidation*: Crude crashes below $60 = ethanol economics killed.
   - *Hit rate*: ~55–60% (structure-driven; correlations stable).

## Classic traps

- **WASDE expectations vs. reality**: Market often prices in an acreage/yield cut weeks before WASDE via rumors. When WASDE prints in line with expectations, price fades (sell the news). Trap: buying strength into WASDE release.

- **Weather hype fade**: A dry forecast 10 days out creates bull sentiment; traders buy. By day 5, if forecast moderates (some rain in updated models), sellers emerge. Overnight shorts get crushed; intraday fades fail.

- **Harvest supply dump**: Come September, farmers rush to harvest and sell. New-crop supply is abundant despite higher prices from summer. Many longs hold into Sep expecting continued highs; sharp sell-off in first 2 weeks of Sep catches them off-guard. Seasonal weakness (Sep–Oct) is real.

- **Crush margin mirage**: Ethanol crush looks profitable on paper ($2/bushel); trader longs ZC expecting demand surge. But crush margin already reflected in ethanol price; ZC doesn't move higher. Or: margin looks terrible, trader shorts ZC; but crushers already reduced production, demand falls less, ZC stabilizes.

- **China demand whipsaw**: Trade-war rumors, tariff announcements, or policy shifts can flip corn demand overnight. Longs holding into expected Chinese purchases get stopped when deal falls through. Short-covering rallies can be equally violent.

- **Leverage + stop-running**: ZC is ~$12.50 per tick; a 10-contract position is ~$12.5k notional with 5–10x leverage. Round-number stops (e.g., 370, 380, 400 cents/bushel) get hunted. Intraday stops on tight retracements (3–5 cents) are vulnerable.

## Liquidity profile

- **Average daily volume** (front month, Dec contract): 150k–350k contracts in normal regime; peak >500k during WASDE or acreage events. Contract-month dependent: Dec (new-crop) is most liquid; Mar/May (old-crop) are lighter.
- **Open interest trend**: ~300k–450k for Dec contract; lighter in May (~150k–250k). Back months negligible for speculator liquidity.
- **Pre-open / post-close behavior**: Globex opens with wide spreads (4–8 cents); 9:30 CT pit open tightens to 1–2 cent spreads. Post-pit close (13:15 CT), Globex widens again.
- **Best session for fills**: 9:45–13:00 CT (pit hours). Avoid 13:15–17:00 CT and overnight Globex unless size is small and slippage acceptable.
- **Bid-ask spread**: 1–2 cents normal during pit hours; 3–5 cents shoulder hours and Globex.

## Options (if applicable)

- **Weekly expirations**: Mondays (expire Friday end of prior week). Popular for short-dated directional plays on weather/data events.
- **Monthly expirations**: 3rd Friday of month. Lower volume than weeklies; wider spreads.
- **Settlement**: 9:30am CT Fridays (weeklies); 9:30am CT on listed expiration date (monthlies).
- **Typical IV rank range**: Planting season (Apr–May): 50–75th percentile. Summer growth (Jun–Aug): 40–65th percentile. Fall/winter: 20–50th percentile. IV spikes on WASDE or acreage shocks.
- **Pin-risk behavior**: Monthly options near expiry can experience pin risk if strike is near ATM. Avoid short gamma near WASDE/Acreage if short calls/puts near-ATM.

## Risk notes

- **Gap risk profile**: Largest gaps occur on USDA data (Acreage, WASDE). Typical gap: 3–6 cents; extreme (>10 cents) on supply surprises. Overnight Globex gaps to pit open average 1–3 cents. Weather forecasts (6–10 day models updating daily) can gap overnight markets if model drastically changes (e.g., drought signal emerges).

- **Limit-up / limit-down mechanics**: CME allows ZC to move 40 cents/day limit-up or limit-down (from prior settlement). In severe droughts (1988) or massive supply shocks, ZC has limit-up for multiple days. Once limit-up hits, trading halts; no way to exit except wait for next day.

- **Worst weekly move in last 5 years**: Aug 2021 (Midwest drought): ZC rallied from 490 → 550 cents (+12%) in 4 weeks. Aug 2023 (flooded fields + replanting): ZC lost 25 cents in 1 week (harvest relief). 2022 post-Ukraine: ag exports surged; ZC rallied 15% in 2 weeks.

- **Tail-risk events to remember**:
  - **1988 Midwest drought**: Temperatures exceeded 95°F for sustained period; ZC rallied >100% in months (limit-up for days).
  - **2012 drought**: Yield forecast cut from 147 → 123 bu/acre; ZC rallied from 530 → 810 cents (+53%) in 6 months.
  - **2022 Ukraine shock**: Exports cut; global supply tightens; ZC rallies despite US abundance (export margins surge).
  - **2023 Midwest wet spring**: Delayed plantings, replanting panic; ZC volatile May–Jun (ultimately not structural as June improved).

## References

- **CME ZC contract specs**: https://www.cmegroup.com/markets/agriculture/grains/corn.contractSpecs.html
- **USDA NASS Crop Progress**: https://quickstats.nass.usda.gov/ (weekly reports May–Sep, includes planting %, silking %, maturity %)
- **USDA WASDE**: https://www.usda.gov/webdocs/NewsReleases (monthly ~10th of month, 11am CT)
- **USDA Planting Intentions**: issued mid-March; Acreage report late June.
- **National Weather Service 6–10 day outlooks**: https://weather.gov/wrh/
- **CME corn futures prices/charts**: Real-time data via your broker; historical at CME Group website.
- **Ethanol crush margin tracking**: EIA weekly Ethanol report; crush margin = ethanol price + DDGS price − corn price (should be monitored weekly May–Oct).
- **Key calendar dates**: Planting (Apr–May), WASDE (monthly), Acreage (late Jun), Harvest (Sep–Nov), Dec contract expiry (3rd week Dec).
