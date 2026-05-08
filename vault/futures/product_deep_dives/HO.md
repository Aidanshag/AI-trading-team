---
type: product_deep_dive
symbol: HO
sector: energies
analyst: Fund Engineer
updated: 2026-04-25T01:30:00Z
---

# [[HO]] — NYMEX ULSD (Ultra-Low Sulfur Diesel)

## Contract specs

- **Exchange / product code**: NYMEX (CME) / HO (42,000 US gallons per contract)
- **Tick size / tick value**: 0.0001 per gallon; $4.20 per contract
- **Contract months**: Monthly; active trading in front 12 months
- **Session hours**: RTH 08:00–17:00 CT (floor). Globex: 17:00 CT Sunday–17:00 CT Friday (23 hours, 5-minute gap)
- **First notice / last trading day**: 3 business days before delivery month; delivery period 1st–last calendar day of month
- **Settlement**: Physical delivery (New York Harbor; basis to Gulf Coast refining hubs via pipeline arbitrage)
- **Margin** (Topstep): ~$2.5K initial, ~$1.2K maintenance (varies with volatility; check live)

## What it actually is

HO futures track the wholesale price of Ultra-Low Sulfur Diesel (ULSD, also called "No. 2 diesel" in industry). The contract settles to physical delivery of 42,000 gallons at New York Harbor—the benchmark delivery point for US East Coast and export markets. ULSD is used for transportation (trucks, rail, commercial vehicles), heating oil (residential/commercial heating in cold climates, particularly New England), power generation, and marine fuel (bunker). Unlike crude oil, which is global, ULSD is regional—the East Coast (delivered NYH) has separate pricing from Gulf Coast and West Coast, though arbitrage across regions is constant.

Speculators use HO for directional positioning and spread trading (crack spreads vs. crude, inter-commodity spreads with other refined products). Hedgers (refineries, distributors, transportation fleets) lock in costs.

## Primary drivers

Ranked by impact in 2024–2026 regime:

1. **Crude oil price and refining margins (crack spreads)**: HO is a refined product, so crude (CL) is the dominant input cost. When crude spikes, HO follows with a lag (1–3 hours). Refining margins ("cracks") = HO price − (CL price × 0.42) − RB (gasoline). Thin or negative margins lead refineries to cut runs; that reduces diesel supply, which can support or cap HO. In high-margin periods (post-demand shock, Russia sanctions, supply disruptions), refineries maximize throughput, increasing diesel supply and capping upside. Post-Ukraine (2022–2023), cracks were historically wide; normalization in 2024–2025 is ongoing.

2. **Seasonal demand for heating oil and transportation**: Winter (Oct–Mar) demand peaks for heating oil (East Coast, New England especially; ~20% of US heating demand). Summer (May–Aug) demand is lower for heating, but diesel demand from trucking and agriculture rises. Shoulder months (Apr, Sept–Oct) see lowest demand and volatile spreads. EIA heating oil stocks (released Thursdays with crude stocks) are key indicators.

3. **Global refining capacity and shutdowns**: Refinery closures (especially on East Coast, which has limited local capacity) tighten supply. EU sanctions on Russian fuel imports (2022 onwards) redirected global diesel flows; US refiners could export more, supporting HO. Refinery maintenance (typically spring and fall) reduces HO supply. Outages at key plants (e.g., Philadelphia Refinery, Corpus Christi) move the market.

4. **Export economics**: US ULSD is exported to Latin America, West Africa, and occasionally Europe. When global prices are high relative to US Gulf/East Coast basis, refiners export; when not, domestic supply swells. Transatlantic diesel arb is active; HO vs. ICE Gasoil spread widens or narrows based on geopolitical flow risk.

