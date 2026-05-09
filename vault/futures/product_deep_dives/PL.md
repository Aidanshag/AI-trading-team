---
type: product_deep_dive
symbol: PL
sector: Precious Metals
analyst: Fund Engineer
updated: 2026-04-28T18:15:00Z
---

# [[PL]] — NYMEX Platinum

## Contract specs

- Exchange / product code: NYMEX (CME Group) / PL
- Tick size / tick value: $0.10 per troy oz = $50 per tick (micro contract 1/10th the size exists as MPL)
- Contract months (delivery cycle): Jan, Apr, Jul, Oct (front 3 months most liquid; far months sparse)
- Session hours (RTH and extended): Sunday–Friday, 5:00 PM–3:00 PM CT next day (23-hour session with brief close 3:00–5:00 PM CT)
- First notice / last trading day: 3rd last business day of contract month
- Settlement: Physical delivery (50 troy oz per contract)
- Margin (initial / maintenance at Topstep, if known): Typically $5–8k initial, $3.5–6k maintenance (lower volatility than PA; larger contract size dampens leverage)

## What it actually is

Platinum (PL) is a NYMEX precious metals contract representing 50 troy ounces of refined platinum bullion. Unlike gold's pure precious-metal profile or palladium's autocatalyst focus, platinum occupies a unique middle ground: ~45% industrial demand (catalytic converters for diesel engines, lab/dental equipment, electrodes, chemical processes), ~40% jewelry (particularly China, India, Middle East), ~10% investment/bullion, ~5% other. This balanced demand structure makes PL sensitive to both industrial cycles (diesel production, manufacturing PMI) and macro risk-off flows (like gold) while maintaining higher correlation to precious-metals sentiment than palladium. Primary hedgers include PGM mining companies (Amplats, Impala, Lonmin in South Africa), automotive OEMs (especially European diesel makers), jewelry manufacturers, and recycling operations; speculators include macro funds, carry traders (platinum often offers positive roll yield), and volatility players. South Africa controls ~80% of global supply, creating a concentration risk similar to palladium's Russian exposure.

## Primary drivers

Ranked by influence in current regime (Apr 2026—diesel decline in EU, platinum jewelry demand in China, labor risks at South African mines):

1. **Diesel autocatalyst demand (European automotive cycle, EU diesel regulations)** — Dominant driver for ~45% of platinum demand. EU is where diesel penetration is highest (55%+ of new-car sales), making diesel emissions regulations and diesel OEM health critical. When EU new-car registrations rise, platinum autocatalyst demand accelerates; downturns hit hard. Current regime headwind: EU transitioning from diesel to EV (diesel share fell from 55% in 2020 to 35% in 2026), eroding PL demand permanently. Unlike palladium (only in gasoline cars), platinum faces secular decline in both diesel and gas as EV adoption compounds.

2. **South African mining labor disruption and supply risk** — South Africa produces ~80% of global platinum supply (Amplats, Impala, Lonmin together account for 2M oz annually). Wage strikes, power outages, safety stoppages, and water availability constraints frequently disrupt production. Any meaningful supply loss (strikes >2 weeks, mine flooding, load-shedding blackouts) can spike PL 3–8%. 2023–2024 saw recurring supply scares; expect 1–2 disruptions per year. Difficult to predict timing, but watch South African mining news (Reuters, Mining Weekly) overnight.

3. **Jewelry demand in China and India (yuan weakness, gold prices, wedding seasons)** — Platinum jewelry is price-sensitive and heavily concentrated in China (jewelry manufacturers in Shenzhen, Foshan) and India (gold/platinum wedding jewelry). Yuan weakness or gold price spikes can reduce platinum jewelry demand (consumers substitute to gold or silver). India's wedding season (Sept–Nov) can lift platinum jewelry buying. Tracking jewelry demand is harder (no high-frequency data), but Chinese PMI weakness or Indian marriage-season data can signal demand shifts weeks ahead.

4. **Real rates and USD strength (DXY, 10Y TIPS yield)** — Platinum is priced in USD and negatively correlated with real rates (r ≈ −0.35 inverse). Not as rate-sensitive as gold (−0.50) because industrial demand stability mutes interest-rate swings. Strong USD still suppresses via import demand for jewelry and industrial applications in EM countries.

