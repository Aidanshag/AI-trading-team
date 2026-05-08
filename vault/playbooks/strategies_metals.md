---
type: playbook
category: trading_strategies
applies_to: [analyst_metals, portfolio_manager, risk_manager]
symbols: [GC, MGC, SI, SIL, HG, PL, PA, ALI]
updated: 2026-04-23
---

# Metals — trading strategies

Products: [[GC]] gold, [[MGC]] micro gold, [[SI]] silver, [[SIL]] micro silver, [[HG]] copper, [[PL]] platinum, [[PA]] palladium, [[ALI]] aluminum.

## 1. Real-yield-pivot gold long

**One-liner**: When 10Y TIPS real yield rolls over from a cycle high, long GC with 15–25 session horizon.

**Thesis**: Gold is a long-duration monetary asset. Its primary macro driver is the 10Y real yield (nominal 10Y − 10Y breakeven, or directly TIPS yield). When real yields pivot down after a cycle high, gold's opportunity cost drops and flows return. The signal is cleaner when DXY is also rolling over.

**Trigger**:
- 10Y TIPS yield prints 5+ bps lower than the trailing 20-day high.
- DXY below its 20-day moving average.
- GC above 50-day moving average (trend confirmation).

**Invalidation**:
- TIPS yield reverses, breaks to new cycle high.
- DXY breaks out strongly.
- Gold breaks below 50-day MA.

**Structure**:
- Long GC (or MGC for sizing) outright, or call spread DTE 30–60.
- Size: 50 bps of equity.

**Exit rules**:
- Target: +2R or 3 weeks.
- Scale out 1/3 at +1.5R.
- Stop: yield or DXY reverses.
- Time stop: 25 sessions.

**Calibration**:
- Expected hit rate: 60%.
- Expected average R: +1.2.
- Historical: 2019 Fed pivot (+3R), 2023 regional bank stress (+2R over 2 weeks).

**Common traps**:
- Chasing gold on a headline rally without real-yield confirmation.
- Ignoring central-bank flow data (structural gold bid is slow but real).
- Holding past TIPS yield reversal.

---

## 2. Gold-silver ratio mean reversion

**One-liner**: When GSR > 85, short the ratio (long SI, short GC); when GSR < 65, long the ratio (long GC, short SI). Target return to 70–80 range.

**Thesis**: The gold-silver ratio (GC/SI by oz) has oscillated in a 40–90 band for decades, with most years 60–85. Extremes reflect regime shifts: high ratios = defensive/deflation; low ratios = inflation/risk-on. The ratio mean-reverts within 2–6 months when not in a generational shift.

**Trigger**:
- GSR > 85: position short ratio. Corroborate with industrial-demand signals (copper-gold confirming pro-cyclical).
- GSR < 65: position long ratio. Corroborate with defensive signals.
- No structural regime shift signal (major Fed pivot, crisis event).

**Invalidation**:
- Ratio breaks beyond 90 or 55 — treat as regime shift, close.
- Concurrent crisis event that changes the dynamics.

**Structure**:
- Paired: long/short GC vs SI in a ratio that normalizes dollar exposure (typical: 2:1 GC:SI by contract, adjust based on prices).
- Size: 50 bps of equity on ratio P&L.

**Exit rules**:
- Target: return to 70–80.
- Stop: ratio extends beyond 90 or 55.
- Time stop: 90 sessions.

**Calibration**:
- Expected hit rate: 60%.
- Expected average R: +1.0.
- Historical: 2020 COVID-spike GSR hit 125 (extreme) — reverted to 75 over 6 months, +3R for early entries.

**Common traps**:
- Entering at the first extreme — wait for confirmation.
- Ignoring silver's industrial sensitivity in tech-demand cycles.
- Legging in — get both within minutes.

---

## 3. Copper China-credit-impulse long

**One-liner**: When Chinese credit impulse turns positive (delta 6-month), long HG via defined-risk structure for 4–8 weeks.

**Thesis**: China consumes ~50% of global copper for construction, grid, and EV. The Chinese credit impulse (change in new credit / GDP) leads industrial activity by 3–6 months. When it turns positive after a downturn, copper demand accelerates. This is one of the cleanest macro-to-commodity linkages.

**Trigger**:
- Chinese credit impulse delta 6-month turns positive.
- LME copper inventories drawing.
- HG above 50-day MA.
- DXY not breaking out (dollar weakness supports commodity bid).

**Invalidation**:
- Next month's credit impulse reverses.
- LME inventory surges.
- DXY breaks out strongly.

**Structure**:
- Long HG via call spread, DTE 45–90 (outright HG too expensive per 50 bps cap).
- Size: 50 bps of equity max-loss.

**Exit rules**:
- Target: +2R or 6 weeks.
- Stop: credit impulse reverses OR inventory surges.
- Time stop: 90 sessions.

