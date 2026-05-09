---
type: playbook
category: trading_strategies
applies_to: [analyst_energies, portfolio_manager, risk_manager]
symbols: [RB, HO, NG, QG, EH]
updated: 2026-04-23
---

# Petroleum derivatives & natural gas — trading strategies

Products: [[RB]] gasoline, [[HO]] diesel/ULSD, [[NG]] nat gas, [[QG]] e-mini nat gas, [[EH]] ethanol. Plus refining cracks and calendar spreads.

## 1. Summer RB-CL gasoline crack

**One-liner**: Long RB-CL crack entering late April, targeting summer driving-season demand peak; close by late July.

**Thesis**: US gasoline demand is seasonal (peaks May–Aug). The RBOB gasoline crack (RB − CL, adjusted) expands into driving season as refiners struggle to meet demand and summer-blend specifications tighten supply. The seasonal expansion is well-documented; it's most tradeable when entering at the pre-season range low.

**Trigger** (all required):
- April 15 – May 15 entry window.
- RB-CL crack at or below the lower bound of its 3-year seasonal range for the week.
- EPA summer-blend switchover is imminent (tightens supply).
- No recession-signal headwinds (ISM crash, US jobs miss).

**Invalidation**:
- Major refinery comes online unexpectedly.
- Recession data surprises bearishly.
- Gasoline inventory builds materially in week-after-entry EIA.

**Structure**:
- Paired long RB / short CL in crack-ratio (42 gallons per bbl), expressed as 1 RB : 1 CL with crack computed as (RB × 42) − CL.
- Size: 50 bps of equity on spread P&L.

**Exit rules**:
- Target: crack return to 3-year seasonal-high for the week.
- Stop: crack breaks below pre-entry low.
- Time stop: July 31 (seasonal window closes).

**Calibration**:
- Expected hit rate: 65%.
- Expected average R: +1.3.
- Historical: reliable 2015–23 with exception of 2020 (COVID demand collapse).

**Common traps**:
- Legging in — get both within 5 minutes.
- Holding past Labor Day — demand reverses.
- Ignoring hurricane forecasts — Gulf refinery concentration means storm disruption can spike crack beyond model range.

---

## 2. Winter HO-CL diesel crack

**One-liner**: Long HO-CL crack entering October, structurally tightening into heating season; close by late February.

**Thesis**: US distillate (diesel/heating oil, same contract HO) demand is winter-seasonal. Inventories typically decline Nov–Feb. When the setup adds structural tightness (inventories already below 5-year range entering autumn) + refinery turnaround season (fall maintenance), the crack expansion is durable over 2–4 months.

**Trigger** (all required):
- Oct 1 – Nov 15 entry window.
- US distillate inventory < 5-year range for the week.
- HO-CL crack below 3-year seasonal median.
- Refinery turnaround schedule confirmed (from EIA refinery-utilization data).
- Cross-Atlantic ULSD vs European gasoil premium favors US exports.

**Invalidation**:
- Distillate inventory build > 5M for 2 consecutive weeks.
- Mild winter forecast (long-range NOAA).
- European gasoil collapse (removes export pull).

**Structure**:
- Paired: 1 HO long : 1 CL short (crack adjusted).
- Size: 50 bps of equity on spread.

**Exit rules**:
- Target: crack return to 3-year seasonal high.
- Scale out 1/3 at +1.5R, 1/3 at +2.5R.
- Stop: distillate builds 2 weeks in a row.
- Time stop: Feb 28.

**Calibration**:
- Expected hit rate: 65%.
- Expected average R: +1.5.
- Historical: reliable in tight-stock years (2022–23 produced +3R over 3 months); failed 2020 (demand destruction).

**Common traps**:
- Entering too early (Sept) — seasonal pattern doesn't hold yet.
- Ignoring refinery utilization — high util can offset tightness.
- Holding into March — stock season flips as heating demand drops.

---

## 3. 3-2-1 refining margin

