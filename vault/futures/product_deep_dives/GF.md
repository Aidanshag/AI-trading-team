---
type: product_deep_dive
symbol: GF
sector: livestock
analyst: Fund Engineer
updated: 2026-04-28T00:45:00Z
---

# [[GF]] — CME Feeder Cattle Futures

## Contract specs

- **Exchange / product code**: CME (Chicago Mercantile Exchange) / GF; unit = 100,000 pounds (~45.4 metric tonnes) of feeder cattle
- **Tick size / tick value**: 0.025 cents per pound; $25 per contract ($0.00025 × 100,000 lbs)
- **Contract months**: Jan, Mar, Apr, May, Aug, Sep, Oct, Nov; April and May are the largest / most liquid (spring placement window); August and September also liquid (fall placement). Near-contract rolls every ~4–6 weeks
- **Session hours**: RTH 09:05–13:00 CT (CME pit); Globex: 17:00 CT Sunday–17:00 CT Friday (nearly 24-hour, 15-min gap)
- **First notice / last trading day**: ~20th of contract month (varies); cash settlement based on USDA Feeder Cattle Price Index
- **Settlement**: Cash settlement (no physical delivery); settles to USDA feeder cattle price index (prices for various weights: 450–650 lbs, 650–850 lbs)
- **Margin** (Topstep): ~$2K initial, ~$1.3K maintenance (varies with IV; confirm live)

## What it actually is

CME Feeder Cattle futures are the primary US price-discovery mechanism for **feeder cattle** — calves and young cattle (400–850 lbs) that are ready to enter feedlots for 120–180 days of grain feeding. One contract = 100,000 lbs of feeder cattle, typically representing ~120–150 head of feeder cattle (~700 lbs per animal average live weight). GF is used by **ranchers** (who breed and raise calves, then sell into the feeder market), **feeders** (who buy feeder cattle, feed grain for 4–6 months, then sell to packers as live cattle [[LE]]), and speculators. Unlike live cattle (LE) which reflects the price of finished cattle at slaughter, GF reflects the **input cost** to the feedlot operation. GF is the **leading indicator for LE**: high feeder prices compress feeder-to-finished margins; low feeder prices expand margins. Ranchers' breeding and selling decisions drive GF supply; feeders' demand for cattle depends on corn prices, feedlot capacity, and expected LE prices 120 days forward. **GF is the primary expression of US beef supply management and rancher profitability.**

## Primary drivers

Ranked by impact in 2024–2026 regime:

1. **Corn prices ([[ZC]]) and feeder-to-finished margin expectations**: A feeder bought at 135 cents/lb (GF) and sold 120 days later as finished cattle at 130 cents/lb (LE) with 15,000–20,000 lbs of corn consumed (cost: ~$3,000–4,000) yields a thin or negative margin. Feeders model the **feeder-to-finished spread** (GF purchased − LE expected in 120 days − estimated feed cost). When GF is high relative to expected LE, feeders stop buying → GF crashes. When GF is cheap relative to expected LE, feeders aggressively buy → GF rallies. **Corn is the critical input cost.** High corn (>$450/bu) = high feeding cost → feeders demand cheap feeders (GF falls). Low corn (<$350/bu) = low feeding cost → feeders bid up feeders (GF rallies). The correlation is **inverted and lagged**: ZC rallies first; GF weakness follows 1–2 weeks as feeders reprice margins downward.

2. **Pasture availability and rancher calf supply (weather, seasonal grass)**: Ranchers produce calves (gestation 9 months; calves born Feb–June peak, with seasonal variation by region). Spring grass (late Mar–Apr) signals time to sell calves from winter births; ranchers flush calves onto the market Apr–May. High-quality pasture = more calves; drought = fewer calves available (ranchers hold or breed fewer). Winter blizzards or drought in ranching regions (Nebraska, Oklahoma, Texas) reduce calf availability 4–6 months later. **Current regime (2024–2026)**: Moderate Midwest drought/wet cycles; calf supplies steady; no major supply shocks. Expect seasonal supply surge Apr–May (spring calves) and Sep–Oct (fall calves from summer breeding).

