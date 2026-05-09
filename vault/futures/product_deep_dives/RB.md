---
type: product_deep_dive
symbol: RB
sector: energies
analyst: Fund Engineer
updated: 2026-04-25T07:00:00Z
---

# [[RB]] — NYMEX RBOB Gasoline

## Contract specs

- **Exchange / product code**: NYMEX (CME) / RB (42,000 US gallons per contract)
- **Tick size / tick value**: 0.0001 per gallon; $4.20 per contract
- **Contract months**: Monthly; active trading in front 12 months (most liquid front 3)
- **Session hours**: RTH 08:00–17:00 CT (floor). Globex: 17:00 CT Sunday–17:00 CT Friday (23 hours, 5-minute gap)
- **First notice / last trading day**: 3 business days before delivery month; delivery period 1st–last calendar day of month
- **Settlement**: Physical delivery (multiple US delivery points; New York Harbor is a major hub but contracts also settle to Gulf Coast)
- **Margin** (Topstep): ~$3.0K initial, ~$1.5K maintenance (typically higher than HO due to volatility; check live)

## What it actually is

RBOB stands for Reformulated Gasoline Blendstock for Oxygen Blending. The RB futures contract tracks the wholesale price of finished (or near-finished) gasoline as blended for the US market. RBOB is the base gasoline stream; oxygen-containing compounds (ethanol, typically) are blended in downstream to meet regulatory and performance specs.

Unlike crude oil (global commodity) or even HO (regional but linked to distinct heating demand), RB is purely a transportation-fuel product. It drives demand from passenger vehicles, light-duty trucks, and some commercial fleet consumption. The US gasoline market is largely isolated from global markets (limited export economics; shipping costs make international arb uneconomical except in extreme price dislocations).

RB is the most volatile refined product and the highest-beta trade to macro demand shocks (recessions crater gasoline use). It is also more speculative than HO—refiners hedge RB margins (crack spreads) more aggressively, and retail speculators trade RB momentum heavily.

## Primary drivers

Ranked by impact in 2024–2026 regime:

1. **Crude oil price and refining margins (gasoline cracks)**: RB is a refined product; crude (CL) is the dominant input cost. When crude spikes, RB follows with a lag (1–3 hours). Gasoline cracks = RB price − (CL price × 0.42) [the refining yield]. In high-margin periods (e.g., post-supply disruption or low global refinery runs), refiners maximize throughput, increasing supply and capping gasoline prices. In low-margin or negative-margin periods (recession, oversupply, crude spike outpacing gasoline demand), refiners cut runs and reduce gasoline supply, supporting RB. Post-Ukraine 2022–2023, cracks were historically wide and volatile; 2024–2025 normalization toward 10–15 year averages is ongoing.

2. **US gasoline demand (transportation, driving season, economic cycles)**: Gasoline is a tight proxy for road fuel consumption. Summer driving season (May–Aug) sees peak demand; winter (Dec–Feb) lowest. A 10% lift in miles driven (holiday travel, summer road trips) lifts RB demand. Recessions collapse RB (2020 Covid lock-down saw RB crater 50%+). Employment data, weekly jobless claims, and PMI manufacturing are leading indicators.

3. **Refinery capacity and maintenance**: East Coast and Gulf Coast refinery outages or planned maintenance reduce gasoline supply. Conversely, return-to-service of idled capacity (e.g., restarting a mothballed refinery) increases supply and caps RB. Spring (Mar–Apr) and fall (Sept–Oct) maintenance windows are known; surprises move the market sharply.

4. **Ethanol price and blending economics**: Ethanol (from corn) is blended into gasoline to boost octane and meet renewable-fuel mandates (RFS, or Renewable Fuel Standard, requires ~10 billion gallons of ethanol blended annually in US gasoline). When ethanol is cheap relative to gasoline, blending is high; when ethanol is expensive, blending is constrained. High RB/ethanol prices incentivize larger ethanol blends (e.g., E15, 15% ethanol). The ZC (corn) futures price is a secondary driver; ethanol-to-corn conversion costs determine blending margins. In 2024–2025, ethanol has been cheaper, encouraging blending; this has capped RB upside.

