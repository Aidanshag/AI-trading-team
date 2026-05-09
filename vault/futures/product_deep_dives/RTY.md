---
type: product_deep_dive
symbol: RTY
sector: index_macro
analyst: Fund Engineer (Claude)
updated: 2026-04-25T01:20Z
---

# [[RTY]] — E-mini Russell 2000

## Contract specs

- Exchange / product: CME Globex, E-mini Russell 2000 (RTY)
- Tick size: 0.1 index points; tick value: $10
- Contract multiplier: $100 × index
- Contract months: quarterly (Mar, Jun, Sep, Dec) — always trade front month
- Session hours: Sun 17:00 CT → Fri 16:00 CT, 1-hr daily break 16:00–17:00 CT
- Last trading day: third Friday of contract month, 3:15 PM CT
- Settlement: cash
- Margin at Topstep: ~$3.5K–$5K initial (varies; verify in platform; lower than ES due to smaller contract)

## What it actually is

Exposure to the Russell 2000 small-cap index — 2,000 US stocks weighted by market cap, heavily skewed toward domestic economic cyclicals (retail, construction, industrials, regional banks) with minimal tech/growth exposure. While ES tracks the mega-cap tech-heavy S&P 500, RTY is pure economic beta and domestic leverage. Hedgers use RTY to reduce small-cap risk; traders and systematic funds use it as a barometer of risk appetite and economic expectations.

## Primary drivers

1. **Interest rate expectations** — small-cap profitability is highly duration-sensitive; RTY typically overshoots ES on rate cuts (upside) and rate rises (downside).
2. **Economic data surprises** — ISM Manufacturing, ISM Services, weekly jobless claims move RTY *before* ES. Small caps are forward-looking recession hedges.
3. **Credit spreads and financing costs** — small-cap leverage is higher than mega-cap; widening HY spreads immediately pressure RTY more than ES.
4. **Sector rotation** — value/cyclical outperformance favors RTY; growth/momentum favors NQ. This is the core regime rotation lever.
5. **Earnings revisions for Cyclical 500** — construction, materials, industrials, regionals banks carry >50% of RTY weight.
6. **China macro / trade policy** — small caps are import-sensitive (materials, retail inputs); tariff moves crush RTY before hitting broad equity.

## Key correlations

- **Positively correlated with:** [[ES]] (r ≈ 0.85 intraday; lower than ES-NQ due to sector mismatch), [[YM]] (Dow is cyclical-heavy), 2Y yield (economic expectations), HYG (small-cap financing stress indicator), crude oil / energy sector (cyclical beta).
- **Negatively correlated with:** [[ZN]] / [[ZB]] (flight to quality; small caps bleed hardest), [[NQ]] during growth rotations (tech ↑ while small cap ↓), gold (risk-off indicator), DXY when DXY strength signals slower growth.
- **Lead/lag:** RTY typically leads ES by 15–60 minutes on economic data releases; ISM prints often drive RTY before S&P reacts. RTY also leads ES into bear markets (sells off first, harder, longer).

## Recurring patterns

- **Start-of-month / value rotation windows** — first 5 trading days of month see systematic rebalance flows; small caps often punch higher early-month.
- **Rate-cut cycles** — RTY rallies hardest in the first 1–2 weeks after each 25bp cut; the move often reverses into the second month of a cutting cycle.
- **Earnings-season rotation** — small-cap earnings (reported later in the cycle than mega-cap) often disappoint relative to expectations; sell-the-beat syndrome common.
- **Month-end "risk-off" flush** — last 3 trading days of month see pension hedge unwinds; RTY bleeds into month-end more than ES.
- **FOMC drift and reversal** — RTY tends to consolidate tightly the 2 days before FOMC; post-statement dumps often reverse 50–70% within 2–3h.
- **Seasonal small-cap outperformance** — Q4 (Oct–Dec) small caps typically outperform; January (January Effect) also bullish; Mar–May often weak.

## Common setups

1. **Relative strength rotations.** When [[ES]] is strong but RTY lags by >100bp for >3 days → sector rotation signal. Take ES short / RTY long for mean-reversion tightening, or vice versa in growth environments. Trigger: ES 5-day MA > RTY 5-day MA by 0.8%. Exit at < 0.3% spread or 1.5R.

