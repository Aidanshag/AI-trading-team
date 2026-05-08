---
type: playbook
applies_to: [all_analysts, portfolio_manager, research]
source: Ed Seykota + the Turtles (Dennis / Eckhardt) + Dunn Capital + Man AHL + ManGLG systematic practice
---

# Trend following — the strategy that works because it follows discipline, not insight

Trend following is the most studied, most published, and most robust systematic strategy in commodities and futures. The edge is not discovering the trend; the edge is riding it with discipline through the drawdowns most humans can't tolerate.

## The five rules (Seykota / Turtles)

1. **Cut losses fast.** A single stop rule, mechanically applied. No exceptions.
2. **Let profits run.** Do not take a target prematurely. Use a trailing stop.
3. **Keep positions small.** Volatility-targeted so every trade risks the same dollars.
4. **Stick to the system.** Don't override based on "this one feels different."
5. **Manage risk at the portfolio level.** Correlated trades are one trade for sizing.

## The two things that hurt trend-followers

- **Chop** — sideways markets that whipsaw stops. Trend-followers underperform for months, sometimes years, in low-vol grind regimes.
- **Gaps** — stops get jumped. Real slippage is always worse than modeled slippage.

Both are the *cost* of access to the long tail of the distribution. The annualized returns come from a few huge trends per year; the rest is drag.

## When trend following wins

- Commodity bull runs (2008, 2022 energies, 2020 ags).
- Currency regime shifts (2022 DXY bull run; 2013 Abenomics JPY).
- Credit/rate cycle pivots (2008, 2022).
- Equity bear markets that trend (not choppy ones).

## When it loses

- Range-bound regimes with compressed vol (2017, 2019, much of 2023).
- Sharp reversals with no follow-through (post-pandemic 2020 flip).

## Signals the fund can use even without a pure trend system

Trend-following lives in the background of every futures desk. Our agents are discretionary-ish, but:

1. **20/50/200-day moving-average state** — every analyst tags their symbol's current trend state (up/flat/down) in the daily thesis.
2. **Donchian channel breakouts** — the classic turtle signal. A new 55-day high with expanding ATR is a high-conviction trend trigger.
3. **Volatility-adjusted momentum** — 3-month return divided by 3-month ATR. Rank this across symbols; longs go to top quintile, shorts (well, defined-risk shorts) to bottom quintile.

## When to defer to trend

- If you're proposing a mean-reversion trade against a strong trend (price > 20/50/200 MA all rising, positive momentum), your reward:risk needs to be ≥ 3:1. Counter-trend trades are fine in small size with tight stops; they are NOT fine with wide stops and loose targets.

## When to override trend

- Regime pivots: the macro framework may identify a regime change before the trend system does. Regime beats trend for entry timing, but trend beats regime for holding discipline.
- Event-driven: FOMC, CPI, etc. produce sharp moves that may or may not begin new trends; don't bet on the gap direction alone.

## Applied to the fund

- **Index/Macro analyst** maintains a weekly trend-state note for all tradeable symbols at `vault/futures/patterns/trend_state.md`.
- **PM** applies trend state as a size modifier: with-trend trades get standard size; counter-trend trades get 0.5× size.
- **Risk Manager** treats counter-trend setups as requiring stricter R:R.

## Seykota's closing thought

*"Everybody gets what they want out of the market."* If you want excitement, you'll get it and lose money. If you want discipline, you'll get a slower, less exciting P&L with drawdowns you can survive. Pick which one you actually want.
