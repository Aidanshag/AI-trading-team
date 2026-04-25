---
type: product_deep_dive
symbol: SI
sector: Precious Metals
analyst: Fund Engineer
updated: 2026-04-25T15:30:00Z
---

# [[SI]] — COMEX Silver

## Contract specs

- Exchange / product code: COMEX (CME Group) / SI
- Tick size / tick value: $0.001 per troy oz = $5 per tick (micro: $0.0001 = $0.50 per tick on SIL)
- Contract months (delivery cycle): Jan, Mar, May, Jul, Sep, Dec (4 near-term months are most liquid)
- Session hours (RTH and extended): Sunday–Friday, 6:00 PM–1:00 AM CT (overnight), then 1:30 AM–1:25 PM CT (RTH)
- First notice / last trading day: 3rd to last business day of contract month
- Settlement: Physical delivery (5,000 troy oz per contract)
- Margin (initial / maintenance at Topstep, if known): Typically $4–6k initial, $3–4.5k maint on standard SI; much tighter on SIL (micro)

## What it actually is

Silver (SI) is the COMEX precious metals contract representing 5,000 troy ounces of refined silver bullion. Unlike gold, silver has dual utility: it is both a monetary asset (store of value, portfolio hedge) and an industrial metal (electronics, solar panels, antibacterial coatings, photography). This dual nature makes silver volatile relative to gold—it tends to amplify precious-metals moves in risk-on/risk-off environments while also being sensitive to manufacturing demand surprises. Hedgers include miners (selling production), fabricators (buying for input), and refiners; speculators range from retail traders to macro funds using it as inflation protection or tactical commodity exposure.

## Primary drivers

Ranked by influence in the current regime (Apr 2026—watch Fed pivot timelines, China stimulus rollout, industrial demand stalling):

1. **Gold (GC)** — Silver's primary peer; GC moves lead SI by 5–15 min on macro news (DXY, rates, safe-haven flows). The SI/GC ratio (currently ~80–100:1) reverts to longer-term means (~65–75:1) but swings 10–20% intra-regime.
2. **USD strength (DXY)** — Inverse relationship. Strong USD (> 105) suppresses silver prices via import demand and carry-trade unwinding. Weak USD (< 100) supports on inflation fears and portfolio rebalancing.
3. **Real rates (10Y TIPS yield)** — Silver, like gold, is negatively correlated with real yields (r = −0.65 typical). When TIPS yields spike, precious metals sell off. Falling real rates are silver's best friend.
4. **Industrial demand (manufacturing PMI, solar capex)** — Secondary but non-trivial. Positive surprises in Chinese PMI or US manufacturing usually lift silver more than gold. Solar subsidies and EV battery adoption (silver paste) add micro-cycle sensitivity.
5. **Macro risk sentiment (VIX, equity vol)** — Spike in risk-off correlates with precious-metals inflows. However, silver's carry trade (borrowing cheap in USD, selling short SI) can cause liquidations in panic widows.

## Key correlations

- **Positively correlated with:**
  - [[GC]] Gold (r ≈ +0.82). Same macro drivers; SI more volatile. Pair trading (long GC/short SI or vice versa on ratio extremes) is a common setup.
  - [[DXY]] inversely via commodity super-cycle (r ≈ −0.55 inverse). Weak USD → higher nominal commodity prices.
  - [[CL]] Oil (r ≈ +0.35–0.45 depending on regime). Both commodities respond to inflation expectations and EM demand.
  - Inflation expectations, 5Y5Y breakevens (r ≈ +0.4).

- **Negatively correlated with:**
  - [[ZB]] T-Bonds, 10Y yields (r ≈ −0.6). Higher nominal rates pull gold/silver down.
  - [[DGS10]] TIPS real yields (r ≈ −0.65). Strongest relationship in rates.
  - [[6E]] EUR/USD (r ≈ +0.45 inverse during Europe risk-off). EUR strength (safe-haven unwind) hammers commodities.

- **Lead/lag relationships:**
  - Gold typically leads silver by 5–20 min on macro news (Fed, geopolitical shocks).
  - Chinese equity weakness often precedes SI weakness by 1–2 trading sessions (demand cycle leading indicator).
  - COMEX silver's overnight (6pm–1am CT) is often frontrun by Shanghai gold (11:30 PM–2:00 AM CT Shanghai time, ~7–9 hrs ahead). Monitor SH gold futures as a proxy during NY evening.