5. **Gasoline inventory levels (EIA weekly)**: Unlike heating oil, gasoline inventory is seasonal. Strategic Petroleum Reserve (SPR) is crude, not gasoline; however, commercial gasoline stocks (refineries + distribution) are tracked weekly by EIA (Thursdays 10:30am ET). Large builds (surprise) are bearish; large draws are bullish. Surprise magnitude >5% drives 3–8 tick RB moves intraday.

6. **Weather and transportation disruptions**: Hurricanes (Aug–Oct) disrupt Gulf Coast refining. Nor'easters or winter storms reduce driving (fewer miles); mild winters reduce heating-fuel-related driving and support transportation-fuel demand equilibrium. Unlike HO (heating oil is weather-sensitive), RB benefits from stable, mild conditions (driving is consistent).

7. **Global refinery runs and export economics**: Unlike HO, RB has minimal export economics (cost to ship to Europe or Asia exceeds price arbitrage in normal conditions). However, global refinery utilization (especially if China or India cuts runs in recession) can affect global crude demand, which in turn affects US crude supply/pricing and refiners' appetite to run. This is indirect.

## Key correlations

**Positively correlated:**
- [[CL]] (crude oil): 0.75–0.90 correlation (very strong). RB follows CL within 1–3 hours intraday on most days. RB is more volatile than HO on a percent basis but less volatile on absolute basis; correlation is tighter than HO/CL due to refining margin being higher-beta.
- [[HO]] (heating oil / ULSD): 0.6–0.75 (strong). Both refined; driven by crude and refining margins. Inter-crack spreads (RB vs. HO) show refiner capacity preferences—when margins are wide, refiners may maximize gasoline over diesel or vice versa. In high-cost-crude environments, refiners optimize yield; spread widens/narrows.
- [[ZC]] (corn): 0.2–0.4 (weak-to-moderate). Ethanol (made from corn) is blended into gasoline. High corn prices → expensive ethanol → lower blending → less pressure on RB. Relationship is indirect and often overwhelmed by crude moves. Most useful as a secondary check on blend economics.
- **US equity indices (SPY/QQQ)**: 0.4–0.6 in normal regimes; −0.5 to −0.8 in recessions. Recession expectations collapse gasoline demand; equity weakness is a leading indicator.

**Negatively correlated:**
- **US 2Y and 10Y rates**: −0.3 to −0.5 (weak-to-moderate). Higher rates signal recession expectations; demand falls.
- **Volatility (VIX)**: 0.2–0.4 (weak positive in normal; strong negative in risk-off). Risk-off events collapse demand; RB sells off harder than commodities in general.
- **USD strength (DXY)**: −0.1 to −0.3 (very weak). Strong dollar slightly caps refinery margins (inputs more expensive relative to outputs); minimal practical impact.

**Lead/lag:**
- Crude oil move → RB response: 30 min to 3 hours (CL is the lead).
- EIA gasoline inventory (Thursday 10:30am ET) → RB move within 1–5 minutes; follow-through through Friday.
- Jobless claims (Thursday release, 8:30am ET) → RB subtly softer if claims spike (recession fear); move is muted unless data is extreme.
- Fed rate decisions / inflation data → RB medium-term drift (weeks to months); not intraday.

## Recurring patterns

**Seasonal:**
- **Spring (Apr–May)**: Transition from winter driving to summer blend. Refiners shift production away from winter gasoline (more severe spec) to summer blend (lower RVP, or Reid Vapor Pressure). Changeover can be disruptive; volumes sometimes thin. Typically bearish (supply switching, less crude utilization needed). Contango usual.
- **Summer (June–Aug)**: Peak driving season. Bullish bias; demand strong. Prices often hold above spring lows. Contango typical as refinery runs are steady and near-term supply abundant. Weather-driven intraday volatility is elevated if heat waves or storms occur.
- **Fall (Sept–Oct)**: Transition back to winter blend. Prices weaken slightly as summer driving ends (Labor Day weekend is often a peak). Volatility drops. Contango steep as refiners prepare winter inventories.
- **Winter (Nov–Mar)**: Low driving season (cold weather, holidays near Feb–Mar are exceptions). Lowest demand season. Prices trade sideways or weak. Backwardation can appear in Jan–Feb if cold-snap forecasts emerge. Feb historically volatile due to forecast uncertainty.

