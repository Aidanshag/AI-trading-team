---
type: product_deep_dive
symbol: KC
sector: softs
analyst: Fund Engineer
updated: 2026-04-25T23:45:00Z
---

# [[KC]] — NYMEX Arabica Coffee

## Contract specs

- **Exchange / product code**: ICE Futures U.S. (formerly NYBOT) / KC
- **Unit**: 37,500 pounds (lbs) per contract (~18 metric tons; one 60kg arabica bag = 132 lbs)
- **Tick size / tick value**: 0.0005 USD per lb; $18.75 per contract
- **Contract months**: March, May, July, September, December (5 months/year cycle; highest volume in front month)
- **Session hours**: RTH 03:00–13:00 ET (floor); ICE Futures platform 17:30 ET Sunday–16:15 ET Friday (post-market trade possible)
- **First notice / last trading day**: 7 days before the last business day of delivery month
- **Settlement**: Physical delivery (arabica coffee, grade 1 or better per contract specs; basis adjustments for origin/quality)
- **Margin** (Topstep typical): ~$3K initial, ~$2K maintenance (varies with IV)

## What it actually is

KC futures track the global price of arabica coffee. One contract = 37,500 lbs of arabica (distinct from robusta, which trades on different exchanges—LIFFE in London). Arabica is higher quality, 60–65% of global production, grown in tropical highlands (Central America, Colombia, Ethiopia, Kenya; limited to 10–20°C altitude bands). Robusta is cheaper, more hardy, dominant in Vietnam and Indonesia. The ICE contract settles via physical delivery at certified warehouses in New York, Miami, and other US ports.

Coffee is consumed daily by ~2 billion people; beverage is inelastic (price elasticity ~0.3, meaning a 10% price rise cuts consumption by ~3%). Roasters (Starbucks, Nestlé, independent) and instant-coffee manufacturers are primary physical hedgers. Speculators use KC for directional exposure and as a proxy for emerging-market risk sentiment (coffee is >90% produced in developing nations, especially Brazil, Vietnam, Colombia; strong pricing benefits those economies).

## Primary drivers

Ranked by impact in current regime (2024–2026):

1. **Brazil crop size and weather**: Brazil is 30–35% of global arabica supply; a major frost, drought, or wet spell shifts global supply expectations by 20–40M bags (1 bag = 60kg). The Brazilian growing season (Oct–Apr) is critical; forecasts of crop shortages drive year-ahead pricing. La Niña/El Niño patterns influence Brazilian rainfall and temperature.

2. **Vietnam & Indonesia robusta competition and USD weakness**: Vietnam dominates robusta (35% of global supply); cheaper robusta prices can suppress arabica if roasters shift blend ratios. Vietnamese production is vulnerable to weather and land-use changes. When USD weakens, non-US roasters (Nestlé, Lavazza, Illy in Europe) get more local currency per coffee dollar, lifting demand. When USD strengthens, non-US demand cools.

3. **Arabica inventory carryover (ICE stocks + global buffer)**: Certified stocks in ICE warehouses + global physical inventories (at roasters, ports, origin countries) set the floor for global coffee prices. Low carry (< 30M bags = ~12 months global consumption) = bullish; high carry (>50M bags) = bearish. Inventory data from International Coffee Organization (ICO) is published monthly.

4. **Global demand (macro, consumption trends)**: Recessions or slowdowns reduce discretionary coffee spending; espresso/specialty demand falls first. Post-Covid, at-home consumption remains elevated, but out-of-home (cafes, offices) is recovering. Climate awareness and premium/organic trends shift roaster sourcing and are bullish for high-altitude arabica.

5. **Geopolitical/currency risk in origin countries**: Colombia, Ethiopia, Honduras, Uganda, Peru are major exporters; political risk, conflict, and currency devaluation affect willingness to sell and export logistics. In 2022, Colombia faced cost-of-living crises; in 2023–2024, Ethiopia's civil conflict disrupted supply. Currency crashes (e.g., Colombia's peso weakening) incentivize exports (producers get more local currency).

## Key correlations

**Positively correlated:**
- **[[ZS]] (Soybeans)**: 0.4–0.5 (moderate). Both are agricultural exports from emerging markets; when USD weakens, both rally. Brazil is a major soybean producer too; weather that hurts soybeans often affects coffee (same season, same geographies).
- **[[ZC]] (Corn)**: 0.3–0.4 (weak-to-moderate). Similar emerging-market weather/currency factors, but corn is more globally produced; weaker correlation than soybeans.
- **Emerging market currencies** (BRL, COP, etc.): −0.3 to −0.5 (negative to the USD side, positive to local currency strength). When Brazilian real weakens vs USD, coffee prices often rise (producers export more aggressively). When BRL strengthens, coffee can sell off.
- **USD weakness (DXY)**: −0.25 to −0.4. Weak dollar = higher real prices for non-US roasters; demand lifts. Strong dollar caps demand.
- **Equity risk sentiment (VIX inverse)**: 0.2–0.3 (weak positive). Coffee is a risk-on asset; in risk-off regimes (flight to safety), it underperforms. In risk-on, it outperforms.

