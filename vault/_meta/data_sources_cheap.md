---
type: meta
updated: 2026-04-23
category: data_infrastructure
---

# Historical data on a student budget

For backtesting strategies in `vault/playbooks/strategies_*`, you need historical futures data. CME DataMine is institutional-priced ($$$). Here's the cheaper path.

## Tier 0: completely free

**These four, combined, cover ~60% of what you need to backtest:**

### yfinance (Python library)
- **What**: End-of-day OHLCV for continuous futures contracts (e.g., `CL=F`, `GC=F`, `ZC=F`, `ES=F`).
- **Price**: Free, via `pip install yfinance`.
- **Depth**: Many years of daily bars. No intraday.
- **Quality**: OK-ish. Continuous contracts are adjusted-rolled; not tick-accurate. Fine for strategy-shape validation, not for precise R-multiple calibration.
- **Gotcha**: rate-limited; don't scrape the whole futures complex in one shot.

### FRED (Federal Reserve Economic Data)
- **What**: Macro time series — rates (DGS10, DGS2, DFF), inflation (CPIAUCSL, breakevens), unemployment, money supply, credit spreads (BAMLH0A0HYM2), DXY, ISM series.
- **Price**: Free, API key-free for low-volume reads.
- **Depth**: Decades. Multiple frequencies (daily/weekly/monthly).
- **Fit for**: `strategies_metals:real_yield_pivot`, regime-classifier signals, macro backtests.

### CFTC Commitments of Traders
- **What**: Weekly positioning data for every major futures contract (specs, commercials, managed money).
- **Price**: Free direct download from CFTC.gov.
- **Depth**: Decades.
- **Fit for**: Positioning-extreme signals across commodities + FX.

### EIA, USDA, NASS, CME public data
- **EIA** (eia.gov): Weekly petroleum inventories (crude, gasoline, distillate) + storage + production. Free API.
- **USDA / NASS**: WASDE, Crop Progress, Cold Storage, Cattle on Feed. All free historical.
- **CME public pages**: Settlement prices and volume summaries free (no tick data).

**Combined coverage**: government data + yfinance gets you every fundamental signal + daily OHLC for every major contract. Enough to validate 70% of the strategy library directionally. You'd miss intraday realism (ATR calibration, event-window behavior).

## Tier 1: one-time purchases (student-friendly)

### FirstRate Data (firstratedata.com)
- **What**: Historical tick and bar data for CME futures — sold as one-time downloads, not subscriptions.
- **Price**: Typical packages $20–$60 for 10–20 years of daily bars on one contract; $100–$300 for intraday on the major complex.
- **Depth**: 20+ years.
- **Quality**: Institutional-grade bars; cleanly continuous or individual contract months.
- **Strategy**: Buy one package covering /ES, /CL, /GC, /ZN for ~$200 total and you have decades of clean bars for your most-traded products. **This is probably the best value for a student.**

### Alpha Vantage free tier
- **What**: 5 API calls/min, 500/day for equities + some commodities (continuous contracts).
- **Price**: Free (Pro is $50/mo).
- **Depth**: Varies; generally recent years.
- **Use**: Supplementary intraday snapshots; not primary.

### Nasdaq Data Link (formerly Quandl)
- **What**: Free tier has CHRIS continuous-contract datasets + many economic series.
- **Price**: Free tier limited; Starter $30/mo.
- **Status**: Much reduced since Nasdaq acquisition; FRED + FirstRate usually beats it.

## Tier 2: low-cost subscriptions ($20–$60/mo)

### EOD Historical Data (eodhd.com)
- ~$20–$60/mo depending on tier.
- Global futures coverage end-of-day.
- Fine for daily-bar backtesting.

### Barchart cmdty
- ~$40–$80/mo for daily commodity historical.
- Solid for ag and energy complex.

## Tier 3: mid-cost ($50–$200/mo)

### Databento (databento.com)
- Starts ~$50/mo for CME daily data; ~$150/mo for intraday.
- Institutional-grade; the "right" answer if budget allows.
- Best for serious intraday backtesting.

## What I'd do on a student budget

**Phase 0 (free, now)**: Install `yfinance`. Pull the FRED series your regime-classifier needs. Download CFTC COT + EIA + USDA archives. Use these to validate 70% of strategies directionally and build your regime file.

**Phase 1 (~$100 one-time, when you want realism)**: Buy FirstRate Data daily-bar packages for /ES, /CL, /GC, /ZN (the four most-traded contracts). You now have 20+ years of clean daily bars for your core products.

**Phase 2 (only if needed)**: Add Databento intraday ($150/mo) once you're actually paper-trading and have a specific intraday calibration question the free data can't answer. Do not subscribe before you have that specific question.

**What to skip entirely on a student budget**:
- CME DataMine (institutional pricing, 10x overkill)
- Bloomberg / Refinitiv (enterprise tier)
- Any "alternative data" vendor promising alpha — they're selling noise to the desperate
- Dow Jones Newswires API ($$$$)

## Writing the backtest harness

Once you have data, the backtest module should live at `tools/backtest.py` with an interface like:

```python
from tools.backtest import backtest_strategy
results = backtest_strategy(
    strategy="strategies_crude_oil:eia_surprise_continuation",
    symbol="CL",
    start="2020-01-01",
    end="2025-12-31",
    data_source="yfinance",   # or "firstrate", "databento"
)
print(f"Hit rate: {results.hit_rate:.1%}")
print(f"Avg R: {results.avg_r:+.2f}")
print(f"Max DD: {results.max_drawdown:+.1%}")
```

The backtest harness is a ~200-line Python module. Build it once, then re-run it every time you tweak a strategy. Results feed the automated calibration update for `vault/playbooks/strategies_*`.

## Bottom-line recommendation

**$0 today**: free-tier government data + yfinance + build the regime classifier.
**~$100 one-time** when you're ready for realism: FirstRate Data daily bars on /ES /CL /GC /ZN.
**Add paid subscriptions only when you have a specific question the free data can't answer.**

This is lean and fits a student budget. It's also not worse than what many small systematic shops were running in 2010.
