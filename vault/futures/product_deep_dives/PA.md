---
type: product_deep_dive
symbol: PA
sector: Precious Metals
analyst: Fund Engineer
updated: 2026-04-25T18:45:00Z
---

# [[PA]] — NYMEX Palladium

## Contract specs

- Exchange / product code: NYMEX (CME Group) / PA
- Tick size / tick value: $0.01 per troy oz = $10 per tick (micro: $0.001 = $1 per tick on PL, if it exists)
- Contract months (delivery cycle): Jan, Mar, Jun, Sep, Dec (front 3 months most liquid; far months illiquid)
- Session hours (RTH and extended): Sunday–Friday, 5:00 PM–3:00 PM CT next day (23-hour session with brief close 3:00–5:00 PM CT)
- First notice / last trading day: 3rd to last business day of contract month
- Settlement: Physical delivery (100 troy oz per contract)
- Margin (initial / maintenance at Topstep, if known): Typically $8–12k initial, $6–9k maintenance (higher volatility, smaller contract → tighter leverage)

## What it actually is

Palladium (PA) is a NYMEX precious metals contract representing 100 troy ounces of refined palladium bullion. Unlike gold and silver, palladium is primarily an industrial metal with ~85% of global demand derived from autocatalysts (catalytic converters in gasoline engines). The remainder is jewelry (~8%), electronics (~4%), and dental/other (~3%). This heavy industrial skew makes palladium fundamentally different from traditional "precious metals"—it is more analogous to a hybrid between copper (industrial commodity) and gold (volatile, liquid, macro-sensitive). Hedgers include primary producers (Norilsk Nickel, Anglo American), auto OEMs (BMW, Mercedes, Toyota), and recyclers recovering catalytic material; speculators include macro funds, volatility traders (PA is highly leveraged and prone to short squeezes), and supply-focused long-term investors.

## Primary drivers

Ranked by influence in current regime (Apr 2026—EV adoption disruption, Russian sanctions compliance, autocatalyst demand stalling):

1. **Auto production cycle (global vehicle sales, light-vehicle production index)** — The dominant driver. When global light-vehicle production rises (China, EU, US), autocatalyst demand accelerates; when it falls (recession, EV transition), demand collapses. Current regime faces headwind: EV adoption (zero PGM in BEVs) is eroding gas-car fleet at ~5–8% annually globally. This is a secular headwind palladium traders cannot ignore.

2. **Russian supply disruption / geopolitical risk** — Norilsk Nickel (Russia) is the world's largest primary palladium producer (~40% of primary supply). Sanctions, export restrictions, and production cutbacks directly constrain supply. PA is prone to supply-shock rallies; any Norilsk news (labor, sanctions tightening, production halt rumors) can spark short squeezes. Secondary suppliers (South Africa ~20%, Canada ~10%) have no spare capacity to offset Russian outages.

3. **Jewelry demand (India, China, EM currency crises)** — Though smaller (~8% of demand), jewelry is price-sensitive and can swing fast. Strong INR (India gold/jewelry demand proxy) or yuan weakness (China discretionary spending) can shift palladium allocations. Also acts as safe-haven hedge in EM currency crises.

4. **Real rates and USD strength (DXY, 10Y TIPS yield)** — Secondary macro driver. PA is priced in USD and is negatively correlated with real rates (r ≈ −0.40), but less so than gold or silver because industrial demand dominance mutes interest-rate sensitivity. Strong USD still suppresses via import demand.

5. **Recycling supply and catalytic converter scrap flows** — Medium-term supply-demand balance. In tight supply environments, recycling (returning ~40% of total supply in normal years) accelerates, creating a supply feedback loop. High prices → higher scrap recovery → eventual supply relief (with 1–2 yr lag).

## Key correlations