5. **Recycling supply flows and end-of-life automotive scrap** — Platinum recycling from diesel catalytic converters returns ~40% of annual supply (1.2M–1.4M oz from ~3M oz total). In tight supply environments, recycling incentives rise, creating a supply feedback loop with 9–18 month lag. High prices → higher scrap recovery rates → eventual supply relief. Recycling ramps when PL prices spike, but the lag means traders holding through price spikes often get caught when recycled platinum arrives 12 months later.

## Key correlations

- **Positively correlated with:**
  - [[GC]] Gold (r ≈ +0.55–0.70). Both respond to risk-off macro sentiment and real-rate drops. Platinum typically lags gold on sentiment, but follows when gold moves persist >2 days.
  - [[SI]] Silver (r ≈ +0.50–0.60). Similar macro drivers; both are precious metals. Platinum is more stable (lower volatility).
  - [[ES]], [[NQ]], global equities (r ≈ +0.45–0.60 during expansion; r ≈ 0 during recessions). Industrial demand → equity demand; correlation breaks in severe downturns.
  - [[HG]] Copper (r ≈ +0.35–0.50). Both tied to global manufacturing, but copper is heavier on China growth; platinum is Europe-diesel focused.
  - [[CL]] Crude Oil (r ≈ +0.25–0.45). Weak correlation; diesel is subset of crude, but crude supply is diversified. Mostly correlation comes through growth sentiment.

- **Negatively correlated with:**
  - [[ZB]], [[ZF]] T-Bonds, T-Notes; real yields (r ≈ −0.35 inverse). Weaker than gold (−0.50) due to industrial demand stability.
  - EUR/USD ([[6E]]) (r ≈ +0.40 inverse during EU recessions). EUR weakness → European auto demand headwind → PL weakness.
  - European diesel-car sales indices (negative relationship; accessible via EU car registration data published monthly).

- **Lead/lag relationships:**
  - EU new-car registration data (published monthly, 10th of next month) leads PL by 3–6 weeks. Strong registration data → forward demand signal → PL rally delayed 20–40 days.
  - Shanghai copper futures (SHFE CU) leads PL by 1–3 sessions on global growth sentiment.
  - South African mining news (wage strike announcements, Eskom load-shedding warnings) leads PL by hours to 1 day (watch overnight news feeds).
  - US gasoline crack spread (CL minus RB) has +0.30 correlation with PL on 3-day lags, suggesting autocatalyst demand transmission.

## Recurring patterns

- **Seasonal (calendar effects):**
  - Jan–Feb: Post-holiday weakness; automotive production and jewelry demand (post-holidays) both slow. PL consolidation or slight declines common (−1 to −3%).
  - Mar–Apr: Spring jewelry demand in China (wedding/gift-giving season), Easter holidays in Europe boost driving. PL recovery expected. **Current season—watch for EU car registration surge and Chinese jewelry demand signals.**
  - May–Jul: Peak automotive production (European summer runs before August shutdowns). High demand, but prices also high, capping speculative participation. Typically range-bound.
  - Aug–Sep: European summer factory shutdowns; jewelry demand picks up. Some production lull, but jewelry demand stabilizes PL. Mid-range consolidation.
  - Sep–Nov: Indian wedding season (Sept–Nov) lifts jewelry demand significantly; Q4 auto production ramp. PL typically strongest season of the year.
  - Dec: Year-end liquidation, tax-loss selling, and holiday slowdowns. Weakest month for speculative positioning; hedgers often roll contracts.

- **Event-driven:**
  - EU new-car registration reports (monthly, published 10th of next month). Diesel sales breakdown is critical. Upside surprise → 2–3 week rally; downside → weakness (−2 to −4% over 5 days).
  - South African mining news (wage strikes, power cuts, safety incidents). Announced disruption >2 weeks → PL gap up 2–5%; minor incidents → 1% noise.
  - Chinese manufacturing PMI (published monthly, mid-month). Below-50 print (contraction) → jewelry demand concerns; below-45 → demand destruction signal, −3 to −5% PL moves.
  - Indian wedding season peaks (Sept–Nov data on jewelry imports/sales). Strength surprises → 1–2 week rallies; weakness → consolidation.
  - Fed/ECB policy decisions affecting EV subsidies, auto tariffs, diesel regulations. Surprise dove signals → risk-on rally in PL; surprise hawkish → headwinds.
  - Major automotive OEM earnings (BMW, Daimler, VW, Audi). Margin guidance on diesel/PGM costs can shift multi-week trends.

