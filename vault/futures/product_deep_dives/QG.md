---
type: product_deep_dive
symbol: QG
sector: energies
analyst: Fund Engineer
updated: 2026-04-25T12:30:00Z
---

# [[QG]] — E-mini Natural Gas (Globex)

## Contract specs

- **Exchange / product code**: NYMEX Globex (CME) / QG (1,000 MMBtu per contract = 10% of NG)
- **Tick size / tick value**: 0.001 per MMBtu; $1.00 per contract (vs. NG $10 per tick)
- **Contract months**: Monthly; actively traded front 6–12 months (most liquid front 2–3)
- **Session hours**: Globex only; 17:00 CT Sunday–17:00 CT Friday (23 hours, 5-minute gap Sunday evening). No floor trading.
- **First notice / last trading day**: 3 business days before delivery month; delivery period 1st–last calendar day of month (same as NG)
- **Settlement**: Physical delivery; same Henry Hub basis as NG
- **Margin** (Topstep): ~$300 initial, ~$150 maintenance (approximately 1/10th of NG; scales linearly with contract size)

## What it actually is

QG (E-mini NG) is the electronically traded, smaller version of the full-size NG contract. One QG = 1/10th of one NG contract. QG was launched to provide a micro-exposure product for retail traders, portfolio hedgers, and algo platforms that want to fine-tune position sizing or risk without committing full NG contract capital. QG has the same underlying commodity (Henry Hub natural gas) and delivery mechanics as NG, but with drastically lower margin, point value, and contract size.

QG is most useful for:
- **Retail/small traders** building position scale (5–20 QG contracts instead of 1–2 NG)
- **Spread traders** (e.g., calendar spreads, ratio spreads) who need granular size control
- **Portfolio hedgers** (utilities, industrial users) who want to hedge smaller volumes of production or consumption
- **Algo/systematic traders** who want lower commission impact on small fills

QG has NOT replaced NG in terms of market dominance—NG remains the primary contract for professionals—but QG's participation has grown 15–20% per year since 2019. Liquidity has improved materially but is still 30–50% that of NG in the front month.

## Primary drivers

**Identical to [[NG]]**, but with one key caveat:

1. **US weather (temperature extremes)** — same dominance
2. **Production + storage inventory** — same, but EIA release moves both QG and NG together
3. **LNG export capacity and international pricing** — same
4. **Industrial demand** — same
5. **Macroeconomic recession risk** — same

**Key difference**: QG is less affected by **institutional positioning and gamma flush events** because the contract is smaller and carries lower notional risk. When macro shocks hit (e.g., 50bp rate cut, energy sector crash), NG sees fast institutional repositioning (hedge fund, commodity index) that can accelerate moves. QG, being a retail/micro contract, tends to follow NG price but with less amplification from institutional gamma rebalancing.

## Key correlations

**With [[NG]] (full-size contract):**
- 0.95–0.99 correlation (nearly perfect). Price divergence is minimal; any split typically represents arbitrage opportunity (QG/NG spread) that closes within seconds to minutes on Globex.
- **Lead/lag**: NG front month on Globex often leads QG by 1–5 seconds due to higher volume and tighter bid-ask. High-frequency algos arb the spread constantly.

**With [[CL]], [[HO]], [[RB]]** and **macro variables (rates, USD, equity)**: 
- Identical correlations as NG (r = 0.75–0.95 to CL; r = 0.3–0.4 to rates, etc.)
- QG tracks NG perfectly, so external correlations are inherited.

**Spread (QG vs NG):**
- Front-month QG/NG spread: typically 0–2 ticks (0–$0.002 per MMBtu). Arbitrage keeps it tight.
- **Time-of-day pattern**: Spread widens overnight (Globex-only activity, fewer arbs), narrows during US session (more algos, tighter competition).

## Recurring patterns

**Identical to [[NG]] for directional trades**, with these specific observations:

**Seasonal:**
- Winter (Oct–Mar) and summer (June–Aug) patterns are identical; QG follows NG seasonal flow.
- Shoulder months (Apr–May, Sept–Oct) thin similarly but slightly more in QG (smaller market).

**Event-driven:**
- **Weekly EIA inventory release** (Thursday 10:30am ET): Both QG and NG gap simultaneously within 1–2 seconds. QG move amplitude is identical on a cents-per-MMBtu basis; the dollar impact is 1/10th (e.g., if NG gaps +$0.15, QG also gaps +$0.15 in price but only +$150 in notional value vs. +$1,500 for NG).
- **NOAA weather updates** (Tues/Fri): Identical to NG; QG follows perfectly.
- **LNG outage announcements**: QG and NG move in sync.