**Negatively correlated:**
- **Real yields (10Y TIPS)**: −0.2 to −0.3. Higher real rates = tighter global liquidity, slower emerging-market growth, weaker demand.
- **[[HE]] (Lean Hogs, livestock)**: 0.15–0.25 (weak positive in most regimes, but can decouple; both emerging-market agricultural plays).

**Lead/lag:**
- **Brazilian weather updates** (Dec–Apr forecasts) → price move within 1–3 days. Firms like Somar Meteorologia and Weather Underground forecasts shift market.
- **ICO monthly reports** (11th of each month) → modest ripple if inventory surprises (typically −2–3% move).
- **USD strength shocks** (Fed tightening, risk-off macro) → coffee sells with 1–3 day lag vs equities.
- **Global demand surveys** (QSR earnings for Starbucks, Nestlé quarterly calls) → longer lag (weeks), subtle signal.

## Recurring patterns

**Seasonal:**
- **Jan–Mar (harvest peak, physical selling)**: Brazilian harvest (Mar–May) and Colombian harvest (Oct–Dec, Jan–Mar second crop) push supply. Prices tend to soften as physical coffee flows. Arabica rally from prior year's lows often fades in this window.
- **Apr–June (low supply, production fears)**: Post-harvest; next major supply is 6+ months away. Roasters worry about coverage; any weather news (frost, drought in next season) can spike prices. May–June coffee often touches seasonal highs.
- **July–Sep (demand peak, summer doldrums)**: Northern-hemisphere summer; iced-coffee demand rises (USA, Europe). But seasonal pattern is weak; coffee often drifts lower into fall as new crop approaches.
- **Oct–Dec (new crop uncertainty + holiday demand)**: New Brazilian/Colombian crops arrive; quality and size unknown until late harvest. Holiday demand (November–December gifting, year-end purchases). Hedging pressure from harvest. Volatility tends to rise.

**Event-driven:**
- **Brazilian frost forecast (June–Aug for Sept crop)**: Most important seasonal trigger. If NOAA or local forecasters flag frost risk 2–4 weeks ahead, market rallies 3–7% over 3–5 days. False alarms can fade quickly.
- **ENSO updates (El Niño/La Niña cycles)**: NOAA releases updated El Niño/La Niña odds monthly. La Niña = wet, La Niña = dry for Brazil's JFM (key growing months). Updates can shift seasonality expectations.
- **ICO reports** (11th of each month): Crop estimates, inventory data. Surprises (e.g., larger-than-expected global crop) drive 1–3% moves, typically realized over 1–2 days.
- **Starbucks / Nestlé earnings calls** (quarterly): Guidance on input costs, pricing power, demand. Material only if they flag supply concerns or demand weakness.
- **Currency volatility** (emerging-market crises): BRL, COP, or other coffee-origin currencies crash → hedging demand lifts coffee 2–5% over 1 week.

**Time-of-day patterns:**
- **London open (02:00 ET)**: ICE opens; early movers (Europeans, Robusta traders) active. Modest volume; directional bias often set by overnight news.
- **09:30–12:00 ET (core US session)**: Best volume and liquidity. Funds active; news flow (US equities, macro) creates movement. Most tradeable window.
- **Post-13:00 ET (floor close)**: Thin; wide spreads. Coffee activity migrates to after-hours on ICE Futures platform, but retail fills worsen.

**Calendar quirks:**
- **Roll window** (contract rolls 7 days before delivery; highest volume in front month → back month ~20 days before expiry): Contango market (new crop higher than old) means smooth roll cost; backwardation (new crop lower) can hurt physical shorts. Post-2021 drought in Brazil, KC was in backwardation; rolls were "costly" (had to buy back at premium, sell front month at discount).
- **Certified inventory flows**: ICE publishes warehouse stocks daily; low stock wednesdays (when official ICE report drops) can see intraday volatility if stocks fall sharply.

## Common setups