3. **Feedlot capacity utilization and feeder demand**: Feedlots are fixed-capacity facilities (typically 10k–100k head per lot); when full (>95% capacity), feeders stop buying; when empty (<80%), feeders aggressively buy to fill pens. USDA Cattle on Feed (3rd Friday monthly) reports feedlot capacity utilization. Tight feedlots = low feeder demand → GF weakness. Loose feedlots = high feeder demand → GF strength. In 2024–2026, feedlots have been 85–95% full on average (normal). Major liquidations (2014–2015 drought forced ranchers to sell herds; took 5+ years to rebuild) or rapid expansion (rare; requires capital) shift capacity dynamically.

4. **Expected live cattle (LE) prices and feeder profitability signals**: Feeders use **LE futures or forward prices** to estimate their exit price 120 days forward. If LE deferred contracts (e.g., Aug LE when buying Apr GF) rally, feeders anticipate good exit prices → they buy feeders aggressively → GF rallies. If LE deferred falls, feeders reduce bids → GF weakens. This is a **forward-looking correlation**: **GF leads LE by ~120 days**. When GF rallies, it signals feeders expect strong future demand and are willing to lock in input costs; LE should rally 3–4 months later. When GF crashes, it signals margin compression fear; LE should weaken in 4 months.

5. **Macro economy, credit availability, and risk appetite**: Feedlots operate on thin margins (typically 3–8% ROIC); they're capital-intensive operations (land, facilities, labor). Recession or credit tightening = feeders have less capital → fewer placements → lower GF demand → GF crashes. Fed tightening (higher rates) = tighter financial conditions → feeders' cost of capital rises → fewer placements. Conversely, low-rate / easy-credit environments encourage feeders to build inventory → GF strength. **Inverse relationship to real rates**: higher real rates = weaker GF (lagged by 4–8 weeks).

## Key correlations

**Positively correlated:**
- [[LE]] (Live Cattle): 0.70–0.85 correlation (strong). GF leads LE by ~120 days. When GF rallies, LE should rally 3–4 months later (feeders are committing capital, signaling confidence in future LE prices). GF weakness precedes LE weakness. The correlation is strongest when looking at GF now vs. LE in 120 days.
- [[HE]] (Lean Hogs): 0.30–0.50 correlation (weak-to-moderate). Both livestock; both sensitive to feed costs (ZC) and macro demand. Hogs have a shorter cycle (4–5 months), so HE leads GF by ~30 days. If HE rallies, it signals demand is healthy → GF should follow.
- **USDA Cattle on Feed (feeder placements)**: When placements are heavy (>2% above trend), GF rallies on near-term demand. When placements are light, GF weakens on demand concern.

**Negatively correlated:**
- [[ZC]] (Corn): −0.40 to −0.60 correlation (moderate-to-strong, inverse). High corn prices crush feeder margins → feeders stop buying → GF falls. Low corn prices expand margins → feeders aggressively buy → GF rallies. Lag: ZC moves first; GF follows 1–2 weeks as feeders adjust bids. **Mechanical link**: feeders won't buy feeders if they can't earn a positive margin on the LE sale.
- **US 2Y real rates (DGS2 − inflation breakeven)**: −0.25 to −0.40 (weak-to-moderate). Higher real rates = tighter credit → feeders reduce placements → lower GF demand → GF falls. Effect is lagged (4–8 weeks) and indirect; effect is weaker during strong demand periods.
- [[ZS]] (Soybeans) — weak negative (−0.15 to −0.25). Soybeans don't directly feed cattle, but high soy prices signal broader feed/crop inflation → all livestock costs rise → aggregate livestock profitability falls → GF weakness. Not a strong trade signal alone.