- **Time-of-day patterns:**
  - London open (12:00 PM UTC = 6:00 AM CT): European automotive/mining news often breaks here. European equities and auto stocks often set the tone.
  - NY open (1:30 PM CT): NYMEX pit opens; volume spike and tactical profit-taking. Wider moves expected.
  - Overnight (5:00 PM–midnight CT): South African news breaks here (Johannesburg late afternoon). Watch mining/strike updates; gaps common.
  - NY midsession (2:00–4:00 PM CT): Institutional rebalancing, fund unwinding. Lower volatility by late afternoon.

- **Calendar quirks:**
  - Roll windows (last 2 weeks of contract quarter): Front contract can widen/narrow spread vs. next quarter on carry (PL often has positive roll yield, attracting carry trades). Liquidity migrations can widen spreads during rolls.
  - Month-end (last 3 days of month): Technical unwinding, rebalancing into month-end close. Watch for gap risk if supply news breaks.
  - Quarterly expirations (Jan, Apr, Jul, Oct): Larger open interest migrations; some squeezes possible if positioning is extreme, but PL is larger contract than PA so less prone to violent squeezes.

## Common setups

1. **EU Auto Registration Surprise (event-driven mean reversion)**
   - **Trigger:** EU new-car registrations beat or miss expectations by >10%. If beat (especially if diesel component beats), PL rallies on forward demand signal; if miss, expect −2 to −3% move lower. Data published monthly (10th of next month); look for diesel % specifically.
   - **Invalidation:** If the registration move is offset by South African supply disruption news (mine halt, strike announcement), correlation flips and PL rallies on supply tightness instead of demand weakness.
   - **Exit:** Close or scale after 3–5% move over 2–3 weeks, or hold if trend extends beyond monthly high/low. Watch for the 3-week lag to play out fully before exiting.

2. **South African Supply Shock (gap and follow-through)**
   - **Trigger:** Breaking news of major South African mine strike announcement (>1 week expected duration), power outages (Eskom load-shedding), or safety closure. PL typically gaps 2–6% on open or overnight on such news.
   - **Invalidation:** If disruption is resolved quickly (<1 week) or deemed minor, PL often reverses the next 2–3 days as supply concerns ease.
   - **Exit:** Ride the move for 3–10 days, monitoring supply status daily. Watch for resolution announcements (strike settled, power restored) as reversal signals. Better to exit on secondary spike than primary gap.

3. **Diesel Demand Weakness (trend shift on PMI / EV data)**
   - **Trigger:** EU manufacturing PMI falls below 45 (severe contraction) or published EV sales surge >25% of monthly new cars (structural demand headwind). Can also trigger on announced diesel emission recalls or new regulatory tightening.
   - **Invalidation:** If the PMI decline is sector-specific (not autos), demand signal is weaker. Monitor auto-production indices separately.
   - **Exit:** Hold for 5–15 days as demand destruction plays out; take half off at 3–5% move, hold remainder for multi-week downtrend. This is a longer-duration setup than supply shocks.

4. **Real-Rate Reversion (macro-driven mean reversion)**
   - **Trigger:** 10Y TIPS yield spikes >0.5% or falls <−0.3% in single session. PL inverse-correlates with real rates (r ≈ −0.35). Falling real rates (Fed pivot) → PL rally; spiking rates → PL weakness.
   - **Invalidation:** If yield move is driven by inflation panic (not rate expectations), commodities may rally together, so PL may not inverse.
   - **Exit:** Hold for 2–5 days or until yield move reverses; scale at 2–4% PL move (smaller than some setups because correlation is weaker).