**One-liner**: When the 3-2-1 crack (3 CL − 2 RB − 1 HO) diverges > 1.5σ from seasonal norm with corroborating refinery signal, position the crack directionally.

**Thesis**: The 3-2-1 crack is the synthetic refinery margin — three barrels of crude input produce two gasoline + one distillate output. It's the fundamental refining economics. When it extends above seasonal norms, refiners have incentive to run hard; when below, turnarounds and run cuts start. The crack mean-reverts to a band driven by structural refining capacity and product demand.

**Trigger**:
- 3-2-1 crack > 1.5σ from 60-day rolling mean.
- Corroborating data: refinery utilization report confirms the direction.
- No major structural event (PADD-3 outage, export-ban news).

**Invalidation**:
- Structural event disrupts refining capacity.
- Crack extends past 2.5σ — treat as new regime.

**Structure**:
- Refining-margin spread: long 3 CL + short 2 RB + short 1 HO (or reverse). Position sized in CL-equivalent.
- Size: 50 bps of equity on spread P&L.

**Exit rules**:
- Target: return to seasonal mean.
- Stop: break beyond 2.5σ.
- Time stop: 20 sessions.

**Calibration**:
- Expected hit rate: 60%.
- Expected average R: +0.9.
- Historical: reliable signal; fails during major refinery-outage events that structurally repricing the margin.

**Common traps**:
- Ignoring RBOB or HO specific drivers — one leg can drive the spread independently.
- Legging in — the three legs must be opened within minutes.
- Holding through a hurricane — Gulf refinery risk reprices everything.

---

## 4. NG storage-surprise positioning

**One-liner**: On EIA Weekly Natural Gas Storage surprise > 15 BCF from consensus, trade the continuation for 2–3 sessions.

**Thesis**: EIA's Weekly NG Storage Report (Thursdays 10:30 ET) is the NG equivalent of the petroleum status report. Surprises > 15 BCF drive multi-session moves. Unlike crude, NG is more weather-driven, so the surprise signal is most clean when weather forecasts are neutral.

**Trigger**:
- EIA storage surprise > 15 BCF vs consensus.
- 30 min post-release confirmation of direction.
- Weather forecasts for next 15 days are neutral-to-aligned with the storage signal.

**Invalidation**:
- Forecast shift (heat wave or cold snap) overrides the storage signal.
- Next-week consensus has already repriced.

**Structure**:
- Outright NG or smaller QG (e-mini).
- Size: 25 bps of equity (NG is highly volatile — half the normal cap).
- Stop: 1.5× 5-min ATR.
- Target: 2R.

**Exit rules**:
- Half off at 2R, trail remainder.
- Full exit by end of session + 2.
- Time stop: 3 sessions.

**Calibration**:
- Expected hit rate: 55%.
- Expected average R: +1.0.
- Historical: works best in shoulder seasons (spring/fall) when weather isn't dominating.

**Common traps**:
- Full sizing on NG — it's half-sized because NG volatility is extreme (weekly moves of 20%+ historical).
- Ignoring weather — a forecast change in the next 48h can override fundamentals.
- Fading storage after first session — the move extends before it doesn't.

---

## 5. Heating-season NG long via options

**One-liner**: Long NG via call-spread in October, structured for a heating-demand-driven rally into January, defined risk.

**Thesis**: Natural gas exhibits strong winter seasonality. Residential + commercial heating demand peaks Nov–Feb. When entering with storage already tight relative to 5-year and weather forecasts supportive (cool bias for Nov–Dec), the rally can deliver 20–40% over 3 months. Due to NG volatility and tail risk, defined-risk options are the preferred structure.

**Trigger**:
- October entry window.
- Storage < 5-year average going into November.
- NOAA long-range forecast shows cool or normal winter bias for US population centers.
- NG front-month has not yet broken above the 3-year seasonal high for the week.

