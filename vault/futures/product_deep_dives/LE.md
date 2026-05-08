---
type: product_deep_dive
symbol: LE
sector: livestock
analyst: Fund Engineer
updated: 2026-04-25T23:55:00Z
---

# [[LE]] — CME Live Cattle Futures

## Contract specs

- **Exchange / product code**: CME (Chicago Mercantile Exchange) / LE; unit = 40,000 pounds (~18.1 metric tonnes) of live cattle
- **Tick size / tick value**: 0.025 cents per pound; $10 per contract ($0.00025 × 40,000 lbs)
- **Contract months**: Feb, Apr, Jun, Aug, Oct, Dec; June and August are the largest / most liquid; near-contract rolls every ~2 months
- **Session hours**: RTH 09:05–13:00 CT (CME pit); Globex: 17:00 CT Sunday–17:00 CT Friday (nearly 24-hour, 15-min gap)
- **First notice / last trading day**: 12th business day of contract month (e.g., Jun LE expires mid-June); cash settlement based on USDA invoice price of choice-grade steers delivered
- **Settlement**: Cash settlement (no physical delivery of live cattle); weekly invoice prices from USDA drive final settlement
- **Margin** (Topstep): ~$1.8K initial, ~$1.2K maintenance (varies with IV; confirm live)

## What it actually is

CME Live Cattle futures are the primary US price-discovery mechanism for fed-cattle (finished steers and heifers ready for slaughter). One contract = 40,000 lbs of live cattle, typically representing ~19–20 head of finished beef cattle (~2,000 lbs per animal live weight). LE is used by cattle feeders (who buy feeder cattle and feed them grain for 4–6 months), packers/processors (who buy cattle at slaughter weight), ranchers (who sell calves), and speculators (who trade cattle-cycle dynamics). Unlike crops (corn, soybeans) which are commodities in global trade, live cattle are domestic (US production) and reflect the health of the US beef supply chain: feed economics (corn prices), disease (bovine respiratory disease, feed-lot mortality), weather (heat stress), packer capacity (processing), and consumer demand (beef prices, economy). Feeder cattle (GF) flows into LE; LE flows into carcass weight (no liquid contract). Live Cattle is the **primary expression of US beef profitability**.

## Primary drivers

Ranked by impact in 2024–2026 regime:

1. **Corn prices ([[ZC]]) and feedlot profitability (feed-to-gain ratio)**: Finished cattle diets are ~70–75% grain (corn, sorghum, barley) and ~25% hay/forage. A 40,000 lb LE contract consumes ~15,000–20,000 lbs of corn equivalent during the 4–6 month feeding period. High corn prices (e.g., $450+/bu) crush feeder-to-finished margins; low corn prices ($350/bu) expand margins. The **feeder-to-finished spread** (GF → LE price; should be positive) is a critical indicator. When LE rallies but ZC rallies faster, feeders lose money; when ZC craters, feeders lock in huge margins → LE should rally. **Current regime (2024–2026)**: corn ~$380–420/bu, allowing modest margins; expect seasonal pressure in fall harvest (Sep–Oct) when new-crop corn floods market.

2. **Feeder cattle (GF) supply and demand (placement, feedlot capacity)**: Feedlots buy feeder cattle (400–800 lb calves) from ranches and feed them to 1,200–1,300 lbs for slaughter. Spring and fall are classic placement windows. Heavy placements (more calves entering feedlots) = more future LE supply in 90–120 days. USDA Cattle on Feed (monthly, 3rd Friday of each month) reports monthly placements, on-feed inventories, and marketings. Surprises >5% vs. consensus drive 1–2 cent moves. Tight feedlot capacity (>95% utilization) can restrict placements and tighten LE supply; excess capacity (80–90% utilization) allows feeders to be selective and pressure LE as supply builds.

3. **Live cattle supply from slaughter (USDA slaughter data, packer run)**: Total US beef cattle slaughter has been ~34–36 billion lbs/year (USDA). Weekly slaughter reports track kill-rate; if packers operate >95% capacity (tight packer schedule), LE supply is constrained. If <85% (excess capacity), packers slow runs, allowing cattle to age in feedlots (heavier weights = more pounds into LE). Packer bankruptcy (rare but happened 2018) or geopolitical illness (avian flu spillover into cattle, highly unlikely but tail-risk) could shock LE. **Key: slaughter data lags feeder placements by 120–150 days.** A surge in spring placements (Apr–May) → heavy slaughter Sep–Nov → LE should be pressured by October.