**Event-driven:**
- **Weekly EIA gasoline inventory release** (10:30am ET Thursdays): Gasoline stocks (excluding SPR) release. Surprise of >4–6% vs. consensus can drive 4–10 tick moves in <5 min. Build surprise (bearish) → sell-off; draw surprise (bullish) → rally. RB moves harder than HO on EIA due to higher demand elasticity.
- **Crude oil surprise gap moves** (EIA Thursday, same time): CL gap up/down carries RB along within minutes. RB tends to amplify CL moves on a percent basis.
- **Refinery maintenance announcements**: Scheduled maintenance (Mar–Apr, Sept–Oct) reduces runs and gasoline supply; bullish for cracks. Unplanned outages (e.g., fires, explosions at major complexes like BP Texas City, Shell Norco) are strongly bullish (immediate supply tightness).
- **Summer blend changeover (Apr–May)** and **winter blend changeover (Sept–Oct)**: Market reprices blend specifications and supply constraints. April often sees technical weakness (summer supply anticipation); Sept–Oct sees brief strength (winter demand prep) then fade.
- **Gasoline export surprises**: Most US gasoline is domestic, but in periods of high refinery output, export cargoes move. News of US gasoline exports can be mildly bearish (supply drain from domestic market is limited, but sentiment shifts).
- **Ethanol policy news**: RFS (Renewable Fuel Standard) changes, EPA waivers on ethanol blending mandates, or tariff changes on Brazilian ethanol imports can affect blending demand. Policy changes are rare but high-impact (e.g., EPA waiver in 2022 reduced ethanol blending demand; RB rallied relative to ethanol margin).

**Time-of-day patterns:**
- **Asian close (6:00am ET)**: Minimal direct impact from RB; mostly sentiment spillover from crude.
- **9:30–14:00 ET**: Core US session. RB trades with strong volume. EIA release (Thursdays 10:30am ET) dominates. CL/RB correlation is tightest during this window.
- **14:00–17:00 ET (floor close)**: Technical consolidation. After EIA, consolidation is common. Late close (15:45–17:00) is thin.
- **Overnight Globex (17:00–23:00 CT)**: Wider spreads (~5–10 ticks). Follows ICE Brent/crude trends. Surprise moves can reverse by NY open.
- **Monday opens (after weekends)**: Weekend refinery news or OPEC announcements can gap RB Monday; typical gaps 8–15 ticks.

**Calendar quirks:**
- **Roll window** (15–20 days before delivery month first notice): Front month volume drops; spreads widen 3–5 ticks. RB rolls slightly worse than HO because volatility is higher; avoid rolling into wide bid-ask.
- **Last trading day** (3 biz days before delivery month start): Very thin; avoid.
- **Summer blend production peak** (May–Aug): Most liquid RB period; best fills 09:30–15:00 ET.
- **Holiday weeks** (Thanksgiving week, Christmas week, New Year week): Volumes thin; avoid large size.

## Common setups

1. **EIA gasoline surprise + CL correlation confirm**
   - *Trigger*: EIA release shows gasoline inventory move (>4% surprise) and CL moved in same direction within 2 hours. RB gapped on release, now consolidating.
   - *Entry*: Long RB if draw surprise + CL up; short if build surprise + CL down. Wait for consolidation (1–2 min), then enter on momentum.
   - *Stop*: 6–10 ticks from entry (RB is more volatile than HO). Typical RR 1:2.
   - *Target*: Prior daily close or 20-day MA; 1.5–2 handle move is typical for RB.
   - *Invalidation*: CL reverses within 30–45 min of EIA; RB tends to lag reversals, so stop is wider than HO.
   - *Hit rate*: ~60–65% (EIA is a reliable catalyst; RB follows CL cleanly).

