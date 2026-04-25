---
type: product_deep_dive
symbol: BZ
sector: energies
analyst: Fund Engineer
updated: 2026-04-25T09:15:00Z
---

# [[BZ]] — Intercontinental Exchange (ICE) Brent Crude

## Contract specs

- **Exchange / product code**: ICE Futures Europe / BZ
- **Unit**: 1,000 barrels (each contract = 1,000 bbl; one tick = $0.01 per barrel = $10 per contract)
- **Tick size / tick value**: 0.01 USD per barrel; $10.00 per contract (1 point = 100 ticks = $1,000)
- **Contract months**: Monthly expirations up to 10 years forward; actively traded in front 12 months
- **Session hours**: 
  - ICE London: 08:00–17:00 GMT (RTH), Mon–Fri
  - Globex (CME / Nymex equivalent spread trading): 23:00 CT Sunday–22:00 CT Friday (23 hours)
  - High overlap with WTI (CL) session 13:30–17:00 GMT / 08:30–12:00 CT
- **First notice / last trading day**: Typically 10 business days before the delivery month; delivery period Brent Schedule (15–25th of delivery month depending on grade/stream)
- **Settlement**: Physical delivery (Brent Blend crude, North Sea, net-settled against dated Brent or cash settlement)
- **Margin** (Topstep / retail broker): ~$2K–$3K initial, ~$1.5K maintenance (varies by broker and IV; check live)

## What it actually is

Brent crude futures (BZ or BRNT.ICE) are the global benchmark price for European and non-US crude. The contract obligates physical delivery of 1,000 barrels of Brent Blend crude (sourced from the North Sea and other FSU/Urals suppliers) or cash settlement. Brent Blend is a specific quality grade (32–35° API, ~0.4% sulfur); it's the reference for ~60% of global crude pricing. Unlike WTI (CL), which is a US-domestic contract, Brent is the "world" crude—used by European refiners, Asian traders, and integrated oil companies for hedging and speculation. Brent is more liquid than CL on a global basis; prices in USD/bbl and are the primary reference for OPEC pricing announcements, long-term supply contracts, and macro crude allocations.

## Primary drivers

Ranked by impact in 2024–2026 regime:

1. **Global macro / recession risk**: Brent is the world crude; demand shocks (China slowdown, global growth shock, energy-intensive sector weakness) hit Brent harder and faster than WTI. A hard recession drops Brent 20–40% within weeks (2008, 2020 Covid shock examples). Soft slowdowns have muted impact. The market prices recession tail risk into equity vol (VIX) with a 2–5 day lag.

2. **OPEC+ production decisions and supply shocks**: OPEC+ (Saudi Arabia, Russia pre-sanctions, UAE, Kuwait, Iraq, etc.) controls ~30% of global supply. Production cuts announced at biannual summits (June, December) are the single largest regime-shift events. A 1M bbl/day cut = ~15–20 bps move in Brent over 1–2 weeks. Russia sanctions (Feb 2022 onwards) removed ~3M bbl/day from OPEC+ production, creating structural premium for non-sanctioned crude. Ukraine/geopolitical shocks spike Brent 5–15% in days.

3. **Refinery utilization and product cracks (spread to refined products)**: Global refinery utilization (currently ~85–90% post-2022 reset) drives throughput and demand for crude feedstock. When refineries run hard (high throughput), crack spreads (e.g., Brent → gasoline/diesel) tighten, lifting crude. When refineries cut runs (maintenance, weak demand), crude weakens. Post-2020, refinery closures in Europe reduced demand permanently; this keeps Brent structurally capped relative to pre-pandemic baseline.

4. **US Dollar strength (DXY)**: Crude is priced in USD; a strong USD makes crude more expensive for foreign buyers, reducing demand. A 5% move in DXY historically correlates to a −3 to −5% move in Brent (inverse, lagged 1–5 days). The correlation strengthened post-2022 (oil-FX arbitrage trade is more active).

5. **Supply disruptions (geopolitical, weather, technical)**: Surprise outages (e.g., Niger coup Feb 2023, Saudi Aramco pipeline damage, Libyan port closures, North Sea storms) spike Brent 2–8% in days. The impact decays quickly if production is restored. Anticipation of disruption (e.g., "Iran sanctions could add $X/bbl") prices in gradually over weeks.

6. **Chinese crude inventory and economic data**: China is the world's largest crude importer (~10M bbl/day); crude imports and inventory fills drive 20–30% of global seaborne demand. When China's economic data weakens or stimulus weakens (growth slowing), import demand falls, pressuring Brent. Strategic Petroleum Reserve (SPR) builds/releases in the US and China's reserve fills are watched closely.

