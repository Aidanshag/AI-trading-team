"""Deep analysis of every strategy across every symbol, bucketed by
trading session and day of week. Identifies WHERE and WHEN each strategy
produces edge — if anywhere.

Output: vault/research/backtests/<date>_deep_analysis.md with:
  1. Per-strategy aggregate (across all symbols)
  2. Per-strategy × symbol expectancy table
  3. Per-strategy × symbol × SESSION expectancy table (RTH / Asian / etc.)
  4. Top 30 most-profitable strategy×symbol×session combos with n >= 30
  5. Bottom 30 worst combos (so we know what to BLOCK, not just what to deploy)
  6. Per-strategy direction bias (long vs short)

Usage:
    python scripts/strategy_deep_analysis.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, stdev

import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.backtest import strategies as strats  # noqa: E402
from tools.backtest.engine import backtest_strategy  # noqa: E402

SYMBOL_MAP = {
    "MES": "ES=F", "MNQ": "NQ=F", "NG": "NG=F", "MCL": "CL=F",
    "GC": "GC=F", "ZN": "ZN=F", "6E": "6E=F",
}

# All 21 strategies in the registry
ALL_STRATEGIES = [
    ("fair_value_gap", strats.fair_value_gap),
    ("order_block", strats.order_block),
    ("liquidity_sweep", strats.liquidity_sweep),
    ("donchian_breakout", strats.donchian_breakout),
    ("bollinger_mean_reversion", strats.bollinger_mean_reversion),
    ("volatility_breakout", strats.volatility_breakout),
    ("pullback_in_trend", strats.pullback_in_trend),
    ("range_mean_reversion", strats.range_mean_reversion),
    ("bollinger_squeeze_break", strats.bollinger_squeeze_break),
    ("keltner_breakout", strats.keltner_breakout),
    ("vol_regime_trend", strats.vol_regime_trend),
    ("vol_spike_fade", strats.vol_spike_fade),
    ("opening_range_breakout", strats.opening_range_breakout),
    ("narrow_range_break", strats.narrow_range_break),
    ("inside_bar_break", strats.inside_bar_break),
    ("rsi2_extreme_reversion", strats.rsi2_extreme_reversion),
    # vwap_reversion removed 2026-05-04 (edge confirmed nonexistent)
    ("volume_spike_reversal", strats.volume_spike_reversal),
    ("support_resistance_bounce", strats.support_resistance_bounce),
    ("gap_fill", strats.gap_fill),
    ("pivot_reversal", strats.pivot_reversal),
]


def session_bucket(et_hour: float) -> str:
    """Map ET hour-of-day to a named trading session.
    Asian: 20:00-04:00 ET (low-vol overnight)
    London: 04:00-09:30 ET (Europe open)
    RTH: 09:30-16:00 ET (US cash open)
    PostClose: 16:00-20:00 ET (US after-hours, evening)
    """
    if 9.5 <= et_hour < 16:
        return "RTH"
    if 4 <= et_hour < 9.5:
        return "London"
    if 16 <= et_hour < 20:
        return "PostClose"
    return "Asian"


def fetch_bars(yf_ticker: str, period: str = "30d", interval: str = "5m"):
    df = yf.download(yf_ticker, period=period, interval=interval, progress=False)
    if df.empty:
        return None
    if hasattr(df.columns, "get_level_values"):
        df.columns = df.columns.get_level_values(0)
    keep = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    df = df[keep].copy().dropna()
    # Convert UTC index to ET for session bucketing
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert("America/New_York")
    return df


def run_with_metadata(label: str, fn, bars, symbol: str) -> list[dict]:
    """Run strategy and return list of per-trade rows with bucketing metadata."""
    try:
        result = backtest_strategy(fn, bars, symbol=symbol, params={})
    except Exception as exc:
        print(f"  ERROR {label} {symbol}: {exc}")
        return []
    rows = []
    for t in result.trades:
        if t.is_open:
            continue
        et = t.entry_date
        if et.tz is None:
            et = et.tz_localize("UTC").tz_convert("America/New_York")
        else:
            et = et.tz_convert("America/New_York")
        rows.append({
            "strategy": label,
            "symbol": symbol,
            "entry_et": et,
            "side": t.side,
            "r": t.r_multiple,
            "session": session_bucket(et.hour + et.minute / 60),
            "dayofweek": et.day_name(),
            "hour_et": et.hour,
        })
    return rows


def aggregate(rows: list[dict], by: tuple, min_n: int = 30) -> list[dict]:
    """Group rows by tuple of keys; compute n, hit, E[R] per group."""
    from collections import defaultdict
    buckets = defaultdict(list)
    for r in rows:
        key = tuple(r[k] for k in by)
        buckets[key].append(r["r"])
    out = []
    for key, rs in buckets.items():
        n = len(rs)
        if n < min_n:
            continue
        hit = sum(1 for r in rs if r > 0) / n
        e_r = mean(rs)
        out.append({
            **dict(zip(by, key)),
            "n": n,
            "hit": hit,
            "expectancy_r": e_r,
            "stdev_r": stdev(rs) if n > 1 else 0.0,
            # Standard error → t-stat against null E=0
            "t_stat": (e_r / (stdev(rs) / (n ** 0.5))) if (n > 1 and stdev(rs) > 0) else 0.0,
        })
    return out


def main() -> int:
    print(f"=== DEEP STRATEGY ANALYSIS — {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC} ===")
    print(f"  21 strategies × 7 symbols × 30d of 5m bars")
    print(f"  Bucketing: per-session (RTH/London/Asian/PostClose), per-DOW, per-direction\n")

    bars_by_symbol = {}
    for sym, ticker in SYMBOL_MAP.items():
        print(f"  fetching {sym} ({ticker})...", end=" ", flush=True)
        bars = fetch_bars(ticker)
        if bars is None or len(bars) < 100:
            print(f"INSUFFICIENT")
            continue
        bars_by_symbol[sym] = bars
        print(f"{len(bars)} bars")
    print()

    # Run every strategy on every symbol
    all_rows: list[dict] = []
    for label, fn in ALL_STRATEGIES:
        print(f"  running {label}...", end=" ", flush=True)
        sub = []
        for sym, bars in bars_by_symbol.items():
            sub.extend(run_with_metadata(label, fn, bars, sym))
        print(f"{len(sub)} trades")
        all_rows.extend(sub)
    total_trades = len(all_rows)
    print(f"\n  TOTAL: {total_trades} trades across all 21 strategies × 7 symbols\n")

    # ── Aggregations ─────────────────────────────────────────
    by_strat = aggregate(all_rows, ("strategy",), min_n=50)
    by_strat_sym = aggregate(all_rows, ("strategy", "symbol"), min_n=30)
    by_strat_sym_session = aggregate(all_rows, ("strategy", "symbol", "session"), min_n=30)
    by_strat_session = aggregate(all_rows, ("strategy", "session"), min_n=50)
    by_strat_sym_side = aggregate(all_rows, ("strategy", "symbol", "side"), min_n=30)
    by_strat_dow = aggregate(all_rows, ("strategy", "dayofweek"), min_n=50)

    # Sort top/bottom
    top_combos = sorted(by_strat_sym_session, key=lambda x: -x["expectancy_r"])[:30]
    bot_combos = sorted(by_strat_sym_session, key=lambda x: x["expectancy_r"])[:20]

    # ── Print headline ────────────────────────────────────────
    print("=== Per-strategy aggregate (across all symbols) ===")
    print(f"{'strategy':<28} {'n':>5} {'hit%':>6} {'E[R]':>7} {'t':>6}")
    print("-" * 60)
    for r in sorted(by_strat, key=lambda x: -x["expectancy_r"]):
        flag = "**" if r["t_stat"] > 2 else "  "
        print(f"{r['strategy']:<28} {r['n']:>5} {r['hit']*100:>5.1f}% "
              f"{r['expectancy_r']:>+7.2f} {r['t_stat']:>+6.2f} {flag}")
    print("\n  ** = t-stat > 2 (i.e., E[R] > 2 SE above 0) — suggestive but NOT proof of edge\n")

    print("\n=== TOP 30 strategy×symbol×session combos (n>=30) ===")
    print(f"{'strategy':<28} {'sym':<5} {'session':<10} {'n':>4} {'hit%':>6} {'E[R]':>7} {'t':>6}")
    print("-" * 78)
    for r in top_combos:
        flag = "**" if r["t_stat"] > 2 else "  "
        print(f"{r['strategy']:<28} {r['symbol']:<5} {r['session']:<10} "
              f"{r['n']:>4} {r['hit']*100:>5.1f}% {r['expectancy_r']:>+7.2f} "
              f"{r['t_stat']:>+6.2f} {flag}")

    print("\n=== BOTTOM 20 (worst — gate these out) ===")
    print(f"{'strategy':<28} {'sym':<5} {'session':<10} {'n':>4} {'hit%':>6} {'E[R]':>7} {'t':>6}")
    print("-" * 78)
    for r in bot_combos:
        print(f"{r['strategy']:<28} {r['symbol']:<5} {r['session']:<10} "
              f"{r['n']:>4} {r['hit']*100:>5.1f}% {r['expectancy_r']:>+7.2f} "
              f"{r['t_stat']:>+6.2f}")

    # ── Save markdown report ─────────────────────────────────
    out_dir = PROJECT_ROOT / "vault" / "research" / "backtests"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    md_path = out_dir / f"{ts}_deep_analysis.md"

    L = []
    L += ["---",
          f"type: deep_analysis",
          f"date: {datetime.now(timezone.utc).isoformat()}",
          f"strategies: 21",
          f"symbols: {list(bars_by_symbol)}",
          f"timeframe: 5m",
          f"period: 30d",
          f"total_trades: {total_trades}",
          "---",
          "",
          "# Deep strategy analysis — 30d intraday on 7 symbols",
          "",
          "## ⚠️ Multiple-comparison caveat",
          "",
          ("With 21 strategies × 7 symbols × 4 sessions × 2 directions, we have "
           "1,176+ cells. Some will look great by chance even if no real edge exists. "
           "Treat any cell as 'suggestive' below n=100 and t<3.0; treat as 'tentative edge' "
           "above n=200 and t>2.5; only call it 'real edge' after walk-forward validation."),
          ""]

    L += ["## Per-strategy aggregate (across all 7 symbols)",
          "",
          "| Strategy | n | Hit% | E[R] | t-stat |",
          "|---|---:|---:|---:|---:|"]
    for r in sorted(by_strat, key=lambda x: -x["expectancy_r"]):
        flag = " ⭐" if r["t_stat"] > 2 else ""
        L.append(f"| {r['strategy']} | {r['n']} | {r['hit']*100:.1f}% | "
                 f"{r['expectancy_r']:+.2f} | {r['t_stat']:+.2f}{flag} |")

    L += ["", "## Per-strategy by SESSION (across all symbols)",
          "",
          "| Strategy | Session | n | Hit% | E[R] | t-stat |",
          "|---|---|---:|---:|---:|---:|"]
    for r in sorted(by_strat_session, key=lambda x: (-x["expectancy_r"]))[:80]:
        flag = " ⭐" if r["t_stat"] > 2 else ""
        L.append(f"| {r['strategy']} | {r['session']} | {r['n']} | "
                 f"{r['hit']*100:.1f}% | {r['expectancy_r']:+.2f} | {r['t_stat']:+.2f}{flag} |")

    L += ["", "## TOP 30 (strategy × symbol × session, n≥30)",
          "",
          "| Strategy | Symbol | Session | n | Hit% | E[R] | t-stat |",
          "|---|---|---|---:|---:|---:|---:|"]
    for r in top_combos:
        flag = " ⭐" if r["t_stat"] > 2 else ""
        L.append(f"| {r['strategy']} | {r['symbol']} | {r['session']} | "
                 f"{r['n']} | {r['hit']*100:.1f}% | {r['expectancy_r']:+.2f} | "
                 f"{r['t_stat']:+.2f}{flag} |")

    L += ["", "## BOTTOM 20 (block these combos)",
          "",
          "| Strategy | Symbol | Session | n | Hit% | E[R] | t-stat |",
          "|---|---|---|---:|---:|---:|---:|"]
    for r in bot_combos:
        L.append(f"| {r['strategy']} | {r['symbol']} | {r['session']} | "
                 f"{r['n']} | {r['hit']*100:.1f}% | {r['expectancy_r']:+.2f} | "
                 f"{r['t_stat']:+.2f} |")

    L += ["", "## Per-strategy by direction (long vs short)",
          "",
          "| Strategy | Symbol | Side | n | Hit% | E[R] |",
          "|---|---|---|---:|---:|---:|"]
    for r in sorted(by_strat_sym_side, key=lambda x: -x["expectancy_r"])[:60]:
        L.append(f"| {r['strategy']} | {r['symbol']} | {r['side']} | "
                 f"{r['n']} | {r['hit']*100:.1f}% | {r['expectancy_r']:+.2f} |")

    L += ["", "## Per-strategy by day-of-week",
          "",
          "| Strategy | Day | n | Hit% | E[R] |",
          "|---|---|---:|---:|---:|"]
    for r in sorted(by_strat_dow, key=lambda x: -x["expectancy_r"])[:50]:
        L.append(f"| {r['strategy']} | {r['dayofweek']} | {r['n']} | "
                 f"{r['hit']*100:.1f}% | {r['expectancy_r']:+.2f} |")

    md_path.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nReport saved: {md_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