5. **Chinese Jewelry Demand (sentiment/data-driven seasonal)**
   - **Trigger:** Chinese manufacturing PMI or jewelry export data surprises to upside; yuan strengthens >2% vs. prior week (improves purchasing power for jewelry). Typically seen in Mar–Apr, Sept–Nov windows.
   - **Invalidation:** If the yuan move is driven by capital-control tightening (not economic optimism), demand may not follow.
   - **Exit:** Hold for 1–3 weeks as demand flows through; this is a slower-burn setup than supply shocks. Scale out at 2–3% move if quick profit available.

## Classic traps

- **The diesel death trap:** Traders see platinum rally on supply news and think it's a structural bull market. They miss the fact that EU diesel is in secular decline (diesel car sales down −20% since 2020, EVs accelerating). A 20% rally on a supply squeeze is followed by a 30% crash over 9–12 months as the EV trend reasserts. Avoid holding PL through earnings seasons; don't assume supply stories create permanent price support.

- **South African labor-disruption overweighting:** Every announced wage strike triggers a PL spike. 70% of announced strikes are resolved within 2–3 weeks without causing major supply loss (companies negotiate faster than in past). Traders chase the spike, then get reversed when settlements are announced. Better to wait for strikes to cause *actual* production loss (verified by company guidance), not just announcements.

- **Jewelry demand misjudgment:** Platinum jewelry is small (40% of demand, not all jewelry is tradeable into). Chinese wedding season gets overstated; actual jewelry buying is lumpy and data-poor. Traders extrapolate one strong Chinese PMI print into a "platinum jewelry rally" that never materializes. Rely on Chinese jewelry export data (not PMI), and even then size small.

- **Recycling lag blindness (same as PA):** When PL prices spike on supply fears, recycling ramps 9–18 months later. Traders buying dips on supply tightness get caught when recycled platinum floods market and prices fall 25–30% a year later. Supply stories have delayed feedback; don't hold supply-driven rallies as structural longs.

- **Real-rate correlation overweighting:** PL's correlation with real rates (−0.35) is half that of gold (−0.50). Traders assume "rates fall = PL rallies" (like gold) and get wrong-footed when industrial demand weakness overrides the macro signal. PL does NOT rally as hard as gold when rates fall; watch for divergence.

- **Diesel demand flip blindness:** When EU auto sales surprise to downside, traders assume it's cyclical (recovers next quarter). They miss the structural shift: diesel % of sales is rolling over permanently (EV adoption). A 5% miss in diesel car sales is not noise—it's the trend. Multiple misses in a row signal permanent demand loss, not cyclical weakness.

## Liquidity profile

- **Average daily volume (front month):** ~8–15k contracts/day (NYMEX PL; lower than PA despite larger contract size due to fewer specs and hedgers; declining secular trend as diesel demand falls).
- **Open interest trend:** ~20–40k contracts open interest on front month; declining −5% YoY (structural diesel headwind, EV adoption).
- **Pre-open / post-close behavior:** Electronic market on CME Globex (5:00 PM–3:00 PM CT) is ~25–30% of pit volume; spreads widen 2–4x during pit close (3:00–5:00 PM CT). Be cautious holding overnight without tight stops.
- **Session with best fills:** 1:30 PM–3:00 PM CT (NY pit peak, overlaps London close). Tightest spreads, best volume. Avoid early morning (6:00–8:00 AM CT) for large size.
- **Roll characteristics:** Positive roll yield (backwardation common, front-month premium). Carry traders favor PL for roll income; attracts some buy-and-hold specs. Roll spreads typically 20–50 ticks during normal market.

## Options (if applicable)

- **Weekly / monthly / quarterly expirations:** Quarterly expirations (Jan, Apr, Jul, Oct) standard. Monthly expirations available but sparse (lower liquidity). Weekly options rare (almost no OI).
- **AM vs PM settlement:** NYMEX PL options settle electronically (not pit); cash-settled, 2 business days after expiration.
- **Typical IV rank range:** Platinum IV clusters 35–65% IV rank historically. Supply shocks can drive IV >70%; quiet periods see IV <30%. IV mean-reverts over 2–4 weeks.
- **Pin-risk behavior:** Low concern on PL (sufficient contract size and volume). Monitor large OI (>2k contracts) on strike clusters within 2–3% of front contract's settlement; delivery squeezes rare but possible in tight supply scenarios.

