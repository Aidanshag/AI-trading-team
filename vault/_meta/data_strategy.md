---
type: data_strategy
created: 2026-05-09
purpose: Define the fund's data sources, what we pay for vs don't, and what would justify upgrading
---

# Data strategy — the $0 path

The fund's data philosophy: **use what we have, accumulate what we can, only pay when there's measurable evidence the cost will be repaid in P&L improvement.**

## What we have access to (free)

### 1. Topstep ProjectX API — `tools/projectx_client.py`
- **Cost**: $0 (covered by Topstep Combine subscription, which we pay for the trading infrastructure)
- **Resolution**: 1-second to daily bars, all CME futures contracts
- **Format**: `client.get_bars(contract_id, start_time, end_time, unit, unit_number, limit)`
- **Validated 2026-05-08**: matches yfinance 100% on closes (998/998 in last 7d on ZN); Topstep is the source of truth for our actual broker
- **Use for**: backtests, live signal generation, intraday data

### 2. yfinance — `yf.download()`
- **Cost**: $0 (open source)
- **Resolution**: 1m to daily bars; intraday limited to ~60 days history
- **Use for**: backup when Topstep API is unavailable; quick exploratory work

### 3. Accumulated live fill data — `state/fund.db:orders`
- **Cost**: $0 (we generate it)
- **What it gives us**: REAL slippage, REAL fill quality, REAL latency on YOUR account at YOUR size
- **Why this is BETTER than tick data**: synthetic tick data tells you what *theoretically* should happen; your accumulated fills tell you what *actually* happens at your trade size on Topstep specifically.
- **Reader**: `scripts/slippage_tracker.py` — populates `vault/research/live_slippage/<date>_per_cell.md`
- **Maturity**: useful after ~30 fills per cell (~3-4 weeks of trading)

### 4. Macro / fundamental data
- FRED (Federal Reserve Economic Data): **free** — we pull rates levels, VIX, dollar indices via `scripts/fetch_fred_macro_levels.py`
- US Treasury Direct API: **free** — auction calendar
- Federal Reserve calendar JSON: **free** — speakers / events
- Combined into `vault/_meta/macro_brief_<date>.md` daily

## What we don't pay for (and why)

| Data type | Typical cost | Why we skip |
|---|---|---|
| **CME tick-by-tick data** (Databento/dxFeed/Polygon) | $200+/mo | Topstep bars + accumulated fills cover us at fund's current size |
| Real-time Level 2 / order book | $100-500/mo | We're a 1-5 contract trader; book depth matters for size that moves the market |
| Premium financial news APIs | $50-200/mo | News calendars are free; news ANALYSIS we'd want to handcraft anyway |
| Bloomberg Terminal | $2,000+/mo | Comically out of scope |
| Charting platforms (TradingView Pro, etc.) | $15-60/mo | We build charts via matplotlib if needed |
| Stock-specific data (Polygon equities) | $29-99/mo | Stock not in scope |

## When upgrading would be justified

We only spend money on data when there's **measurable evidence** the cost will be repaid:

1. **Tick data** ($200/mo) becomes worth it if we discover that bar-resolution backtest is materially diverging from live fills AFTER 30+ days of accumulated fill data. Currently we have 0 evidence of this.
2. **Real-time Level 2** ($100/mo) becomes worth it if we run a maker strategy where book depth determines entry quality. Not in current scope.
3. **Faster news feeds** become worth it if we add an event-driven strategy with sub-second reaction requirement. Not in current scope.

The pattern: don't pay for capability we haven't shown we need. Solve with free data + accumulated own-fills until that's no longer enough.

## Data quality concerns we monitor

- **yfinance vs Topstep divergence**: confirmed minimal as of 2026-05-08; recheck monthly
- **Bar boundaries vs. session opens**: 5m bars don't always align with 9:30 ET RTH; documented in regime classifier
- **Holiday / half-session handling**: Topstep API correctly returns reduced data; backtest assumes continuous which can mislead
- **Timezone consistency**: project uses ET as canonical local; UTC for storage; verified in `tools/trader_utils.py`

## What we accumulate over time (free)

This is the actual long-term moat:

- Per-cell live R-multiples (vs OOS predictions)
- Per-symbol slippage profiles
- Per-time-of-day slippage profiles
- Per-regime fill quality data (when regime classifier is wired in)
- Order rejection patterns
- Latency distributions
- Failed-fill scenarios

After 6-12 months of accumulated data, we have a slippage / friction model that NO purchased dataset can match — because it's specific to our broker, account size, and order patterns.

## Resolution upgrades available at $0 cost (immediate)

`tools/bar_fetcher.py` currently fetches 5-min bars. We can upgrade to 1-min bars from Topstep API at zero cost:
- 5x more granularity
- Better entry/exit timing precision in backtest
- Catches intra-bar volatility 5m bars miss

Limit consideration: 1-min over 60 days = ~25,920 bars per symbol. ProjectX limit per request = 1000 bars. So pagination required (~26 requests per symbol).

## Files / scripts that consume data

| Consumer | Reads from | Output |
|---|---|---|
| `scripts/live_trader.py` | Topstep API real-time | Trades |
| `scripts/backtest_*.py` | yfinance (currently) → migrate to Topstep API | Backtest results |
| `scripts/daily_strategy_validation.py` | yfinance → migrate to Topstep API | `state/strategy_validation.json` |
| `scripts/slippage_tracker.py` | `state/fund.db:orders` | `vault/research/live_slippage/` |
| `scripts/fetch_fred_macro_levels.py` | FRED API | `vault/_meta/macro_levels.json` |
| `scripts/fetch_treasury_auctions.py` | Treasury Direct API | `vault/_meta/auctions.json` |
| `scripts/fetch_fed_speakers.py` | Fed JSON calendar | `vault/_meta/fed_speakers.json` |

## Net cost summary

**Annual data spend**: $0

**What we get**:
- Topstep bars (1s to daily) on any CME futures
- All free macro / fundamental sources
- Accumulating live fill data (will be the best slippage model after 6 months)

**What we'd get for $200/mo ($2,400/yr)**:
- Tick-level CME data
- Probably ~5% better backtest fidelity, which translates to maybe 0.5% better risk-adjusted returns
- $2,400/yr cost vs. $250-500/yr expected return improvement on our current capital → bad ROI

**Upgrade trigger**: when we have $500K+ at risk AND a strategy whose edge depends on sub-bar timing.
