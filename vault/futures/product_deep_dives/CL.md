---
type: product_deep_dive
symbol: CL
sector: energies
analyst: seed (Claude)
updated: 2026-04-23
---

# [[CL]] — Crude Oil (WTI)

## Contract specs

- Exchange / product: NYMEX, Light Sweet Crude Oil (CL) — West Texas Intermediate
- Tick size: $0.01/barrel; tick value: $10.00 per contract
- Contract multiplier: 1,000 barrels
- Contract months: monthly (all 12) — liquidity concentrates in the front 2
- Session hours: Sun 18:00 ET → Fri 17:00 ET, 1-hr daily break 17:00–18:00 ET
- Last trading day: 3rd business day before the 25th of the month preceding delivery
- First notice day: business day before the last trading day of the preceding month
- Settlement: physical (Cushing, OK delivery) — **roll before FND to avoid delivery notice issues**
- Margin at Topstep: ~$5K initial (verify)

Also see [[MCL]] (micro, 1/10 size) for smaller account sizing.

## What it actually is

The global benchmark for US grade light sweet crude oil. Used by producers, refiners, airlines, macro funds, and increasingly sovereign-wealth players. Physical settlement at Cushing gives WTI a different basis than Brent — Cushing pipeline constraints can produce local price dislocations.

## Primary drivers

1. **OPEC+ policy** — production quotas, compliance, Saudi/Russia dynamics. JMMC meetings move the tape.
2. **US inventory data** — EIA Weekly Petroleum Status Report, Wednesdays 10:30 ET (10:30 CT next day after holidays).
3. **Geopolitical risk** — Middle East tension, Russia/Ukraine, straits (Hormuz, Bab-el-Mandeb), pipeline attacks.
4. **Demand signals** — China refining margins, US driving season, jet fuel demand proxies, global PMIs.
5. **USD** — weaker dollar supports oil (inverse correlation varies, typically −0.3 to −0.5).
6. **Term structure** — contango (forward > spot) vs backwardation; shifts signal physical market tightness.

## Key correlations

- Positively correlated with: [[RB]], [[HO]] (refining complex), [[BZ]] (Brent, not on our list), energy equities (XOM/CVX/EOG), CAD (petrocurrency), RUB.
- Negatively correlated with: [[DXY]] proxies ([[6E]] inversely), airlines (proxy), defensive equities on risk-off days.
- Lead/lag: API inventory estimates (Tuesday PM) often lead EIA Wednesday print by one day.

## Recurring patterns

- **Pre-EIA Tuesday evening** — API estimate release; Tuesday close often positions for Wednesday print.
- **OPEC meeting weeks** — vol compresses into the meeting, expands after the decision.
- **Summer driving season** — US gasoline demand seasonal peak May-Aug; RBOB crack expands.
- **Winter heating demand** — distillate (HO) demand Nov-Feb; natural gas more than oil, but related.
- **Hurricane season** (Jun-Nov) — Gulf production and refining risk; premium builds and decays on forecasts.
- **Roll dynamics** — front-month roll can produce basis noise; avoid entries in the last 3 days before FND.

## Common setups

1. **Inventory surprise fade.** EIA surprise (>1σ away from consensus). Wait 30 min post-release. If the move extends but stalls at a prior level with declining volume, fade with tight stop. Small size, high win-rate.
2. **OPEC-driven trend.** Post-OPEC decision with surprise output change → wait for session close to confirm direction, then trend trade with 1.5× ATR stop, 2R target.
3. **Crack-spread play.** Long [[RB]] / Short [[CL]] during summer driving season if inventory and crack margins support. Position as a spread, not two outrights.
4. **Calendar spread (carry play).** When front-month goes into backwardation, long front / short back spread expresses physical tightness with lower directional exposure.

## Classic traps

- **Trading CL like a stock.** Oil is a physically-delivered commodity with flow-driven price, not EPS-driven. News-driven moves can reverse hard when flow normalizes.
- **Ignoring the roll.** Holding to FND = delivery mechanics = disaster. Roll by 3 business days before FND.
- **Fading OPEC.** Don't fade surprise output changes on day 1; the move extends before it doesn't.
- **Mid-East headline lottery.** Buying oil on a tweet about the Middle East is often already-priced; late entries get stopped.

## Liquidity profile

- Front-month volume: ~500K–800K contracts daily.
- Spread: 1 tick typical.
- Best liquidity: 9:00 ET – 14:30 ET (European + NY overlap).
- Thin: 17:00 ET – 20:00 ET (Asian handoff).

## Options on /CL

- LO (American-style) weeklies and monthlies.
- Expiration: 3 business days before the underlying futures last trading day.
- IV regime: typically 25-40 vol, spikes to 50+ on OPEC weeks or geopolitical events.
- Pin risk: strong at round strikes with high OI, especially near options expiry.
- Common structure: bull call spread in the front month for OPEC/geopol upside; iron condor across EIA for short-vol plays.

## Risk notes

- Gap risk: weekend headline risk (Middle East) can gap 3-5% Sunday open.
- No price limits in normal conditions; market can trend hard.
- Worst weekly moves: April 2020 (−300% due to negative settlement — USO/UVO collapse), spring 2022 (Russia invasion).
- Tail risk: the April 2020 negative-price event taught the market that physical-delivery benchmark can be broken by storage crises.

## References

- EIA Weekly Petroleum Status Report: https://www.eia.gov/petroleum/supply/weekly/
- OPEC JMMC calendar: https://www.opec.org
- Genscape / Kayrros for pipeline/storage satellite data (premium).
- CME product page: https://www.cmegroup.com/markets/energy/crude-oil/light-sweet-crude.html
