---
type: product_deep_dive
symbol: CT
sector: softs
analyst: Fund Engineer
updated: 2026-04-25T14:30:00Z
---

# [[CT]] — ICE Cotton (December Contract)

## Contract specs

- **Exchange / product code**: ICE Futures US / CT; unit = 50,000 lbs (22.68 metric tonnes) per contract
- **Tick size / tick value**: 0.01 cents per pound ($5.00 per contract); smaller moves = 0.0001¢ = $0.50 (mini-tick)
- **Contract months**: Mar, May, Jul, Oct, Dec; December is new-crop and largest/most liquid; delivery (physical) is against Certified Cotton held in ICE-approved warehouses
- **Session hours**: RTH 10:30–14:30 ET (pit in New York); Globex: 19:00 ET Sunday–15:00 ET Friday (nearly continuous)
- **First notice / last trading day**: 7 business days before last business day of the delivery month (mid-December for Dec contract); last trading day typically Dec 17 area; first notice usually Dec 10
- **Settlement**: Physical delivery (Certified Cotton per ICEC standards; 1–1.6 inches staple, color grades 1–7, leaf-grade restriction) or cash settlement at ICE reference price
- **Margin** (Topstep estimate): ~$2.2K initial, ~$1.6K maintenance (varies with volatility; confirm live)

## What it actually is

ICE Cotton futures (CT) are the global price discovery mechanism for cotton—a natural fiber used in textiles (apparel, home goods), industrial applications (tire cord, conveyor belts), and specialty chemicals. One contract = 50,000 lbs (~23 metric tonnes). The US is one of the world's largest cotton producers (~3.5–4M bales/year = ~17–20M bales in top years when supplies are abundant); India, China, Brazil, and Australia are also major producers. Global consumption (~25–26M bales/year post-pandemic) makes cotton fundamentally a global commodity: supply shocks in any major region move prices worldwide. The December contract (new-crop, harvested Aug–Oct in US) is the primary trading vehicle. Speculators trade cotton for macro agricultural exposure, seasonal patterns, and volatility plays. Hedgers include cotton farmers, textile mills (spinners), apparel manufacturers, and trading houses managing inventory. Cotton is highly correlated with broader agricultural weakness/strength (droughts, trade flows, demand cyclicality).

## Primary drivers

Ranked by impact in 2024–2026 regime:

1. **USDA acreage + yield forecasts (March Intentions, June Acreage, monthly WASDE)**: US cotton acreage has ranged 10–16M acres in recent years; post-2022 plantings shifted lower as farmers favored soybeans (more profitable in some regions post-Ukraine). USDA Planting Intentions (mid-March) and June Acreage report set market tone for the entire season. Yield estimates (lbs/acre) are critical: good yields + low acreage = tight supply. WASDE monthly forecasts (ending stocks, exports) drive sustained directional moves. A surprise >10% acreage swing vs. consensus triggers 200–400 points (1–2 cents/lb) moves. Post-2025, drought in Texas (major US cotton region) heightens acreage uncertainty.

2. **Global supply dynamics (India, Brazil, Australia, China production + ending stocks)**: World ending stocks below 6M bales (historical range 6–8M) signal supply tightness; above 8M signals abundance. India—the world's largest cotton producer (~5–6M bales)—has high domestic consumption and limited export; India weather/pest (Bt cotton challenges) swings global supply. Brazil's second-crop cotton (Feb–May harvest) adds competition. Australian droughts reduce supplies; Chinese production is falling (shift away from cotton to synthetic fibers). ICE monitors these via ICAC (International Cotton Advisory Committee) reports; monthly release is typically volatile.

3. **Global demand signals (textile mill consumption, apparel demand, inventory cycles)**: Textile mills in Vietnam, Indonesia, Pakistan, China drive ~70% of global consumption. Apparel demand is pro-cyclical: recessions → order cancellations → mill de-stocking → cotton prices crash. China's economic growth signals (PMI, export orders) cascade through cotton via mill buying. Post-Covid, fast-fashion (H&M, Zara) normalized; slow-fashion trends reduce fiber demand. Fashion cycles + e-commerce growth (Amazon, Shein) create demand whipsaw.

4. **Weather in US South (Texas, Georgia, Oklahoma, Arkansas, Louisiana, Mississippi)**: Cotton is rain-sensitive; drought during April–Aug (flowering + boll development) reduces yields. Texas Panhandle (20% of US acreage) saw persistent drought 2024; this will again be a key focus in 2026. Excessive rain during harvest (Sept–Nov) delays ginning and reduces quality (inage, color). Tropical storms (June–Oct) can destroy crops in Gulf states. NOAA 10-day outlooks + long-range forecasts (June–Aug) drive intraday/week moves during growing season.