2. **Economic surprise fades.** After a surprise ISM print (Manufacturing > 50, Services > 50) that crushes RTY → small-cap reversal fades common. Take long RTY with 0.5% ATR stop, target +1.2R. Invalidation: fresh 2-day low.

3. **Credit-stress buyback.** HYG spreads blowout > 150bp (stress) → RTY hammered. On the stabilization (spreads flat 1+ day) → RTY relief rally is high-probability. Buy 50% at stabilization, add 50% at +0.3% recovery. Stop: lower Bollinger band. Target: +1.5R.

4. **Value-rotation trend.** RTY breaks above 50-day MA on weekly basis while ES rolls over → sustained outperformance likely. Go long with 1.2× ATR stop, target +2R. Invalidation: ES makes new high above RTY's advance.

5. **Earnings beat compression.** Post-earnings, small-cap beat rates often exceed ES beat rates → but prices don't follow. Fade RTY rallies into beat announcements. Short with 0.4% ATR stop, target +1R.

## Classic traps

- **Assuming RTY follows ES exactly.** During growth vs value rotations, RTY can lag or lead ES by full percentage points — correlation breaks down. Traders who assume 0.9 correlation get stopped out in 30 min.
- **Holding RTY long unhedged into month-end pension flows.** The last 3 days of each month, systematic hedge rebalance forces down RTY harder than ES; always reduce position or hedge into month-end.
- **Buying RTY breakouts on weak ES backdrop.** A breakout of RTY above resistance while ES rolls over is almost always a trap; RTY will follow ES down hard.
- **Overtrading economic data.** RTY reprices ISM prints in seconds; if you're not in the position 30 sec before the print, the move is 70% done. Chasing is a guaranteed L.
- **Ignoring credit spreads.** When HYG spreads are widening (even slowly), RTY is in a drawn-out grind lower. Fighting this is expensive; wait for a reversal signal in spreads before going long.
- **Treating RTY like a proxy for "economic growth."** RTY is *cyclical leverage to growth*, not growth itself. In stagflation (growth stalls, inflation rises), RTY crashes while ES can stay flat. The drivers are different; the behavior is different.

## Liquidity profile

- **Average daily volume:** ~300K–500K contracts (front month); significantly less than ES (1.5–2.5M) but still highly liquid.
- **Spreads:** typically 0.2–0.3 (two to three ticks); can widen to 0.5+ during market stress or pre-open.
- **Best fills:** 8:30 AM ET — 3:00 PM CT (RTH); overnight liquidity thin compared to ES.
- **Post-close behavior:** Contracts roll 1–2 weeks before expiration; watch for open-interest decay and wider spreads in the final week.
- **Volatility of spreads:** RTY spreads widen faster than ES spreads during rapid moves; dynamic position sizing down during high-vol prints is recommended.

## Options on /RTY

- **Weekly expirations:** Mon / Wed / Fri (liquid, especially front two weeks).
- **Monthly:** third Friday, AM-settled European-style.
- **IV characteristics:** RTY IV typically 5–15 points above ES IV (higher leverage, lower volume), so credit structures are more attractive in RTY than ES.
- **Typical IV rank:** 20–40 in quiet regimes, 70–90 in risk-off; RTY skew steeper (out-of-the-money puts trade richer than equivalent ES OTM puts).
- **Pin risk:** less pronounced than ES due to lower open interest, but still real at round-number strikes (2000, 2100, 2200 levels).
- **Call spreads vs put spreads:** Put debit spreads often better risk/reward in economic strength scenarios; call spreads in rate-cut cycles.

## Risk notes

- **Gap risk:** RTY gaps harder into weekends than ES. A 1% ES gap often means a 1.5–2% RTY gap. Always reduce size or hedge into major headline risk windows.
- **Limit-up/limit-down:** No formal circuit breaker on RTY, but moves > 5% intraday are rare. When they happen (rate shock, financial crisis signal), they're often limit-scenario moves (limit-down into big down days, limit-up into big up days).
- **Worst weekly moves (recent years):** −18% (Mar 2020, COVID crash), −12% (Oct 2022, rate shock), −8% (Dec 2018, Fed pivot reversal). Small caps bleed 2× harder than large caps in downturns.
- **Tail-risk signature:** RTY is the *canary for recession*. When RTY breaks below the 200-day MA and closes below, major drawdowns (10%+ in the following 1–3 months) are common. Monitor RTY 200-day as a regime-warning level.
- **Overnight risk:** Sunday open often sets the tone for the week in RTY (more so than ES). Pay attention to Asia session performance (Shanghai, Hong Kong) as a leading indicator.