**Invalidation**:
- NOAA revises to warm-winter bias.
- Storage build accelerates beyond 5-year range.

**Structure**:
- NG or QG call spread, DTE 60–90.
- Strikes: ATM to OTM 20%.
- Size: 50 bps of equity max-loss.

**Exit rules**:
- Target: +2R or first week of January (whichever comes first).
- Stop: forecast warms dramatically OR storage swings to 5-year-high.
- Time stop: Feb 1.

**Calibration**:
- Expected hit rate: 55%.
- Expected average R: +1.4.
- Historical: 2022 winter (+3R pre-Europe-crisis exit), 2018 bomb-cyclone (+4R).

**Common traps**:
- Entering too late (Nov) — strength is often priced by then.
- Outright long NG — tail risk is unbounded without defined-risk wrapping.
- Holding past Feb — heating demand plateaus.

---

## 6. RB summer-blend switchover

**One-liner**: Long RB in late March–early April, targeting the EPA summer-blend transition supply-tightening event, exit by Memorial Day.

**Thesis**: The EPA's summer-blend gasoline (lower Reid Vapor Pressure) switchover starts early May and completes by late May. Refiners must transition inventory of summer-spec product; winter-blend inventory can't be sold after the changeover. This creates a 4–6 week window of tightening supply as pipelines and terminals rebuild summer-spec stock. RB typically rallies 10–20% in this window.

**Trigger**:
- Late March: RB front-month below the 60-day high.
- US gasoline inventory trending lower.
- No major refinery outage pre-switchover (which would complicate the pattern).

**Invalidation**:
- Major demand shock headline (recession, pandemic-adjacent).
- Early inventory build signaling oversupply.

**Structure**:
- Long RB or long RB call spread (defined risk preferred, DTE 45–60).
- Size: 50 bps of equity max-loss.

**Exit rules**:
- Target: Memorial Day approach OR +2R.
- Stop: RB breaks below March low.
- Time stop: May 31.

**Calibration**:
- Expected hit rate: 60%.
- Expected average R: +1.3.
- Historical: reliable pattern; muted in 2020 (COVID demand collapse).

**Common traps**:
- Over-sizing into Memorial Day — seasonal strength often peaks pre-holiday.
- Ignoring gasoline inventory data — a build week can reverse the move.
- Holding past Memorial Day — supply loosens post-peak demand anticipation.

---

## 7. Diesel cross-Atlantic arb

**One-liner**: When European gasoil trades at a > $8/bbl premium to US ULSD (HO), long HO as arb pulls US exports higher.

**Thesis**: The global diesel market is integrated via shipping. When European gasoil (ICE) commands a large premium over US ULSD (HO), arbitrage flows drive US exports of distillate to Europe, tightening US supply and supporting HO. The relationship is measurable via published prices; the arb typically closes within 10–20 sessions.

**Trigger**:
- European gasoil front-month − US HO front-month > $8/bbl ($0.19/gal).
- Export data confirms increased US distillate shipments to Europe.
- No concurrent US demand collapse that would swamp the arb signal.

**Invalidation**:
- Spread collapses rapidly back below $4/bbl.
- European refinery returns from outage (removes the tightness driver).

**Structure**:
- Long HO outright or HO-CL crack (captures both the arb and the margin thesis).
- Size: 50 bps of equity.

**Exit rules**:
- Target: spread compresses to < $4/bbl.
- Stop: spread widens > $15/bbl (arb isn't working; treat as new regime).
- Time stop: 20 sessions.

**Calibration**:
- Expected hit rate: 60%.
- Expected average R: +1.2.
- Historical: worked during 2022 Russia-Ukraine energy dislocation (+4R). Works in most years with European refinery tightness.

**Common traps**:
- Ignoring freight economics — if shipping is tight/expensive, arb doesn't close as fast.
- Not tracking European inventory — the root cause matters.
- Confusing gasoil (ICE) with HO (NYMEX) specs — they're slightly different grades.