## Key correlations

**Positively correlated:**
- [[CL]] (WTI crude): 0.85–0.95 correlation (very strong). Both respond to global crude demand; WTI trades at a discount to Brent (currently ~$1–$3/bbl due to US export restrictions pre-2015, now structural due to Light Sweet premium). Spread (Brent–WTI, or "BZ–CL spread") is traded separately; spread typically 0–3 bbl difference, but can widen in supply disruption scenarios.
- **Global equities (ES, NQ, STOXX, Hang Seng)**: 0.35–0.55 correlation (moderate-to-strong in risk-on, weak in risk-off). Crude is a "risk asset"; in equity sell-offs, Brent often drops faster than equities (correlation inverts to −0.2 to +0.1 in panic). Lead/lag: equities often move first; crude follows 2–24 hours.
- **Real yields (10Y TIPS, DGS10−inflation)**: 0.3–0.5 correlation (moderate). Higher real yields signal slower growth (equities also down), reducing energy demand. The link is indirect (via growth expectations).
- **Rates differentials (US vs. EUR, JPY)**: 0.2–0.4 (weak). When US rates rise relative to global (widening carry), USD strengthens, crude falls.

**Negatively correlated:**
- **US Dollar (DXY, spot USD/EUR)**: −0.35 to −0.55 (moderate-to-strong inverse). Strong dollar makes crude expensive for non-US buyers; demand falls. Lag: 1–5 days.
- **Equity volatility (VIX)**: −0.3 to −0.5 in normal regimes; flips to +0.1–+0.3 in extreme geopolitical (Syria, Iran, Russia sanctions) due to supply-shock premium. In Covid sell-off (Mar 2020), VIX spiked and crude crashed together (both are risk-off).
- **Chinese economic data surprises** (PMI, GDP growth, credit growth): Weak surprises correlate −0.2 to −0.4 with Brent 1–5 days later.

**Lead/lag:**
- OPEC+ production announcements → Brent reprices within 30 min. Most of move is within day 1; follow-through over 1–2 weeks as supply actually tightens.
- Geopolitical news (sanctions, war, coup, pipeline attack) → Brent spikes within 15 min to 2 hours; hold duration depends on supply impact (if 1M+ bbl/day disrupted, rally holds for weeks; if minor, fades in hours).
- Global growth shocks (China stimulus, Fed pivot, recession signal) → equities move first; Brent follows 6–48 hours with lag.
- US economic data (employment, manufacturing) → lag depends on asset class; Brent typically follows equities by 4–24 hours.

## Recurring patterns

**Seasonal:**
- **Winter (Dec–Feb)**: Northern Hemisphere heating demand + North Sea weather disruptions (storms, platform maintenance). Volatility elevated. Brent typically $2–$4/bbl higher than summer baseline. Maintenance cycles on North Sea platforms also occur (late winter is peak for turnarounds).
- **Summer (June–Aug)**: Refinery maintenance season in Europe; throughput lower. Demand steady but not peak. Seasonal dip into July–August (lowest demand typically Aug).
- **Spring / Fall (March–May, Sept–Nov)**: Transition periods. Shoulder-month volatility is moderate; spreads widen. Refinery turnarounds wind down (end of May); demand begins seasonal climb in fall.
- **Chinese New Year (late Jan–Feb)**: Asian refining demand often dips 1–2 weeks around CNY; Brent can show 2–5% pullback into the period, then rebound. Structural; happens annually.

**Event-driven:**
- **OPEC+ biannual meetings** (June, December, occasional emergency summits): Largest multi-day volatility events. Market re-prices supply outlook. A production cut announcement: +$2–$5/bbl move over 2 days. Uncertainty ahead of meetings can drive volatility up 20–30% (IV rise). Post-meeting clarity can snap volatility lower.
- **Geopolitical shocks** (sanctions, wars, coups, pipeline attacks): Brent spikes 3–15% intraday; duration depends on supply impact. 2022 Ukraine invasion: +$20/bbl in weeks. 2023 Niger coup: +5% initial, faded within days (low supply impact). Iran nuclear deal negotiations: range-bound with volatility +/- 5%.
- **Chinese economic data** (PMI, industrial output, crude purchases announced): Weak data → 1–3% pressure on Brent, lagged 1–5 days.
- **US energy inventory reports** (EIA crude, distillate, gasoline)**: Secondary impact (Brent more global). But large US drawdown surprises can signal global demand strength; can lift Brent by 1–2% if tied to refining activity.
- **Refinery maintenance schedules** (announced quarterly; shutdowns Feb–May, Aug–Sept typical). Large refinery outages (1M+ bbl/day throughput loss) tighten cracks, supporting Brent by 1–3%.