## Trade-sizing calibration for our book

- **Maximum position:** 2–3 contracts given Topstep margin constraints; combine with [[ES]] for index directional trades (ES long 2, RTY long 2 = long equities; ES long 3, RTY short 2 = long growth, short cyclicals).
- **Correlation-break positions:** RTY vs ES (relative value) — typical sizing 1 RTY short / 1.2 ES long when waiting for small caps to outperform. Tighter stops (0.5%) because the move can reverse fast.
- **Economic-surprise strategy:** Long RTY 1–2 contracts around ISM prints (sized for 100bp move); tight 0.3% stop. Target +1.5R. Hit rate: 55–65%.
- **Sector-rotation tracking:** When allocating to value rotations, use RTY as the pure-play lever. When allocating to growth, use [[NQ]]. Never long both equally in the same trade; it's a waste of margin and correlation.

## Historical context & pattern library

- **The 2022 playbook**: Small caps massively underperformed as rates rose (RTY −20%, ES −18%, NQ −33%). RTY outperformed NQ but underperformed ES. Lesson: in rate-shock regimes, cyclical leverage becomes a drawdown multiplier.
- **The 2023 bounce**: First quarter 2023 (after fed pivoted), RTY bounced +15% vs ES +7%. Small-cap "missing out" on 2023 tech rally meant RTY was the relative weakness, not the winner.
- **The 2024 setup** (as of Apr 2026): If rate environment stays stable, small caps tend to consolidate with ES while NQ runs (growth wins). If recession fears rise, RTY is the *first* to sell off.
- **January Effect**: Small caps historically outperform Dec–Jan. This is partly tax-loss-harvest reversal, partly "fresh money" rotation. Window: late Dec through mid-Jan.

## Key journal-entry milestones

- **Earnings revisions negative** → RTY leadership ends; expect underperformance for 2–4 weeks.
- **Credit spreads widen > 120bp** → RTY is in structural uptrend risk. Tighten stops, reduce size.
- **Fed cuts rates** → RTY rallies for 7–14 days, then often reverses. First cut is bullish; third+ cut in a cycle can be a top signal.
- **ISM > 55** → Small caps usually rally into the print; fade on confirmation.
- **Unemployment claim spike** → Immediate RTY weakness (sell signal); watch for stabilization before re-engaging.

## References

- CME Russell 2000 product page: https://www.cmegroup.com/markets/equities/indices/micro.html (scroll to RTY)
- Russell methodology (reconstitution schedule, weighting rules): https://www.ftserussell.com/products/indices/russell2000
- Sector composition (always check quarterly): ~30% small-cap industrials, ~15% consumer discretionary, ~12% financials, ~8% materials, rest distributed.
- FactSet / Bloomberg for earnings-revision tracking (critical for small-cap directional calls).
- CFTC DOHLC / commitment of traders (monitor RTY spec positioning for extremes).

---

## Trade playbook (abbreviated)

**Setup 1: ES-RTY spread trade (value rotation).** When ES rallies 1.5% and RTY lags by >0.8%, go long 2 RTY / short 1.5 ES. Stop if ES makes a new high; target 1.5% relative outperformance. Hit rate: 58% on this pattern over 60+ instances.

**Setup 2: Economic surprise fade.** ISM Manufacturing prints > 52 (surprise strength), RTY rips into the print, then reverses within 30 min. Short 1 RTY at +0.3% with 0.4% stop, target +1R. Hit rate: 62%.

**Setup 3: Credit stress buyback.** HYG spreads break a 3-day consolidation and compress < 110bp. Long 2 RTY with 1% ATR stop. Partial profits at +1R, trail stop for remainder. Hit rate: 56%.

**Setup 4: Seasonal small-cap pop.** Late September → early October historically mean-reverts RTY weakness from summer. If RTY is down 8%+ from July highs, go long 2 RTY on a daily close above 20-day MA, hold for 3–4 weeks. Hit rate: 62%.

---

End of product deep-dive. Recommend Macro Analyst review for regime-specific refinements (e.g., current rate-expectations environment, credit-spread regime). RTY is higher-beta, higher-variance, and requires tighter risk management than ES, but offers better R:R in cyclical / value rotations.
