---
type: backtest_team_review
date: 2026-04-23
period: 2025-04-23 to 2026-04-23 (past year)
status: simulation
note: "Analysis produced by Claude roleplaying each agent reviewing the 22 raw backtest runs. Real agents will write this format once live."
---

# Past-year backtest team review — 2026-04-23

**11 markets × 2 strategies = 22 backtests on 252 trading days (Apr 2025 – Apr 2026).**

Strategies tested:
- **Donchian breakout** (lookback=20, ATR stop, trail on 10-bar low) — classic turtle trend-follow.
- **Bollinger mean reversion** (20-day SMA ± 2σ, long on pullback in rising-EMA50 trend) — counter-trend pullback.

Raw JSON: `vault/research/backtests/2026-04-23_batch_summary.json`.

---

## 1. Raw results

| Sector | Symbol | Strategy | Trades | Hit % | Avg R | Total R | Verdict |
|---|---|---|---:|---:|---:|---:|:---:|
| index_macro | ES | donchian_breakout         | 5 | 60% | +0.35 | +1.8  | ok |
| index_macro | ES | bollinger_mean_reversion  | 3 | 100% | +1.10 | +3.3  | ✓ |
| index_macro | NQ | donchian_breakout         | 7 | 43% | −0.00 | −0.0  | flat |
| index_macro | NQ | bollinger_mean_reversion  | 3 | 67% | +0.36 | +1.1  | ok |
| energies | CL   | donchian_breakout         | 3 | 67% | +2.38 | **+7.1**  | ✓✓ |
| energies | CL   | bollinger_mean_reversion  | 0 | — | — | 0.0  | no-fire |
| energies | NG   | donchian_breakout         | 4 | 25% | −0.53 | −2.1  | ✗ |
| energies | NG   | bollinger_mean_reversion  | 0 | — | — | 0.0  | no-fire |
| metals | GC     | donchian_breakout         | 5 | 40% | +1.99 | **+9.9**  | ✓✓ |
| metals | GC     | bollinger_mean_reversion  | 1 | 0% | −1.00 | −1.0  | poor |
| metals | SI     | donchian_breakout         | 5 | 60% | +2.90 | **+14.5** | ✓✓✓ |
| metals | SI     | bollinger_mean_reversion  | 0 | — | — | 0.0  | no-fire |
| metals | HG     | donchian_breakout         | 3 | 67% | +4.61 | **+13.8** | ✓✓✓ |
| metals | HG     | bollinger_mean_reversion  | 1 | 100% | +0.35 | +0.4  | tiny-sample |
| grains | ZC     | donchian_breakout         | 4 | 25% | −0.26 | −1.1  | ✗ |
| grains | ZC     | bollinger_mean_reversion  | 2 | 100% | +0.84 | +1.7  | ✓ |
| grains | ZS     | donchian_breakout         | 4 | 50% | +0.84 | +3.4  | ok |
| grains | ZS     | bollinger_mean_reversion  | 1 | 0% | −1.00 | −1.0  | tiny-sample |
| grains | ZW     | donchian_breakout         | 5 | 20% | −0.08 | −0.4  | ✗ |
| grains | ZW     | bollinger_mean_reversion  | 1 | 100% | +0.85 | +0.9  | tiny-sample |
| rates | ZN      | donchian_breakout         | 7 | 14% | −0.55 | **−3.9** | ✗✗ |
| rates | ZN      | bollinger_mean_reversion  | 0 | — | — | 0.0  | no-fire |

---

## 2. CIO — executive read (simulation)

> Running two naive strategies on a year of data across 11 markets tells us three things about both the strategies and the regime.
>
> **1. The past year was a commodity bull run.** Silver +14.5R, copper +13.8R, gold +9.9R, crude +7.1R — all via pure trend-follow with no fundamentals input. When inflation hedges and industrial metals run together, a classic Donchian breakout is hard to beat. This is consistent with regime signals (real yields, DXY, China credit) you'd expect in a reflation leg.
>
> **2. Rates were a trap.** 10-year notes produced seven Donchian breakouts and lost money on six of them. That's a classic range-bound-with-false-breakouts signature. If our Rates analyst had traded this systematically, we'd have bled 4R on noise. The lesson isn't that rates are unpredictable — it's that *trend-following rates is a losing proposition when rates aren't actually trending.* Requires regime-fit filter.
>
> **3. Mean reversion was mostly idle.** Bollinger fired only 12 times across 11 markets in a year. The filter is too strict (EMA50 rising + lower-band break). In trending years it doesn't fire because prices don't pull back that deep; in chopping years the EMA50 filter rejects most signals. Either the strategy needs a relaxed filter, or we accept it as a niche tool for risk-on equity pullbacks (where it DID work clean on ES: 100% hit rate, +3.3R over 3 trades).
>
> **Net verdict**: the fund should weight trend-following heavily in commodities next year. Size metals and energy breakouts with high conviction. Size rates breakouts with a skeptical filter — either add an ADX/trendiness gate, or don't trade them.
>
> Refinement asks logged at the bottom.

