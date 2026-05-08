---
type: product_deep_dive
symbol: NG
sector: energies
analyst: Fund Engineer
updated: 2026-04-25T06:15:00Z
---

# [[NG]] — NYMEX Natural Gas (Henry Hub)

## Contract specs

- **Exchange / product code**: NYMEX (CME) / NG (electricity equivalent: ~10,000 MMBtu)
- **Tick size / tick value**: 0.001 per MMBtu; $10 per contract
- **Contract months**: Monthly; active trading in front 12 months + spreads beyond
- **Session hours**: RTH 08:00–17:00 CT (floor). Globex: 17:00 CT Sunday–17:00 CT Friday (23 hours, 5-minute gap)
- **First notice / last trading day**: 3 business days before delivery month; delivery period 1st–last calendar day of month
- **Settlement**: Physical delivery (Henry Hub, Louisiana; net-settled basis differential)
- **Margin** (Topstep): ~$3K initial, ~$1.5K maintenance (varies with IV; check live)

## What it actually is

NG futures track the spot price of natural gas at Henry Hub, the primary US price benchmark. The contract obligates physical delivery of 10,000 million BTU (MMBtu) per contract or cash settlement. Natural gas is used for electricity generation (30% of US grid), heating (residential/commercial), industrial feedstock (chemicals, steel, fertilizer), and exports (LNG). Unlike crude, NG is not globally fungible—US markets (Henry Hub) are the primary reference, with separate benchmarks for Europe (TTF) and Asia (JKM). Speculators use NG futures for directional positioning; hedgers (utilities, producers, industrial users) lock in input costs for fuel and feedstock.

## Primary drivers

Ranked by impact in 2024–2026 regime:

1. **US weather (temperature extremes)**: Winter cold (heating demand ↑↑) and summer heat (cooling demand + generation ↑) are the dominant signals. Temperature anomalies vs. 30-yr normals matter more than absolute temp. Forecast accuracy inversely predicts NG volatility 3–10 days ahead.

2. **Production + storage inventory**: Weekly EIA inventory reports (Thursdays 10:30am ET) are the most important data point. Storage levels (currently ~1.2 trillion cu ft; normal ~2.5T) set the floor for summer and ceiling for winter. Producers' willingness to pump is tied to price, capex cycles, and private equity funding (energy sector is bifurcated post-2022).

3. **LNG export capacity and international pricing**: Cheniere, Freeport, and other LNG exporters arbitrage US Henry Hub vs. foreign benchmarks (TTF Europe, spot Asia LNG). When arbitrage is wide (Europe premium >$3/MMBtu), US producers redirect supply offshore; when negative, exports slow. Post-Ukraine, European premium persisted; it has normalized but remains >$0.50 in most regimes.

4. **Industrial demand (fertilizer, chemicals, steel, power generation)**: Seasonal pulses (spring planting, summer cooling) plus structural: aluminum smelting is 100% electricity-dependent; fertilizer production needs gas; petrochemicals hinge on spreads. Power generation mix (coal → gas switching) is dynamic and regime-dependent.

5. **Macroeconomic recession risk**: Hard recessions (2008–2009, Covid 2020) saw NG crater as industrial demand collapsed. Softer slowdowns have little impact. The market prices recession-tail risk into winter (Oct–Mar) but not summer (Apr–Sep).

## Key correlations

**Positively correlated:**
- [[CL]] (crude oil): 0.3–0.5 correlation (weak-to-moderate). Oil prices lift when rates rise, which also pressures NG demand; but NG is driven more by weather and storage. Oil-to-gas switching happens in certain industrial processes (fertilizer, ammonia); when oil spikes, gas demand can rise. Not reliable for prediction—often decoupled for weeks.
- [[HO]] (heating oil) and [[RB]] (gasoline): 0.2–0.4 (weak). Both are energy, but HO is more correlated with NG than RB (seasonal heating overlap). RB is decoupled—driven by refinery throughput, crude, and demand.
- **US 2Y rates** (fed funds proxy): 0.3–0.4 correlation (weak-to-moderate). Higher rates = wider USD, weaker global demand, lower LNG prices, which cap US NG. Also, higher real rates reduce industrial capex and energy-heavy consumption.
- **EIA crude stock surprise** (z-score): 0.15–0.25. Weak because different demand drivers, but crude surprise can signal macro demand surprise that affects NG.

