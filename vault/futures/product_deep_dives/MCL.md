---
type: product_deep_dive
symbol: MCL
sector: energies
analyst: Fund Engineer
updated: 2026-04-25T08:15:00Z
---

# [[MCL]] — NYMEX Micro Crude Oil

## Contract specs

- **Exchange / product code**: NYMEX (CME) / MCL (1,000 barrels per contract; standard CL is 1,000 barrels, so MCL is NOT a "micro" by count—see Note below)
- **Tick size / tick value**: 0.01 per barrel; $10 per contract
- **Contract months**: Monthly; active trading in front 12 months (most liquid front 3, identical to CL)
- **Session hours**: RTH 08:00–17:00 CT (floor). Globex: 17:00 CT Sunday–17:00 CT Friday (23 hours, 5-minute gap)
- **First notice / last trading day**: 3 business days before delivery month; delivery period 1st–last calendar day of month
- **Settlement**: Physical delivery (Cushing, Oklahoma—WTI delivery point; identical to CL)
- **Margin** (Topstep): ~$500–600 initial, ~$250–300 maintenance (varies; typically 1/20th to 1/30th of full CL margin)

## Critical note: What "Micro" means

MCL is **not** a smaller contract by barrel count; it is a smaller contract by **margin and notional value**. Both CL and MCL are 1,000 barrels per contract. The difference is margin capital required: CL requires ~$10k–12k initial margin; MCL requires ~$500–600 initial margin.

MCL was introduced by CME to allow retail traders, small CTAs, and fractional-sized traders access to the crude benchmark without tying up massive margin. Institutionally, MCL and CL are fungible in deliverable quantity but live on separate exchange symbols and settle independently (though very tight spread).

For this fund's purposes:
- **MCL vs CL relative liquidity**: CL is the global standard (100x the open interest of MCL); MCL is a secondary market used by retail and small CTAs.
- **Spread basis**: MCL/CL basis is typically **zero to +0.02** (MCL slightly bid above CL due to the convenience of lower margin). In vol spikes, MCL bid-ask may widen.
- **Execution priority**: Size <10 contracts: MCL likely tighter fills. Size >10 contracts: CL is better.
- **This fund's posture**: Recommend CL for swing strategies (>1 contract size) and higher conviction. Use MCL for sizing small (1–2 contract) trials or when CL margin is tight due to portfolio loading.

---

## What it actually is

WTI (West Texas Intermediate) crude oil, priced at delivery in Cushing, Oklahoma. MCL tracks the same global crude-pricing benchmark as CL—the benchmark is the same; the **contract structure** (margin, tick value, notation) is different.

MCL is a pure commodity play on crude-oil price. It is not a geopolitical bet on Middle East supply (Brent crude tracks that separately). It is not a play on US refining margins (those live in refined products: RB, HO). MCL is the raw-material input price that drives all downstream energy (refined products, petrochemicals, power).

Crude oil demand is driven by:
1. Global petroleum consumption (transportation fuels, heating oil, feedstock for plastics/chemicals)
2. OPEC+ production decisions (constrain vs. grow supply)
3. Geopolitical supply shocks (wars, sanctions, accidents)
4. Macroeconomic cycles (recessions kill demand; growth lifts it)
5. US dollar strength (crude prices in USD; weak dollar makes crude cheaper for non-US buyers, lifting demand)

MCL has identical drivers to CL but with the caveat that the **micro size makes it more suitable for retail/fractional bets**, not strategic core holdings.

---

## Primary drivers

Ranked by impact in 2024–2026 regime:

1. **OPEC+ production and supply announcements**: OPEC+ (Saudi Arabia, Russia, UAE, Iraq, and 10+ other members) controls ~30% of global crude supply. They meet quarterly (and ad-hoc) to set production targets. A surprise cut (e.g., Saudi Arabia announces −2 mbbl/d) supports crude; a surprise increase weakens it. Historically, OPEC+ announcements move CL 3–8% in minutes. MCL moves identically but with thinner liquidity (may see wider spreads).