- **Positively correlated with:**
  - [[GC]] Gold (r ≈ +0.50–0.65). Both are precious metals and respond to macro risk-off, but palladium lags on industrial demand weakness.
  - [[SI]] Silver (r ≈ +0.45–0.55). Similar macro drivers, but PA is less sensitive to jewelry demand (the dual-driver advantage).
  - [[CL]] Crude Oil (r ≈ +0.35–0.50). Proxy for global growth; higher oil → higher auto production → higher PGM demand.
  - [[HG]] Copper (r ≈ +0.40–0.60). Both are industrial commodities tied to global manufacturing and EV transition risk.
  - Global equities ([[ES]], [[NQ]], ex-China) during expansion phases (r ≈ +0.45–0.65).

- **Negatively correlated with:**
  - [[ZB]], [[ZF]] (T-Bonds, T-Notes); real yields (r ≈ −0.40 inverse). Weaker correlation than gold because industrial demand is less rate-sensitive.
  - [[6E]] EUR/USD (r ≈ +0.35 inverse during EU risk-off). EUR weakness → European auto demand headwind.
  - EV adoption indices / EV sales growth rate (secular headwind, not tradeable directly, but visible in Q4 earnings calls).

- **Lead/lag relationships:**
  - Global vehicle production (published monthly) leads PA by ~2–4 weeks. Disappointing auto-assembly data often presages PA weakness.
  - Shanghai copper (SHFE CU) often leads PA by 1–3 trading sessions on China growth sentiment (both tied to manufacturing PMI).
  - Norilsk Nickel disruption news breaks on Russian media first, then PA gaps on open (0–2 hr lead on Western exchanges waking up).

## Recurring patterns

- **Seasonal (calendar effects):**
  - Jan–Feb: Post-holiday seasonal weakness; auto production ramps slowly. PA often trades lower on seasonal inventory drawdown (fewer new vehicles rolling off production lines).
  - Mar–Apr: Spring pickup in vehicle sales (tax refunds, Easter promotions in EU). PA can rally on production pickup signals. **Current season—watch for Q1 production data.**
  - May–Jul: Peak production season (northern hemisphere summer factory runs, pre-CAFE standard resets). Higher demand, but also higher spot prices limit speculative long positioning.
  - Aug–Sep: Post-summer inventory adjustments; some production cutbacks in Europe (summer shutdowns). Often consolidation range.
  - Oct–Nov: Q4 production ramp (year-end dealer deliveries, new model-year launches in US). PA strength expected unless recession fears flare.
  - Dec: Year-end liquidation and tax-loss selling; typically weakest month for speculative longs. Hedgers often roll or cover ahead of holidays.

- **Event-driven:**
  - Global vehicle production reports (published monthly by IHS Markit, SAAR data from US/EU automakers). Upside surprise → rally; downside → selloff (−2 to −5% moves common).
  - Fed/ECB policy decisions (especially EV subsidy changes, automotive tariffs, environmental regulations affecting PGM recycling standards).
  - Norilsk Nickel announcements (earnings, dividends, production guidance, sanctions compliance updates). Any supply tightening → short squeeze.
  - Catalytic converter theft waves (seasonal in urban areas, Q4 spike; tight supply stories emerge when thefts drop scrap availability).
  - Auto earnings seasons (Q1, Q3). Margin guidance on PGM input costs can shift sentiment.

- **Time-of-day patterns:**
  - London open (12:00 PM UTC = 6:00 AM CT): European auto sector sentiment can set tone for NY session. Manufacturing data often releases here.
  - NY open (1:30 PM CT): NYMEX pit opens; typically see volume spike and tactical profit-taking on overnight gaps.
  - NY midsession (2:00–4:00 PM CT): Institutional desk rebalancing, fund unwinding. Lower volatility by late afternoon.
  - Overnight (5:00 PM–midnight CT): Lower volume, wider spreads; stop-hunting and gaps common on supply news.

- **Calendar quirks:**
  - Roll windows (last 2 weeks of contract month): Front contract can widen/narrow spread vs. next month on carry and delivery logistics. Watch for delivery-month squeezes (PA is smaller contract, easier to corner).
  - Month-end (last 3 days of contract): Technical unwinding, rebalancing, and often gap risks if supply news breaks overnight.
  - Q1 earnings season (late Jan, late Apr): Auto OEM margin guidance surprises can shift multi-week trends.

