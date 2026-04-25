---
type: product_deep_dive
symbol: ES
sector: index_macro
analyst: seed (Claude)
updated: 2026-04-23
---

# [[ES]] — E-mini S&P 500

## Contract specs

- Exchange / product: CME Globex, E-mini S&P 500 (ES)
- Tick size: 0.25 index points; tick value: $12.50
- Contract multiplier: $50 × index
- Contract months: quarterly (Mar, Jun, Sep, Dec) — always trade the front month
- Session hours: Sun 17:00 CT → Fri 16:00 CT, 1-hr daily break 16:00–17:00 CT
- Last trading day: third Friday of contract month, 9:30 AM ET
- Settlement: cash
- Margin at Topstep: ~$14K initial (varies by tier; verify in platform)

## What it actually is

Exposure to the S&P 500 index, the single most-watched US risk asset. Used by everyone: hedgers, macro funds, directional traders, market makers, systematic trend followers. Deepest liquidity of any futures contract in the world.

## Primary drivers

1. **Fed policy path** — rate expectations dominate. Long-duration assets (growth > value) especially sensitive.
2. **Earnings season** — aggregate S&P EPS revisions + guidance from MAG-7 names (which are ~30% of the index).
3. **Macro data** — CPI, NFP, ISM, retail sales in order of typical impact.
4. **Credit spreads** — HY spreads widening is a leading bearish signal; compressed spreads = risk-on backdrop.
5. **VIX term structure** — backwardation is a warning; contango is normal.
6. **Dealer positioning** (opex weeks) — pin levels and gamma walls matter more than macro on opex week.

## Key correlations

- Positively correlated with: [[NQ]] (r≈0.9 intraday), [[YM]], [[RTY]], BTC during risk-on, high-yield credit (HYG).
- Negatively correlated with: [[ZN]] / [[ZB]] (typical flight-to-quality), DXY (often), gold (often), VIX.
- Lead/lag: credit spreads often lead equities by 1–3 days around risk-off turns.

## Recurring patterns

- **Sell-the-rip in bear regimes, buy-the-dip in bull regimes** — the simplest regime-fit rule that works.
- **Turn-of-month/year flows** — systematic flows (pension rebalance) produce predictable pressure late in rebalance windows.
- **Opex week dynamics** — pinning at large gamma strikes; post-opex Monday often reverses.
- **FOMC drift** — the session before FOMC tends to be quiet; post-statement rips/dumps are common and often reverse within 48h.
- **NFP Friday** — initial reaction often retraces ~50% within 30 min.

## Common setups

1. **Regime-trend continuation.** Daily close above 50-day MA in a rising-breadth tape → long via call spread or outright with 1.2× ATR stop. Exit at 2R or trend break.
2. **Opex pin.** High call wall + low VIX term backwardation → iron condor around the pin strike, 5–10 DTE.
3. **Event window fade.** After FOMC/CPI, first-30-min direction often reverses. Small, defined-risk fade with tight stop.
4. **Gap-fill plays.** Large overnight gaps (> 0.75%) tend to partially fill in RTH — high-probability intraday move.

## Classic traps

- **Buying a breakout into a downtrend.** Counter-trend "breakouts" in bear regimes are stop-runs.
- **Fading strong trend days.** Wide-range trend days extend further than feel right; don't counter-trade 3+ standard deviation days.
- **Overnight gaps before CPI/NFP** — don't hold unhedged overnight into known binary prints.
- **Opex Friday afternoon** — volume dries up, spreads widen, pins become magnets; do not initiate new trades in the last 90 min.

## Liquidity profile

- Average daily volume: ~1.5–2.5M contracts on the front month.
- Spreads: typically 0.25 (one tick); can widen around open/close and events.
- Best fills: RTH (8:30 AM ET — 3:00 PM CT).
- Overnight liquidity: plenty except the 30 min surrounding the daily break.

## Options on /ES

- Weekly expirations: Mon/Wed/Fri (very liquid).
- Monthly: third Friday, AM-settled European-style.
- Quarterly EOM: last trading day, PM-settled.
- 0DTE: extremely liquid but pure vol-crush/gamma-squeeze territory — do NOT trade outright; defined-risk structures only.
- Typical IV rank: 20–50 in quiet regimes, 60–90 in crisis.
- Pin risk real at round strikes with high open interest.

## Risk notes

- Gap risk: Sunday open can gap 2–3% on weekend news; never be unhedged into major weekend news.
- Circuit breakers: 7% / 13% / 20% daily moves trigger halts.
- Worst weekly moves recent years: −12% (Mar 2020), −8% (Oct 2022), −5% on multiple CPI prints.
- Tail risk: compressed vol + long-gamma dealer hedging can mask building risk; monitor VIX + term structure.

## References

- CME: https://www.cmegroup.com/markets/equities/sp/e-mini-sandp500.html
- SpotGamma / SqueezeMetrics for dealer positioning (paid, optional).
- FedWatch tool for rate expectations: https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html