5. **Crude oil and polyester fiber competition**: Cotton competes with polyester (petro-derived, ~60% of global fiber market). High oil → high polyester costs → mills substitute into cotton. Low oil → polyester becomes cheap relative to cotton, demand shifts. Also: textiles use PET polyester, which is energy-intensive to produce; oil >$80/bbl is a meaningful headwind to polyester-cotton switching. Crude oil also affects global cotton shipping costs (fuel surcharge).

6. **China trade policies and tariffs (US-China textile tariffs, Vietnam +25% tariff exposure)**: Post-2024, US-China tensions remain high. Apparel tariffs on Chinese imports (25–35%) boost Vietnam, Indonesia, Bangladesh apparel production. But Vietnam is resource-constrained; any supply disruption = margin squeeze on mills. US tariffs on Chinese textiles are passed through to consumers, dampening demand. USMCA (North America) trade flow is another swing factor.

## Key correlations

**Positively correlated:**

- **[[ZS]] (Soybeans): 0.50–0.60 correlation**. Both are major US crops competing for acreage; both driven by USDA reports, weather, global demand. In acreage-shift years (like 2023–2024 when soy profitability pulled acres from cotton), the correlation flips or weakens. Soybean-meal is livestock feed; cotton doesn't share that spillover.

- **[[ZW]] (Wheat): 0.35–0.45 correlation (weak-to-moderate)**. All row crops, all weather-sensitive. But wheat has separate global supply dynamics (Black Sea, Europe, China hoarding). Correlation is tighter during severe US droughts (multi-crop stress).

- **[[CL]] (Crude Oil): 0.25–0.40 correlation (weak-to-moderate)**. Higher oil → polyester costs up → cotton demand up. But the link is indirect; correlation strengthens in extremes (oil >$80 is bullish cotton, oil <$50 is bearish).

- **Global emerging-market equities (MSCI EM, China CSI 300): 0.35–0.50 correlation (moderate)**. Cotton is a play on global growth/demand; EM growth = textile mill orders = cotton demand. China's PMI is an early signal.

**Negatively correlated:**

- **US 10Y real yields (nominal 10Y yield - CPI breakeven): −0.25 to −0.35**. Higher real rates = tighter financial conditions, lower growth, mill de-stocking, reduced apparel demand. Cotton prices fall. Inverse relationship is moderate but consistent.

- **US Dollar Index (DXY): −0.15 to −0.25 (weak negative)**. Strong dollar = US cotton pricier for foreign mills; bearish. But DXY is noisy; the relationship is loose.

- **Equity volatility spikes (VIX >25): −0.20 to −0.30**. Risk-off → mills reduce forward purchases, apparel orders cancelled, inventory cuts. Cotton is pro-cyclical and sells off in VIX spikes. But the lag is 2–5 days; futures can anticipate VIX spikes.

**Lead/lag relationships:**

- USDA Planting Intentions (March) → 30-min move; effects ripple 3–7 days.
- USDA June Acreage → similar, but less surprise (already partly priced).
- USDA WASDE (monthly, 11:00 ET) → immediate 50–150 point move (0.3–0.75¢/lb).
- ICAC report (monthly, typically early month) → 100–300 point move if supply surprise.
- China PMI (manufacturing, early month) → delayed 1–3 day effect; mills' forward purchasing patterns adjust.
- Weather forecasts (6–10 day outlooks, May–Aug) → gradual repricing over 2–5 days; severe drought forecast can trigger rally within hours.

## Recurring patterns

**Seasonal:**

- **Spring (March–May): Planting Risk Ramp**: As US cotton planting accelerates (mid-March to mid-May in South), rain-induced anxiety peaks. Delayed plantings (wet soils in Feb–March) are bullish short-term (smaller intended acres), but planted acreage eventually catches up. USDA June Acreage report (released late June) typically realizes ~90% of planted intentions. Volatility is elevated March–May; mean reversion is common post-Acreage.

- **Early Summer (June–July): Growth Stress & Heat Watch**: Cotton enters flowering (late June–July). Heat stress and rain deprivation during pollination (late June–early July) destroy yield. This is the most price-sensitive window; 10-day forecasts for heat/drought can trigger 300–500 point rallies intra-week. NOAA 6–10 day outlook is the bible; any hint of dryness in Texas panhandle is bullish.