**Time-of-day patterns:**
- **European morning (08:00–13:30 GMT)**: Highest volume on ICE London floor. Brent sets the tone for global crude markets. Wide two-way participation (major banks, state oil companies, hedge funds).
- **Globex open (23:00 CT US Sunday through London close 11:00 CT)**: Brent continues on Globex. Liquidity varies; tight in US evening, picks up in early morning, then ties to ICE London open at 13:30 CT.
- **London afternoon (14:00–17:00 GMT / 09:00–12:00 CT)**: Overlap with US trading (equity markets, NYMEX). Fund rebalancing and cross-asset flows occur. Good fills; tight spreads.
- **Post-close (post-17:00 GMT)**: Globex only; wider spreads (3–5 ticks typical vs. 1–2 in core hours). Lower volume.
- **Asia open (19:00–23:00 UTC, 14:00–18:00 SGT)**: Medium volume; Chinese traders become active. Sentiment influences but not primary liquidity.

**Calendar quirks:**
- **Contract roll** (15–25 days before expiration): Front month volume shifts to next month. Spreads widen in the expiring month. Contango (normal) makes roll cost-neutral; backwardation (rare, but occurs in supply shocks) forces directional traders to roll at a loss.
- **Expiration week**: Last 5 days of contract. Bid-ask widens significantly; avoid execution if possible. Final day (first trading day of delivery month) is essentially illiquid for speculative traders.

## Common setups

1. **OPEC+ surprise cut / production concern + breakout**
   - *Trigger*: OPEC+ announces production cut or supply disruption (e.g., Saudi output reduction announced). Brent gaps up; check close above prior resistance (often prior month high or 50-day MA).
   - *Entry*: Long if gap holds and price closes above resistance in first 2–3 hours of trading.
   - *Stop*: Below the gap low. Typical: 0.50–1.00 (50–100 ticks).
   - *Target*: Prior swing high or 1.5–2x the gap size; often multi-day follow-through into technical resistance.
   - *Invalidation*: Close back below entry within 4 hours (news reverses or traders take profit).
   - *Hit rate*: ~55–65% (event-driven setup; OPEC cuts have been structurally bullish since 2016 (OPEC+ formed); false breaks less common than with weather/macro).

2. **DXY spike (strong dollar) + Brent weakness setup (fade)**
   - *Trigger*: DXY rallies 1%+ in a session (rates rise, USD demand). Brent sells off 1–2% correlatively. Overshoot setup: if DXY rises >1.5% in day, Brent often overshoots lower (technical capitulation, algos selling).
   - *Entry*: Short Brent if DXY gap up >1.5% and Brent breaks below prior daily low (swing low of last 3 days).
   - *Stop*: Above the gap high of the DXY rally day. Typical: 0.75–1.50.
   - *Target*: Next technical support (20-day MA, prior week low, or 61.8% retracement of prior rally).
   - *Invalidation*: DXY reverses >50% of its gain; Brent bounces back above entry.
   - *Hit rate*: ~45–55% (weaker setup than OPEC event; requires confirmation from technicals; false breaks common).