**Lead/lag:**
- **GF leads LE by ~120 days** (biological lag: feeders must grow cattle for 4+ months). Traders who are long GF are effectively long LE deferred; GF break-out should precede LE strength by 3–4 months.
- **ZC moves first; GF follows by 1–2 weeks** as feeders reprice margin expectations downward.
- **USDA Cattle on Feed (3rd Friday monthly)** → immediate 1–2 cent GF reaction if feeder placements surprise >3%. Heavy placements → bullish GF (demand is strong), but 4-month forward bearish LE (supply incoming). Light placements → bearish GF (demand weak), but 4-month forward bullish LE (supply will be tight).
- **Spring grass emergence (late Mar–early Apr)** → calves become available; ranchers sell; GF supply surge; GF may dip before rallying on feeder demand.

## Recurring patterns

**Seasonal:**
- **Spring placement and calf flush (Mar–May)**: Winter-born calves mature (6–8 months old); grass pasture comes online; ranchers sell. GF supply surges; prices typically soften Mar–Apr as supply hits market. By mid-May, demand from feeders (who want to fill pens before summer heat) absorbs supply; GF often rallies May–Jun. Early-spring GF (Jan/Mar contracts) often trades at a discount to later-spring GF (Apr/May) due to supply reality.

- **Summer feeder strength (Jun–Jul)**: Spring-placed calves are now 2–3 months into feedlots (critical growth phase). Feeders are confident in placements; fewer new calves available (it's summer; calves born in Feb–Apr, now mostly in feedlots). GF can drift sideways or grind higher on tight near-term supply. Heat stress on rangeland can reduce forage quality; ranchers hold cattle; supply tightens.

- **Fall placement surge (Aug–Sep)**: Fall/autumn breeding from prior summer comes to term; new calves become available Aug–Sep. Feeders want to fill pens before winter (to avoid winter weather/mortality). Ranchers sell into strength (good prices, available cattle). Aug–Sep GF is typically the highest-volume, most-liquid contract window. GF often rallies late Aug into early Sep on placement demand.

- **Winter and deferral strength (Nov–Mar)**: Fewest calves available (late fall births are immature; most 6-month-old calves already in feedlots by Nov). Deferred GF contracts (Jan, Mar) trade at a carry/contango to near-month (Nov, Dec). Prices often grind higher on storage/carry (cold storage cost, financing). New-year feeders refresh placements; moderate GF demand.

**Event-driven:**
- **USDA Cattle on Feed (3rd Friday monthly)**: Placements, on-feed inventory, marketings. Heavy placements (>2% above trend) → bullish GF (demand signal). Light placements → bearish GF (demand weak). Surprises >3% drive 1–2 cent moves. Light placements in spring (Mar–Apr) = shortage signal → GF spike.

- **USDA Cattle Inventory (Jan–Feb, typically)**: Annual inventory report on total US cattle stock (breeding herd, feeders, others). If breeding herds are shrinking, long-term calf supply will tighten 12–24 months later. Affects deferred contracts most.

- **USDA Crop Progress on Pasture condition (monthly May–Sep)**: Poor pasture = reduced forage; ranchers sell cattle early (supply surge, GF weakness). Good pasture = cattle stay longer; supply tightens; GF strength.

- **Drought / weather events (especially rangeland weather, Apr–Aug)**: Severe drought in ranching regions (Texas, Oklahoma, Nebraska) reduces forage; ranchers liquidate cattle → GF crashes. Conversely, good rains = abundant forage → ranchers hold; GF rallies on supply tightness.

**Time-of-day patterns:**
- **9:05–11:00 CT (pit open)**: Moderate volume; good fills. Often reverses overnight Globex action.
- **11:00–13:00 CT (pit approach to close)**: Lower volume; bid-ask widens.
- **Post-pit close (13:00–17:00 CT)**: Globex only; wider spreads; lower volume than LE.
- **Overnight Globex**: Very thin; avoid unless size is tiny.
- **USDA Cattle on Feed release (3rd Friday, ~13:00 CT)**: Sharp volatility; spreads widen; good fills during the 10-min window around release.

**Calendar quirks:**
- **Roll window (7–10 days before FND)**: Volume/liquidity shifts to next contract. Spreads widen. GF is less liquid than LE; roll windows are more pronounced (wider bid-ask).
- **Contango structure**: Near-month contracts usually trade at a discount to deferred (Mar < Apr, Apr < May typically). This reflects carry costs and supply seasonality (spring supply surge pushes near-contract prices down).
- **Front-month contract expiration (cash-settlement)**: Settlement is the USDA Feeder Cattle Price Index (various weight categories averaged). Most traders roll 10–14 days before FND.

## Common setups

1. **Spring feeder flush + early April dip + May rally**
   - *Trigger*: Feb–Mar GF rallies on expectations of spring calf availability. By late Mar, calves start hitting market; GF supply surge confirmed. Price dips Apr 1–15 as ranchers dump calves.
   - *Entry*: Short GF in mid-Mar when price is near seasonal highs (before supply hits). Or long GF on the early Apr dip (supply is overdone; feeders still want cattle; demand absorbs supply by mid-May).
   - *Stop*: If short, above recent high. If long, below entry − 2 cents.
   - *Target*: If short, mid-Apr support (2–4 cents below entry). If long, late May high (3–5 cents above entry).
   - *Invalidation*: (Short) Feeders aggressively buy before dip fully materializes → price rebounds. (Long) Drought hits ranching regions; supply dries up; short-term supply tightness = long invalidated if ZC rallies (margin compression).
   - *Hit rate*: ~50–58% (seasonal is real; timing is tricky; entry discipline is critical).

2. **Corn rally + feeder margin compression**
   - *Trigger*: ZC rallies 5+ cents over 1–2 weeks (weather shock, export demand, supply concern). Feeder-to-finished margin (GF bought now − LE in 120 days − estimated corn cost) compresses dramatically. Feeders reassess: margins fall from +4 cents/lb to +2 cents/lb or worse.
   - *Entry*: Short GF on the ZC spike (lag: GF weakness follows corn 1–2 weeks). Initiate on day 7–10 of the ZC rally if GF hasn't reacted yet.
   - *Stop*: Above recent GF high (2–3 cents typical).
   - *Target*: 20-day MA or prior support; exit on 2–3 cent retracement or if ZC breaks lower (margin hope returns).
   - *Invalidation*: ZC rallies further (margin concern intensifies) → short is stopped. Or: LE rallies simultaneously with ZC (unexpected demand strength) → feeders' margins hold → short fails.
   - *Hit rate*: ~48–55% (mechanical; works well in trending corn, fails when ZC spikes are temporary).

3. **Heavy Cattle on Feed placements + GF strength + 4-month LE pre-fade**
   - *Trigger*: USDA Cattle on Feed (3rd Friday) shows heavy placements (>2% above trend). GF rallies on immediate demand signal. But market begins to price 120-day LE weakness (supply incoming in 4 months).
   - *Entry*: Long GF on the placement surprise day (first 30 min, ride the demand signal). Then fade GF (sell) on day 2–3 as the 4-month LE implication sinks in. Conversely, short GF deferred contract (e.g., Aug when buying Apr) to express the 4-month LE pressure.
   - *Stop*: If long/fade, below gap low. If short deferred, above recent high.
   - *Target*: If fade short, retest entry or deeper (1–3 cents). If short deferred (Aug), hold for 4-month LE fade (5–8 cent move over 2–4 months).
   - *Invalidation*: (Long fade) Feeders are so bullish on margins that they keep buying; GF doesn't fade. (Short deferred) ZC crashes (margin recovery hope) → feeder demand rebounds → short invalidated.
   - *Hit rate*: ~45–52% (complex; multi-month lags are unpredictable; timing is everything).

4. **Late summer / early fall feeder demand + Aug–Sep rally**
   - *Trigger*: Late Jul–early Aug, feedlots are filling up from spring placements; demand for new feeders rises. Aug–Sep GF typically sees strongest demand. Technical break above recent resistance (e.g., 180 cents/lb).
   - *Entry*: Long GF in early Aug on the technical breakout + seasonal demand confluence.
   - *Stop*: Below 20-day MA or 2–3 cents below entry.
   - *Target*: Seasonal high (typically 3–8 cents above entry); exit on daily close below 10-day MA or if ZC rallies hard (margin compression signal).
   - *Invalidation*: Drought hits ranching regions; supply dries up; GF spikes higher too fast → long is stopped on secondary supply shocks. Or: feedlots fill faster than expected; placements ease; GF fails to rally → short GF from resistance level works.
   - *Hit rate*: ~52–60% (seasonal demand is strong; feeder profitability is real in late summer; setup rewards trend discipline).

## Classic traps

- **Margin-compression false signal**: ZC rallies; feeders reprice margin lower. GF should fall. But LE simultaneously rallies (unexpected demand surge); feeders' margins actually hold or improve. GF falls less than expected; short GF stops out.

- **Spring supply surge over-extrapolation**: Ranchers sell in Mar–Apr; GF dips. Specs short expecting continued selling. But by mid-May, supply is absorbed; feeders resume aggressive buying; GF rallies sharply; shorts are caught.

- **Cattle on Feed placement hype reversal**: Heavy placements release; market rallies GF on demand signal. But next day, specs realize supply is now known in pipelines; 4-month forward LE weakness becomes certain. Longs panic; sharp GF fade.

- **Drought signal delayed / then accelerated**: Early drought warnings hit; ranchers don't immediately sell (hope for rain). GF stays bid. Drought worsens; ranchers liquidate hard; GF crashes sharply in 2–3 weeks. Traders who shorted too early on soft drought news get stopped before the big fade; contrarians catch the sharp fall.

- **Feedlot capacity illusion**: A feedlot reports 92% capacity utilization (considered "normal"). But on-feed inventory is actually declining (cattle are being marketed faster than new calves are placed). GF is bid but supply is actually tightening. Long GF hits resistance and reverses.

- **Ignore the 120-day lead**: Traders focus on near-month GF without considering 120-day LE. A feeder placement surge (GF rallies) that should pressure LE 4 months later gets ignored. Longs GF but miss the set-up: GF strength now = LE weakness in 4 months = GF weakness in 5+ months. Holding too long into the LE fade.

- **Cheap leverage + round-number stops**: GF is ~$25 per tick; a 50-contract position is ~$125K notional with 10x leverage. Round-number stops (160, 170, 180 cents/lb) get hunted. Tight stops (1 cent) are vulnerable to volatility spikes.

## Liquidity profile

- **Average daily volume** (front month): 40k–120k contracts in normal regime; peak >200k during major USDA Cattle on Feed or heavy placement season (Apr–May, Aug–Sep). Apr/May and Aug/Sep contracts are most liquid; Jan/Mar lighter.
- **Open interest trend**: ~80k–150k for Apr/May and Aug/Sep; lighter for other months. Total market is smaller than corn (ZC) or even live cattle (LE); retail spec participation is moderate.
- **Pre-open / post-close behavior**: Globex opens 17:00 CT Sunday with moderate volume; spreads 3–5 cents. 9:05 CT pit open tightens to 2–3 cent spreads. Post-pit close, Globex widens to 4–6 cents.
- **Best session for fills**: 9:15–12:30 CT (pit hours). Avoid 13:00–17:00 CT and overnight unless size is small. GF is less liquid than LE; wider spreads are normal.
- **Bid-ask spread**: 2–3 cents normal during pit hours; 3–5 cents shoulder hours; 5–8 cents overnight Globex. Roll weeks: spreads widen 1–2 cents.

## Options (if applicable)

- **Weekly expirations**: Mondays (expire Friday end of prior week). Less popular than LE weeklies; lower volume.
- **Monthly expirations**: 3rd Friday of month. Primary expiration; higher volume than weeklies but still modest.
- **Settlement**: 9:30am CT Fridays (weeklies); 9:30am CT on listed expiration date (monthlies).
- **Typical IV rank range**: Placement season (Mar–May, Aug–Sep): 45–70th percentile. Summer/winter: 25–50th percentile. IV spikes on USDA Cattle on Feed or major ZC moves.
- **Pin-risk behavior**: Monthly options near expiry can pin if strike is near ATM. Avoid short gamma in the week of Cattle on Feed if short calls/puts near money. Less severe than LE because volume is lower.

## Risk notes

- **Gap risk profile**: Largest gaps occur on USDA Cattle on Feed (3rd Friday), major ZC moves, and drought announcements. Typical gap: 2–4 cents; extreme (>5 cents) on severe drought or unexpected placement surprises. Overnight Globex gaps to pit open average 1–2 cents.

- **Limit-up / limit-down mechanics**: CME allows GF to move 3 cents/day limit-up or limit-down (from prior settlement). Rarely hit in modern era; last limit-move would have been 2012 severe drought. If limit is hit, trading halts; no way to exit except next day.

- **Worst weekly move in last 5 years**: Mar 2012 (worst US Midwest drought in 60 years): GF rallied from 110 → 145 cents (+32%) over 8 weeks; massive rancher liquidation shock. May 2014–2015 (post-drought rebuild): GF crashed from 155 → 120 cents (−23%) as herd rebuilding saturated supply. Fall 2023: GF drifted lower on ZC pressure; no shocking weekly move.

- **Tail-risk events to remember**:
  - **2012 severe Midwest drought**: Unprecedented rancher herd liquidation; GF spiked 30%+; took 5+ years to rebuild breeding herds; structural supply tightness for years.
  - **2014–2015 post-drought oversupply**: Herd rebuilding flooded market with calves; GF crashed 20%+ over months; feeder margins compressed.
  - **COVID-2020**: Packer closures (infection outbreaks) → fear of LE weakness → feeder demand collapsed → GF crashed 10–15% in 2–3 weeks despite unprecedented LE strength (structural dislocation).
  - **Periodic ZC spikes (2010, 2021)**: Feed cost surges → feeder demand evaporates → GF weakness 1–2 weeks later.
  - **Avian flu spillover (2023–2024 rumors)**: Speculation of cattle exposure; no confirmed cases; GF unaffected. But tail-risk if spillover occurs (cattle disease = supply shock; massive price spike).

## References

- **CME GF contract specs**: https://www.cmegroup.com/markets/agriculture/livestock/feeder-cattle.contractSpecs.html
- **USDA Cattle on Feed report**: Issued 3rd Friday monthly; https://usda.gov/nass (monthly placements, on-feed, marketings)
- **USDA Cattle Inventory report**: Issued Jan–Feb; total breeding herds, feeders, others
- **USDA Feeder Cattle Price Index**: Published monthly; primary settlement reference for GF
- **USDA Pasture Condition (weekly May–Sep)**: Impacts rancher selling decisions
- **USDA Crop Progress (weekly May–Sep)**: Forage availability signal
- **Live cattle (LE) deep-dive**: See `vault/futures/product_deep_dives/LE.md` (GF leads LE 120 days)
- **Corn (ZC) deep-dive**: See `vault/futures/product_deep_dives/ZC.md` (inverse margin driver)
- **Lean Hogs (HE) deep-dive**: See `vault/futures/product_deep_dives/HE.md` (parallel livestock, shorter cycle)
- **Key calendar dates**: Cattle on Feed (3rd Fri each month), Crop Progress (Thu May–Sep), WASDE (monthly ~10th), GF contract expirations (20th of month, cash-settled).