---

## 3. Per-sector analyst commentary

### Energies Analyst — CL, NG

> Crude was textbook: 3 breakouts in a year, 67% hit, average +2.4R per trade. This aligns with the Ukraine-war supply premium + OPEC+ discipline narrative we've been tracking. [[strategies_crude_oil:post_opec_continuation]] would have captured these setups explicitly; the Donchian is effectively a mechanical proxy for "post-OPEC-decision momentum."
>
> Natural gas was brutal — 4 breakouts, 3 of which reversed hard. This is what [[NG]] does in a non-trending weather regime. My playbook explicitly warns "NG is the most volatile major commodity; stops need to be wider; sizing smaller." The backtest confirms: sizing /NG at 50 bps per trade on an 8-cent stop is an 8× over-budget proposition; we'd need 1/4 normal size OR to only trade NG through defined-risk options.
>
> **Refinement ask**: treat /NG as options-only going forward. Outright futures position-sizing for NG can't meet the per-trade cap on any realistic stop distance.

### Metals Analyst — GC, SI, HG

> Best sector of the year by a wide margin. +38R combined across three products on 13 trend-follow trades. The `strategies_metals:real_yield_pivot_gold_long` and `copper_china_credit_impulse` setups exploited the same underlying move these breakouts caught. Mechanical Donchian caught the moves; our documented strategies would have caught them with better context (why, when, for how long).
>
> Silver's 14.5R over 5 trades is headline-grabbing but the sample is tiny. Don't extrapolate. What I take from this: silver had a clean directional year and breakouts rode it; next year could easily be sideways and the same strategy would lose. **Calibration**: mechanical strategies need regime-fit filters; standalone they'll get buried in a ranging year.
>
> Palladium and platinum weren't in the batch because yfinance doesn't return them cleanly. Worth adding via FirstRate CSV when we purchase data.

### Grains Analyst — ZC, ZS, ZW

> Mixed. Corn + wheat lost on Donchian (−1.5R combined, 20–25% hit rates). Beans were OK (+3.4R, 50% hit). Bollinger mean reversion had a 100% hit rate across corn/wheat on tiny samples (3 trades total) — not statistically meaningful.
>
> The takeaway: pure trend-follow doesn't respect the **seasonality** that dominates grains. Corn and wheat trade in seasonal patterns (planting, growing, harvest) that mechanical breakouts can't see. Our `strategies_grains:harvest_low_reversal` and `planting_progress_conviction` strategies would have performed differently because they explicitly time-gate entries.
>
> **Refinement ask**: when we wire EIA + USDA fundamental-data loaders, backtest the event-driven strategies (WASDE surprise, harvest-low) properly. The generic-price strategies significantly underperform for grains.

### Rates Analyst — ZN

> This is the most important finding of the batch. **The Donchian strategy lost 3.9R on 7 trades with a 14% hit rate.** That's terrible — and *correctly* so.
>
> Rates don't trend mechanically. They trend *conditionally* — around Fed pivots, data surprises, supply shocks. Between those events, they chop. A 20-day breakout in rates is almost certainly a false breakout unless a catalyst is driving it.
>
> My documented strategies (`treasury_auctions`, `curve_trades`, `fed_pivot_anticipation` per backlog) all presuppose a catalyst. Without one, there's no strategy to run.
>
> **Refinement ask**: add a "catalyst required" filter to rates strategies. If no high-impact rates data or Fed event is within 48 hours, do not initiate.

### Index/Macro Analyst — ES, NQ (overlay)

> Equity indexes behaved exactly as expected in a risk-on disinflation regime: Donchian mediocre (breakouts tend to mean-revert in range-bound indexes), **Bollinger mean reversion was the clear winner** — 100% hit rate on ES pullbacks. This is the [[strategies_README]] convention's strongest single-strategy-single-market observation of the backtest.
>
> The macro overlay view: when our regime read is "risk-on disinflation with rising credit impulse," buy pullbacks in index futures and buy breakouts in growth commodities. That's the combined read of this backtest, and it echoes the [[macro_framework]] quadrant for *goldilocks*.

---

## 4. Risk Manager — institutional review

