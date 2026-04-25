---
type: playbook
category: trading_strategies
applies_to: [analyst_softs, portfolio_manager, risk_manager]
symbols: [KC, CT, SB, CC, OJ, LBR]
updated: 2026-04-23
---

# Softs — trading strategies

Products: [[KC]] coffee, [[CT]] cotton, [[SB]] sugar, [[CC]] cocoa, [[OJ]] orange juice, [[LBR]] lumber.

**Sector note**: softs are thinner than grains and metals. Position size 50% of normal per-trade cap. Every strategy here assumes that reduction.

## 1. Weather-driven supply shock (coffee, cocoa, OJ)

**One-liner**: On confirmed drought, frost, or hurricane hit to a major producer, long front-month via defined-risk option structure for 2–4 weeks.

**Thesis**: Producer concentration in softs (Brazil for coffee/sugar, West Africa for cocoa, Florida for OJ) means single-source weather events produce large supply shocks. Because softs markets are thin, the price response is sharp and often sustained for weeks as the market absorbs revised production estimates.

**Trigger**:
- Confirmed weather event (news wire with official meteorological confirmation) in a primary producer.
- Front-month spike of 3%+ day 1.
- Producer country's crop agency (CONAB, ICCO, USDA) confirms or increases damage estimate within 3–5 days.

**Invalidation**:
- Weather event was localized and damage reports come in minor.
- Secondary producer region compensates (e.g., Vietnam stepping up when Brazilian coffee hits).

**Structure**:
- Long call spread, DTE 30–45, defined risk.
- Size: 25 bps of equity max-loss (half normal due to softs liquidity).

**Exit rules**:
- Target: +2R or 15 sessions.
- Stop: weather reverses / damage reports revised lower.
- Time stop: 30 sessions.

**Calibration**:
- Expected hit rate: 55%.
- Expected average R: +1.3.
- Historical: 2021 Brazilian coffee frost (+4R), 2020 Ivory Coast dry spell (+2R), 2022 Florida OJ hurricane (+3R).

**Common traps**:
- Entering on day-1 spike — the volatility-premium is elevated. Wait for day-2 close.
- Ignoring substitute production — other regions often absorb shocks.
- Over-sizing on illiquid contracts (OJ, cocoa).

---

## 2. Ethanol-sugar pivot

**One-liner**: When crude oil rallies > 10% and BRL weakens, long sugar as Brazilian mills divert cane to ethanol instead of export.

**Thesis**: In Brazil, sugarcane is diverted between sugar production and ethanol production based on relative economics. When crude is strong (ethanol valuable) and BRL is weak (USD-denominated sugar uncompetitive for export), mills shift toward ethanol. Sugar supply tightens, prices rise. The pivot takes 4–8 weeks to show in prices.

**Trigger**:
- Crude rallies > 10% month-over-month.
- BRL weakens > 5% month-over-month.
- Brazilian sugar crush data shows mill-mix shifting toward ethanol.

**Invalidation**:
- Crude reverses materially.
- BRL rallies strongly.
- Thai or Indian sugar output surges (substitute supply).

**Structure**:
- Long SB outright or call spread, DTE 60–90.
- Size: 25 bps of equity.

**Exit rules**:
- Target: +2R or 8 weeks.
- Stop: crude reverses or BRL rallies strong.
- Time stop: 90 sessions.

**Calibration**:
- Expected hit rate: 55%.
- Expected average R: +1.4.
- Historical: played out reliably 2016, 2021, 2022 — coincident crude rally + BRL weakness setups.

**Common traps**:
- Ignoring Indian / Thai data — secondary producers can supply-side offset.
- Timing — this is a 4–8 week trade, not a quick one.
- Entering late — after the pivot is known, it's priced.

---

## 3. Cotton Chinese-demand pulse

**One-liner**: When Chinese cotton import data surges consecutively, long CT with 4–6 week horizon.