**Calibration**:
- Expected hit rate: 60%.
- Expected average R: +1.3.
- Historical: 2016 (+3R), 2020-Q3 stimulus (+4R).

**Common traps**:
- Single-month credit data — use the 6-month delta.
- Ignoring Chilean/Peruvian supply events.
- Sizing for outright HG — stops are usually too wide for firm per-trade cap.

---

## 4. Palladium supply-shock defined-risk long

**One-liner**: On Russian/Nornickel supply disruption or sanction headlines, long PA via call spread (never outright due to volatility).

**Thesis**: ~40% of global palladium comes from Russia (primarily Nornickel). Supply disruptions — whether strike, sanctions, transport, or refinery — produce sharp upward moves. Palladium is the most volatile of the precious metals; option structures are mandatory.

**Trigger**:
- Credible supply-disruption headline.
- PA front-month spikes 3%+ day 1.
- No concurrent demand-destruction signal (auto-sales collapse).

**Invalidation**:
- Disruption resolved quickly.
- EV-adoption headlines (long-term substitution concern emerges).

**Structure**:
- Long PA call spread, DTE 30–45, strikes OTM.
- Size: 25 bps of equity max-loss (half-size for volatility).

**Exit rules**:
- Target: +2R or 4 weeks.
- Stop: disruption resolves.
- Time stop: 45 sessions.

**Calibration**:
- Expected hit rate: 55%.
- Expected average R: +1.5.
- Historical: 2022 Russia sanctions (+4R), 2018 Nornickel dam issue (+2R).

**Common traps**:
- Ever doing outright PA — it's been known to gap 15%+ in a session. Always defined risk.
- Ignoring auto-sales data — PA is for gasoline catalysts; EV trend is a long-term headwind.
- Fading a resolved disruption — but waiting too long means the move is done.

---

## 5. Platinum-palladium ratio convergence

**One-liner**: When PL/PA ratio is below 0.6 (historically extreme low), long PL / short PA spread targeting mean reversion to 0.9–1.1.

**Thesis**: Platinum and palladium are catalytic-converter metals but serve different engine types — platinum for diesel, palladium for gasoline. Historically the PL/PA ratio has oscillated 0.9–1.4, with 1.0–1.1 as the typical band. Extreme divergences (like PA overshooting during 2019–22 supply crunch) produced ratios as low as 0.4–0.5 — mean-reverting targets.

**Trigger**:
- PL/PA ratio < 0.6 (extreme low).
- No imminent diesel-banning regulatory event (kills PL demand outright).
- Supply-shock premium in PA that's arguably over-done.

**Invalidation**:
- Ratio extends to < 0.4 (new regime).
- Diesel-banning headlines (European cities banning ICE vehicles).

**Structure**:
- Paired: long PL + short PA (note: short PA is disallowed outright; use long PL + long PA put spread for defined risk).
- Size: 25 bps of equity max-loss.

**Exit rules**:
- Target: ratio returns to 0.9.
- Stop: ratio extends beyond 0.5.
- Time stop: 90 sessions.

**Calibration**:
- Expected hit rate: 55%.
- Expected average R: +1.2.
- Historical: 2020–21 trade worked +3R; some setups take 6+ months to converge.

**Common traps**:
- Size matters — both metals are thin; work micro-equivalents when available.
- Ignoring diesel-policy news — European regulatory shifts affect platinum demand structurally.
- Timing — convergence can take months.

---

## 6. Aluminum energy-cost transmission

**One-liner**: When European nat-gas prices spike and Chinese smelter curtailments are reported, long ALI for 4–8 weeks.

**Thesis**: Aluminum smelting is 30–40% energy cost. When power prices spike (particularly European nat gas during winter) or Chinese curtailments are announced (environmental/policy), smelter capacity comes offline. Supply tightens; LME inventories draw. This plays out over weeks, not days.

**Trigger**:
- European TTF (nat gas) front-month > 3-year high.
- LME aluminum inventory drawing for 2+ weeks.
- Chinese smelter curtailment headlines.

**Invalidation**:
- Energy prices collapse.
- Smelters come back online.
- Chinese policy reverses.

**Structure**:
- Long ALI via call spread, DTE 60–90.
- Size: 50 bps of equity max-loss.

**Exit rules**:
- Target: +2R or 8 weeks.
- Stop: energy prices collapse OR LME inventory surges.
- Time stop: 90 sessions.

**Calibration**:
- Expected hit rate: 55%.
- Expected average R: +1.3.
- Historical: 2022 European energy crisis (+3R over 2 months).

**Common traps**:
- Ignoring demand side — construction slowdown can offset supply tightness.
- Short-term focus — this is a weeks-to-months thesis.
- Sizing outright — defined-risk wrapping protects against sudden energy reversals.