**Negatively correlated:**
- **US real yields (10Y TIPS)**: −0.3 to −0.4. When real yields rise (inflation falls, rates rise), growth expectations weaken, industrial demand falls. NG is pro-cyclical.
- **USD strength (DXY)**: −0.2 to −0.3. Strong dollar caps LNG export prices; weak dollar lifts them, supporting Cheniere and other exporters' ability to pay US producers. Effect is modest.
- **Equity indices during demand shocks**: −0.2 to −0.3 in recession scenarios, uncorrelated otherwise.

**Lead/lag:**
- EIA inventory report (Thursday 10:30am ET) → price move within 1–5 minutes, then ripple effects through Friday close.
- Weather forecasts (6–10 day outlooks from NOAA, European model) shift market 2–5 days ahead of actual temps.
- OPEC/geopolitical shocks → oil first, then NG with 3–7 day lag (arbitrage adjustment).

## Recurring patterns

**Seasonal:**
- **Winter (Oct–Mar)**: Heating demand peak. Bullish bias, but volatility intensifies when forecasts show cold snaps 5+ days ahead. January–February historically most volatile. Post-2022 reset: winter 2024–2025 still expensive ($3–$5 range) despite high storage.
- **Summer (June–Aug)**: Cooling demand peak + lower heating. Price typically lower than spring/fall, but extreme heat (>95°F sustained) or power gen spikes can drive short-term rallies. May/June historically weakest months (seasonal dips into storage).
- **Shoulder months (Apr–May, Sept–Oct)**: Transition periods; lowest average volumes and widest bid-ask. Tends to be choppy, low momentum.

**Event-driven:**
- **Weekly EIA inventory release** (10:30am ET Thursdays): Largest regular volatility event. Miss or surprise of >5% vs. consensus can drive 5–15 tick moves in <5 min. Pattern: if draw larger than expected (bullish surprise), price gaps up and holds; if build smaller than expected (bullish), more subdued.
- **NOAA weather updates** (issued Tuesdays, Fridays; 6–10 day outlooks updated daily): Cold snap forecasts 5+ days out → gradual bid-up over 2–4 days. Opposite for warming. Very liquid in response.
- **LNG export plant maintenance or delays** (announced ~monthly): Capacity reduction → lower US production incentive → bearish NG. Freeport outages (2022) caused structural premium.
- **FOMC decisions + Fed guidance**: Rate holds/cuts affect arbitrage and macro demand expectations. Changes in rate expectations can swing NG by 1–2% over hours.

**Time-of-day patterns:**
- **Asian close (6:00am ET)**: Spillover from TTF (European natural gas) if there was overnight action. Minimal direct impact; mostly sentiment.
- **9:30–14:00 ET**: Core US session (stock market hours, fund activity). NG trades flattest or trends slowly; algos active.
- **14:00–17:00 ET (floor close)**: Technical consolidation, then fund rebalancing 15–30 min before close. Risk-off days often see late NG weakness (energy is pro-cyclical).
- **Overnight Globex (17:00–23:00 CT)**: Quieter, wider spreads; susceptible to surprise news or TTF moves. Not primary trading time for US speculators.

**Calendar quirks:**
- **Roll window** (20–25 days before delivery month first notice): Front month volume drops, spreads widen, and the contract transitions to the next month. If contango (farther months higher), roll is neutral; if backwardation (farther months lower), rolling forces a "cost" that directional traders must account for. Post-Ukraine, NG was in extreme backwardation (winter > summer by $1–$2).
- **Last trading day** (3 biz days before delivery month start): Final close-out opportunity. Thin liquidity; wide slippage. Avoid if possible.