- **Mid-Summer (August): Boll Development & Crop-Sizing**: Late July through August is critical boll development; yields finalize. Pest pressure (boll weevil in parts of South, whitefly in Texas) is monitored. Crop conditions typically start declining in Aug if drought persists. USDA Crop Progress report (weekly, Thursdays evenings) is followed closely. Aug rallies are common if crop condition drops below 75% "good–excellent."

- **Harvest (September–November): Supply Pressure & Ginning Delays**: New-crop cotton enters market from late August onward (Texas first, then Southeast). Supply pressure typically caps prices into October–November. Tropical storms (June–Oct) risk delayed harvest and lower quality. Ginning rates are tracked; if ginning is slow (weather), prices can hold up slightly. November typically sees a seasonal low as full harvest supply hits market.

- **Winter Storage (December–February): Carry & Contango Roll**: By January, most US cotton is ginned; supply is identified. Old-crop spreads (Nov vs. Dec) show storage carry. Typical contango is 50–100 points (0.3–0.5¢/lb); near-term demand from apparel (winter fashion) and strategic mill buying can tighten it. New-crop (March, May) premiums are modest in normal years.

**Event-driven:**

- **USDA Planting Intentions (typically March 28, 2026)**: Acreage estimate for cotton, soybeans, wheat, all row crops released simultaneously. Market reacts to cotton acreage vs. consensus. Surprises >10% vs. estimate trigger sharp moves. 2024 saw lower cotton acreage (farmers favored soybeans); 2026 depends on price recovery and planting-time profitability.

- **USDA June Acreage (typically late June, ~30th)**: Final planted acreage. Less volatile than March (expectations already adjusted) but can still surprise if weather prevented planting in some regions.

- **USDA Crop Progress (weekly, Thursday evening, May–October)**: "Good–excellent" percentages, planting %, flowering %, picking %. Drop below 75% good-excellent triggers short covering / rallies. Recoveries back above 75% can trigger selling.

- **USDA WASDE (monthly, first 10 days of month, ~11:00 ET)**: Ending stocks, export estimates, production forecasts. Anything shocking (supply cuts, export surge) is volatile. Winter months (Dec, Jan, Feb) often see supply adjustments as harvest data comes in.

- **ICAC Report (first Thursday of each month, ~10:00 ET)**: International Cotton Advisory Committee publishes global supply, demand, ending stocks. Can surprise market with India/Brazil/Australia adjustments. Reports are published in early morning; 150–400 point moves are normal.

- **China PMI (manufacturing, ~9:30 ET last business day of month)**: Signal of apparel-mill health and forward orders. Beats or misses can move textile mills' cotton demand outlook. Weak China PMI (<49) is bearish.

- **Tropical storm season (June–October)**: Hurricanes in Gulf and Atlantic can threaten Gulf cotton states (Louisiana, Mississippi, parts of Georgia). Risk of crop loss is real; pre-storm rallies and post-damage reassessment moves are common.

**Time-of-day patterns:**

- **Open (10:30–11:30 ET)**: High volume, good fills. Pit opens; overnight Globex action is rebalanced. ICAC report, if released, is during this window. Most active period.

- **Mid-session (11:30–13:30 ET)**: Steady two-way flow. Technical support/resistance tested. Generally good liquidity.

- **Close (14:00–14:30 ET)**: Pit closing approach; volume drops into close. Specs and hedgers square up. Can see technical reversals.

- **After-hours (14:30–19:00 ET)**: Globex only; wide spreads (50–100+ ticks). Lower volume; not primary window.

- **Overnight Globex (19:00 ET–10:30 ET next day)**: Thin trading. Gaps can form if overnight macro news (China data, emerging-market moves). Wide spreads (100–200+ ticks). Not a primary entry window.

**Calendar quirks:**

- **Roll weeks (first notice day approach, ~Dec 10 for Dec contract)**: First notice day is typically Dec 10; last trading day is ~Dec 17. Specs begin rolling Dec contracts to March (next month) 2–3 weeks prior (early December). Volume can spike in Dec contract into expiration; March contract picks up volume. Wide bid-ask spreads are common during roll. Position squaring can create intra-week swings.

- **Post-Acreage volatility (late June into July)**: After USDA Acreage report (June ~30), market reprices for confirmed planted acres. Technical breakdowns or rallies are common over next 2–3 weeks as traders adjust hedges.

- **December holiday effect (last 2 weeks of Dec)**: Volume often thins into holiday; liquidity can deteriorate. Not recommended for new position entry. Closes early Dec 25, early Jan 1.

## Common setups

For each, give trigger / invalidation / exit:

1. **USDA Acreage Surprise + Breakout**
   - **Trigger**: USDA June Acreage report (late June) shows acreage >15% below consensus. March contract rallies through key resistance (e.g., 75¢/lb historical level). Volume supports the breakout.
   - **Invalidation**: Price breaks below the pre-report level within 2 trading days (mean reversion); new acreage estimates prove inaccurate (early revisions in WASDE); global supply replaces US tightness (India/Brazil ramp production).
   - **Exit**: Take 50% at +150–200 points; trail stop on remainder to 50% breakeven; cover on close below pre-report level or if next WASDE cuts estimate revision.

2. **Seasonal Summer Drought Rally (May–July)**
   - **Trigger**: NOAA 6–10 day forecast shows heat + dryness in Texas/Oklahoma May–July; prior week's Crop Progress report showed <70% good-excellent; technical break above 20-day moving average.
   - **Invalidation**: Forecast reverts to normal/wet; heavy rains arrive within 5 days; crop condition report jumps back >75% good-excellent.
   - **Exit**: Sell 50% at +250–350 points (mean reversion into harvest); trail stop on rest to breakeven; cover if moisture forecast reverses or crop condition recovers.

3. **Fall Harvest Supply Pressure + Technical Short**
   - **Trigger**: September–November, new-crop cotton supply swamps market. Price holds below 65¢/lb, or breaks below 60-day moving average. Global ending stocks >7.5M bales signals oversupply.
   - **Invalidation**: WASDE cuts global production (India drought, Brazil freeze, Australia dry); tropical storm develops, threatens harvest; export demand spikes unexpectedly.
   - **Exit**: Cover 50% into rallies to short-term resistance; trail stop on rest; take profits if price falls to 200-day support or WASDE cuts supply outlook.

4. **China PMI Miss + Equity Selloff Spillover**
   - **Trigger**: China manufacturing PMI misses consensus (e.g., <48 vs. >49 expected); stock market sells off >1% in one day. Apparel mill orders expected to decline. Cotton breaks below short-term support.
   - **Invalidation**: Immediate China policy support (stimulus announced); PMI revision upward; equity market rebounds within 2 days; mills issue forward demand guidance.
   - **Exit**: Sell rallies into resistances; cover on 2-day close back above 50-day MA; take profit if equity markets stabilize.

5. **Polyester Parity Shift (Crude Oil Break)**
   - **Trigger**: Crude oil breaks below $50/bbl; polyester spreads widen (cotton cost advantage shrinks). Mills' cotton-to-polyester switching pressure. Technical break below key support.
   - **Invalidation**: Crude oil rallies back above $60/bbl; cotton demand recovers; geopolitical risk props oil prices.
   - **Exit**: Cover on crude oil rebound or technical bounce; take loss if crude breaks lower (structural energy shift).

## Classic traps

- **Post-USDA report fade**: USDA reports (Acreage, WASDE) often see sharp initial moves that reverse 60–70% over 2–5 days. Specs chase breakouts only to be trapped. Wait for 2-day confirmation and volume shift before adding to directional bets.

- **False drought rallies**: Heat waves in May–June that don't persist into July often see reversals as crop adapts and rains arrive by early-to-mid July. Chasing +300 point rallies on 10-day heat alerts often ends badly when the drought doesn't materialize.

- **"Harvest is coming" short squeezes**: Specs see supply timing out (late Aug–Sept) and pile into shorts; short covering rallies into late August can tag spec stops. Respect short-term bounces even in seasonal downtrends.

- **Inventory confusion**: Mills' published inventory is lagged by 30–60 days; real-time inventory is opaque. Specs sometimes trade on outdated stock assumptions; positions can reverse sharply when real demand data arrives.

- **Trade policy whipsaw**: US-China tariff announcements (or reversals) can spike cotton 200+ points overnight, then fade 70% within days as mills adjust sourcing. Don't chase tariff rallies at extremes.

- **Liquidity illusion near expiration**: Dec contract into first notice day (Dec 10) can appear liquid but shows extreme bid-ask spreads (100+ ticks). Position squaring is violent. Avoid new entries within 2 weeks of first notice; migrate to March contract.

## Liquidity profile

- **Average daily volume (front month, Dec)**: ~100–200K contracts/day in normal conditions; spikes to 300K+ on USDA events, event days. Typically more liquid than softs like cocoa (SB), less liquid than energies (CL, NG).

- **Open interest**: Dec contract typically holds 200–400K open interest (varies with season); March holds 100–200K. Winter contracts (Jan–April) decay to 50–100K. Liquidity concentrates in Dec, March contracts; avoid April, May (very thin).

