---
type: catalog
status: ACTIVE — living document
purpose: Canonical list of strategy concepts for the IB workstream. Shared library (futures-compatible) + IB-specific (equities + options).
updated: 2026-05-17
---

# IB strategy catalog

The IB workstream can run THREE buckets of strategies:

## Bucket 1 — Shared library (works on equities AS-IS)

The 36 strategies in `tools/backtest/strategies.py` are pure-bar logic. They work on ANY OHLCV bar series — futures, equities, ETFs, FX. When IB Phase 2 (historical backfill) pulls equity bars, these can be backtested unchanged. Examples that translate well:

| Strategy | Notes for equities |
|---|---|
| `narrow_range_break` | Works on stocks. Hit rate may differ vs futures. |
| `pivot_reversal` | Works on stocks, especially ETFs at intraday pivots. |
| `vol_spike_fade` | Same on equities — volume spikes at exhaustion fade well. |
| `inside_bar_break` | Same. |
| `bollinger_mean_reversion` | Same, and historically WORKS better on ETFs than futures. |
| `keltner_breakout` | Same. |
| `keltner_channel_revert` | Same. |
| `rsi2_extreme_reversion` | Originally designed for stocks (Larry Connors). Works. |
| `support_resistance_bounce` | Works on stocks, especially at psychological round numbers. |
| `donchian_revert` | Works. |
| `volume_spike_reversal` | Works. |

Most things that look like trend / breakout / mean-reversion patterns translate broker-agnostically.

## Bucket 2 — IB-specific equity strategies (in `tools/backtest/ib_strategies.py`)

These exploit mechanics that DON'T exist on futures (overnight gaps, earnings releases, etc.):

| Strategy | Trigger | Best for |
|---|---|---|
| `overnight_gap_continuation` | 0.5%+ overnight gap + session open → enter direction of gap | Large-cap stocks with news flow, ETFs at major opens |
| `etf_oversold_revert` | RSI-2 ≤ 10 → long, hold ~5 days | SPY, QQQ, IWM, sector SPDRs; classic Connors |
| `post_earnings_drift` | 3%+ overnight gap on daily bars → ride drift for 3 days | Large-caps with earnings 4×/yr |
| `opening_drive` | First N bars of session move ≥ 0.75 ATR → ride momentum | SPY/QQQ during active markets |

Future additions to consider (when we have more data):
- **Dividend ex-date fade** — stocks fall by ~div amount on ex-date, often overshoot, mean-revert
- **Sector rotation pair trade** — XLK vs XLF / XLE etc. relative strength
- **Index inclusion/exclusion** — index funds buy/sell mechanically on S&P 500 add/remove
- **Russell rebalance** — Russell 2000 rebalancing creates predictable volume
- **Buyback announcement drift** — similar to PEAD but for buyback news

## Bucket 3 — Options strategies (NOT YET BUILT)

Options strategies require infrastructure we don't have yet:
- **Black-Scholes pricing** + greeks (delta, gamma, theta, vega)
- **IV surface** tracking + term structure
- **Multi-leg position P&L** (an iron condor is 4 legs)
- **Strike + expiry selection** algorithms
- **Margin/buying-power** calculation (different from futures notional)
- **Assignment risk** management (American-style options can be assigned anytime)

When we build this — likely AFTER Combine pass + IB Phase 2 backfill — the strategies to design first:

### Premium-selling (high probability, capped reward)

| Strategy | Mechanic | Use case |
|---|---|---|
| **Cash-secured PUT** | Sell ATM/OTM put on stock you want to own, collect premium | Generates income; if assigned, you get the stock at a discount |
| **Covered call** | Long stock + sell OTM call | Income on positions you're holding; caps upside |
| **Iron condor** | Sell ATM call spread + ATM put spread | Theta capture on range-bound names (SPY weekly is classic) |
| **Calendar spread** | Sell near-term + buy longer-term same strike | IV term-structure plays; benefits from IV crush after events |
| **Vertical credit spread** | Sell ATM, buy OTM same expiry | Defined risk; high hit rate; collects premium |