## Common setups

1. **EIA surprise gap + follow-through**
   - *Trigger*: EIA release shows inventory draw or build surprise (>5% vs. consensus). Price gaps; look for close above/below the gap by second 5-min bar.
   - *Entry*: Long if surprise is bullish (larger draw than expected) and price holds above gap. Short if bearish (smaller draw).
   - *Stop*: Gap low/high (for longs/shorts). Typical: 3–5 ticks.
   - *Target*: First technical resistance/support (often a prior daily close or 20-day MA); 1:2 to 1:3 RR typical.
   - *Invalidation*: Close back through entry 30 min post-release (market reverses surprise).
   - *Hit rate*: ~55–60% in 2024 sample (EIA surprise + structural backdrop). Miss rate 40–45%.

2. **Weather front fade (5–3 days before cold snap)**
   - *Trigger*: NOAA 6–10 day outlook shows cold snap (−2σ or colder); NG has rallied 2–5% over 3 days.
   - *Entry*: Sell (short) if price pauses or shows weakness intraday (Bollinger Band touch). Often setup develops Wed–Thu with cold snap show for the following week.
   - *Stop*: Above the high of the bounce. Typical: 5–8 ticks.
   - *Target*: Recent baseline (before rally began); exit on trend break (close of daily below 20MA).
   - *Invalidation*: Forecast updated to show even colder = short stops out.
   - *Hit rate*: ~45–50% (many setups fade intraday, few hold to target; requires discipline to stay in through Wednesday oscillations).

