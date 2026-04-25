---
type: product_deep_dive
symbol: CC
sector: softs
analyst: Fund Engineer
updated: 2026-04-25
---

# [[CC]] — Cocoa #10 (New York Cocoa)

## Contract specs

- Exchange / product: ICE Futures U.S. (NYBOT), Cocoa #10
- Tick size: $1/metric ton; tick value: $10 per contract
- Contract multiplier: 10 metric tons per contract
- Contract months: March, May, July, September, December (rolling throughout the year)
- Session hours: 7:45 AM ET — 4:30 PM ET (RTH open 9:30 AM ET)
- Last trading day: 10th business day of the delivery month
- Settlement: physical (cocoa beans delivery) or cash settlement; most financial players do cash
- Margin at Topstep: ~$6K–$8K initial (verify in platform)

## What it actually is

Fermented, dried cocoa beans traded as a commodity futures contract. Primary price driver is West African supply (Côte d'Ivoire ~40%, Ghana ~20%, Indonesia, Nigeria). Used by chocolate manufacturers (Hershey, Mars, Nestlé) as a hedge, and heavily traded by financial funds and CTAs who ride volatility and structural supply cycles. This is the global benchmark for cocoa bean pricing. Unlike sugar or coffee, cocoa has significant idiosyncratic risk: Ivory Coast political instability, cocoa pod disease (black pod, frosty pod rot), and weather concentrated in a narrow geography makes it volatile and mean-reverting.

## Primary drivers

1. **Ivory Coast politics & stability** — Ivory Coast produces ~40% of global supply. Coups, unrest, or policy shifts (export taxes, port restrictions) create immediate supply disruption and price shocks.
2. **West African rainfall patterns** — Oct–Feb dry season (harvest) and Apr–Sep rainy season (growing/pod development) directly affect yields. La Niña / El Niño significantly alter these patterns; monitor NOAA ocean-temp forecasts.
3. **Pod disease incidence** — Black pod rot and frosty pod rot are endemic in West Africa. Wet seasons = higher disease pressure = lower yields. Regional humidity spikes = disease risk premiums.
4. **Global grind demand** — chocolate consumption (especially in China's confectionery boom) and industrial cocoa processing (cocoa powder, cocoa butter) drive end-user demand. Chinese GDP slowdowns reduce grind.
5. **Fund positioning & technical flows** — cocoa is a commodity index component; CTAs and index-tracking funds create cascade reversals when positioned heavily one-directionally. COT spikes often precede violent 3–5% reversals.
6. **Currency effects** — West African currencies (CFA franc, Ghana cedi) depreciate in commodity downturns; cheaper cocoa to buyers abroad, but depreciating local currency can offset some of the pricing effect.

## Key correlations

- Positively correlated with: [[SB]] (sugar — softs complex), [[KC]] (coffee — producer overlap, weather), [[BZ]]/[[CL]] (oil — energy costs, shipping fuel). Weak correlation with equities (negative in downturns when risk-off reduces grind).
- Negatively correlated with: DXY (stronger dollar depresses prices; cocoa prices in USD). [[ZC]] (corn — competing agricultural investment flows).
- Lead/lag: Ivory Coast rainfall (Monitor NOAA/SMN-Côte d'Ivoire for Oct–Feb moisture anomalies) leads by 6–12 weeks. Global grind data (published monthly by Trade Analyst or Cocoa Barometer) leads by 2–4 weeks.

## Recurring patterns

- **Oct–Feb harvest season supply glut** — new-crop cocoa floods market; prices tend to peak in Sep (pre-harvest anxiety), then collapse 10–20% as harvest arrives.
- **Apr–May "hungry gap" rally** — post-harvest storage depletes; if prior crop was tight, May–Jun rally as demand meets shrinking inventory.
- **Ivory Coast election / policy risk** — every 5 years, elections bring political uncertainty. Pricing often spikes 3–8 weeks ahead of election on supply-disruption fears (2020, 2025 cycles).
- **Black pod outbreaks** — monsoon rains (May–Sep) trigger disease; disease data published Aug–Sep often sparks 3–5% rally as yields drop.
- **Fund capitulation cascades** — cocoa is 5–8% of commodity indices. Large CTAs long in quiet markets get shaken out on a 3% break; forced liquidations can create 8–12% down moves in 1–2 days.
- **Grind crush spread** — when cocoa rallies relative to cocoa butter and cocoa powder end-products, grinders reduce purchases; supply accumulates, creating reversal pressure.

## Common setups

1. **Pre-election political-risk spike.** 6–10 weeks before Ivory Coast elections, watch for first headline of unrest or policy threat (export tax, fuel shortage). Long via bull call spread (or outright with 3% stop). Exit on first reversal below 5-day MA or at +3R. Typical: +5–8% in 3–4 weeks.
2. **Monsoon-scare disease play.** Apr–May, when monsoon rains start in West Africa, disease pressure rises. Watch for first NOAA forecast of abnormally wet Jun–Jul. Long ahead of disease-risk season; exit on drought forecast or yield estimate increase. Typical: +4–6% over 4–6 weeks.
3. **Fund positioning unwind.** When COT data shows record commercial short (hedgers selling) and large speculators heavily long, watch for a 2–3% break on news. Ride the cascade short; cover at 5–8% down.
4. **Harvest-relief short.** Sep, near end of old-crop cycle, watch for delivery/storage cost inversion (calendar spread widens sharply). Harvest arrival is imminent; short the calendar spread or sell outright. Exit on first close above pre-harvest levels.

## Classic traps

- **Ignoring Ivory Coast headlines** — a small news item (minister statement, shipping port delays) can gap the market 2–3% overnight. Check WSJ, Reuters Africa feed, and Ivory Coast government announcements daily during Apr–Sep.
- **Chasing dry-spell rallies on single report** — one NOAA forecast of dry conditions doesn't confirm drought; 2–4 weeks of consistent dry data required. Trade the pattern, not one forecast.
- **Holding into grind-data release** — first-week-of-month grind data can whip 3–4%. If you're long a bounce and grind misses, be ready to exit; don't hold into data.
- **Underestimating disease risk** — traders often assume "normal disease" but forget that wet seasons create exponential disease pressure. If disease forecasts are dire, rally strength is often trap; sell into them.
- **Assuming Ivory Coast is stable** — it isn't. A coup or unrest event in nearby Burkina Faso or Ghana can ripple to Ivory Coast and trigger contagion selling (5–10% down in hours). Keep country-risk radar active.
- **Leverage during "boring" cocoa** — cocoa is often range-bound for 6–8 weeks, then explodes 10–15% on one headline. High leverage in "quiet" phases gets taken out on gaps; respect tail-risk.

## Liquidity profile

- Average daily volume: 40K–100K contracts on front month (May, July most liquid during main seasons).
- Spreads: typically 2–4 ticks ($20–$40) in normal flow; widens to 10–15 ticks around USDA forecasts or Ivory Coast news.
- Best fills: 10:00 AM — 1:00 PM ET (London overlap, when European chocolate makers and African traders active).
- Pre-open (7:45–9:30 AM ET): thinner liquidity; overnight Ivory Coast news can create gaps of $100–300/ton on open.
- Post-close evening (4:30–6:00 PM ET on automated platforms): very thin, wide spreads; avoid.

## Options (if applicable)

- Monthly expirations only (no weeklies).
- Settlement: American-style (exercise any time before expiry).
- Typical IV rank: 25–40 in calm periods, 60–80 during harvest scares or election years.
- Put walls: often cluster at round levels (2000, 2100, 2200 $/ton strikes) in bear markets.
- Call walls: less pronounced, but form above resistance in bull markets; pin risk can occur near 2400–2600 strikes during supply rallies.

## Risk notes

- **Gap risk: extreme.** Overnight Ivory Coast news (coup threat, shipping strike, export ban, disease outbreak) can gap 3–5% on open. Never hold large unhedged positions into news windows (election weeks, harvest transitions, monsoon starts).
- **Limit moves:** rare but possible during coups or major disease outbreaks (2 consecutive limit moves trigger halt). 2020 Ivory Coast political crisis saw limit-up days.
- **Worst weekly moves (last 5 years):** +12% (2021 drought + election uncertainty), −10% (2022 harvest relief + fund capitulation).
- **Tail-risk events:** Ivory Coast coup or civil unrest, major disease outbreak (witches'-broom in Indonesia-type scenario), supply-chain disruption (port strikes, fuel shortage), sudden Chinese demand collapse, commodity index cascade (all softs down together).
- **Margin call risk:** cocoa can gap 5% on open; Topstep margin can get eaten fast. Size accordingly; recommend 2–3% risk per trade maximum.

## References

- ICE Futures: https://www.theice.com/products/14/Cocoa-Futures
- Ivory Coast government: cocoa export data, political calendar.
- NOAA Climate Prediction Center: West African rainfall patterns, monsoon forecasts.
- Trade Analyst / Cocoa Barometer: monthly grind data, global inventory, disease updates.
- Reuters Africa / Bloomberg commodity desks: Ivory Coast news feed.
- ICCO (International Cocoa Organization): quarterly grind forecasts, surplus/deficit projections.