3. **Chinese stimulus / growth shock + reflex rally (anticipation play)**
   - *Trigger*: Chinese policymakers announce stimulus (rate cut, bank lending easing, infrastructure spending). Market prices in demand recovery. Brent rallies 2–5% over 2–5 days as hedge funds frontrun demand.
   - *Entry*: Long on stimulus news if Brent breaks above prior day's high in the first 2 hours. Or scale into dips during the 2–5 day rise.
   - *Stop*: Below yesterday's low (recent support). Typical: 0.50–1.00.
   - *Target*: Prior swing high or 1–2% gain if stimulus fully prices in; trail stop 2–3% above entry once in the money.
   - *Invalidation*: Follow-up data shows stimulus didn't boost activity (lag effect); Brent rolls over.
   - *Hit rate*: ~50–60% (stimulus trades are crowded; execution and timing matter. Chinese policymakers often deliver on announcements 4–12 weeks out, so initial pop can reverse if data doesn't follow).

4. **Refinery crack weakness (refined products weaker than crude, mean reversion)**
   - *Trigger*: Crack spread (Brent → RBOB + ULSD) compresses sharply (spreads drop >15% in 2–3 days). This signals refinery demand weakness. Contrarian setup: crack weakness has historically been a short-term floor for Brent (at 15–20% discount to pre-crack-collapse, Brent value becomes attractive).
   - *Entry*: Long Brent if crack spread is >2 standard deviations compressed (screener: crack < 25% of 90-day average). Enter on a bounce/technical support.
   - *Stop*: Below the low of the crack-collapse day. Typical: 0.50–1.00.
   - *Target*: 50-day MA or 1–2% mean reversion; exit on crack stabilization.
   - *Invalidation*: Cracks collapse further (structural refinery demand loss, as happened in 2024 with European refinery closures). Re-evaluate thesis.
   - *Hit rate*: ~45–50% (mean reversion plays are lower-probability than trend-following; fit is best in choppy / non-trending markets).

## Classic traps

- **Geopolitical spike + fade**: News of a Middle East escalation hits; Brent rallies 5–10% in hours. Market prices in 1–3M bbl/day supply loss. But within 3–7 days, if actual supply loss is smaller or diplomatic resolution emerges, the premium fades. Traders who bought on the spike often face hard reversals.

- **OPEC+ announcement disappoint**: Market expects a 2M bbl/day production cut. OPEC+ announces only 1M bbl/day cut. The surprise to the downside causes a sharp selloff (3–8% in hours) as longs liquidate. Trap: going long expecting cuts on the morning of the announcement—surprise reversals are common.

- **Chinese stimulus trap**: Stimulus is announced; Brent rallies 3–5% over 2–3 days. But if follow-up data (PMI, industrial output) doesn't show demand recovery, the rally fades. Longs who bought mid-rally get stopped out.

- **DXY whipsaw**: US data beats; DXY rallies; Brent sold off on algo correlation. But if fed-cut expectations also rise (higher growth = lower rates ahead), the DXY rally reverses within hours. Shorts on the DXY spike get whipsawed.

- **Contango curve trap**: Brent is deeply in contango (front month discount). Retail traders short the far contracts thinking they'll converge. But if supply cuts happen, the far months rally more (supply loss extends into future). Contango shorts can face unlimited losses if curve inverts.

- **Roll-period slippage**: Entering a position 3–5 days before contract expiration. Spreads widen from 1–2 ticks to 5–10 ticks. Stop gets hit from slippage, not price movement. Avoid entering in final expiration week.

- **Overnight Asia move + gap to London open**: Shanghai/Singapore trading (17:00–23:00 UTC) sees a Brent selloff (China weakness news). By London open (08:00 GMT), the move is partially reversed. A trader who shorted overnight gets whipsawed by the bounce.

- **Overleveraged fund redemption**: Happens rarely but heavily. A major hedge fund faces redemptions (e.g., Archegos 2021, or a crypto/SPX fund in drawdown). They liquidate all positions including long crude. Brent can spike down 10–15% in hours from forced selling. Shorts caught in the spike covering, then recovery. Timing is impossible to predict; hedge by avoiding outsized leverage during peak redemption windows (quarter-end, month-end, especially after equity drawdowns).

## Liquidity profile

- **Average daily volume** (front month): 300k–600k contracts in normal regime; 800k–1.2M during vol events (OPEC meetings, geopolitical). Summer (Apr–Aug) sees 200k–400k (lighter).
- **Open interest trend**: ~500k–800k for front month; typically 2–3x greater than WTI (CL) open interest. Back months are significantly thinner (<100k OI).
- **Pre-open / post-close behavior**: ICE London opens 08:00 GMT with wide spreads (3–5 ticks); tightens by 09:00. Globex closes at 22:00 CT (post-London close); spreads widen to 3–8 ticks post-17:00 GMT.
- **Best session for fills**: 09:30–17:00 GMT / 03:30–12:00 CT (peak London + partial US overlap). Fills are tight (1–2 ticks) and predictable.
- **Bid-ask spread**: 0.01–0.02 (1–2 ticks) in core hours; 0.03–0.05 (3–5 ticks) outside peak session and post-expiration.
- **Slippage profile**: Market orders in core hours expect fill at mark ±1–2 ticks. Outside hours, ±3–8 ticks typical. Limit orders with 2–3 tick tolerance fill >95% of the time in peak session.

## Options (if applicable)

- **Listed expirations**: Monthly (3rd Thursday). Quarterly (end of Q) also popular for medium-term hedges.
- **Weekly expirations**: Some brokers offer; less common than for crude (CL) and NG.
- **Settlement**: European-style (exercise only on expiration date); cash-settled on ICE BFOE (Brent Front Offtake Exchange) mid-price.
- **Typical IV rank range**: 
  - Normal backdrop: 35–65th percentile IV.
  - Geopolitical risk periods (Iran sanctions, Middle East escalation): 70–95th percentile IV.
  - Post-OPEC cuts / production discipline periods: 40–60th percentile IV.
- **Volatility term structure**: Typically upward-sloping (back months higher IV than front) reflecting uncertainty about future supply/demand. Inverts during acute geopolitical (front month spiked IV from supply shock).
- **Pin-risk behavior**: Minimal compared to equities. Expirations can see last-minute skew trades, but typical Brent expirations don't exhibit clustering around strikes. Assignment is physical delivery for unrolled short calls/puts; retail rarely face assignment due to cash settlement being primary.

## Risk notes

- **Overnight gap risk**: Brent trades Globex 23:00 CT Sunday–22:00 CT Friday, then ICE London opens at 13:30 CT (08:00 GMT) Monday–Friday. Asia session (Shanghai, Singapore, Dubai) runs during Globex hours (14:00–22:00 UTC). A major news event overnight (geopolitical, OPEC surprise, Chinese data) can gap Brent 2–5% at London open. Stops placed on Globex often get run before London open market order fills.

- **Limit-up / limit-down mechanics**: ICE Brent has no daily price limits under exchange rules. However, market can be halted for "disorderly" trading. In extreme cases (2022 Ukraine shock), Brent traded with 15+ minute halts as circuits trigger. No circuit breaker per se, but trading halts can lock positions in place temporarily.

- **Worst weekly move in last 5 years**: 
  - Feb 2022 (Ukraine invasion): Brent spiked from $92 → $120/bbl (+30%) in first 2 weeks.
  - June 2022 (China lockdown reversal, OPEC+ increase): Brent fell from $120 → $100 (−17%) in week.
  - March 2023 (banking crisis + Saudi output cut): Brent rallied from $75 → $88 (+18%) in 10 days.
  - Oct 2023 (Israel-Hamas, supply concern): Brent rallied from $82 → $98 (+20%) in 3 weeks.

- **Tail-risk events to remember**:
  - **Ukraine invasion (Feb 2022)**: Geopolitical shock; Russia removed from OPEC+; supply concern spiked Brent to $120/bbl (highest since 2014). Impact extended 6+ months.
  - **China zero-Covid reversal (Dec 2022)**: Sudden pivot to openings; demand expectations reset. Brent rallied from $80 → $88 over month.
  - **Saudi-Russia OPEC+ production cuts (2016 onwards)**: Structural shift from competition-driven to production-discipline model. Supports crude prices above $40–$50 floor long-term.
  - **Suez Canal blockage (Mar 2021, Ever Given incident)**: Showed single-point-of-failure risk for global oil supply routing. Brent premium held +$0.50/bbl for months.
  - **Iran nuclear deal on/off cycles** (2015, 2018, 2023 negotiations): Deal prospects reduce sanctions; Brent premiums fade. Deal collapse prospects spike Brent 2–5%.
  - **North Sea Ekofisk fields outage (2016)** and other megafield incidents: Demonstrate single-platform disruptions can move 5%+ if production >1M bbl/day.

## Comparison to CL (WTI)

- **Brent is global; WTI is US-centric**. Brent more sensitive to non-US shocks (China, OPEC, geopolitical).
- **Brent liquidity is higher** (particularly on ICE London). CL higher on NYMEX, but Brent is the "world" crude.
- **Brent trades in GBP / euro impact**. Changes in EUR/USD affect Brent valuations (to a lesser degree); WTI is pure USD.
- **BZ–CL spread (Brent–WTI)** currently ~$1–$3/bbl (Brent premium). Spread widens during supply disruptions (Brent gains supply protection value). Historically narrow near parity.
- **Seasonality slightly different**: Brent peaks in winter (heating demand + North Sea storms); WTI peaks in summer (US driving season). Both correlate 0.85–0.95, so spread seasonality is the dominant variation.

## Takeaway for portfolio construction

Brent is the primary hedging vehicle for global oil exposure. It's more liquid than WTI and responds to global macro faster. Entry-level traders should trade Brent for macro directional views (stimulus/recession, geopolitical risk) and WTI for US-specific setup (refinery, storage, supply). A long Brent / short WTI spread (selling the Brent premium) can hedge if expecting mean reversion.
