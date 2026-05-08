---
type: playbook
category: trading_strategies
applies_to: [analyst_grains, portfolio_manager, risk_manager]
symbols: [ZC, ZS, ZW, ZL, ZM, ZO, ZR]
updated: 2026-04-23
---

# Grains & Oilseeds — trading strategies

Products covered: [[ZC]] corn, [[ZS]] soybeans, [[ZW]] wheat (CBOT), [[ZL]] soybean oil, [[ZM]] soybean meal, [[ZO]] oats, [[ZR]] rough rice. Read alongside the [[energies_analyst|product deep-dives]] for each.

## 1. WASDE surprise continuation

**One-liner**: On a USDA WASDE release, wait 30 min, enter in direction of the confirmed move with a 1.5× ATR stop and a 2R target.

**Thesis**: Monthly WASDE reports revise ending stocks, yield, and export estimates. Large surprises (> 1σ from consensus) produce tradeable one-day and multi-day moves. The first 15 minutes post-release is noisy and often reverses partially; the 30-minute mark filters out flash reactions and captures the durable directional move.

**Trigger** (all three required):
- WASDE headline surprise ≥ 1σ from consensus on ending stocks or yield.
- 15–30 min post-release, price has held direction of initial move within 25% of the post-release peak/trough.
- Volume in the 15–30 min post-release window is ≥ 2× the 20-day average for that time window.

**Invalidation** (exit immediately):
- Price retraces > 50% of the 0–15 min post-release move within the next hour.
- A counter-report or correction is issued by USDA within the day.

**Structure**:
- Outright front-month futures.
- Size: per-trade risk 50 bps of equity (firm cap).
- Stop: 1.5× the 20-bar 5-minute ATR from entry.
- Target: 2R (2× stop distance) on the first scale-out; let the second half trail on 20-period high/low.

**Exit rules**:
- Half off at 2R.
- Remaining half trails on the prior day's low (long) / high (short).
- Full exit by end of session day + 2 unless a fresh catalyst extends the thesis.

**Calibration**:
- Expected hit rate: 55–60%.
- Expected average R: +0.9 to +1.2 (weighted by hit rate).
- Best realized: +3R on large surprise prints (e.g. 2012 drought WASDEs).
- Worst realized: −1R on clean invalidation.

**Common traps**:
- Trading the first 15 min — the algos and spread traders front-run and reverse repeatedly.
- Ignoring crush spread implications — a bullish soybeans number may be bearish meal if the stocks tightness is oil-side.
- Chasing on the second day — most of the R has already been taken.

---

## 2. South American weather-season positioning

**One-liner**: Long soybeans or wheat Dec–Feb if Brazilian drought signal confirmed across two independent forecast sources + CONAB yield cut.

**Thesis**: Southern-hemisphere summer (Dec–Mar) is the critical growing season for Brazilian soybeans and Argentine corn/soybeans. Supply shocks in the southern hemisphere during US dormant season produce multi-week trends that US producers cannot offset. The market underprices southern-hemisphere weather risk until mid-flowering stage.

**Trigger** (all required):
- Two independent weather forecast services (ECMWF + GFS, or similar) show below-normal precipitation for Mato Grosso / Buenos Aires province for the next 15-day outlook.
- Brazilian CONAB or Argentine Rosario Grain Exchange issues a yield cut ≥ 2%.
- Front-month futures have broken above the 20-day moving average on rising volume.

**Invalidation**:
- Forecasts revert to normal precipitation across both services.
- BRL or ARS strengthens > 3% (dollar-denominated grain prices typically compress).

**Structure**:
- Outright front-month soybeans (ZS) or a [[crush_spreads|paired crush spread]] if thesis is oil-driven.
- Alternative for defined risk: long call spread, DTE 30–45.
- Size: 50 bps of equity.
- Stop: below the 20-day MA (wider than a typical stop due to swing-horizon trade).

**Exit rules**:
- Scale out 1/3 at +1.5R, 1/3 at +3R.
- Final 1/3 exits when forecast reverts OR CONAB revises yield upward.
- Time stop: session close Feb 28 (end of critical window).

**Calibration**:
- Expected hit rate: 45–55% (lower due to weather mean-reversion).
- Expected average R: +1.2 to +1.8 when it hits (payoff skewed right).
- Historical: 2012 drought (+8R), 2020 La Niña (+4R), 2023 whipsaw season (−1R, then +2R).

**Common traps**:
- Entering on a single forecast run — weather models revise rapidly.
- Ignoring currency effects — BRL weakness can kill a USD-denominated long even with bullish fundamentals.
- Holding past harvest — once Brazilian harvest begins (Feb/Mar), supply floods and the trend reverses.

---