- **Bid-ask spread**: Typically 20–50 ticks (0.1–0.25¢/lb) in normal market; can widen to 100+ ticks in low-vol periods or during roll. Best fills in first 2 hours (10:30–12:30 ET) and 1 hour before close (13:30–14:30 ET).

- **Pre-open / post-close behavior**: Overnight Globex (19:00 ET–10:30 ET) often opens 50–200 points away from prior close on macroeconomic news; gaps are common. Post-close (after 14:30 ET), Globex volume is minimal, spreads widen. Not recommended for new positions.

- **Session with best fills**: 11:00–13:00 ET is prime (overlaps US pit and electronic trading). 10:30–11:00 ET (open) is volatile but liquid. Avoid after-hours Globex unless necessary to exit.

## Options (if applicable)

- **Expirations**: December, March, May, July, October contracts have active options; quarterly (Jan, Apr, Jul, Oct) also available in some brokers.

- **AM vs PM settlement**: Most ICE cotton options settle at noon (12:00 ET) on expiration day (Thursday of the week the futures expire); March and December options often have more liquidity.

- **Typical IV rank range**: 30–70 range is normal; 20–30 (low IV) common in fall/winter (low-volatility harvest season); 60–80 (high IV) in spring/early summer (drought/weather risk). IV spikes on tropical storm threats (80+).

- **Pin-risk behavior**: Rare, but can occur near-the-money; most options settle to cash (CME-cleared). Assignment risk is low on ICE cotton.

- **Greeks sensitivity**: Vega is significant in spring/summer (weather volatility); delta is high on ITM calls/puts. Theta decay is moderate (1–2% per week for ATM, 30 DTE options).

## Risk notes

- **Gap risk profile**: Cotton can gap 200–400 points (1–2¢/lb) on overnight macro shocks (China news, trade policy, oil moves, US economic data). Pre-market positions are vulnerable. Use stop orders or close positions before 3:00 PM ET if holding overnight.

- **Limit-up / limit-down mechanics**: ICE cotton has daily price limits (typically 2¢/lb swing = 4,000 points, equivalent to $2K per contract) for the first 10 days of trading; limit is expanded to 3¢/lb thereafter. Limit-up / limit-down scenarios are rare but possible in droughts or major supply shocks. Position can be stuck for a day.

- **Worst weekly move in last 5 years**: Feb 2024 saw a 450-point (2.25¢/lb) weekly rally on drought fears in Texas / India production concerns. Oct 2020 (pandemic) saw a 600-point (3¢/lb) decline week. Typical worst week is 300–400 points (1.5–2¢/lb); account for 500+ point gaps in risk sizing.

- **Tail-risk events to remember**: 
  - **2020 COVID crash**: Cotton crashed 40% in March 2020 (April contract from 72¢ to ~46¢) in panic selling; recovered within 4 months on demand recovery.
  - **2010 Russia drought**: Global grain shortage (Russia, Ukraine) spilled into commodities; cotton saw 200+ point rallies but eventually stabilized.
  - **2022 India production shock**: India (world's largest producer) faced pest pressure; price spike 500+ points over a month.

- **Delivery risk (physical holders)**: If holding a Dec contract into first notice (Dec 10) without a hedge or roll, you may be assigned cotton physically. Physical delivery requires cash settlement or warehouse receipt transfer; costs ~$500–1500 per contract (delivery, handling, insurance). Not recommended for spec traders. Always roll or close 2 weeks before first notice.

- **Storage and carry costs**: If you're accidentally assigned cotton, storage costs are ~$0.02–0.04/lb/month (~$500–1000/contract/month). Can erode P&L quickly. Avoid delivery situations.

## References

- **CME/ICE product page**: https://www.theice.com/products/254/Cotton-Futures
- **USDA NASS**: https://www.nass.usda.gov/ (Acreage, Crop Progress, WASDE)
- **ICAC (International Cotton Advisory Committee)**: https://www.icac.org (Global supply/demand data, monthly reports)
- **US Department of Agriculture WASDE**: https://www.usda.gov/webdocs/publications/ (Monthly crop forecasts)
- **NOAA Weather Forecast Office**: https://www.weather.gov (6–10 day outlooks, especially during growing season)
- **China National Bureau of Statistics**: Official PMI releases (searchable, lagged 1–2 days)
- **Further reading**: 
  - Commodity Futures Trading Commission (CFTC) Commitment of Traders (CoT) for cotton positioning trends
  - Trading Economics cotton price + economic calendar for event scheduling
  - Recent Journal of Agricultural Economics articles on cotton demand elasticity and polyester substitution