2. **Macroeconomic data (US nonfarm payroll, PMI, GDP, consumer spending)**: Crude is a leading indicator of economic health. Strong employment → confidence → driving → gasoline demand → crude demand. Recessions kill crude (2020 Covid: crude crashed 60% in 3 weeks). Weekly jobless claims (Thursdays) and monthly NFP (first Friday) are highest-impact economic releases for crude. MCL will follow CL within 30–120 minutes of major data.

3. **US dollar strength (DXY)**: Crude is priced in USD. A weak dollar (DXY falling) makes crude cheaper in foreign currencies, encouraging foreign demand and lifting prices. A strong dollar (DXY rising) makes crude more expensive globally, damping demand. DXY and crude correlation is −0.4 to −0.6 (moderate-to-strong negative). Fed rate decisions and US-China trade tension drive DXY moves that secondary-transmit to crude.

4. **Geopolitical supply shocks**: Ukraine invasion (Feb 2022) spiked Russian supply concerns and crude rallied from $92 → $120 in 2 weeks. Israel-Hamas escalation (Oct 2023) raised Middle East risk premium but no direct supply disruption. Iran sanctions periodically constrain exports. Hurricane season (Gulf of Mexico offshore) raises disruption risk. These are binary/tail-risk events but have moved crude 5–15% in single days.

5. **US crude inventory (EIA weekly release)**: EIA reports US crude stocks ending on Wednesdays each Thursday 10:30am ET. Surprise builds (market expected draws) are bearish for crude; surprise draws are bullish. Surprise magnitude >4% vs. consensus typically moves crude 1–3%. MCL follows CL with a 5–30 minute lag.

6. **Refinery utilization and cracking**: When US refineries run hot (output-maximizing), they buy crude; high utilization is bullish. When refineries cut runs (low margins, maintenance, or demand collapse), crude demand falls. Refinery utilization is reported monthly; weekly proxies (refinery inputs) are available. Tight refinery margins (crack spreads) can suppress crude demand on a medium-term basis (weeks).

7. **Seasonal patterns**: Winter (Nov–Mar) typically sees higher demand (heating oil, seasonal industrial peak in some regions). Summer (May–Aug) demand is flat but driving season is strong. However, seasonality is overwhelmed by the above drivers in most regimes. Crude does not have a clean seasonal bias like gasoline.

---

## Key correlations

**Positively correlated:**
- **CL (full crude)**: Perfect by definition (MCL and CL track the same underlying). Spread basis is typically 0–2 cents; correlation is >0.99 (essentially 1.0).
- **RB (RBOB Gasoline)**: 0.75–0.90 (very strong). RB is refined from crude; crude move leads RB by 30 min to 3 hours.
- **HO (ULSD/Diesel)**: 0.7–0.85 (strong). Same relationship as RB; HO typically lags crude by 1–3 hours but tighter correlation than RB.
- **Natural Gas (NG)**: 0.2–0.4 (weak). Both energy commodities but different supply/demand drivers. Sometimes move together (geopolitical shock); often diverge (shale supply changes, seasonal demand).
- **Global equity indices (SPY, STOXX Europe, Shanghai Composite)**: 0.3–0.6 (weak-to-moderate) in normal regimes; −0.7 to −0.9 (strong negative) in recessions. Equity weakness → recession fears → crude demand collapse.

**Negatively correlated:**
- **USD Index (DXY)**: −0.4 to −0.6 (moderate-to-strong negative). Strong dollar caps crude; weak dollar lifts it. Relationship is structural (pricing in USD globally).
- **US 10Y Treasury yield**: −0.3 to −0.5 (weak-to-moderate negative). Rising rates signal inflation expectations (bullish for crude supply concerns) but also recession risk (bearish demand). Net effect is slightly negative (recession dominates).
- **Volatility (VIX)**: 0.2–0.4 (weak positive in normal; strong negative −0.6 to −0.8 in risk-off crash). Risk-off spikes collapse crude demand sharply.