## 3. Crush spread mean reversion

**One-liner**: Fade the board soybean crush when it reaches ±1.5σ from its 60-day mean with at least two fundamental drivers corroborating.

**Thesis**: The board soybean crush (`ZM price × 0.022 + ZL price × 11 − ZS price`, in cents/bushel) reflects processor margins. It mean-reverts because:
(a) high crush incentivizes processors to buy beans / sell meal+oil, compressing the spread, and
(b) low crush causes processors to slow throughput, tightening meal and oil, expanding the spread.

The 60-day rolling mean is a stable anchor in most regimes.

**Trigger**:
- Crush is ≥ 1.5σ above or below its 60-day mean.
- **For fading high crush** (short spread): processor utilization reports high AND oil/meal inventories are building.
- **For fading low crush** (long spread): processor slowdown headlines AND oil or meal basis strengthening (physical pull).

**Invalidation**:
- Crush breaks beyond 2.5σ without mean-reversion signal — treat as new regime.
- A structural shock (biofuel policy change, major processor outage) is announced.

**Structure**:
- Paired position: long or short the crush as a single trade.
- Formula expression: 1× ZS paired against 11× ZL + 0.022× ZM units per bushel (use multi-leg order if supported; otherwise enter legs within 5 minutes).
- Size: 50 bps of equity against the **spread** P&L, not the legs.

**Exit rules**:
- Target: return to the 60-day mean (half out) or to the opposite 0.5σ (full).
- Stop: further 1σ adverse move OR structural-shock news.
- Time stop: 15 trading days (beyond that, the mean has probably shifted).

**Calibration**:
- Expected hit rate: 60–65% (mean-reversion trades tend to have higher hit rates, smaller R).
- Expected average R: +0.8 to +1.2.
- Historical: steady performer in non-drought years; suspends during Jun–Aug US weather season.

**Common traps**:
- Shorting a high crush during a soybean oil demand shock (RD/biodiesel mandate announcements) — oil keeps pulling the spread wider.
- Legging in — if you can't get all three legs quickly, abandon the trade.
- Running it through a WASDE — reports revise end-stock assumptions that reprice the spread.

---

## 4. Planting-progress conviction trade

**One-liner**: Position for the Jun 30 Grain Stocks + Planted Acres report based on weekly NASS Crop Progress divergence from trend.

**Thesis**: The Jun 30 USDA Planted Acres / Grain Stocks report is arguably the most-important grain print of the year. Weekly NASS Crop Progress data in May–Jun leaks information that the market often prices slowly. Systematic divergence between progress and trend (e.g., corn 20% planted vs 50% trend) is a tradeable edge into the Jun 30 print.

**Trigger**:
- By Jun 15, a weekly NASS report shows crop progress ≥ 10 percentage points behind the 5-year average for that week.
- Weather forecasts do not show a catch-up window in the next 14 days.
- Front-month corn or soybeans has not yet priced the divergence (< 3% off pre-planting levels).

**Invalidation**:
- Rapid catch-up week (planting progress gains > 15 pp in a single week).
- A surprise large upward revision in Planted Acres intentions report.

**Structure**:
- Long front-month corn or soybeans, scaled in 50%/30%/20% over 3 weeks.
- Defined-risk alternative: long call debit spread, DTE = Jun 30 + 15 days.
- Size: 50 bps of equity total across the three entries.

**Exit rules**:
- Jun 30 report: if acres print is a bullish surprise, half off immediately on the 30-min post-release close; hold the rest for Jul follow-through.
- Jun 30 report: if acres print is bearish/in-line, exit full position on the 30-min close.
- Stop: broken through pre-May low.

**Calibration**:
- Expected hit rate: 50–55% (binary event drives distribution).
- Expected average R: +1.5 to +2.0 when it hits (asymmetric pay-off on surprise prints).
- Historical: 2019 wet spring in corn belt produced a 6-week trend post-Jun 30 +$0.80/bu = ~5R.

**Common traps**:
- Under-sizing — the Jun 30 print is one of the biggest R opportunities in grains, don't leave the trade tiny because of "event risk" if the thesis is genuinely strong.
- Buying into a Jun 29 rally — late entries rarely work; the leak has already been priced.
- Ignoring cross-sector — a delayed corn plant means delayed soybean plant (rotation); the trade is often in both.

---

## 5. Harvest-low reversal

**One-liner**: Buy corn or soybeans on the season-low printed during harvest pressure (Sept–Oct) once basis strengthens and export sales pick up.

**Thesis**: Harvest pressure produces a seasonal low in corn (Oct) and soybeans (late Sept–early Oct). The board price bottoms before the underlying supply-demand story does because:
(a) commercial hedging compresses board prices,
(b) farmer selling peaks in the first 6 weeks of harvest,
(c) export pace and basis rebuild once harvest-hedge pressure abates.