1. **Frost scare (Brazilian June–Aug cold forecast)**
   - *Trigger*: Weather forecasts (INMET Brazil, or global models like ECMWF, GFS) show frost risk 2–4 weeks ahead for southern Brazil (Minas Gerais, São Paulo). Frost occurs <0°C, kills buds/flowers. Early warning (20–30 days out) typically see 2–3% rally over 3 days.
   - *Entry*: Long if price breaks above prior 5-day high on the news. Can layer into rallies on each forecast update.
   - *Stop*: Below recent swing low (typically 5–8 ticks). Wider stop if building position over multiple days.
   - *Target*: Prior seasonal resistance (often major resistance from 2–3 months prior). 1:1.5 to 1:2 RR typical.
   - *Invalidation*: Forecast updates to show frost risk lower (warmer temps) or disappears → short signal (many false alarms).
   - *Hit rate*: ~50–55% (many frost scares fail to produce lasting rallies; market often ropes shorts then fades). Requires news discipline—don't chase; enter on breakout of prior setup, not on hype alone.

2. **Arabica-robusta spread arbitrage (KC vs LIFFE robusta)**
   - *Trigger*: Robusta (LIFFE) trades at unusually low premium to arabica or at discount (historically arabica should trade $0.20–0.50/lb premium). When robusta spiked 2022–2023 (supply shock from Vietnam + geopolitical), the spread inverted (robusta > arabica in some cases). Now in 2024–2026, spread has normalized but can re-widen if robusta supply tightens or arabica loosens.
   - *Entry*: If KC is 15–25 cents/lb above LIFFE robusta (adjusted for contract sizes), long arabica or short robusta. If spread inverts, short KC or long robusta.
   - *Stop*: Prior extreme of spread (typically 5–8 ticks wider/narrower than normal).
   - *Target*: Historical mean spread (~20–30 cents/lb in favor of arabica).
   - *Invalidation*: Roaster blend ratio shifts (e.g., Nestlé announces robusta mix increase) → invalidates mean-reversion, needs new trade thesis.
   - *Hit rate*: ~55–60% (spread mean-revision is reliable if you trust the historical mean; careful on structural shifts in roaster behavior).

3. **ICO inventory surprise + follow-through**
   - *Trigger*: ICO monthly report (11th of month) shows certified inventory or global carryover estimate differs >10% from market expectations. Large build (bearish surprise) or draw (bullish surprise).
   - *Entry*: If bearish surprise (stocks build), short into the dip if price hasn't fully given up gains. If bullish (stocks draw), cover shorts or go long if price rallies.
   - *Stop*: Opposite side of initial move (if shorts, stop is above the rally high post-release).
   - *Target*: Statistically, inventory surprises have <1-day half-life; pick profits within 24–48 hours.
   - *Invalidation*: Reversals in next 2–3 hours (whipsaw) often indicate weak conviction; exit if reversal is sharp.
   - *Hit rate*: ~50–52% (inventory data is less volatile than crop news, so moves are smaller; win rate is near 50-50, but sizing can favor expected direction based on seasonal bias).

## Classic traps

- **Frost scare + false alarm**: A frost is forecast for Brazil 3 weeks ahead; KC rallies 5%. Forecast updates show frost risk dropping to 20%, then further to 10%. Many longs hold thinking "the risk is still real"; instead, market sells off 6%. Trap: chasing rallies without confirming the frost is happening.

- **Robusta supply shock (Vietnam weather, land disease)**: When robusta spikes, market assumes roasters will demand more arabica (supply substitute). In reality, roasters tighten blends, buy more instant coffee, and reduce total coffee consumption. Arabica doesn't follow robusta as cleanly as expected. Trap: buying KC on robusta strength without confirming arabica demand.

- **Currency collapse without supply concern**: BRL crashes 15% vs USD; coffee rallies 3–4% on export incentives. But if the BRL crash is due to Brazil recession fears, demand may be weak; the rally fades. Trap: shorting on the rebound thinking the currency move is transient.

- **ICO report "surprise" that wasn't**: Analysts estimate global carry as 45M bags; ICO prints 45.2M bags. Market was looking for 42M (real surprise would be major shortage news). The 45M print is not a surprise to informed traders; price doesn't move. Trap: fading on what you think is a surprise that the market already priced in.

- **Certified inventory drain without fundamental support**: ICE warehouse stocks drop 500k bags; traders assume roasters are buying and coffee is tight. In reality, origin countries (Brazil, Colombia) have high private inventory; drains are just timing. Prices peak despite the "tightness." Trap: going long on low ICE stocks.

- **Leveraged liquidations in thin hours**: Coffee is relatively illiquid (avg volume ~40k contracts/day; much lower than crude oil or equities). Overnight stops at round numbers (e.g., 200, 210 cents/lb) are hit by algo liquidations. Morning gaps of 5–10 ticks are common. Trap: holding stops at round numbers overnight in NG.

## Liquidity profile