### Directional / volatility

| Strategy | Mechanic | Use case |
|---|---|---|
| **Long straddle pre-earnings** | Buy ATM call + put before earnings | Bets on IV expansion + big move (long vega) |
| **Short straddle post-earnings** | Sell ATM call + put after earnings | IV crush capture; high theta decay |
| **Long calls on momentum** | Replace shares with deeper-OTM calls | Leveraged directional bet; limited risk |
| **Protective puts** | Long stock + long ATM put | Insurance during volatile periods |

### Multi-leg structures (advanced)

| Strategy | Mechanic | Use case |
|---|---|---|
| **Iron butterfly** | Sell ATM straddle + buy OTM wings | Tight range expectation |
| **Broken-wing butterfly** | Unbalanced butterfly with asymmetric risk | Skew the P&L profile |
| **Diagonal spread** | Sell short-term OTM + buy LEAPS | Long-term directional + theta collection |
| **Ratio spread** | More short legs than long | High premium income with directional risk |

## Bucket 4 — IB-specific equity research targets

When we have IB historical bar data (Phase 2), specific research questions worth exploring:

1. **Multi-regime validation** — IB gives 10+ years. Run our 36 strategies × SPY/QQQ/IWM bars across 2008 financial crisis, 2020 COVID crash, 2022 Fed tightening, 2024 rally. Which strategies survive ALL regimes?
2. **Sector vs broad-market** — does `narrow_range_break` work on XLK (tech sector ETF) better than on SPY (broad)? Sector concentration may create cleaner signals.
3. **Small-cap vs large-cap** — IWM (small) vs SPY (large) — same strategies, different alpha profiles. Some strategies (mean-revert) work better on volatile small caps; others (trend) work better on smoother large caps.
4. **Pair trading** — do MSFT vs GOOG mean-revert when spread > 2σ? Pair trading is a classic stat-arb that requires two correlated instruments (impossible to test on single-instrument futures).
5. **Friday close fade for equities** — different mechanism than grain Friday fade. Equity institutional rebalancing happens Friday afternoon.

## Bucket 5 — Cross-broker learnings (Topstep ↔ IB)

Things to track that flow both ways:

| Direction | What |
|---|---|
| Topstep → IB | Strategies that survive Topstep's tight $150 risk cap also survive IB's smaller-position-size constraint. If a strategy needs $500+ per trade to be meaningful, it's a non-starter on either. |
| Topstep → IB | The 3 backtest fixes (min_stop_ticks floor + gap_fill session boundary + exec_mirror friction) apply to BOTH workstreams — same engine. |
| IB → Topstep | Multi-regime walk-forward on 10yr IB equity data tells us if a futures strategy's edge is regime-specific or robust. |
| IB → Topstep | If a mean-revert strategy works great on SPY but fails on ES futures, that's a clue about market structure differences (cash equity microstructure vs futures). |

## Knowledge flow rules

- Findings unique to ONE workstream: write under `vault/ib/research/` or `vault/futures/research/`
- Findings applicable to BOTH: write under `vault/research/` (top-level) and cross-link
- Strategy code that works on both: stays in `tools/backtest/strategies.py`
- Strategy code unique to IB (equities or options): goes in `tools/backtest/ib_strategies.py`
- Future option pricing infrastructure: planned `tools/options/` (greeks, BS, multi-leg)

## Open questions to revisit

1. When do we build the options pricing infrastructure? (Estimate: 2-3 day project; needs user direction)
2. Do we want a separate `IB_STRATEGY_REGISTRY` (currently isolated) or merge into the main `STRATEGY_REGISTRY`? Current decision: separate, to prevent accidentally running equity strategies against futures bars.
3. Should IB Phase 2 historical backfill prioritize stocks, ETFs, or both? Probably broad ETFs first (SPY/QQQ/IWM/XL*) since they have the cleanest signal density.
4. What's the budget for IB market data subscriptions? (Real-time L1 quotes typically $1.50-15/mo per exchange). Delayed data is free and sufficient for backtesting.