4. **Beef demand signals (US consumer, exports, food inflation)**: Beef prices to consumers are tracked via USDA Retail Beef prices. Recessions or high inflation reduce beef demand (consumers substitute toward cheaper protein). Exports (typically 10–15% of US production) to Japan, South Korea, Mexico, and Canada are sensitive to trade policy and FX (strong dollar = cheaper US beef abroad = bullish). Winter holidays (Nov–Dec) boost retail beef demand. Summer grilling season (Jun–Jul) typically supports demand. **COVID-era phenomenon (2020–2021)**: packer bottlenecks, low cattle slaughter → LE rallied 50%+ despite economic lockdown.

5. **Macro economy, real rates, and risk appetite**: Recessions = lower meat demand = lower LE. Energy prices (especially cold-storage electricity costs) and labor (processing wages) feed into packer margin and pricing power. Fed tightening (higher real rates) = tighter financial conditions → reduced cattle placements (feeders need financing). Periods of strong risk appetite = stronger commodity demand → LE correlates mildly with equities. **Inverse relationship to DXY**: stronger dollar = cheaper US beef exports = net positive for LE; but correlation is weak (−0.15 to −0.25).

## Key correlations

**Positively correlated:**
- [[ZC]] (Corn): 0.45–0.65 correlation (moderate-to-strong). High corn prices crush margins → LE drops. Low corn prices expand margins → LE rallies. Lag: corn moves first; LE follows 2–4 weeks as feeders adjust placements. Direct mechanical link: feeders won't buy calves if margins are negative.
- [[GF]] (Feeder Cattle): 0.70–0.85 correlation (strong). GF is 3-month leading indicator of LE. When GF rallies, it signals incoming LE supply cost is rising → LE should rally ahead of supply arrival (100+ days out). Fall placement surge (Sep) → GF spikes → LE rallies anticipating heavier supply in Dec–Jan.
- [[HE]] (Lean Hogs): 0.25–0.45 correlation (weak-to-moderate). Both are livestock; both sensitive to feed costs (ZC, ZS) and macro demand. Hogs have shorter cycle (4–5 months vs. cattle 6+ months), so HE leads LE by 30–60 days. If HE rallies, it signals demand/margins are healthy → LE should follow.
- **USDA Cattle on Feed (monthly placement data)**: Correlated with LE pricing 90–120 days forward. Heavy placements (>2% above trend) → future LE supply surge → near-term LE bearish, 4-month LE bullish.

**Negatively correlated:**
- [[ZS]] (Soybeans) — weak negative (−0.1 to −0.2). Soybeans don't directly feed cattle, but high soy prices signal broader crop/feed inflation → all livestock costs rise → aggregate livestock demand falls → LE weakness. Not a strong trade signal alone.
- **US 2Y real rates (DGS2 − inflation breakeven)**: −0.25 to −0.4 (weak-to-moderate). Higher real rates = tighter credit → feeders reduce placements → future LE supply contracts. But effect is lagged (2–3 months) and weak because livestock cycles are biological, not rate-driven.
- **Equity indices during sharp recessions**: −0.2 to −0.35. Recessions = lower protein demand → LE crashes. But in bull markets, correlation is near-zero.

**Lead/lag:**
- Feeder Cattle (GF) leads LE by ~90–120 days (biological lag: calves must grow).
- Corn (ZC) moves first; LE follows by 2–4 weeks as feeders adjust supply expectations.
- USDA Cattle on Feed (3rd Friday each month) → immediate 1–2 cent reaction if >3% surprise; 90-day forward effect.
- Weather (heat stress in summer) → immediate LE pressure (heat kills gains; cattle lighter at slaughter) within 1–2 weeks.

## Recurring patterns