3. **Seasonal storage drawdown (Oct–Feb)**
   - *Trigger*: In winter, large draws (>100 BCf/week) are normal; track cumulative draw vs. 5-yr avg. When actual draw lags history significantly (slower than seasonal), it's bullish signal.
   - *Entry*: Long if draw is smaller than seasonal average for N weeks. Establish over multiple EIA releases (don't put all on one).
   - *Stop*: Below the low of entry week. Usually wide (10–15 ticks) because holding through multiple EIA events.
   - *Target*: Seasonal peak (typically Feb near 120 BCf draw/week); exit on reversal signal.
   - *Invalidation*: Massive cold snap that accelerates draws = long may need to exit.
   - *Hit rate*: ~50% (structural bias, but micro setups within the seasonal trend often don't work).

## Classic traps

- **EIA whipsaw**: Market responds to release, gaps up/down 10+ ticks, then reverses 80% within 10 minutes as fast money exits and structural players enter. Many intraday traders get trapped on the fade.

- **Weather forecast disappointment**: A cold snap is forecast 7 days out; market rallies. Forecast updates reduce cold snap intensity by day 5; sell-off. Traders who bought the forecast often face hard stops.

- **Storage + production decoupling**: Occasionally, production stays high despite low prices (producer hedging, capex commitments); storage doesn't build as fast as expected. Market expects bearish surprise on EIA; print is less bad; whipsaw up. Trap: shorting before EIA when supply story is resilient.

- **LNG arbitrage trap**: When US exports are profitable (TTF >> HH), producers pump, supply is abundant. Market looks bearish. But the arbitrage also relieves pressure—without exports, storage would be fuller (and prices lower). The "relief" can catch shorts.

- **Globex overnight move + gap to open**: Overnight, TTF rallies or crashes; NG follows on Globex. By the time US session opens, the move is priced and overleveraged. Morning reversal often whips overnight traders.

- **Leverage + stop-running**: NG has ~$10k notional per contract; retail and hedge funds often 5–10x leverage. Stops at round numbers (e.g., $3.00, $2.50, $4.00) get ran. If entering short-term, avoid round numbers.

## Liquidity profile

- **Average daily volume** (front month): 200k–500k contracts in normal regime; 500k–1M in winter. Post-Ukraine spike: 1M+ common. Summer (Apr–Aug): 150k–300k (thin).
- **Open interest trend**: ~400k–600k for front month; summer sees OI drop to ~200k–300k. Back months are significantly thinner.
- **Pre-open / post-close behavior**: Globex opens Sunday 17:00 CT with wide spreads (~3–5 ticks); fills at open better from 09:30–10:00 ET. Post-close (16:00–17:00 ET floor) is thin; fills worse.
- **Best session for fills**: 09:45–15:30 ET core hours. Avoid 15:45–17:00 ET (floor close approaching), overnight Globex.
- **Bid-ask spread**: 1–2 ticks normal in core hours; 3–5 ticks in shoulder months / post-close.

## Options (if applicable)

- **Weekly expirations**: Mondays (expire Friday end of day prior week). Actively traded for short-dated directional plays and mean-reversion.
- **Monthly expirations**: 3rd Thursday of month. Lower IV, wider spreads.
- **Quarterly (seasonal expirations)**: End of Q1/Q2/Q3/Q4. Very active in winter (Oct–Mar) months.
- **Settlement**: 10:30am CT Fridays (for weeklies); 16:00 CT on listed expiration date (for monthlies).
- **Typical IV rank range**: Summer (Apr–Aug): 15–35th percentile (low IV). Fall–winter (Sept–Mar): 50–85th percentile (high IV).
- **Pin-risk behavior**: Weekly options on NG are vulnerable to pin risk near strike prices close to EIA release times. Avoid short gamma near Friday close if EIA is Thursday.

## Risk notes

- **Gap risk profile**: Highest intraday gap risk is EIA release (Thursday 10:30am). Overnight gaps on TTF spikes or geopolitical shocks (energy sector sensitive to Russia/OPEC flow disruption). Typical gap: 3–8 ticks; extreme (>15 ticks) on supply surprises.

- **Limit-up / limit-down mechanics**: NG has no daily price limits under CME rules, but exchange reserves right to halt trading in case of "disorderly" markets. In extreme cold snaps (2021) or LNG export outages (2022), NG has spiked 50%+ in weeks—no circuit breaker halts per-day.

- **Worst weekly move in last 5 years**: Feb 2021 (Texas freeze): NG rallied from $2.60 → $4.80 in single week (+85%). Jan 2022 (post-Ukraine): rallied $2.80 → $5.40 (+93%). Summer 2022 (EU storage crisis): rallied from $2.50 → $10+ in European TTF (NG stayed $3–$4 due to US export cap constraints and storage abundance). US winter 2024 was more muted (~$2.50–$4.50 range).

- **Tail-risk events to remember**:
  - **Texas freeze (Feb 2021)**: Unexpected polar vortex, production froze, storage couldn't backfill. Supply shock.
  - **Ukraine invasion + European energy crisis (Feb 2022)**: Geopolitical shock; Europe cut Russian supply; TTF spiked 400%+. US NG benefited from LNG export upside.
  - **Freeport LNG outage (May 2022–Aug 2022)**: Plant explosion halted US exports; NG sold off. Re-opening lifted prices when capacity returned.
  - **Post-UAE interest-rate shock (Sept 2022)**: Energy is pro-cyclical; rate shock killed growth expectations; NG sold off despite cold winter expectations.

## References

- **CME NG contract**: https://www.cmegroup.com/markets/energy/natural-gas/natural-gas.contractSpecs.html
- **EIA weekly storage report**: https://www.eia.gov/naturalgas/storage/weekly/ (Thursday 10:30am ET release)
- **NOAA weather outlook**: https://weather.gov/wrh/ (National Weather Service regional forecasts; 6–10 day outlooks updated daily)
- **Henry Hub spot prices**: https://www.eia.gov/dnav/ng/hist/rhhngsp.htm (daily close reference)
- **Liquidity notes**: Winter (Oct–Mar) is the most liquid period; summer is thin. Roll 20+ days before expiration to avoid liquidity drop-off.