## Recurring patterns

- **Seasonal (calendar effects):**
  - Jan–Mar: Seasonal industrial demand (electronics, solar prep for spring install). Silver can outperform gold.
  - Apr–May: Passover and spring wedding season lift demand slightly (jewelry); hedged by supply anticipation (mine output ramping post-winter).
  - Jun–Aug: Summer doldrums; lower industrial and jewelry demand. Tends to trade tighter and weaker on seasonal rebalancing.
  - Sep–Oct: Diwali season (Oct–Nov) drives jewelry demand from India; Nifty weakness can suppress. Watch INR movements.
  - Nov–Dec: Holiday demand, year-end rebalancing, and safe-haven flows (if risk-off). GC typically leads.

- **Event-driven:**
  - FOMC meetings and Fed speaker commentary (especially real-rate sensitive plays).
  - US inflation prints (CPI/PPI). SI is more sensitive to *upside surprises* in inflation than to expected inflation.
  - Chinese PMI (manufacturing, service) on 1st business day of month. China is ~15% of global silver demand (solar, electronics).
  - Mining production disruptions (labor, environmental, geopolitical—e.g., Peru, Mexico unrest).
  - Central bank gold-buying announcements (China, Russia often buy in Q1; creates portfolio-rebalancing demand).

- **Time-of-day patterns:**
  - London open (12:00 PM UTC = 6:00 AM CT): Modest activity spike; European equity selling can pressure SI.
  - London close / NY open (4:00 PM UTC = 10:00 AM CT): FOMC, economic data often drops here. Volatility peak.
  - NY midsession (2:00–3:00 PM CT): Mid-day consolidation; momentum burns off.
  - After-hours (overnight 6 PM–1 AM CT): Lower volume, wider spreads; prone to stop-hunting on thin depth.

- **Calendar quirks:**
  - Roll windows (6–10 days before first notice): Front month can decouple on carry arbitrage unwinding; vol can spike.
  - Month-end (last 2 days of contract): Technical unwinding, fund rebalancing.
  - Expiration Mondays: If large open interest, risk of squeezes or pin action near option strike clusters.

## Common setups

1. **Gold/Silver ratio mean reversion:**
   - Trigger: Ratio pushes > 100:1 (silver underprices relative to historical). Long SI / short GC (or long SI outright).
   - Invalidation: Ratio breaks to 110:1 or above (extended unwind); structural divergence in industrial demand.
   - Exit: Ratio returns to 85–90:1, or risk hit 5%.
   - Win rate: ~55–60% when combined with real-rate support (TIPS yield falling). Weak in climbing-rates regime.

2. **Breakout after consolidation:**
   - Trigger: SI consolidates 3–5 days within a ±2% band. Break above with volume (ADV > 1M contracts). Real-rate tailwind (TIPS yield < 1%).
   - Invalidation: Close back inside consolidation band next day, or real rates spike.
   - Exit: First target 3% above entry; second target 7%. Trail a stop at 5-day low.
   - Win rate: ~58% with macro confirmation, ~48% without.

3. **Risk-on/risk-off rotations:**
   - Trigger: VIX drops sharply (equity inflows) OR equity drawdown > 5% (safe-haven bid). SI tends to lead GC on 2–4 hour lag.
   - Invalidation: Reversal in equity direction or shift in real-rate expectation.
   - Exit: Fade SI move when it lags GC by > 20 min (momentum exhaustion).
   - Win rate: ~62% on high-conviction macro days (FOMC, CPI).

## Classic traps

- **Liquidity illusion on thin spreads:** Front-month SI can show sub-$0.05 spreads but evaporates beyond 500-contract blocks. Slippage on large size is brutal.
- **Gap risk overnight:** COMEX silver has a 5.5-hour gap (1:00 AM–6:00 PM CT) where no contract is open. Gap fills can be 1–3% and trigger stops routinely. Smaller on calm nights; massive on geopolitical shock.
- **Gold divergence:** SI is not just "volatile gold." When mining supply disruption is localized (e.g., Peru) or industrial demand crashes (e.g., China lockdown surprise), SI can decouple sharply and grind lower despite GC strength.
- **Inverse relationship mismatch:** Traders assume SI and DXY always move inverse. They do long-term, but on 1–5 day horizons, DXY can rally (safe-haven) while SI rallies (inflation fear). Know the macro regime.
- **Earnings drag on silver miners:** SI can rise while [[AG]], [[PAAS]], and [[HL]] (silver producer equities) underperform if mining costs are soaring or geopolitical risk is high. Fundamental disconnect.
- **Carry-trade unwinding:** Borrowed silver can be shorted into strength. Sudden rate expectations (Fed hiking longer than expected) can trigger violent buybacks. Watch for 8–12 handle moves in 1 hour.