2. **Summer driving season ramp (May–early June)**
   - *Trigger*: April weakness (blend changeover) fades. May opens with firmer tone (driving season, Memorial Day weekend looming). Price closes above 20-day MA for 3+ days.
   - *Entry*: Long RB on a retest of the May low if overall trend is firming. Look for closes above 10-day MA.
   - *Stop*: Below the April low. Typical: 12–15 ticks (seasonal tailwind is moderate).
   - *Target*: 40–60% of the Apr weakness. Hold if Jun–Jul momentum is strong.
   - *Invalidation*: Recession headlines or jobless claims spike; demand fears short-circuit seasonal.
   - *Hit rate*: ~55–60% (seasonal demand lift is real but not guaranteed; requires broader-market confidence).

3. **Crack spread fade (high refining margin compression)**
   - *Trigger*: RB − (CL × 0.42) is >$0.15/gallon for 3+ days. This signals wide refining margins; refineries are maximizing gasoline yield.
   - *Entry*: Short RB or go long CL/short RB (crack short) when crack is elevated and beginning to compress (RB momentum stalls). Cracks mean-revert over 3–7 days.
   - *Stop*: Above the entry week high. Typical: 10–12 ticks.
   - *Target*: Average crack (RB down $0.10–0.12 range); often 40–60 ticks down.
   - *Invalidation*: Refinery outage (crack blows out); exit and reassess.
   - *Hit rate*: ~48–55% (cracks are sticky; mean-reversion is not clean, but data supports it).

4. **Ethanol-to-RB divergence (blending-margin signal)**
   - *Trigger*: Ethanol futures (ZEC, the continuous contract) spike relative to RB (blending margin compresses). Or conversely, ethanol crashes while RB holds firm (blending margin widens). Divergence >2% is notable.
   - *Entry*: If ethanol is expensive, RB underperforms: short RB or short the spread. If ethanol is cheap, blending is encouraged: long RB or long the spread.
   - *Stop*: 8–10 ticks; this is a secondary driver, so risk-management is tighter.
   - *Target*: Convergence back to 10-day MA or typical blending spread. Usually 20–40 ticks.
   - *Hit rate*: ~45–50% (blending margin is real but often overwhelmed by crude moves; use as a secondary confirmation, not primary signal).

5. **Post-EIA momentum bounce (short-term mean-reversion)**
   - *Trigger*: EIA misses (large build or unexpected draw). RB spikes or crashes; initial move is violent (>10 ticks in minutes). Within 5–10 min, move slows; oscillators are overbought/oversold (RSI >80 or <20).
   - *Entry*: Fade the initial spike. If RB spiked (draw surprise), take a small short on overbought. If RB crashed (build surprise), take a small long on oversold.
   - *Stop*: 5–8 ticks. This is low-hold (1–5 min); exit on profit or hold for mean-reversion confirmation.
   - *Target*: 50% of initial EIA move; often 5–10 ticks.
   - *Invalidation*: CL continues to move in same direction (structural, not technical); stop out.
   - *Hit rate*: ~50–55% (EIA whipsaws are common; fade often works but timing is precise).

## Classic traps

- **EIA-driven reversal**: RB gaps on large inventory move, then reverses within 30–60 min. Retail traders chase the gap; pros exit into panic. Worst trap when weather forecast is also disruptive (e.g., hurricane watch overlapping EIA release).

- **Refinery surprise backpedal**: Major refinery goes offline; RB rallies strongly. Market reprices supply tightness over next 2–3 days. When the refinery restarts early (or news of restart leaks), RB reverses hard. Traders caught long the disruption-trade face liquidation.

- **Seasonal complacency**: April–May blend changeover is bullish for cracks but not always for RB absolute. Traders expecting May strength miss that CL weakness can overwhelm seasonal gasoline demand lift.

- **Ethanol surprise blur**: Ethanol prices spike (cold crop forecast, production issues). Market assumes RB benefit (tight blending supply). But if crude spikes more, RB is dragged down despite blending margin premium.

- **Overnight Globex gap reversal**: RB gaps >10 ticks overnight on crude spike or refinery news. NY open fades 60–70% of the gap within 1 hour. Traders holding gap-ups for daylight get whipsawed.

- **Demand complacency in drawdown**: Recession fears build; RB is in a downtrend. A surprise draw EIA (usually bullish) barely lifts RB because demand expectations have already fallen. False signal; short still holds.

## Liquidity profile

