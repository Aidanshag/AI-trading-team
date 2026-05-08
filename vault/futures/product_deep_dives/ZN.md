---
type: product_deep_dive
symbol: ZN
sector: rates
analyst: seed (Claude)
updated: 2026-04-23
---

# [[ZN]] — 10-Year Treasury Note

## Contract specs

- Exchange / product: CBOT, 10-Year US Treasury Note (ZN)
- Tick size: 1/64 point = $15.625 per tick (half-tick in front month at times)
- Contract multiplier: $100,000 face value
- Contract months: quarterly Mar/Jun/Sep/Dec
- Session hours: Sun 17:00 CT → Fri 16:00 CT, 1-hr daily break
- Last trading day: 7th business day preceding last business day of contract month
- Settlement: physical (deliverable basket of eligible Treasury notes)
- Margin at Topstep: ~$2K initial (verify — rates margin is low)

Also on the curve: [[ZT]] (2Y), [[ZF]] (5Y), [[ZB]] (30Y), [[UB]] (Ultra).

## What it actually is

The benchmark US intermediate Treasury future. The "belly of the curve" — what the market uses to express view on the Fed's 12-24 month rate path. Deliverable basket means the CTD (cheapest-to-deliver) drives pricing; basis traders and hedgers run large books around the CTD.

## Primary drivers

1. **Fed policy path** — near-term rate decisions, dots (quarterly SEP), forward guidance.
2. **Macro data** — CPI, NFP, ISM, retail sales. Rates move more on data surprises than any other asset class.
3. **Inflation expectations (breakevens)** — 10Y breakeven = nominal yield − 10Y TIPS real yield.
4. **Treasury supply** — quarterly refunding announcements, auction cycle (2/5/7/10/30), bill-to-bond ratio.
5. **Foreign flows** — Japan/China holdings, sovereign-wealth activity, FX hedging costs for foreign buyers.
6. **Risk-off flight-to-quality** — ZN rallies on equity sell-offs typically, except in inflation-shock regimes where correlation inverts.

## Key correlations

- Positively: [[ZF]], [[ZB]], [[UB]] (duration instruments), long-duration equities (growth, REITs, utilities), gold in dovish regimes.
- Negatively: [[DXY]] in growth-led moves, banks (financials), commodities in reflationary regimes.
- Note: **rates-equity correlation is regime-dependent** — positive in disinflation (2009-2021), negative in inflation shock (2022).

## Recurring patterns

- **Pre-FOMC drift** — 2-3 days before FOMC, vol compresses.
- **Auction concessions** — the session before a 10Y auction often sees ZN weaken (concession building); post-auction bounce is a recurring setup when takedowns are strong.
- **NFP/CPI spike** — initial 30-min move is often extended, then retraces partially.
- **Quarter-end rebalance flows** — pension rebalancing late in the quarter produces predictable bid/offer pressure.
- **Fed-speak drift** — Chair speeches and influential FOMC members (vice chair, NY Fed president) move the belly.

## Common setups

1. **Data-surprise continuation.** CPI / NFP surprise > 1σ; wait 30 min, enter in direction of initial move if follow-through is clean; 1.5× ATR stop.
2. **Post-auction bounce.** After a strong 10Y auction (tail < 0.5 bp, bid-to-cover > 2.5), long ZN into the Asian session; close by end of following RTH.
3. **Curve trade (2s10s).** When the curve is at extreme steepness or inversion, trade the re-entry to mean via paired ZT/ZN or ZN/ZB spread. Size by DV01, not contracts.
4. **Fed-pivot anticipation.** When macro data flips but Fed communication hasn't caught up, position long ZN 1-2 weeks before likely pivot commentary.

## Classic traps

- **Fighting the Fed** — when the Fed is explicitly communicating a direction, leaning against it before data turns is a losing trade 4 times out of 5.
- **Ignoring the auction schedule.** Entering long before a 10Y auction with no concession risk estimate = surprise risk.
- **Trading ZN on equity logic.** Rates and equities can move together or opposite depending on regime. Don't assume risk-off = ZN long without checking the inflation axis.
- **Basis-related noise** — delivery month trading can produce weird intra-day moves due to CTD rolls; avoid new entries in the last 2 weeks of contract life.

## Liquidity profile

- Front-month volume: ~1.5M contracts daily.
- Spread: 0.5-1 tick typical (very tight).
- Best liquidity: 7:00–15:00 CT.
- Overnight: very liquid Asian session (sovereign wealth + BOJ-related flows).

## Options on /ZN

- OZN weekly and monthly.
- American-style, physical-settled (into futures).
- IV regime: typically 5-8 vol, spikes to 10-12 around big data.
- Common structure: risk-reversals around FOMC (sell upside/buy downside or reverse based on bias); iron condors in low-vol grind.

## Risk notes

- Low outright margin but high DV01 per contract; size is often larger than feels comfortable.
- Gap risk: moderate; weekend risk usually limited unless major Fed communication.
- No price limits in normal conditions.
- Worst moves: 2022 Fed hiking cycle produced sustained 30-50 bp/week yield moves = 2-4 points of ZN; 2023 SVB week saw a 30 bp single-day rally.
- Tail risk: Treasury liquidity stress events (Oct 2019, Mar 2020) produce disproportionate rate moves; watch repo markets.

## References

- Treasury auction schedule: https://www.treasurydirect.gov/auctions/auction-calendar/
- FRED DGS10 (10Y yield), T10YIE (10Y breakeven).
- Fed calendar and SEP: https://www.federalreserve.gov
- CME product page: https://www.cmegroup.com/markets/interest-rates/us-treasury/10-year-us-treasury-note.html