5. **Weather and transportation disruptions**: Cold snaps and extreme weather reduce trucking (ice) and increase heating demand (Nor'easters). Conversely, mild winters reduce heating demand sharply. Hurricane season (Aug–Oct) can disrupt Gulf Coast refining, raising HO.

6. **Macroeconomic recession risk**: Recessions collapse trucking and transportation demand. 2020 Covid lockdowns saw HO crater (diesel demand fell 30%+). Softer slowdowns have modest impact.

## Key correlations

**Positively correlated:**
- [[CL]] (crude oil): 0.7–0.85 correlation (strong). HO follows CL within 1–3 hours intraday. The relationship is nearly deterministic over short timeframes; divergence signals margin shifts or supply news.
- [[RB]] (RBOB gasoline): 0.6–0.75 (strong). Both refined products; driven by crude, refining margins, and demand. Cracks between the two (RB vs. HO) show refiner capacity choices—when margins are wide, refineries prefer gasoline; when tight, they balance.
- [[NG]] (natural gas): 0.15–0.3 (weak). Both energy; correlated in macro demand shocks (recession), but NG is more weather-sensitive (heating). Not reliable for prediction; often decoupled for weeks.
- **Heating oil stock surprise** (EIA, z-score): 0.3–0.5 (moderate). Larger-than-expected builds (supply surprise) are bearish; draws are bullish. Thursday EIA release moves HO 1–5% intraday.

**Negatively correlated:**
- **US 2Y rates**: −0.2 to −0.4 (weak-to-moderate). Higher rates weaken demand (recession expectations, higher discount rates for future cash flows).
- **Equity indices during demand shocks**: −0.3 to −0.5 in recession; uncorrelated in normal regime.
- **USD strength (DXY)**: −0.1 to −0.3 (very weak). Strong dollar slightly caps export demand.

**Lead/lag:**
- Crude oil move → HO response: 30 min to 3 hours (CL is the lead).
- EIA inventory report (Thursday 10:30am ET) → HO move within 1–5 minutes; ripple through Friday.
- Refinery news (planned maintenance, unplanned outage) → HO move within 1–30 min, then reassessment as supply picture changes.

## Recurring patterns

**Seasonal:**
- **Winter (Oct–Mar)**: Peak heating oil season. Bullish bias, especially Oct–Feb. Volatility high in Nov–Jan when forecast uncertainty is greatest. Feb historically has had extreme moves (Texas freeze 2021, Northeast blizzards frequent). Contango typical as heating season ends.
- **Spring (Apr–May)**: Weakest season; heating demand collapses. Bearish bias. Contango steep (summer supply abundant). Liquidation of winter longs often creates intraday whipsaw.
- **Summer (June–Aug)**: Diesel demand for trucking and agriculture peaks, but refined-product demand overall is modest. Weather-driven (heat can spike power-gen demand). Backwardation typical late summer before fall demand ramp. Very thin trading in July–Aug.
- **Fall (Sept–Oct)**: Transition; bearish-to-bullish. Heating oil stocks build in Sept; volatility drops until cold-snap forecasts appear (late Sept onwards). October is "shoulder" month with low volumes.

**Event-driven:**
- **Weekly EIA inventory release** (10:30am ET Thursdays): Distillate stocks (HO + heating oil) release. Surprise of >3–5% vs. consensus can drive 2–8 tick moves in <5 min. Build surprise (bearish) → sell-off; draw surprise (bullish) → rally.
- **Crude oil surprise gap moves** (EIA Thursday, same time): CL gap up/down often carries HO along within minutes. HO is more stable (lower vol) than CL; HO lags CL's move.
- **Refinery maintenance announcements** (press releases, planned outages): Scheduled maintenance in spring (Mar–Apr) and fall (Sept–Oct) reduces runs; bearish for diesel supply. Unplanned outages (e.g., fires, floods) are bullish (tight supply).
- **Geopolitical / sanctions news**: Russia fuel export restrictions (2022 onwards) tightened global diesel supply; supported US exports and global prices. Similar for other Middle East / North Africa disruptions. News moves HO in 15–60 min.
- **Atlantic hurricane season activity** (Aug–Oct): Forecasts of storms approaching Gulf Coast refineries cause intraday rallies; misses see reversals.

**Time-of-day patterns:**
- **Asian close (6:00am ET)**: Spillover from ICE Gasoil (Europe) if overnight action. Minimal direct impact; mostly sentiment.
- **9:30–14:00 ET**: Core US session. HO trades with moderate volume, follows CL closely. Algos link CL/RB/HO via crack relationships.
- **14:00–17:00 ET (floor close)**: Technical consolidation. EIA release (if Thursdays 10:30am ET) dominates; otherwise, slow grinding. Late close (15:45–17:00) is thin.
- **Overnight Globex (17:00–23:00 CT)**: Wider spreads; follows ICE Gasoil (ULSD equivalent, London). Surprise moves here often reverse by NY open.

**Calendar quirks:**
- **Roll window** (20–25 days before delivery month first notice): Front month volume drops, spreads widen. HO rolls smoother than crude because margins are less volatile; typical roll cost is modest.
- **Last trading day** (3 biz days before delivery month start): Final close-out opportunity. Avoid if possible; thin liquidity, wide slippage.
- **Heating season ramp** (Oct–Nov): In Oct, the market shifts from summer supply (contango) to winter premium (backwardation). This transition often sees technical whipsaws.

## Common setups

1. **EIA distillate surprise + CL correlation confirm**
   - *Trigger*: EIA release shows distillate inventory move (>3% surprise) and CL moved in same direction within 2 hours. HO pauses or reverses after initial gap.
   - *Entry*: Long HO if draw surprise + CL up; short if build surprise + CL down. Wait for 1–2 min consolidation after initial spike, then re-enter on momentum.
   - *Stop*: 5–8 ticks from entry. Typical RR 1:2 (1 risk, 2+ target).
   - *Target*: Prior daily close or 20-day MA; 1–2 handle move is typical.
   - *Invalidation*: CL reverses within 30 min of EIA (HO tends to be stickier, but correlation break is a stop).
   - *Hit rate*: ~60–65% (margin of safety is high because CL is leading; HO follows).

2. **Heating oil seasonality fade (late Apr–early May)**
   - *Trigger*: March–April heating oil demand seasonal peak; storage builds heavily May onwards. Price holds above winter high for <1 week into early May, then cracks.
   - *Entry*: Short HO after a 2–3 day rally into May if demand forecast is mild. Look for closes below the 10-day MA.
   - *Stop*: Above the May high. Typical: 10–12 ticks (wide because carry is against you).
   - *Target*: 40–50% of the winter run-up. Exit on break of 50-day MA below.
   - *Invalidation*: Cold snap forecast for late May (rare but happens); short stops out.
   - *Hit rate*: ~50–55% (seasonal tail-wind is strong; precision entry is hard).

3. **Crack-spread widening (high refining margin)**
   - *Trigger*: HO price − (CL price × 0.42) − RB is >$0.12/gallon for 3+ days. This signals strong refining margins; refineries maximize throughput.
   - *Entry*: Long HO on reversal of crack contraction (when it starts to narrow again, HO momentum often stalls). Short is riskier because high margins attract supply; fade the rally.
   - *Stop*: Below the entry week low. Typical: 8–10 ticks.
   - *Target*: Average crack (HO down to $0.08–0.10 spread); often 30–50 ticks.
   - *Invalidation*: Refinery maintenance or outage announced (spreads blow out); exit and reassess.
   - *Hit rate*: ~45–50% (mean-reversion is not always clean; refining factors are dynamic).

4. **Contango-to-backwardation flip (Oct–Nov heating season)**
   - *Trigger*: In late September, the term structure is contango (front month cheaper than back). By mid-Oct, heating season premia appear; front month inverts relative to back (backwardation). Price of front month rallies relative to next month(s).
   - *Entry*: Buy front month (short back month = bull spread) when the structure starts to flatten (slope of contango steepness decreases). Collect the roll cost as backwardation sets in.
   - *Stop*: If structure re-steepens (contango returns), exit.
   - *Target*: ~0.05–0.10 per gallon spread gain over 3–6 weeks.
   - *Hit rate*: ~55–60% (term structure mean-reversion is reliable; calendar spreads are lower-risk).

## Classic traps

- **EIA whipsaw**: HO gaps on the release, then reverses. Worse than CL because HO is less volatile; retail traders often get caught trying to fade the initial move.

- **Heating-season hope**: A cold snap is forecast for December; market rallies HO in October. The forecast weakens; sell-off in November. Traders caught long the forecast often face hard stops.

- **Refinery maintenance surprise**: Maintenance is announced in advance, but the market reprices it gradually. When the plant actually shuts down (1–2 weeks later), the move has already happened; shorts cover.

- **Crack margin compression + inventory build**: Margins widen, encouraging refinery runs; supply ramps. Market expects bearish EIA (large builds); if so, HO sells off sharply. But the build was already priced. False tail.

- **Overnight gap from ICE Gasoil**: Gasoil (European ULSD) rallies on overseas news. US HO gap up on open. By 10:30am ET, arb traders unwind; HO fades.

- **Lever + stop-run**: HO ~$4.20 per tick; 10 contracts = $42/tick. Retail often 10x leverage. Stops at round numbers ($2.00, $2.50, $3.00 per gallon) get ran. Avoid round numbers for short-term entries.

## Liquidity profile

- **Average daily volume** (front month): 150k–350k contracts in normal regime; peak in winter (Oct–Feb) at 300k–600k. Summer (May–Aug): 80k–150k (thin).
- **Open interest trend**: ~200k–400k for front month; summer OI drops to ~100k–150k. Back months are thin.
- **Pre-open / post-close behavior**: Globex opens Sunday 17:00 CT with wide spreads (~5–8 ticks); fills at open better from 09:30–10:00 ET. Post-close (15:45–17:00 ET) is thin; avoid.
- **Best session for fills**: 09:45–15:30 ET core hours. Avoid 15:45–17:00 ET and overnight Globex.
- **Bid-ask spread**: 2–3 ticks normal in core hours; 4–6 ticks in shoulder months / thin periods.
- **Slippage notes**: HO is less liquid than CL; limit-order execution is slower. Use market orders for size >100 contracts if in thin periods.

## Options (if applicable)

- **Weekly expirations**: Mondays (expire Friday end of day prior week). Less volume than CL or RB; consider buying rather than selling premium.
- **Monthly expirations**: 3rd Thursday of month. Standard NYMEX calendar.
- **Settlement**: 10:30am CT Fridays (weeklies); 16:00 CT on listed expiration date (monthlies).
- **Typical IV rank range**: Summer (Apr–Aug): 20–40th percentile (low IV). Winter (Oct–Mar): 55–75th percentile. Peak IV in Jan–Feb near forecast inflection points.
- **Pin-risk behavior**: Less acute than NG/CL because HO is less volatile. Avoid short gamma near EIA release dates if short options.

## Risk notes

- **Gap risk profile**: Largest intraday gap risk is EIA release (Thursday 10:30am ET). Overnight gaps on crude oil spikes or refinery news. Typical gap: 4–10 ticks; extreme on supply shocks (>20 ticks rare).

- **Limit-up / limit-down mechanics**: HO has no daily price limits under CME rules; exchange reserves right to halt in disorderly markets. Extreme moves (oil embargoes, major refinery explosions) can spike HO 20%+ in a day (2022 post-Ukraine spikes were 15%+ in 2 days).

- **Worst weekly move in last 5 years**: Feb 2021 (Texas freeze): Refinery outages; HO spiked from $1.40 → $1.85 (+32% in week). Jan 2022 (post-Ukraine): HO rallied $1.80 → $3.20 (+78% in 2 weeks). Summer 2022 (margins peak): HO stayed $2.80–$3.20 (less extreme than crude; refineries hedged via cracks).

- **Tail-risk events to remember**:
  - **Texas freeze (Feb 2021)**: Refinery shutdowns; diesel supply contracted sharply.
  - **Ukraine invasion + energy crisis (Feb 2022)**: Russian diesel export bans; global supply tight; US cracks soared.
  - **Philadelphia Refinery issues (2023–2024)**: East Coast capacity constraints; HO basis to NYH tightens; local premium lifts.
  - **Summer 2024 hurricane season**: Minor storms; brief spikes on refinery outage fears; no major disruptions.

## References

- **CME HO contract specs**: https://www.cmegroup.com/markets/energy/refined-products/heating-oil.contractSpecs.html
- **EIA distillate (heating oil + ULSD) stocks**: https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=DHHNGSP&f=D (daily) or weekly report Thursday
- **NYMEX settlement data**: https://www.cmegroup.com/market-data/
- **ICE Gasoil (European ULSD)**: https://www.theice.com/ (for arb context; regional basis spreads)
- **Refinery utilization**: https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=IMUURT&f=M (monthly refinery capacity utilization; key for crack forecasting)
- **Heating oil stocks vs. winter demand**: Historical analysis at https://www.eia.gov/outlooks/steo/ (Short-Term Energy Outlook; seasonal demand tables)