**Time-of-day patterns (Globex-specific):**
- **Sunday evening (17:00–22:00 CT)**: QG opens on Globex Sunday; wide spreads (3–8 ticks between bid/ask). Very thin. Avoid unless absolutely necessary.
- **US session (09:30–17:00 ET)**: Tightest spreads (1–2 ticks), highest volume. Fills are easy here.
- **Overnight (17:00–23:00 CT Mon–Fri)**: Spreads widen (3–5 ticks) but liquidity is available. Lower traffic than US session but still tradeable.
- **Pre-close before Friday 17:00 CT**: Very thin in final 30 min; avoid.
- **Globex-only risk**: Unlike NG (which has floor trading in RTH), QG has no floor fallback. Liquidity is purely electronic. In extreme market events (flash crashes, circuit breaker halts), QG can have wider spreads than NG.

**Calendar quirks:**
- **Roll window** (15–25 days before delivery month): Same as NG. Front month contracts thins; back contracts pick up. Roll into back month 20+ days before expiration.
- **Overnight index roll risk**: If you hold QG overnight (Globex-only), you may be holding across a price jump from the prior session's close to the next morning's open. No floor/RTH price to anchor to overnight; gaps to next session are possible if market gaps overnight.

## Common setups

**Setups are identical to [[NG]] in structure**, with execution adjustments:

1. **EIA surprise gap + follow-through (QG variant)**
   - *Trigger*: EIA release at 10:30am ET; both QG and NG gap within 1–2 seconds. Price closes above/below the gap by second 1-min bar.
   - *Entry*: Long if bullish surprise, short if bearish. QG and NG entry signals are identical.
   - *Stop*: Gap low/high (identical to NG).
   - *Target*: Technical resistance/support (same zones as NG).
   - *Execution advantage in QG*: Lower notional size per contract; can scale size (e.g., 10 QG instead of 1 NG) for finer position control. Particularly useful for swing traders who want to scale into size.
   - *Hit rate*: ~55–60% (identical to NG).

2. **Weather front fade (5–3 days before cold snap)**
   - *Trigger*: NOAA outlook shows cold snap; NG and QG rally 2–5% over 3 days.
   - *Entry*: Short on weakness; QG setup identical to NG.
   - *Stop / Target*: Identical mechanics to NG.
   - *Execution advantage*: QG allows traders to short 10 contracts for 1 NG equivalent, testing the setup with smaller risk exposure per-contract, then scaling if the thesis holds.
   - *Hit rate*: ~45–50% (identical to NG).

3. **Seasonal storage drawdown (Oct–Feb)**
   - *Trigger*: Winter draw tracking. QG is increasingly used by utility and producer hedgers for seasonal rebalancing.
   - *Entry*: Long if draw lags seasonal average.
   - *Hit rate*: ~50% (identical to NG).

## Classic traps

**Identical to [[NG]]**, with one additional risk:

- **Liquidity cliff during news**: If a major NG event (e.g., production shutdown, Hurricane Gulf Coast disruption) occurs overnight on Globex, QG can widen to 5–10 ticks bid-ask very quickly. A retail trader holding 10 QG contracts may face 1–2 minute delays filling on market close-outs. NG, with deeper liquidity, is faster to fill. **Always use limit orders on QG overnight or around major news windows.**

- **Spread arbitrage distortion**: If for any reason QG is mispriced relative to NG (e.g., during a flash crash or Globex halt), the arb spread can blow out to 5–20 ticks. A trader holding a QG position may see a window where they're marked 0.10–0.20 worse than NG traders on the same underlying move. This is temporary but creates psychological pain.

- **Lever up temptation**: Because QG margin is 1/10th of NG, retailers often leverage 10x or more. This amplifies losses on adverse moves. The classic trap: "I can control 10 QG with the margin of 1 NG, so I'll size 10 QG like they're equivalent to 1 NG, then let the algo scale." This leads to under-disciplined risk.

## Liquidity profile

