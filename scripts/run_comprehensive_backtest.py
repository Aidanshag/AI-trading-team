"""Comprehensive batch: 5 strategies x 11 markets = 55 backtests.

Output: per-strategy + per-market scorecard, ranked by edge.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tools.backtest.data import load_bars
from tools.backtest.engine import backtest_strategy
from tools.backtest.metrics import summary_stats
from tools.backtest.strategies import STRATEGY_REGISTRY

MARKETS = [
    ("ES=F",  "E-mini S&P 500",   "index_macro"),
    ("NQ=F",  "Nasdaq 100",       "index_macro"),
    ("CL=F",  "Crude Oil",        "energies"),
    ("NG=F",  "Natural Gas",      "energies"),
    ("GC=F",  "Gold",             "metals"),
    ("SI=F",  "Silver",           "metals"),
    ("HG=F",  "Copper",           "metals"),
    ("ZC=F",  "Corn",             "grains"),
    ("ZS=F",  "Soybeans",         "grains"),
    ("ZW=F",  "Wheat",            "grains"),
    ("ZN=F",  "10-Year T-Note",   "rates"),
]

end = datetime.now(tz=timezone.utc).date()
start = end - timedelta(days=365)

OUT_DIR = Path("vault/research/backtests")
OUT_DIR.mkdir(parents=True, exist_ok=True)

all_results = []

print(f"Comprehensive backtest: {len(STRATEGY_REGISTRY)} strategies x {len(MARKETS)} markets")
print(f"Period: {start} to {end}")
print()

for symbol, name, sector in MARKETS:
    try:
        bars = load_bars(symbol, str(start), str(end), source="yfinance")
    except Exception as e:
        print(f"  {symbol}: FAIL load - {e}")
        continue

    for strat_name, strat_fn in STRATEGY_REGISTRY.items():
        try:
            result = backtest_strategy(strat_fn, bars, symbol=symbol)
            stats = summary_stats(result)
            stats["sector"] = sector
            stats["market_name"] = name
            all_results.append(stats)
        except Exception as e:
            print(f"  {symbol}/{strat_name}: ERR {e}")
            continue

# Print summary ranked by total R per strategy
print("\n=== STRATEGY EDGE RANKING (by aggregate total_R across all markets) ===")
strategy_aggregates: dict[str, dict] = {}
for r in all_results:
    s = r["strategy"]
    if s not in strategy_aggregates:
        strategy_aggregates[s] = {"trades": 0, "wins": 0, "losses": 0, "total_r": 0.0, "n_markets": 0}
    if r["n_trades"] > 0:
        strategy_aggregates[s]["trades"] += r["n_trades"]
        strategy_aggregates[s]["wins"]   += r.get("n_wins", 0)
        strategy_aggregates[s]["losses"] += r.get("n_losses", 0)
        strategy_aggregates[s]["total_r"] += r.get("total_r", 0)
        strategy_aggregates[s]["n_markets"] += 1

ranked = sorted(strategy_aggregates.items(), key=lambda kv: kv[1]["total_r"], reverse=True)
print()
print(f"{'Strategy':<28}{'Markets':>9}{'Trades':>9}{'WinRate':>10}{'TotalR':>10}{'AvgR/trade':>12}")
print("-" * 80)
for s, agg in ranked:
    wr = agg["wins"] / agg["trades"] if agg["trades"] else 0
    avg_r = agg["total_r"] / agg["trades"] if agg["trades"] else 0
    print(f"{s:<28}{agg['n_markets']:>9}{agg['trades']:>9}{wr:>10.0%}{agg['total_r']:>+10.1f}{avg_r:>+12.2f}")

# Save full results
out_path = OUT_DIR / f"{end.isoformat()}_comprehensive.json"
out_path.write_text(json.dumps(all_results, default=str, indent=2))
print(f"\nFull JSON: {out_path}")

# Save scorecard markdown
scorecard_path = OUT_DIR / f"{end.isoformat()}_strategy_scorecard.md"
lines = [
    "---",
    f"type: strategy_scorecard",
    f"date: {end.isoformat()}",
    f"period: {start} to {end} (1 year)",
    f"n_strategies: {len(STRATEGY_REGISTRY)}",
    f"n_markets: {len(MARKETS)}",
    "---",
    "",
    f"# Strategy Edge Scorecard — {end.isoformat()}",
    "",
    "## Strategy ranking (1-year performance, all markets aggregated)",
    "",
    f"| Rank | Strategy | Markets | Trades | Win Rate | Total R | Avg R/trade |",
    f"|---|---|---:|---:|---:|---:|---:|",
]
for i, (s, agg) in enumerate(ranked, 1):
    wr = agg["wins"] / agg["trades"] if agg["trades"] else 0
    avg_r = agg["total_r"] / agg["trades"] if agg["trades"] else 0
    lines.append(f"| {i} | {s} | {agg['n_markets']} | {agg['trades']} | "
                 f"{wr:.0%} | {agg['total_r']:+.1f} | {avg_r:+.2f} |")
lines.append("")
lines.append("## Per-strategy per-market detail")
lines.append("")
by_strategy: dict[str, list] = {}
for r in all_results:
    by_strategy.setdefault(r["strategy"], []).append(r)
for s, rows in by_strategy.items():
    lines.append(f"### {s}")
    lines.append("")
    lines.append("| Market | Trades | Win Rate | Avg R | Total R | Max DD R |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    rows_sorted = sorted(rows, key=lambda r: r.get("total_r", 0), reverse=True)
    for r in rows_sorted:
        if r["n_trades"] == 0:
            continue
        lines.append(
            f"| {r['symbol']} | {r['n_trades']} | "
            f"{r.get('hit_rate', 0):.0%} | "
            f"{r.get('avg_r', 0):+.2f} | "
            f"{r.get('total_r', 0):+.1f} | "
            f"{r.get('max_drawdown_r', 0):+.1f} |"
        )
    lines.append("")
lines.append("## Calibration recommendation")
lines.append("")
lines.append("Top-quartile strategies (by Total R) get full sizing weight in PM decisions.")
lines.append("Bottom-quartile strategies get half-sizing OR get suspended pending review.")
lines.append("Strategies with < 10 trades across all markets are statistically inconclusive — log only.")

scorecard_path.write_text("\n".join(lines))
print(f"Scorecard: {scorecard_path}")
print(f"Total result rows: {len(all_results)}")