**Seasonal:**
- **Spring placement surge (Mar–May)**: Grass pasture comes online; ranchers sell calves; feeders buy. GF rallies; LE rallies on expectations of future supply. Typically Mar–Apr LE is 2–4 cents premium to Jun/Aug (deferred supply). This premium compresses as May/Jun approach (supply reality).
- **Summer slow period (Jun–Jul)**: Fewer new placements; cattle in feedlots maturing. Slaughter stable. LE often drifts sideways or grinds lower on slow-moving supply. Heat stress (July) can sharp-correct LE lower (cattle lose weight in heat).
- **Fall placement and harvest (Aug–Sep)**: Second-largest placement window (harvest season, pre-winter). GF rallies. LE initially rallies on healthy margins (good-quality feeders available), then sells off Sep–Oct as new-crop cattle flow into slaughter and supply becomes visible. **Sep–Oct is historically the weakest season for LE** (supply peak, demand soft).
- **Winter steady (Nov–Mar)**: Slaughter remains steady; Christmas/New Year demand provides brief support. Cattle on feed peak (after all fall placements); slow drawdown through winter. Price typically in contango (deferred months trade higher due to carry). Extreme cold/blizzards can briefly shock feedlots (mortality, feed cost), but events are rare.

**Event-driven:**
- **USDA Cattle on Feed (3rd Friday of each month)**: Placements, on-feed inventory, marketings. >2% surprise drives 1–3 cent moves. Tight inventory → bullish. Heavy placements → bearish 4-month forward (supply incoming).
- **USDA slaughter data (weekly)**: Less volatile than Cattle on Feed; mostly confirms existing trends. Sharp >10% drop (packer outage) can spike LE.
- **USDA Crop Progress on Corn (weekly May–Sep)**: Poor crop = high future feed costs → bearish LE margins near-term. Good crop = cheap future feed → bullish.
- **Weather events (heat waves, blizzards)**: Summer heat (Jun–Jul) kills cattle gains → immediate sharp LE sell-off (losses exceed gain). Blizzards (Jan–Feb) rarely halt production; mostly noise.
- **Disease outbreaks (bovine respiratory disease, pneumonia in feedlots)**: Seasonal (fall/winter when cattle are crowded indoors); higher mortality reduces supply → bullish for LE 30–60 days out. Very rare extreme events (brucellosis in wild herds, tuberculosis) could shock prices, but US herds are well-managed; tail-risk.

**Time-of-day patterns:**
- **Asia close (5:30am CT)**: Minimal direct impact; overnight volumes low.
- **9:05–11:00 CT (pit open + first hour)**: Moderate volume; good fills. Often reverses overnight action. USDA Cattle on Feed usually drops at ~13:00 CT on the 3rd Friday (limit-up/down scenarios rare).
- **11:00–13:00 CT (pit approach to close)**: Lower volume; technical plays. Bid-ask widens near close.
- **Post-pit close (13:00–17:00 CT)**: Globex only; wider spreads; lower volume.
- **Overnight Globex**: Very thin; avoid unless size is tiny.

**Calendar quirks:**
- **Roll window (7–10 days before FND)**: Volume/liquidity shifts to next contract. Spreads widen. Typical contango (Jun > Apr, Aug > Jun) reflects carry costs and supply build. Backwardation (rare, only if supply crunch) = get paid to roll.
- **Front-month contract expiration (cash-settlement; no physical delivery)**: Settlement is the USDA Choice Steer price for the contract month. Most traders roll 10–14 days before FND to avoid settlement basis risk.

## Common setups

1. **Feeder-to-finished margin compression + trend fade**
   - *Trigger*: GF rallies 5+ cents while LE stays flat → feeder-to-finished margin (GF → LE in 120 days) narrows dramatically; feeders profitability deteriorates. Trend-following specs are long GF; LE weakness breaks their thesis.
   - *Entry*: Short LE (or long ZC to hedge feeder long) if GF premium to LE has narrowed to <4 cents. Trigger is GF outperforming LE over 5-day window.
   - *Stop*: Above recent LE high (3–5 cents typical).
   - *Target*: Recent LE support or 20-day MA; exit on close above stop or if margin widens again (bearish signal reverses).
   - *Invalidation*: ZC crashes (margins expand) or GF breaks sharply lower (feeder demand signaling weakness) → margin compression feared = short LE stopped.
   - *Hit rate*: ~50–55% (mechanical margin trades can fail if both move together; timing is critical).