- **Average daily volume** (front month): 50k–150k contracts in normal regime; 150k–400k in winter/volatility. Summer: 30k–80k.
- **Open interest trend**: ~80k–150k front month; back months 20k–50k. Growing trend (+15% YoY) as retail participation increases.
- **Pre-open / post-close behavior**: Sunday 17:00 CT open is very wide (5–10 ticks); fills poor. Best pre-open: Mondays 08:00–09:00 CT (pre-RTH, algos already placed orders). Post-close (Fridays 16:00–17:00 CT): thin; avoid.
- **Best session for fills**: 09:45–15:30 ET (US session). EIA release (10:30am ET) has **best fills** because volume and volatility spike momentarily.
- **Bid-ask spread**: 
  - US session (09:30–17:00 ET): 1–2 ticks
  - Overnight (17:00–23:00 CT): 3–5 ticks
  - Sunday open & late Friday: 5–10 ticks (avoid)
  - Post-EIA or major news: can be 1 tick (ultra-tight due to gamma hedging)

## Options (if applicable)

- **Weekly expirations**: Mondays (expire Friday prior week). Lower IV than NG; less retail participation in QG options.
- **Monthly expirations**: 3rd Thursday of month.
- **Settlement**: 10:30am CT Fridays (for weeklies); standard for monthlies.
- **Volume / open interest**: QG options trade 40–60% of NG option volume; less liquid but tradeable.
- **Typical IV rank**: Same as NG (lower in summer, higher in winter) but sometimes slightly lower because fewer retail hedgers use QG options.
- **Note**: Credit spreads and iron condors on QG are NOT recommended due to liquidity. Long calls/puts only if you believe you can fill both legs easily.

## Risk notes

- **Gap risk profile**: Overnight (Globex-only): 3–8 ticks typical; during EIA 1–2 ticks (synchronized with NG). Worst-case overnight gap: 15–20 ticks on extreme supply shock (e.g., Hurricane disruption announced overnight, LNG outage announced overnight).

- **Liquidity collapse in extreme moves**: If NG limit-down or limit-up occurs (rare but possible in extreme cold snap), QG may face liquidity crisis. Because QG is electronically only, a Globex halt affects QG immediately. NG's floor trading can sometimes provide a liquidity bridge. **In extreme tail events, QG can be harder to exit than NG.**

- **No circuit breaker on QG**: Unlike some equity futures (ES, NQ), there is no circuit breaker halt on QG for single-contract limit moves. Theoretically, QG could gap 20%+ in a single move and stay locked limit if the event is severe enough. This is a theoretical risk but historically rare.

- **Worst weekly move in last 5 years**: Identical to NG (Feb 2021 freeze: +85%; Jan 2022 Ukraine: +93%). QG experiences the same % moves but at 1/10th notional scale.

- **Tail-risk events**: Identical to NG (Texas freeze, Ukraine, Freeport outage, rate shock). QG's smaller size makes individual tail events less catastrophic for retail but the same market moves occur.

## Execution notes for Fund Engineer / PM

**When to use QG vs NG:**

1. **Use NG** if:
   - Sizing is large (>10 contracts notional) — better liquidity, tighter spreads, faster fills.
   - Trading around EIA or major events — NG has deeper institutional volume.
   - Holding overnight (Mon–Fri) — NG's day/RTH session provides a fallback if Globex is thin.

2. **Use QG** if:
   - Fine-tuning size (e.g., building position in stages: +5 QG per day over 3 days vs. trying to scale NG 0.5 at a time).
   - Retail/micro hedges — e.g., a small producer hedging <1M MMBtu; 5 QG is easier to manage than 0.5 NG.
   - Spread trading (calendar spreads, inter-month) — granular sizing control helps with leg ratio optimization.
   - Low capital availability but high conviction — 10 QG with 1/10th the margin is a legitimate way to scale conviction on a thesis.

**Risk management caveat**: Don't use QG's lower margin requirement as an excuse to over-leverage. A 10x levered QG position is still a leveraged position and will hurt just as hard on a −5% NG move.

## References

- **CME QG contract specs**: https://www.cmegroup.com/markets/energy/natural-gas/e-mini-natural-gas.contractSpecs.html
- **EIA weekly storage report**: https://www.eia.gov/naturalgas/storage/weekly/ (applies to both NG and QG)
- **Globex trading hours**: QG trades 17:00 CT Sunday–17:00 CT Friday (no floor trading)
- **Volume / open interest (real-time)**: Check CME DataMine or your broker's platform; QG front month typically 1/2 to 1/3 the volume of NG but growing steadily.
- **Margin / commission**: Verify current at Topstep; plan for ~1/10th the margin of NG but slightly higher commission per contract due to smaller notional value.