## Risk notes

- **Gap risk profile:** PL gaps on South African supply news and EU automotive data. Monday opens (after weekend strike announcements or Eskom updates) can gap 2–4% up or down. Risk management: size small overnight, use tight stops (30–50 ticks max per contract).
- **Limit-up / limit-down mechanics:** PL limit moves are 2% (or $2.00/oz) per day. In extreme supply scenarios (e.g., major mine flood, prolonged national strike >4 weeks), PL can hit limit moves. Rare, but happened during COVID (2020 South African lockdowns drove limit moves). This creates exit risk if you're on wrong side.
- **Worst weekly move in last 5 years:** −16% (Mar 2020, COVID demand destruction). +14% (Feb 2022, Russia-sanctions-spillover fears into South African supply). Worst single-day move: −12% (Mar 2020).
- **Tail-risk events to remember:**
  - Mar 2020: COVID lockdowns tanked automotive demand globally; PL crashed −30% in 3 weeks.
  - Dec 2015: South African electricity crisis (Eskom load-shedding); PL spiked +12% on supply concerns, then gave back 8% when production resumed.
  - 2018: Major wage strikes at Amplats and Impala (longest in decades); PL traded in wide range, squeezed 8% higher, then reversed on settlement news.
  - 2016–2017: Diesel-gate aftermath (VW scandal fallout); EU diesel regulations tightened; initial PL weakness as demand fell, then stabilized.

## References

- **CME product page:** https://www.cmegroup.com/trading/metals/precious/platinum.html
- **South African mining data:** Amplats investor relations (quarterly production reports), Mining Weekly (strike news), Eskom status (power cuts).
- **EU automotive data:** SAAR reports from ACEA (European Automobile Manufacturers' Association), published monthly.
- **Chinese jewelry demand:** Chinese jewelry export data (Ministry of Commerce), Chinese manufacturing PMI (NBS), Chinese wedding-season industry reports (Shenzhen jewelry associations).
- **Indian jewelry imports/demand:** Ministry of Commerce India data, gold/jewelry import statistics.
- **Recommended reading:**
  - Johnson Matthey PGM Market Report (quarterly and annual). Excellent supply-demand breakdown by end-use.
  - Anglo American investor presentations on PGM demand trends. Best source for auto-industry positioning.
  - Amplats, Impala, Lonmin earnings call transcripts (quarterly). Direct guidance on production, strikes, costs.
  - Reuters / Financial Times articles on South African mining labor (weekly monitoring).

---

## Analyst notes

Platinum occupies an awkward position in 2026: it is a precious metal (benefits from risk-off, real-rate weakness) but with dominant industrial exposure (diesel autocatalysts) in structural decline. This creates a hybrid risk profile where PL can rally hard on supply shocks or macro stimulus (like gold) but then reverses sharply when the secular EV/diesel headwind reasserts. It is more liquid and less volatile than PA (palladium), making it suitable for tactical, medium-term trading, but not for structural long positioning.

The South African supply concentration (80% of world supply) creates recurring shock risk: strikes happen 1–2x per year, power outages are frequent, and mine accidents are unpredictable. These shocks generate 2–6% gaps with 3–10 day follow-through, making PL attractive for event-driven traders willing to monitor overnight news.

The diesel secular decline is the bear case. EU diesel car sales are down −40% from 2015 peak; EV penetration is >20% in major markets and accelerating. Long-term PL demand for autocatalysts is in decline, even as short-term supply can squeeze prices. This structural headwind suppresses long-term valuations and caps multi-month upside rallies. Any trader holding PL into automotive earnings season risks getting whipped by margin guidance that flags PGM input cost pressure.

**Current regime context (Apr 2026):** EU automotive production is stabilizing but diesel sales continue structural decline. South African labor is elevated risk (wages, power shortages) but no major strikes imminent. Jewelry demand in China is steady on yuan stability. Real rates are moderate, creating neutral macro backdrop for PL. Recommend tactical positioning on supply shocks or EU demand surprises (both tradeable 1–3 week moves), but avoid structural longs. Size small (1–2 contracts max) and use tight stops (30–50 ticks) to manage gap risk on overnight news.