**Thesis**: China is the world's largest cotton importer and a swing buyer. When Chinese imports surge (typically tied to state-reserve-building or yuan-adjusted mill economics), US cotton inventory draws faster than the market initially prices. The signal is measurable via USDA Weekly Export Sales to China.

**Trigger**:
- Two consecutive Weekly Export Sales prints to China > 150% of trailing-4-week average.
- Chinese reserve-release announcement NOT imminent (would offset demand).
- CT front-month hasn't broken to new 60-day high.

**Invalidation**:
- Chinese government announces reserve release.
- Yuan weakens dramatically (reduces import economics).

**Structure**:
- Long CT front-month or call spread, DTE 45–60.
- Size: 25 bps of equity.

**Exit rules**:
- Target: +2R or 6 weeks.
- Stop: weekly export pace reverts to normal.
- Time stop: 8 weeks.

**Calibration**:
- Expected hit rate: 55%.
- Expected average R: +1.2.

**Common traps**:
- Fading the first Chinese buy — single-week pulses are noise.
- Ignoring currency — yuan moves can override demand signal.
- Over-sizing — cotton liquidity is adequate but not deep.

---

## 4. Cocoa Ivory-Coast concentration trade

**One-liner**: On political/economic risk headlines from Ivory Coast (70%+ of global cocoa), long CC for 3–6 week window via defined-risk structure.

**Thesis**: Ivory Coast + Ghana produce > 70% of global cocoa. Political instability, fiscal crisis, or price-fixing disputes produce immediate supply-concern rallies. The concentration risk is structural; the market is slow to price these events because information flow from West Africa is imperfect.

**Trigger**:
- Credible news of political or fiscal instability in Ivory Coast or Ghana.
- Cocoa front-month spikes 2%+ on the news.
- No imminent harvest window (harvest supply would offset).

**Invalidation**:
- Situation resolves quickly.
- Harvest data confirms normal supply.

**Structure**:
- Long CC call spread, DTE 30–45.
- Size: 25 bps of equity max-loss.

**Exit rules**:
- Target: +2R or 3 weeks.
- Stop: situation resolves, price retraces.
- Time stop: 6 weeks.

**Calibration**:
- Expected hit rate: 55%.
- Expected average R: +1.3.
- Historical: 2023–24 Ivory Coast production crisis produced a multi-month rally (+5R for early entries).

**Common traps**:
- Chasing after day-1 — entry on day-2 close avoids the vol-premium spike.
- Over-sizing in thin CC liquidity.
- Ignoring harvest timing — Oct–Mar main harvest can overwhelm political supply concerns.

---

## 5. Lumber-housing cycle

**One-liner**: When US housing permits turn up for 2 consecutive months and existing home sales stabilize, long LBR into spring building season.

**Thesis**: Lumber demand is driven by US residential construction. Housing permits lead construction starts by ~2 months. When permits inflect up + existing home sales stabilize (signaling buyer confidence), lumber rallies into the Mar–May spring building season. The move is volatile but directionally reliable.

**Trigger**:
- US housing permits up MoM for 2 consecutive months.
- Existing home sales flat-to-up MoM.
- LBR front-month below 60-day high.
- Entry window: Dec 15 – Feb 15.

**Invalidation**:
- Permits reverse.
- Mortgage rates spike.
- LBR builds inventory ahead of building season.

**Structure**:
- Long LBR outright or call spread, DTE 60–90.
- Size: 25 bps of equity (lumber is notoriously volatile).

**Exit rules**:
- Target: +2R or Memorial Day.
- Stop: permits reverse or mortgage rates break out.
- Time stop: May 31.

**Calibration**:
- Expected hit rate: 50%.
- Expected average R: +1.5 (volatile outcomes; when it works, works big).
- Historical: lumber has extreme boom-bust cycles (2020–21 +200% rally, 2022 −70% drop). Size conservatively.

**Common traps**:
- Sizing normally — lumber is a half-size-or-smaller contract.
- Ignoring mortgage rates — housing is rate-sensitive.
- Holding past May — seasonal pattern expires.