2. **Cattle on Feed placement surprise + 120-day forward fade**
   - *Trigger*: USDA Cattle on Feed shows heavy placements (>3% above trend); market briefly rallies (bullish for future supply), then sells off as specs realize supply incoming in 4 months will pressure prices.
   - *Entry*: Long LE on initial rally surprise (first 30 min), then reverse short on day 2 as the 120-day implication sinks in.
   - *Stop*: Below gap; typically 2–4 cents.
   - *Target*: Retest recent prior support or 10-day MA; exit on close below entry + 0.5 cents (tight discipline).
   - *Invalidation*: Corn rallies sharply (margin recovery hope) → feeder demand rebounds → short is stopped.
   - *Hit rate*: ~48–52% (complex; lags are unpredictable; many fades fail).

3. **Heat stress summer sell-off + bounce**
   - *Trigger*: Extended forecast (6–10 day outlook) shows sustained heat >95°F during Jun–Jul (peak growth/finish period); LE rallies on concern cattle will be lighter → slaughter weight pressure. But heat typically peaks for 3–5 days; cattle recover post-event.
   - *Entry*: Sell (short) LE if price spikes on heat forecast and holds near highs going into weekend.
   - *Stop*: Above the intraday high of the spike; typically 3–5 cents.
   - *Target*: Prior support (5-day MA); exit on daily close below MA or break of entry.
   - *Invalidation*: Forecast updates to even worse heat → short is stopped. Or: LE is already weak and heat sell-off is structural (not fade); tight stops are essential.
   - *Hit rate*: ~45–52% (heat spikes create sharp moves but reversals are quick; setup rewards quick fingers, penalizes holders).

4. **Fall Cattle on Feed surge + Sep–Oct seasonal weakness**
   - *Trigger*: Aug–Sep Cattle on Feed shows record/near-record placements (fat feedlots buying calves before winter); market prices this as future supply surge.
   - *Entry*: Short LE in late Aug or early Sep on the placement confirmation, anticipating Oct weakness.
   - *Stop*: Above 20-day MA (or ~2–3 cents above entry typical).
   - *Target*: Sep–Oct seasonal lows (typically 3–8 cents lower than Aug high). Exit on bounce back through 10-day MA.
   - *Invalidation*: ZC crashes (margin recovery hope) or Cattle on Feed next month shows heavy marketings (supply being culled faster than expected) → short is stopped.
   - *Hit rate*: ~55–62% (seasonal is strong; structural supply surge is real; setup has high alpha if disciplined).

## Classic traps

- **Margin-compression false signal**: Feeder-to-finished spread narrows but ZC rallies simultaneously; feeders actually have good margins and keep buying. Short LE on margin compression fails; corners stop.

- **Cattle on Feed hype reversal**: Heavy placements release; market rallies on surprise (animals already committed to feedlots). Next day, specs realize this was already known → 120-day forward supply is now certain → sharp LE sell-off. Longs caught wrong-footed. Conversely, light placements → bearish surprise, but specs who were already short cover too fast → whipsaw.

- **Heat forecast fade over-hold**: Weather model predicts 5-day heat wave. LE spikes. Forecast updates; heat is moderate. LE fades sharply. But traders holding shorts expecting a bigger fade get run over if the heat actually arrives and cattle die. Weather is hard to predict; fades are risky.

- **Crush margin mirage (cattle version)**: Beef prices rally (retail demand surge). Spec expects LE to soar. But feeders already locked in cattle prices via forward contracts with packers. Retail beef price ≠ wholesale LE price with a 1-week lag. Retail up doesn't always flow through to LE. Bearish surprise kills longs.

- **Cheap leverage + stop-running**: LE is ~$10 per tick; a 20-contract position is ~$200K notional with 10x leverage. Round-number stops (75, 80, 90 cents/lb) get hunted. Tight stops (1–2 cents) are vulnerable to volatility spikes.

- **Ignore ZC and GF**: Traders focus on LE in isolation, missing the lead-lag with corn and feeder cattle. ZC rallies 10 cents; LE should weaken in 2–4 weeks. If LE is strong while ZC rallies, it's a contrarian signal (demand is very strong, margins can absorb cost). Ignoring these links = blind trades.

## Liquidity profile