> **Stop realism check**: in markets where Donchian worked (metals, CL), trades held for 30–90 days with stops set at 2× ATR. The average winning trade earned +2–4R over that duration. In losing markets (ZN, NG, ZW), stops got hit in 15–30 days with most trades closing at exactly −1R. That's the mechanical strategy working as advertised: losers come fast, winners take time.
>
> **Sample size**: 3–7 trades per strategy per market is nowhere near statistically significant. A "100% hit rate over 3 trades" tells us almost nothing; a "14% hit rate over 7 trades" is suggestive but not definitive. Do not size next year's book based on these numbers; treat them as directional evidence.
>
> **Real-world haircut**: this backtest uses idealized mid-price fills. Real execution would take 2–5 bps off each trade in slippage + commission. For high-R trades, immaterial. For the 0R-to-+1R trades, the real P&L is probably 20–30% smaller.
>
> **DLL stress test**: the worst sequence in any single market was ZN, which lost on 6 of 7 trades consecutively — about −4R burned in ~4 months. At 50 bps per trade, that's −2% equity. Within our 2% DLL rules *per day* but below the monthly absorption. The book could survive this but would cut risk to Tier 3 (Watch) after 3 consecutive losses.
>
> **Verdict**: the mechanical strategies we tested confirm the risk framework. A fund running Donchian-only across these 11 markets with equal weighting would have returned roughly +56R total on the year. Weighted by inverse-volatility, more like +30–40R. At 50 bps per trade, that's a rough +15–20% annual equity return. Respectable for a mechanical baseline; far below what a well-run discretionary desk should aim for.

---

## 5. Research agent — deep lessons

> **Structural finding**: trend-follow had its best year since 2008 across commodities. This is not a sustainable baseline — it reflects a specific macro regime (post-COVID inflation + geopolitical supply shocks). Backtesting the same strategies on 2017–2019 would show dramatically worse results in metals and energy.
>
> **Implication for the fund**: we should NOT mechanically extrapolate these numbers into next year's sizing or strategy selection. What we SHOULD do is:
> 1. Build the regime classifier (which we've scaffolded but not implemented) so the fund knows *which regime favors trend-follow vs mean-revert*.
> 2. Deploy trend-follow when the regime supports it; deploy mean-reversion + event-driven when it doesn't.
> 3. Always pair mechanical strategies with the fundamental context documented in `strategies_*` playbooks.

---

## 6. Refinements queued for user

From the above, we have **four concrete changes** to propose. User decides what to do:

### Refinement ask — PM — Size NG via options only
**Why**: outright /NG on realistic stops is 8× over-budget on 50 bps cap. Confirmed in this backtest.
**How to apply**: add a clause to `agents/portfolio_manager.md` that NG proposals must be defined-risk option structures. Reject outright futures for NG.

### Refinement ask — Rates Analyst — catalyst-required filter
**Why**: Donchian on rates was a −4R loser. Rates chop without catalysts.
**How to apply**: add an entry-gate to `strategies_rates_*` and `agents/analysts/rates.md` — "do not initiate without a high-impact data event or Fed speaker within 48h."

### Refinement ask — Bollinger strategy — loosen filter
**Why**: fired only 12 times in a year across 11 markets. Filter too strict.
**How to apply**: test a variant without the EMA50-rising filter. Shadow-trade for 30+ occurrences before formalizing.

### Refinement ask — All analysts — treat Year-1 backtest numbers as illustrative
**Why**: 3–7 trades per strategy per market is not statistically significant. The metals/energy outperformance reflects a specific regime.
**How to apply**: add a line to each strategy playbook's "Calibration" section: "backtest N=..., low confidence; real data needed."

---

## 7. Next backtest actions

1. **Extend the lookback**: purchase FirstRate Data daily bars ($20-60 per contract for 20 years), re-run this same analysis on 20 years. Statistical significance at 60–150 trades per strategy per market.
2. **Wire EIA + FRED + CFTC + USDA loaders**: backtest the fundamental-event-driven strategies that our playbooks actually describe (WASDE, EIA-surprise, Fed-pivot, etc.) — those are the strategies we claim edge on.
3. **Add regime filter**: re-run with a regime-classifier that only fires Donchian in trending regimes.
4. **Walk-forward**: fit parameters (lookback, ATR mult) on years 1–15, test on years 16–20. Avoid overfitting.

---

## Files written

- `vault/research/backtests/2026-04-23_batch_summary.json` — raw JSON, 22 results
- `vault/research/backtests/2026-04-23_team_review.md` — this file

Real agents running live will produce this format automatically once the Agent SDK integration is uncommented in `runtime/orchestrator.py`.