## Liquidity profile

- **Average daily volume (front month):** ~50–80M oz (equivalent to ~10–16M contracts of 5,000 oz). Highly liquid; one of COMEX's top 5.
- **Open interest trend:** Typically 80–150k contracts open. Heaviest in 3 near-term months (Jan, Mar, May) and Dec. Far months (Jun–Nov) are thin.
- **Pre-open / post-close behavior:** 6:00 PM CT open (Sunday) sees 15–30% of daily vol in first 15 min (carryover from Friday close + weekend news). Quiet between 1:00 AM–1:30 AM CT (gap zone).
- **Session with best fills:** 7:00–10:30 AM CT (US morning, overlapping London tail). Spreads tighten to $0.01–0.02 per oz. Avoid 1:00 AM–1:30 AM CT gap zone at all cost for size.

## Options (if applicable)

- **Weekly / monthly / quarterly expirations:** 
  - Monthly options (American-style) expire 4 Fridays before contract delivery month.
  - Weeklies available on front month; Friday settlement.
  - Quarterly (Jan, Apr, Jul, Oct) used by large structural hedgers.

- **AM vs PM settlement:** COMEX SI options are PM-settled; this means settlement value is set at 1:30 PM CT (RTH close).

- **Typical IV rank range:** 20–80 depending on macro regime. Baseline ~40. Spikes to 60–70 during FOMC days, geopolitical shocks, or mining disruptions. Crashes to 15–20 during summer doldrums.

- **Pin-risk behavior:** SI has notable pin-risk around strike clusters in delivery months (especially March, May). Avoid shorting calls or buying puts within $0.50 of major strike clusters in final 2 days of contract month. Miners often have large put positions; can force delivery surprises.

## Risk notes

- **Gap risk profile:** VERY HIGH overnight (1:00 AM–6:00 PM CT close). Typical overnight gap: 0.5–1%. Extreme scenarios (geopolitical, Fed surprise): 2–4%. *Always* use a stop-loss—no overnight naked shorts or longs. Always use stops.
- **Limit-up / limit-down mechanics:** SI has a 10% daily limit (expanded from 5% during high-vol periods). Limit-up or limit-down scenarios are rare but can occur on supply shocks or risk-on capitulation. When this happens, trading halts for 15 min, then limit expands to 15% and resets nightly.
- **Worst weekly move in last 5 years:** –8.5% (weeks ending Mar 16 2020, COVID crash). +7.2% (week of Nov 8 2021, rate pivot unwind). Expect ±5% in normal weeks; ±8% in high-beta macro weeks.
- **Tail-risk events to remember:**
  - Ukraine invasion (Feb 2022): +3.5% in 4 hours on risk-off inflow.
  - Energy crisis (Sep 2022): +4.5% as inflation expectations spiked, then –5% as Fed hawkishness reasserted.
  - China stimulus (Nov 2023): +6% over 3 days on industrial demand hope; faded as real rates didn't follow.
  - Deposit bank stress (Mar 2023): +4.5% on safe-haven bid; reversed quickly as Fed stabilized system.

## References

- CME COMEX Silver product page: https://www.cmegroup.com/markets/metals/precious/silver.contractSpecs.html
- Historical SI/GC ratio analysis: Track via TradingView, watch 65–75:1 as long-term fair value.
- Federal Reserve TIPS yield (DGS10) as primary macro driver: Monitor daily.
- China manufacturing PMI (Caixin Manufacturing PMI) as industrial demand proxy: 1st business day of each month.
- Mining production calendars: Peru (first global producer), Mexico (second). Track labor disputes and environmental risk.
- Silver Institute annual demand reports (released yearly in April).
- Seasonality: Use 10-year historical SI charts to validate patterns; seasonal decay is real but non-dominant in current regime (macro > seasonal).
