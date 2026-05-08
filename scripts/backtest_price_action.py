"""One-shot intraday backtest of the price-action strategies.

Pulls 30 days of 5m bars from yfinance for each of our 7 focus symbols,
runs fair_value_gap / order_block / liquidity_sweep, and reports per-symbol
expectancy, hit rate, and trigger frequency.

This validates the new strategies against real recent market data BEFORE
committing live capital. Output is a markdown report at
vault/research/backtests/<date>_price_action_intraday.md.

Usage:
    python scripts/backtest_price_action.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

import yfinance as yf

# Ensure we can import from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.backtest import strategies as strats  # noqa: E402
from tools.backtest.engine import backtest_strategy  # noqa: E402

# Internal symbol → yfinance ticker. Micros use their parent contract bars
# because price action is identical (only tick value differs).
SYMBOL_MAP = {
    "MES": "ES=F",   # E-mini S&P — covers MES
    "MNQ": "NQ=F",   # Nasdaq
    "NG":  "NG=F",   # Natural gas
    "MCL": "CL=F",   # Crude — covers MCL
    "GC":  "GC=F",   # Gold
    "ZN":  "ZN=F",   # 10Y note
    "6E":  "6E=F",   # Euro FX
}

STRATEGIES_TO_TEST = [
    ("fair_value_gap", strats.fair_value_gap, {}),
    ("order_block", strats.order_block, {}),
    ("liquidity_sweep", strats.liquidity_sweep, {}),
]


def fetch_bars(yf_ticker: str, period: str = "30d", interval: str = "5m"):
    """Fetch + normalize OHLCV bars from yfinance."""
    df = yf.download(yf_ticker, period=period, interval=interval, progress=False)
    if df.empty:
        return None
    # yfinance >=0.2 returns MultiIndex even for single ticker
    if hasattr(df.columns, "get_level_values"):
        df.columns = df.columns.get_level_values(0)
    keep = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    df = df[keep].copy().dropna()
    df.index = df.index.tz_localize(None) if df.index.tz else df.index
    return df


def run_one(label: str, fn, params, bars, symbol: str) -> dict:
    """Run one strategy on one symbol's bars; return summary dict."""
    try:
        result = backtest_strategy(fn, bars, symbol=symbol, params=params)
    except Exception as exc:
        return {"strategy": label, "symbol": symbol, "error": str(exc)}

    closed = [t for t in result.trades if not t.is_open]
    n = len(closed)
    if n == 0:
        return {"strategy": label, "symbol": symbol, "trades": 0}

    rs = [t.r_multiple for t in closed]
    wins = [r for r in rs if r > 0]
    return {
        "strategy": label,
        "symbol": symbol,
        "trades": n,
        "hit_rate": len(wins) / n,
        "avg_r": mean(rs),
        "avg_win_r": mean(wins) if wins else 0.0,
        "avg_loss_r": mean([r for r in rs if r <= 0]) if (n - len(wins)) else 0.0,
        "best_r": max(rs),
        "worst_r": min(rs),
        "expectancy_r": mean(rs),  # per-trade R-multiple expectation
    }


def main() -> int:
    print(f"=== Price-action backtest — {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC} ===")
    print(f"  symbols: {list(SYMBOL_MAP)}")
    print(f"  strategies: {[s[0] for s in STRATEGIES_TO_TEST]}")
    print(f"  data: yfinance 30d of 5m bars (intraday)")
    print()

    bars_by_symbol = {}
    for sym, ticker in SYMBOL_MAP.items():
        print(f"  fetching {sym} ({ticker})...", end=" ", flush=True)
        bars = fetch_bars(ticker)
        if bars is None or len(bars) < 100:
            print(f"INSUFFICIENT DATA ({0 if bars is None else len(bars)} bars)")
            continue
        bars_by_symbol[sym] = bars
        print(f"{len(bars)} bars [{bars.index[0]} → {bars.index[-1]}]")
    print()

    rows: list[dict] = []
    for label, fn, params in STRATEGIES_TO_TEST:
        for sym, bars in bars_by_symbol.items():
            row = run_one(label, fn, params, bars, sym)
            rows.append(row)

    # Print formatted table
    print(f"{'strategy':<20} {'symbol':<5}  {'trades':>6}  {'hit%':>6}  {'avgR':>7}  {'expR':>7}")
    print("-" * 70)
    for r in rows:
        if "error" in r:
            print(f"{r['strategy']:<20} {r['symbol']:<5}  ERROR: {r['error']}")
        elif r.get("trades", 0) == 0:
            print(f"{r['strategy']:<20} {r['symbol']:<5}  {'0':>6}  {'-':>6}  {'-':>7}  {'-':>7}")
        else:
            print(f"{r['strategy']:<20} {r['symbol']:<5}  "
                  f"{r['trades']:>6}  "
                  f"{r['hit_rate']*100:>5.1f}%  "
                  f"{r['avg_r']:>+7.2f}  "
                  f"{r['expectancy_r']:>+7.2f}")
    print()

    # Per-strategy aggregate
    print("=== Per-strategy aggregate ===")
    by_strat: dict[str, list[dict]] = {}
    for r in rows:
        if r.get("trades", 0) > 0:
            by_strat.setdefault(r["strategy"], []).append(r)
    for strat, items in by_strat.items():
        total_n = sum(it["trades"] for it in items)
        total_wins = sum(it["trades"] * it["hit_rate"] for it in items)
        weighted_exp = sum(it["expectancy_r"] * it["trades"] for it in items) / max(total_n, 1)
        print(f"  {strat:<20}  n={total_n:>4}  hit={total_wins/total_n*100:>5.1f}%  "
              f"weighted_E={weighted_exp:+.2f}R")
    print()

    # Save markdown report
    out_dir = PROJECT_ROOT / "vault" / "research" / "backtests"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    md_path = out_dir / f"{ts}_price_action_intraday.md"
    lines = [
        "---",
        f"type: backtest",
        f"date: {datetime.now(timezone.utc).isoformat()}",
        f"strategies: [fair_value_gap, order_block, liquidity_sweep]",
        f"symbols: {list(bars_by_symbol)}",
        f"timeframe: 5m",
        f"period: 30d",
        f"data_source: yfinance",
        "---",
        "",
        "# Price-action strategy backtest — 30d intraday",
        "",
        "## Per-symbol-per-strategy results",
        "",
        "| Strategy | Symbol | Trades | Hit% | Avg R | Exp R |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for r in rows:
        if "error" in r:
            lines.append(f"| {r['strategy']} | {r['symbol']} | ERROR | - | - | - |")
        elif r.get("trades", 0) == 0:
            lines.append(f"| {r['strategy']} | {r['symbol']} | 0 | - | - | - |")
        else:
            lines.append(
                f"| {r['strategy']} | {r['symbol']} | {r['trades']} | "
                f"{r['hit_rate']*100:.1f}% | {r['avg_r']:+.2f} | "
                f"{r['expectancy_r']:+.2f} |"
            )
    lines += ["", "## Per-strategy aggregate (across all symbols)", "",
              "| Strategy | n | Hit% | Weighted E[R] |",
              "|---|---:|---:|---:|"]
    for strat, items in by_strat.items():
        total_n = sum(it["trades"] for it in items)
        total_wins = sum(it["trades"] * it["hit_rate"] for it in items)
        weighted_exp = sum(it["expectancy_r"] * it["trades"] for it in items) / max(total_n, 1)
        lines.append(f"| {strat} | {total_n} | {total_wins/total_n*100:.1f}% | {weighted_exp:+.2f}R |")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report saved: {md_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