## Common setups

1. **Auto Production Breakout (mean reversion on production surprise)**
   - **Trigger:** Global vehicle production beats or misses expectations by >5%. If beat, PA rallies on demand optimism; if miss, expect −2 to −3% move lower. Data is published monthly (usually early in month).
   - **Invalidation:** If the production miss is offset by supply disruption news (Norilsk alert), the correlation flips and PA rallies on supply tightness instead.
   - **Exit:** Close or scale after 3–5% move (typical range), or hold if the trend extends beyond weekly high/low.

2. **Norilsk Supply Shock (gap and follow-through)**
   - **Trigger:** Breaking news of Norilsk production halt, sanctions tightening, labor action, or environmental shutdown (watch Russian news overnight). PA gaps up 3–8% on open or overnight.
   - **Invalidation:** If news is minor (e.g., brief labor strike resolved within 48 hrs), PA often reverses the next day on short covering relief.
   - **Exit:** Ride the move for 1–3 days, but watch for short covering rallies (where shorts panic-buy, causing a spike, then fade). Better to exit on secondary spike than the primary gap.

3. **Real-Rate Reversion (macro-driven mean reversion)**
   - **Trigger:** 10Y TIPS yield spikes >0.5% or falls <−0.3% in a single session. PA typically inverse-correlates with real rates on multi-day moves. Falling real rates (Fed pivot fears) → PA rally; spiking rates → PA weakness.
   - **Invalidation:** If the yield move is driven by inflation panic (not rate expectations), commodities actually tend to rally together, so PA may not inverse as expected.
   - **Exit:** Hold for 2–5 days or until the yield move reverses; take profits at extremes (PA up 5–7% on strong real-rate drop).

## Classic traps

- **The EV transition illusion:** Many traders view high PA prices as a sign of tight supply; they miss the long-term EV demand headwind. A 30% rally on Norilsk news looks bullish until you realize EV sales growth is −5% YoY. Avoid holding PA through earnings seasons; the longer-term trend is bearish despite near-term squeezes.
- **Short squeeze desperation:** PA's small contract size ($10/tick, 100 oz contracts) makes it prone to violent short squeezes on supply rumors. Traders get whipped in and out; avoid chasing the spike. Wait for the second day to fade into squeeze rallies.
- **Recycling lag blindness:** When PA prices spike, recycling ramps 6–12 months later. Traders who buy dips on supply tightness often get caught when recycled supply hits and prices fall 20–30% 9 months later. Supply stories have delayed feedback.
- **Autocatalyst demand noise:** Auto production can be lumpy (plant shutdowns, model-year transitions). A single month of lower production doesn't signal demand collapse; look at rolling 3–6 month average. Single-month overreactions are trade-killing traps.
- **Russian news overweighting:** Every sanctions rumor sparks a PA spike. 80% of these rumors never materialize into actual supply loss (Norilsk finds workarounds, grey-market export paths). Filter out headline noise by checking whether actual *production* has fallen, not just whether headlines exist.

## Liquidity profile

- **Average daily volume (front month):** ~20–40k contracts/day (NYMEX PA pit + electronic; down 20% vs. 2020 due to EV transition and algorithmic fragmentation).
- **Open interest trend:** ~80–120k contracts open interest on front month; declining secular trend (−3% YoY) as EV adoption suppresses long-term interest.
- **Pre-open / post-close behavior:** Small electronic market exists on CME Globex (5:00 PM–3:00 PM CT); volume is ~30–40% of pit volume, spreads widen 2–3x during pit close (3:00–5:00 PM CT). Avoid holding overnight without a stop.
- **Session with best fills:** 1:30 PM–3:00 PM CT (NY pit peak, overlaps with London close). Tightest spreads, highest volume. Early morning (6:00–8:00 AM CT) has wider spreads, fewer market makers.

## Options (if applicable)