- **Average daily volume** (front month): 250k–500k contracts in normal regime; peak in summer (June–Aug) at 400k–700k. Winter (Dec–Feb): 200k–350k. Spring/fall: 150k–250k (thin).
- **Open interest trend**: ~300k–500k for front month; summer OI peaks at ~600k. Back months: <100k (very thin).
- **Pre-open / post-close behavior**: Globex opens Sunday 17:00 CT with wide spreads (8–15 ticks); fills improve from 09:30–10:00 ET. Post-close (15:45–17:00 ET) is thin; avoid.
- **Best session for fills**: 09:45–15:30 ET core hours. Volume is highest 10:00–14:00 ET (post-EIA window).
- **Bid-ask spread**: 2–4 ticks normal in core summer hours; 5–10 ticks in shoulder/winter periods.
- **Slippage notes**: RB is more liquid than HO but less than CL. Limit orders fill slowly during EIA (release chaos); use market orders for size >50 contracts during high-impact events.

## Options (if applicable)

- **Weekly expirations**: Mondays (expire Friday end of day prior week). Moderate volume; more liquid than HO options, less than CL options.
- **Monthly expirations**: 3rd Thursday of month. Standard NYMEX calendar.
- **Settlement**: 10:30am CT Fridays (weeklies); 16:00 CT on listed expiration date (monthlies).
- **Typical IV rank range**: Summer (May–Aug): 30–50th percentile (moderate IV). Winter (Nov–Mar): 40–60th percentile. Peak IV in May–Jun when hurricane season approaches and summer demand is priced.
- **Pin-risk behavior**: Moderate; RB is less volatile than crude but more than rates. Avoid short gamma near EIA and OPEC announcement dates.

## Risk notes

- **Gap risk profile**: Largest intraday gap risk is EIA release (Thursday 10:30am ET). Overnight gaps on crude spikes (>5% in crude = 8–15 tick RB gap). Weekend gaps on geopolitical news (refinery disruptions, supply announcements). Typical gap: 5–15 ticks; extreme on supply shock >20 ticks.

- **Limit-up / limit-down mechanics**: RB has no daily price limits under CME rules. In extreme moves (refinery explosions, major geopolitical supply disruptions), RB can spike 20%+ in a day (2022 Ukraine spike: RB went from $2.80 → $3.80 in 1 week).

- **Worst weekly move in last 5 years**: 
  - **Jan 2022 (Ukraine invasion)**: RB rallied from $2.70 → $3.45 (+28% in 1 week) as refinery-disruption fears spiked.
  - **Summer 2022 (high refining margins)**: RB rallied to $4.00+ on demand resilience and supply tightness; later faded as recession fears materialized.
  - **May 2023 (China stimulus, demand recovery)**: RB rallied on Chinese economic data; faded when followed by US recession data.

- **Tail-risk events to remember**:
  - **Ukraine invasion (Feb 2022)**: Russian refinery output constraints; global margins soared. US refinery runs maxed; RB spiked but capped by demand recession fears.
  - **Texas freeze (Feb 2021)**: Refinery outages; gasoline supply constrained sharply; RB rallied 15%+ in week.
  - **COVID-19 lockdowns (Mar 2020)**: Gasoline demand collapsed 30%+; RB crashed from $2.00 → $0.90 in 3 weeks.
  - **Summer 2024 hurricane season**: Tropical storms threatened Gulf refining; RB volatility spiked but no major disruptions materialized.

## References

- **CME RB contract specs**: https://www.cmegroup.com/markets/energy/refined-products/rbob-gasoline.contractSpecs.html
- **EIA gasoline stocks**: https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=GASSGSP&f=D (daily) or weekly report Thursday
- **NYMEX settlement data**: https://www.cmegroup.com/market-data/
- **ICE Brent and WTI crude**: https://www.theice.com/ and https://www.cmegroup.com/ (for arb context; RB vs. CL crack spreads)
- **Refinery utilization**: https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=IMUURT&f=M (monthly; refinery capacity utilization is a leading indicator of crack margins)
- **US gasoline demand**: https://www.eia.gov/outlooks/steo/ (Short-Term Energy Outlook; seasonal demand profiles)
- **Renewable Fuel Standard (RFS) and ethanol blending**: https://www.epa.gov/renewable-fuel-standard-program (policy-driven blending mandates affect RB)