**Lead/lag:**
- OPEC+ announcement → CL/MCL response: immediate (minutes) if surprise; muted if expected.
- US NFP (1st Friday) release 08:30am ET → CL/MCL move within 30 seconds; strong if data misses expectations.
- EIA crude inventory (Thursdays 10:30am ET) → CL/MCL move within 5 minutes.
- Fed policy decision → CL/MCL drift over hours/days (USD repricing is the lag mechanism).

---

## Recurring patterns

**Seasonal:**
- **Winter (Nov–Mar)**: Slight demand bias from heating oil; crude often trades higher than summer counterparts. Mean price 2015–2025 typically $5–10/bbl higher in winter. Not a lockstep seasonal; macro dominates.
- **Spring (Mar–May)**: Refinery maintenance begins; some demand softness. Crude often weak Apr–early May. Contango typical.
- **Summer (Jun–Aug)**: Flat-to-slightly-firm (driving season). Demand steady; geopolitical risk premium can spike (hurricane season, OPEC meetings). Contango is typical.
- **Fall (Sept–Oct)**: Transition. Demand soft; refiners prepare for winter. Backwardation can appear if hurricane risk is priced.

**Event-driven:**
- **OPEC+ meetings** (quarterly, announced months in advance): Tend to be catalysts. If market expects a cut and none is announced, crude sells off; if surprise cut is announced, crude rallies. Volatility is highest 1 week before and through announcement.
- **Fed rate decisions** (8 per year): Rate hikes signal dollar strength → crude weakness. Rate cuts signal growth hopes → crude strength. Lag is hours to days.
- **US economic data surprises**: NFP beat → strength; miss → weakness. Same-day impact.
- **Geopolitical flare-ups**: Iran sanctions, Middle East tension, pipeline disruptions. Impact: 2–10% move lasting days to weeks depending on supply impact.
- **Hurricane season (June–Nov, peak Aug–Oct)**: Gulf of Mexico offshore production (~1.5 mbbl/d of US crude) at risk. Risk premium during peak; typically fades post-season.

**Time-of-day patterns:**
- **Asian session (6:00pm–8:00am ET)**: Lower volume. Crude follows overnight news (OPEC, geopolitical). Globex spreads 2–4 ticks wider than RTH.
- **London session (2:00am–8:00am ET)**: ICE Brent crude trades (global benchmark used by non-US buyers). If Brent moves (due to geopolitical, OPEC, or European factors), WTI (CL/MCL) often lags; cross-market arb follows.
- **US pre-market (7:00–8:30am ET)**: Anticipation of EIA inventory data (if Thursday). Volume picks up; spreads tighten.
- **US cash session (8:30am–3:00pm ET)**: Core US. Highest volume. EIA release (Thursdays 10:30am ET) is the major catalyst. Spreads 1–3 ticks. Best time for fills.
- **Post-close (3:00–5:00pm ET)**: Thinner. Late-day reversals are common; avoid large size.
- **Evening Globex (5:00pm–6:00pm CT)**: Transition period. Spreads widen slightly.

**Calendar quirks:**
- **Roll window** (15–20 days before delivery month first notice): Front month volume shifts to next month. Typical back-month contango is 0.50–1.50/bbl. Rolls are smooth for CL (highest volume); MCL rolls can see wider spreads.
- **Last trading day** (3 biz days before delivery month): Very thin. Avoid.
- **Holiday weeks** (Thanksgiving, Christmas, New Year): Volumes thin; avoid large size. Overnight spreads can widen to 5+ ticks.
- **Summer driving season peak** (May–Aug): Highest volume period for energy sector. CL sees peak open interest ~400k contracts; MCL peak ~50k contracts (rough estimate).

---

## Common setups