The reversal is signaled by basis strengthening ahead of the board.

**Trigger**:
- Season-low printed in corn (Oct) or soybeans (late Sept).
- USDA Weekly Export Sales report shows 2 consecutive weeks of above-trend sales.
- Basis at interior elevators strengthens ≥ 5 cents from the harvest-pressure trough.

**Invalidation**:
- Basis weakens again OR export sales roll over.
- South American planting is going smoothly (removes fundamental tailwind).

**Structure**:
- Long front-month futures or Mar/May calendar (the deferred contract expresses the carry-forward thesis cleaner).
- Size: 50 bps of equity.
- Stop: below the harvest low.

**Exit rules**:
- Target: return to the pre-harvest range midpoint (half) or pre-harvest high (full).
- Stop: break below harvest low on 2-day close.
- Time stop: end of Jan — beyond that, the South American harvest narrative takes over.

**Calibration**:
- Expected hit rate: 55–60%.
- Expected average R: +1.2 to +1.5.
- Historical: reliable in most years; fails in years of structural oversupply (e.g. 2016 corn).

**Common traps**:
- Buying the low without waiting for basis confirmation — many false bottoms.
- Holding into Brazilian harvest (Feb) — the thesis has expired by then.
- Over-sizing on soybeans specifically — soy is more volatile than corn; stops run wider and need smaller nominal size.

---

## 6. Inter-commodity corn/wheat ratio

**One-liner**: When ZW/ZC ratio drops to < 1.0, go long wheat / short corn as a feed-substitution mean-reversion.

**Thesis**: Corn and wheat compete as feed grain (wheat substitutes for corn in rations above certain price parity). Historically, the wheat/corn ratio oscillates in a 1.1–1.8 range. When it falls below 1.0, wheat is "cheaper per calorie" than corn and feed demand for wheat rises, supporting wheat and pressuring corn.

**Trigger**:
- ZW/ZC ratio (front-month) ≤ 1.05.
- USDA Grain Stocks report does not show a wheat export collapse (rules out structural demand failure).
- No imminent wheat harvest pressure (Jun–Jul) that would extend the discount.

**Invalidation**:
- Wheat-specific supply shock that further tightens wheat alone (Russia export ban, Australian drought).
- Ratio breaks below 0.90 — treat as new regime, exit.

**Structure**:
- Paired: long ZW + short ZC in a 2:1 ratio by contract (or DV01-adjusted if preferred).
- Size: 50 bps of equity on the spread.

**Exit rules**:
- Target: ratio returns to 1.30 (mid-range).
- Stop: ratio breaks below 0.90.
- Time stop: 45 trading days.

**Calibration**:
- Expected hit rate: 55–60%.
- Expected average R: +1.0 to +1.4.
- Historical: works in normal-demand regimes; failed 2022–23 (Russia/Ukraine shock pushed wheat away from corn).

**Common traps**:
- Legging in — get both sides within minutes.
- Fading a war-driven wheat premium — geopolitics can extend the ratio indefinitely.
- Running through Aug Grain Stocks — wheat revisions can reprice the ratio without warning.

---

## 7. Export-pace momentum

**One-liner**: When USDA Weekly Export Sales beats 4-week average by > 50% for 2 consecutive weeks, position long the demanded grain for 3–4 weeks.

**Thesis**: Weekly Export Sales report is a forward demand indicator. Two consecutive outsized weeks signals a real demand impulse (not a single-buyer event), which typically leads price by 2–4 weeks as physical pipelines fill and shippers chase capacity.

**Trigger**:
- Two consecutive Weekly Export Sales prints > 150% of the trailing-4-week average.
- The buyer country / region is named in the report (removes unknown-destination ambiguity).
- Basis at export elevators (Gulf, PNW) strengthens in sympathy.

**Invalidation**:
- Third-week print reverts to near-average (demand pulse was a 2-week blip).
- Major buyer cancellation reported.

**Structure**:
- Long front-month or next-deferred (deferred catches the forward pipeline).
- Size: 50 bps of equity.
- Stop: below the last-week-before-signal low.

**Exit rules**:
- Target: 2R or 4-week hold, whichever comes first.
- Stop: weekly export sales report a major cancellation OR basis rolls over.

**Calibration**:
- Expected hit rate: 55%.
- Expected average R: +1.2.
- Historical: consistent in China-soybean pulse years (late summer / early autumn).

**Common traps**:
- Single-week prints — one-off purchases are just noise.
- Not paying attention to the destination — "unknown" buyers often rescind.
- Confusing Sales with Shipments — the report has both; Sales is the forward indicator.