- **Weekly / monthly / quarterly expirations:** Quarterly expirations (Mar, Jun, Sep, Dec) are standard. Weekly expirations on PA are sparse (lower liquidity); monthly expirations also available but less standard than quarterly.
- **AM vs PM settlement:** NYMEX PA options settle electronically (not pit-settled); settlement is cash-based, 2 business days after expiration.
- **Typical IV rank range:** Palladium IV tends to cluster 40–70% IV rank historically. High IV (>70%) often coincides with supply-shock events; low IV (<30%) during quiet consolidation phases. IV mean-reverts over 2–4 weeks.
- **Pin-risk behavior:** Less concern on PA than on equity options due to lower volume, but monitor large open interest (>5k contracts) on strike clusters within 2–3% of the front contract's settlement. Delivery logistics can incentivize pinning on key strikes.

## Risk notes

- **Gap risk profile:** PA is highly prone to overnight gaps on supply news. Monday opens (after weekend Norilsk news, Russian regulatory changes) can gap 3–5% up or down. Risk management: no naked overnight longs without a close stop-loss. If holding overnight, position size should be ≤1 contract until PA stabilizes.
- **Limit-up / limit-down mechanics:** PA limit moves are 3% (or $3.00/oz) per day. In extreme supply-shock scenarios (war, sanctions collapse, major refinery fire), PA can hit limit-up on consecutive days, locking traders out of profitable exits. This happened in 2022 during Russia sanctions (PA hit limit-up 5 days in a row, then crashed −30% in one day when futures were adjusted).
- **Worst weekly move in last 5 years:** −18% (Feb 2022, Russian invasion + short covering cascade). +22% (Apr 2020, COVID supply shock + short squeeze). Worst single-day move: −14% (Sep 2022, recession fears + deleveraging).
- **Tail-risk events to remember:**
  - Feb 2022: Russian invasion triggered supply panic; PA gapped limit-up multiple days. Delivery gridlock and CME emergency margin hikes ensued.
  - Mar 2020: COVID lockdowns tanked auto demand; PA crashed −30% in 3 weeks on demand destruction fears.
  - 2019–2020 diesel scandal echo: EU tightened catalytic converter standards; initial boost to PA, then demand collapsed as Euro-6 adoption killed older diesels faster.
  - 2016–2018: China environmental crackdown (catalytic converter recycling restrictions) boosted PA on constrained supply, then reversed when Chinese stimulus eased regs.

## References

- **CME product page:** https://www.cmegroup.com/trading/metals/precious/palladium.html
- **Norilsk Nickel investor relations:** Primary source for production and sanctions compliance guidance.
- **Global vehicle production data:** IHS Markit (acquired by S&P Global), SAAR reports from VDMA (Germany), SMMT (UK), CAAM (China).
- **Catalytic converter scrap recovery:** ICTA (International Catalytic Traders' Association) reports; lag indicators of future supply.
- **Recommended reading:**
  - Anglo American PGM Market Reports (quarterly); excellent breakdown of demand by end-use.
  - Johnson Matthey PGM Supply-Demand Report (annual); historical and forward production forecasts.
  - CME Metals Magazine articles on supply disruption case studies.

---

## Analyst notes

PA is the highest-risk, highest-leverage precious metals contract due to its small contract size, thin liquidity, and supply concentration risk (Norilsk 40%+ global share). It is suitable only for traders with risk discipline and ability to monitor Russia-related news overnight. The secular EV headwind is undeniable—primary demand (autocatalysts) is in structural decline—but short-term supply shocks can create violent, leveraged squeezes that reward tactical traders willing to size small and cut quickly.

**Current regime context (Apr 2026):** Auto production is stabilizing post-COVID but remains 3–5% below pre-pandemic trend. EV adoption is accelerating (15–20% of new sales in developed markets), eroding gas-car PGM demand further. No major Norilsk supply disruption is imminent, but geopolitical risk premium on Russian supply persists. Recommend light positioning until supply clarity improves; mean-revert rallies (on supply rumors or real-rate drops) are tradeable 1–3 day moves, not multi-week holds.