- **Average daily volume** (front month): 40k–60k contracts in normal regime; spikes to 80k–120k in harvest season (Oct–Dec) or frost-scare windows. Summer months (June–Aug) can see volume drop to 20k–30k.
- **Open interest trend**: ~150k–200k for front month; back months significantly thinner (20k–40k). Spread trading (buy-sell calendar spreads) occurs but not deep.
- **Pre-open / post-close behavior**: ICE opens 17:30 ET Sunday; early volume is thin. Best fills 09:30–13:00 ET weekdays. Post-13:00 ET, liquidity drops sharply; fills worsen. Overnight (13:00–17:30 ET next day) on ICE Futures platform is thin.
- **Best session for fills**: 09:45–12:30 ET core hours. Avoid post-close and pre-open.
- **Bid-ask spread**: 1–2 ticks normal in core hours (0.0005 USD = $18.75 per tick); 3–5 ticks in off-hours or low-volume periods.
- **Roll mechanics**: Roll 10–15 days before delivery. Contango (May > March, etc.) means rolling is a cost (buying back at higher price); backwardation is a benefit (buying back at lower price). Plan roll size to match risk limits; rolling 50+ contracts can move the spread.

## Options (if applicable)

- **Weekly expirations**: Mondays (expire Friday end of day of prior week). Lower IV, thinner than monthly; used for short-dated directional hedges.
- **Monthly expirations**: 3rd Thursday of month (same as many other NYMEX contracts).
- **Settlement**: 10:00am ET for weeks and monthlies. American-style (can exercise early).
- **Typical IV rank range**: Harvest seasons (Oct–Dec): 55–75th percentile (higher volatility). Summer (June–Aug): 20–40th percentile (lower volatility). Frost-scare events can spike IV 80–90th percentile for weeks.
- **Pin-risk behavior**: Coffee options near major strike prices (e.g., 200, 210 cents/lb) can see pinning into expiry. Avoid short gamma positions into expiration if price is near strike.
- **Spread structure appeal**: Vertical spreads (e.g., long 210 call / short 220 call) are popular in low-IV summer periods to define risk; put spreads are used for bearish harvest bets.

## Risk notes

- **Gap risk profile**: Overnight gaps (17:30 ET to 09:30 ET next day) are 1–3 ticks typical in normal regimes. Frost scares, currency crises, or ENSO updates can see gaps of 5–8 ticks. No daily price limits on ICE coffee, but exchange can halt trading if disorderly.

- **Limit-up / limit-down mechanics**: ICE does not have daily limits; however, trading can be halted by exchange discretion. In extreme rallies (e.g., 2010 frost scare: coffee rallied 1.5× in weeks), volume dries up and fills worsen, but no hard circuit breaker.

- **Worst weekly move in last 5 years**: July 2021 (Brazilian frost scare, Minas Gerais): coffee rallied from 120 cents → 160 cents (+33%) in 4 weeks. 2021–2022 (global supply shock from frost + Vietnam drought): rallied 160 → 230 cents (+44%). 2024 (Brazilian dry spell, crop reduction concerns): soft rally 210 → 240 cents (+14%). Summer 2024 (lack of demand surprise) soft sell-off 240 → 220 cents (−8%).

- **Tail-risk events to remember**:
  - **Brazilian freeze (July 2021)**: Frost in Minas Gerais (world's largest arabica region) destroyed buds; global output was reduced; prices rallied 50%+ over summer.
  - **Vietnam robusta disease + drought (2022–2023)**: Coffee leaf rust (fungus) and dry weather cut Vietnam output; arabica benefited from supply tightness in coffee complex.
  - **Brazilian dry spell (2024, ongoing)**: La Niña pattern brought drought to Minas Gerais, São Paulo; crop forecasts for 2025 were cut; prices supported.
  - **ENSO flip (late 2023–early 2024)**: El Niño replaced La Niña; forecasts for 2024–2025 shifted wetter for Brazil. Market sold off on prospect of ample new crop. Correction from highs.

## References

- **ICE KC contract specs**: https://www.theice.com/products/13875/Arabica-Coffee-Futures
- **International Coffee Organization (ICO) reports**: https://www.ico.org/ (monthly crop estimates, inventory data, published 11th of month)
- **INMET Brazil weather**: https://www.inmet.gov.br/ (Brazilian meteorology for frost/rain forecasts)
- **NOAA ENSO outlook**: https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensoyears.shtml (El Niño/La Niña probabilities, updated monthly)
- **Somar Meteorologia** (private Brazilian forecaster): https://www.somar.com.br/ (frost risk, rainfall outlooks; subscription required but widely used by trade)
- **Coffee market liquidity**: Volume is 40k–60k contracts/day front month; much lower than oil/grains. Roll 10+ days before expiration to avoid end-of-month squeeze.
- **Cross-commodity hedge**: If long coffee, consider short [[ZS]] or [[ZC]] as a Brazil-weather hedge (both are major Brazilian exports; correlated 0.4–0.5).
