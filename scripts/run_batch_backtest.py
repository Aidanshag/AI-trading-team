"""Run all strategies against all major markets for the past year.

Produces markdown reports under vault/research/backtests/ + a summary
table aggregating the results.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tools.backtest.data import load_bars
from tools.backtest.engine import backtest_strategy
from tools.backtest.metrics import summary_stats
from tools.backtest.strategies import STRATEGY_REGISTRY

# 11 major liquid futures (yfinance continuous-contract symbols)
MARKETS = [
    ("ES=F",  "E-mini S&P 500",        "index_macro"),
    ("NQ=F",  "E-mini Nasdaq 100",     "index_macro"),
    ("CL=F",  "Crude Oil WTI",         "energies"),
    ("NG=F",  "Natural Gas",           "energies"),
    ("GC=F",  "Gold",                  "metals"),
    ("SI=F",  "Silver",                "metals"),
    ("HG=F",  "Copper",                "metals"),
    ("ZC=F",  "Corn",                  "grains"),
    ("ZS=F",  "Soybeans",              "grains"),
    ("ZW=F",  "Wheat",                 "grains"),
    ("ZN=F",  "10-Year T-Note",        "rates"),
]

STRATEGIES = ["donchian_breakout", "bollinger_mean_reversion"]

end = datetime.now(tz=timezone.utc).date()
start = end - timedelta(days=365)

OUT_DIR = Path("vault/research/backtests")
OUT_DIR.mkdir(parents=True, exist_ok=True)

all_results = []

for symbol, name, sector in MARKETS:
    try:
        print(f"Loading {symbol} ({name})...", flush=True)
        bars = load_bars(symbol, str(start), str(end), source="yfinance")
        print(f"  loaded {len(bars)} bars", flush=True)
    except Exception as e:
        print(f"  FAIL: {e}", flush=True)
        continue

    for strat_name in STRATEGIES:
        strat = STRATEGY_REGISTRY[strat_name]
        try:
            result = backtest_strategy(strat, bars, symbol=symbol)
            stats = summary_stats(result)
            stats["sector"] = sector
            stats["market_name"] = name
            all_results.append(stats)
            print(f"  {strat_name:<30}  trades={stats['n_trades']:>3}  "
                  f"hit={stats.get('hit_rate',0):.0%}  "
                  f"avg_R={stats.get('avg_r',0):+.2f}  "
                  f"total_R={stats.get('total_r',0):+.1f}", flush=True)
        except Exception as e:
            print(f"  {strat_name}: EXCEPTION {e}", flush=True)

# Write the aggregate summary
summary_path = OUT_DIR / f"{end.isoformat()}_batch_summary.json"
summary_path.write_text(json.dumps(all_results, default=str, indent=2))
print(f"\nAggregate JSON: {summary_path}")
print(f"Total results: {len(all_results)}")