1. **OPEC+ production surprise + consensus building**
   - *Trigger*: OPEC+ announces a cut or increase. Market initially spikes (draw surprise) or crashes (increase surprise). Within 1–5 hours, consensus forms (was it enough to tighten markets? too much?). Crude consolidates or reverses.
   - *Entry*: Wait for consolidation post-announcement (initial spike fades). Enter on structural confirmation: if supply cut is real and demand is steady, crude tends to hold higher; if cut is symbolic (half of announced, etc.), it fades.
   - *Stop*: 1.00–2.00 from entry (crude volatility is high post-OPEC). Typical RR 1:2 to 1:3.
   - *Target*: Prior month high or consolidation breakout. $2–5 move is typical.
   - *Invalidation*: Equities collapse (recession fears short-circuit supply logic); crude breaks stops.
   - *Hit rate*: ~50–55% (OPEC is unpredictable; often the move is already priced in by market consensus).

2. **EIA inventory surprise + refinery utilization confirmation**
   - *Trigger*: EIA weekly crude inventory (Thursdays 10:30am ET) shows surprise draw (bullish) or surprise build (bearish). Within 30 min, refinery-utilization signals confirm (e.g., draw + utilization rising → structural demand, not just seasonal). Crude consolidates post-spike.
   - *Entry*: 15–45 min post-EIA. Enter on consolidation if secondary signals align (e.g., draw + US equities firm = demand intact).
   - *Stop*: 0.75–1.50 from entry. This is shorter-term (1–5 days); tighter stop than OPEC.
   - *Target*: 50% of EIA move revisit; typically 1–3 dollar move.
   - *Invalidation*: CL reverses into close (typical of reversals on low-conviction data).
   - *Hit rate*: ~55–60% (EIA is real supply signal; if confirmed by secondary indicators, hit rate is solid).

3. **Macroeconomic data miss + recession fear formation**
   - *Trigger*: NFP misses (e.g., 100k vs. expected 200k). Market re-prices recession probability. Equities sell off. Crude crashes as investors de-risk and pivot to flight-to-safety (bonds, gold).
   - *Entry*: Short crude on initial spike down (panic selling). Set tight stop; expect reversal within 2–5 hours as reality-check (labor market is still tight; may be noise).
   - *Stop*: 1.00–1.50 above entry. This is a volatility play; don't risk big.
   - *Target*: 50% of initial move; often covered within 1 hour as equities stabilize.
   - *Invalidation*: Data is confirmed as real slowdown (repeated weak prints); crude continues down.
   - *Hit rate*: ~45–50% (mean-reversion on data surprises is common but not guaranteed; depends on regime confidence).

4. **USD strength + crude-strength divergence (carry unwind)**
   - *Trigger*: US dollar (DXY) rallies sharply on Fed rate expectations or relative growth. Crude does NOT follow up (usually crude would fall with DXY up). This suggests carry positioning (fund long crude, short USD) is unwinding. Crude is held up by structural factors (supply cut, demand resilience) but USD strength is capping it.
   - *Entry*: Short crude against the USD rally. Size small (carry unwinds can be quick, but structural support can reverse shorts).
   - *Stop*: 1.50–2.00 above entry. Hold for 1–3 days.
   - *Target*: Carry basis compression; typically 1–2 move.
   - *Invalidation*: Supply shock (geopolitical) overwhelms carry; crude rallies despite USD strength.
   - *Hit rate*: ~40–45% (carry unwinds are real but timing is difficult; often trapped on stops).

5. **Seasonal demand weak + inventory build surprise**
   - *Trigger*: Spring (Apr–May) or fall (Sept–Oct). EIA shows larger-than-expected build (demand is weak). Refinery utilization is declining. Crude is in a downtrend.
   - *Entry*: Short crude on the EIA data + utilization confirmation. Hold for 1–2 weeks.
   - *Stop*: 2.00–3.00 above entry. Seasonal demand weakness is gradual; stops are wider.
   - *Target*: Seasonal lows (typically −4 to −6 from entry over 2–3 weeks).
   - *Invalidation*: Geopolitical shock (refinery outage, OPEC cut) interrupts seasonal weakness.
   - *Hit rate*: ~50–55% (seasonal weakness is real but often contested by investors holding for summer/winter strength).

---

## Classic traps

- **OPEC surprise fade**: Market rallies on OPEC announcement of a supply cut. Within 1–3 days, traders realize the cut is smaller than expected or compliance is questionable. Crude reverses hard; traders long the announcement get stopped out.