- **Average daily volume** (front month): 80k–200k contracts in normal regime; peak >300k during major USDA Cattle on Feed or on placement-shock days. Jun/Aug contracts are most liquid; Apr/Oct lighter.
- **Open interest trend**: ~150k–250k for Jun/Aug; lighter for deferred. Total market is smaller than corn (ZC) or soybeans (ZS); retail spec participation lower.
- **Pre-open / post-close behavior**: Globex opens 17:00 CT Sunday with reasonable volume; spreads 2–4 cents. 9:05 CT pit open tightens to 1–2 cent spreads. Post-pit close, Globex widens to 3–5 cents.
- **Best session for fills**: 9:15–12:30 CT (pit hours). Avoid 13:00–17:00 CT and overnight unless size is small.
- **Bid-ask spread**: 1–2 cents normal during pit hours; 2–4 cents shoulder hours; 4–6 cents overnight Globex.

## Options (if applicable)

- **Weekly expirations**: Mondays (expire Friday end of prior week). Popular for short-dated directional plays (margin trades, heat events, Cattle on Feed day).
- **Monthly expirations**: 3rd Friday of month. Lower volume than weeklies.
- **Settlement**: 9:30am CT Fridays (weeklies); 9:30am CT on listed expiration date (monthlies).
- **Typical IV rank range**: Placement season (Mar–May, Aug–Sep): 50–75th percentile. Summer/winter: 30–55th percentile. IV spikes on USDA Cattle on Feed or heat events.
- **Pin-risk behavior**: Monthly options near expiry can pin if strike is near ATM. Avoid short gamma in the week of Cattle on Feed if short calls/puts near money.

## Risk notes

- **Gap risk profile**: Largest gaps occur on USDA Cattle on Feed (3rd Friday) and USDA slaughter shocks. Typical gap: 1–3 cents; extreme (>5 cents) on placement surprises. Overnight Globex gaps to pit open average 0.5–2 cents. Disease outbreaks or packer closures are tail-risk; gaps could exceed 5 cents but are very rare.

- **Limit-up / limit-down mechanics**: CME allows LE to move 3 cents/day limit-up or limit-down (from prior settlement). Rarely hit in modern era (last limit-move: 2008 financial crisis, rare disease events). If limit is hit, trading halts; no way to exit except next day.

- **Worst weekly move in last 5 years**: May 2021 (post-COVID packer recovery, tight supply): LE rallied from 115 → 128 cents (+11%) in 4 weeks. Mar 2020 (COVID lockdown, packer fear): LE crashed from 115 → 85 cents (−26%) in 2 weeks. Fall 2023 (feed-cost pressure, soy rally): LE drifted lower (no shocking weekly move; trend down ~4 cents over month).

- **Tail-risk events to remember**:
  - **2008 financial crisis**: LE crashed 50%+ as demand collapsed; feeders bankrupted; packer consolidation.
  - **COVID-2020**: Packer closures (infection outbreaks) → severe supply bottleneck → LE rallied +50% in weeks despite recession (unique structural shock).
  - **2014–2015 drought**: Severe Midwest drought → herd liquidation (ranchers sold cattle early) → oversupply → LE crashed 25–30% over months.
  - **Periodic heat stress (2012, 2021)**: Sustained heat in Jul–Aug → cattle light at slaughter → LE weakness for 2–3 weeks but recovers post-event.

## References

- **CME LE contract specs**: https://www.cmegroup.com/markets/agriculture/livestock/live-cattle.contractSpecs.html
- **USDA Cattle on Feed report**: Issued 3rd Friday monthly; https://usda.gov/nass (monthly placements, on-feed, marketings)
- **USDA slaughter data**: Weekly cold-storage report; https://usda.gov/nass
- **USDA Retail Beef prices**: Tracked weekly; consumer demand indicator
- **Feeder cattle (GF) deep-dive**: See `vault/futures/product_deep_dives/GF.md` (linked: GF leads LE 120 days)
- **Corn (ZC) deep-dive**: See `vault/futures/product_deep_dives/ZC.md` (primary cost driver)
- **Lean Hogs (HE) deep-dive**: See `vault/futures/product_deep_dives/HE.md` (parallel livestock, shorter cycle)
- **Key calendar dates**: Cattle on Feed (3rd Fri each month), Crop Progress (Thu May–Sep), WASDE (monthly ~10th), LE contract expirations (mid-month, cash-settled).