- **EIA whipsaw**: Inventory data shows draw (bullish). Crude spikes; within 30 min, traders realize draw is seasonal and demand is weak. Spike fades; spike-chasers are trapped long.

- **Recession contagion**: Equities sell off hard on bad economic data. Crude crashes alongside (demand fears). But crude recovery is faster than equities (supply is inelastic; demand will recover). Traders short into recession fear miss the bounce.

- **Geopolitical premium collapse**: War news (e.g., Israel-Hamas, Ukraine) spikes crude on supply-risk premium. Market realizes actual supply impact is minimal. Premium unwinds over days/weeks; crude falls 5–15%. Risk-on traders miss the unwind.

- **Carry-trade reversal**: Crude rallies on positive macro; investors are long crude/short USD (carry). Fed surprisingly hikes; USD rallies; carry unwinds. Crude crashes despite tight supply. Structural longs caught off-guard.

- **Overnight gap reversal**: Crude gaps 3–5% overnight on geopolitical news (e.g., Iran announcement). US cash open fades 50–70% of gap within 1 hour. Gap-trading overnight holders miss the fade.

---

## Liquidity profile

- **CL (full crude) average daily volume** (front month): 600k–1.2M contracts daily in normal regime. Peak in summer (June–Aug): 800k–1.5M contracts. Winter: 400k–700k. Spring/Fall: 500k–900k.
- **MCL liquidity**: ~5–10% of CL volume on average. Front month MCL: 30k–80k contracts daily (rough estimate). Peak in summer: 50k–100k. Winter: 20k–40k. **MCL is less liquid but still tradeable for 1–5 contract size.**
- **CL open interest trend**: ~350k–600k front month; back months 50k–200k. **MCL open interest**: ~20k–40k front month (rough estimate).
- **Pre-open / post-close behavior**: Globex opens Sunday 17:00 CT. Spreads are wide (3–7 ticks for CL, 4–10 ticks for MCL) until US pre-market (7:00am ET). Post-close (3:00–5:00pm ET) thins out.
- **Best session for fills**: 09:30–15:00 ET. Volume is highest 10:00–14:00 ET (post-EIA window).
- **Bid-ask spread**: CL: 1–3 ticks normal in core hours. MCL: 3–8 ticks (wider due to lower volume). In EIA / low-volume hours, MCL spreads can widen to 10+ ticks.
- **Slippage notes**: CL is ideal for size >5 contracts. MCL is better for size 1–3 contracts (lower total notional, tighter fills). For size >10 contracts, CL is preferable to MCL (lower market-impact cost).

---

## Options (if applicable)

- **Weekly expirations**: Mondays (expire Friday end of day prior week). Moderate volume on CL; minimal volume on MCL.
- **Monthly expirations**: 3rd Thursday of month. Standard NYMEX calendar.
- **Settlement**: 10:30am CT Fridays (weeklies); 16:00 CT on listed expiration date (monthlies).
- **Typical IV rank range**: Summer (May–Aug): 30–50th percentile. Winter (Nov–Mar): 40–60th percentile. Peak IV in summer when geopolitical/hurricane risk is priced; peak in winter on heating-demand uncertainty.
- **Pin-risk behavior**: Low-to-moderate. Crude is less pinnable than interest-rate futures but more than equities. Avoid short gamma near OPEC announcements and EIA releases.
- **MCL options**: Very thin; not recommended for structured plays. If sizing small (1 contract), stick to futures.

---

## Risk notes

- **Gap risk profile**: Largest overnight gap risk is geopolitical (Russia, Iran, Middle East). Typical overnight gap (Globex open Sunday or after major news): 1–3%. Extreme (war, blockade, sanctions announcement): 3–10% gap. Recent example: Ukraine invasion Feb 2022 = crude gap up 5%+ overnight, fade 50% by 10:00am ET.

- **Intraday gap risk**: EIA inventory release (Thursdays 10:30am ET) is the highest-impact intraday catalyst. Typical EIA move: 1–3% in minutes. Surprise >4% vs. consensus: 3–5% move.

- **Limit-up / limit-down mechanics**: CME does not have traditional daily price limits on CL/MCL. In 2022 Ukraine invasion, crude spiked 20%+ in a single day without a halt. Historically rare, but tail-risk to remember.

- **Worst weekly moves in last 5 years**:
  - **Feb 2022 (Ukraine invasion)**: CL rallied from $92 → $130 (+41% in 1 week) as Russian supply fears spiked.
  - **Apr 2020 (COVID-19 demand collapse + storage crunch)**: CL crashed from $60 → negative (briefly went to −$37 due to storage expiration mechanics on May WTI futures; cash WTI stayed positive but crashed 70% in days).
  - **Nov 2022 (OPEC+ shock cut)**: CL crashed from $85 → $75 (−12% in 1 day) on surprise 2 mbbl/d production cut announcement.

- **Tail-risk events to remember**:
  - **Ukraine invasion (Feb 2022)**: Russian supply constraints; geopolitical premium spiked. CL rallied 41% in 1 week.
  - **OPEC+ surprise cut (Nov 2022)**: Announcement of 2 mbbl/d cut surprised market (vs. 0.5 mbbl/d expected); market sold off hard (risk-off repositioning).
  - **COVID-19 demand collapse (Mar–Apr 2020)**: Lockdowns killed demand; storage filled. May WTI futures went negative (inversion arbitrage). Cash crude crashed 70% in 3 weeks but recovered 50% within months.
  - **Hurricane Katrina (Aug 2005)**: Gulf offshore shutdowns; crude spiked 15% in week. No sustained supply loss (damage was overstated); crude faded 50% of spike within 2 weeks.
  - **Venezuela sanctions (2017–2019)**: Persistent supply loss (−1 mbbl/d) over years; crude spiked mid-2019 then faded as shale filled void.

---

## MCL-specific considerations

1. **Margin efficiency**: MCL requires ~$500–600 margin per contract (vs. $10k–12k for CL). If sizing 1–3 contracts, MCL is more efficient. If sizing 5+ contracts, CL margin becomes negligible on a per-contract basis.

2. **Spread basis**: MCL trades at +0–2 cent premium to CL (convenience value due to lower margin). Basis is stable and tradeable; in vol spikes, basis can widen to +5 cents briefly.

3. **Slippage comparison**: For 1–2 contracts:
   - CL: typical slippage 0.10–0.20 (1–2 ticks on a 1,000-contract order is negligible impact).
   - MCL: typical slippage 0.10–0.25 (spreads are wider; tighter order book).
   - **Advantage**: MCL on very small size (1 contract).

4. **Execution timing**: MCL fills improve 09:45–14:30 ET (peak CL volume). Avoid 17:00–08:30 CT overnight and 14:45–15:15 ET (thin spell before close).

5. **Mixing MCL and CL in a portfolio**: Not recommended. Stick to one or the other to avoid confusion and basis-trade complexity. If sizing trials at 1 contract, use MCL; scale to CL at 2+ contracts.

---

## References

- **CME CL contract specs**: https://www.cmegroup.com/markets/energy/crude-oil/light-sweet-crude.contractSpecs.html
- **CME MCL contract specs**: https://www.cmegroup.com/markets/energy/crude-oil/micro-light-sweet-crude-oil.contractSpecs.html
- **EIA crude oil data**: https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=DHHNGSP&f=D (daily crude prices)
- **NYMEX settlement data**: https://www.cmegroup.com/market-data/ (real-time and historical futures data)
- **ICE Brent crude**: https://www.theice.com/ (global benchmark for comparison)
- **OPEC+ announcements**: https://www.opec.org/ (quarterly meeting schedules and decisions)
- **EIA Weekly Petroleum Report**: https://www.eia.gov/petroleum/weekly/ (Thursdays 10:30am ET; inventory data)
- **Refinery utilization (EIA)**: https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=IMUURT&f=M (monthly; leading indicator of crude demand)
- **US Dollar Index (DXY)**: https://www.ice.com/market-data/continuous-futures (ICE currency index)
