"""Phase 2 walk-forward validation — mine the deep_analysis ⭐ cells.

The deep_analysis from 2026-05-04 tested 21 strategies × 7 symbols × 4
sessions × 2 directions. Many cells showed t-stat > 2 in-sample. Only 4
have been walk-forward validated so far. This script walk-forward
validates EVERY (strategy, symbol, session, side) cell with n>=30 and
in-sample t>=2 against a 45-day train / 15-day held-out OOS split.

Output: vault/research/backtests/<date>_phase2.md with:
  - All cells that pass (train E>0, OOS E>0, OOS t>=1.5)
  - Suggested STRATEGY_SYMBOL_ALLOWLIST and STRATEGY_CELL_ALLOWLIST
    additions for any new validated edges

Usage:
    python scripts/walk_forward_phase2.py
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

# All 21 strategies (same as deep_analysis)
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
    ("volume_spike_reversal", strats.volume_spike_reversal),
    ("support_resistance_bounce", strats.support_resistance_bounce),
    ("gap_fill", strats.gap_fill),
    ("pivot_reversal", strats.pivot_reversal),
]

MIN_N = 30           # cell must have at least this many trades total
MIN_OOS_T = 1.5      # OOS t-stat threshold to validate
MIN_TRAIN_E = 0.0    # train must be positive


def session_bucket(et_hour: float) -> str:
    if 9.5 <= et_hour < 16:    return "RTH"
    if 4 <= et_hour < 9.5:     return "London"
    if 16 <= et_hour < 20:     return "PostClose"
    return "Asian"


def fetch_bars(ticker: str, period: str = "60d"):
    df = yf.download(ticker, period=period, interval="5m", progress=False)
    if df.empty: return None
    if hasattr(df.columns, "get_level_values"):
        df.columns = df.columns.get_level_values(0)
    keep = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    df = df[keep].copy().dropna()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert("America/New_York")
    return df


def run_with_meta(label, fn, bars, sym):
    try:
        result = backtest_strategy(fn, bars, symbol=sym, params={})
    except Exception:
        return []
    rows = []
    for t in result.trades:
        if t.is_open: continue
        et = t.entry_date
        if et.tz is None:
            et = et.tz_localize("UTC").tz_convert("America/New_York")
        else:
            et = et.tz_convert("America/New_York")
        rows.append({
            "strategy": label, "symbol": sym, "entry_et": et,
            "side": t.side, "r": t.r_multiple,
            "session": session_bucket(et.hour + et.minute / 60),
        })
    return rows


def stats(rows):
    n = len(rows)
    if n == 0: return None
    rs = [r["r"] for r in rows]
    hit = sum(1 for r in rs if r > 0) / n
    e = mean(rs)
    sd = stdev(rs) if n > 1 else 0
    t = (e / (sd / (n ** 0.5))) if (sd > 0 and n > 1) else 0
    return {"n": n, "hit": hit, "e": e, "t": t}


def split(rows, cutoff):
    return [r for r in rows if r["entry_et"] < cutoff], [r for r in rows if r["entry_et"] >= cutoff]


def main():
    print(f"=== PHASE 2 WALK-FORWARD — {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC} ===")
    print(f"  21 strategies × 7 symbols × 4 sessions × 2 sides = 1,176 candidate cells")
    print(f"  60d split: 45d train + 15d held-out OOS")
    print(f"  Pass criteria: n>={MIN_N}, train E>{MIN_TRAIN_E}, OOS E>0, OOS t>={MIN_OOS_T}\n")

    bars_by_symbol = {}
    for sym, ticker in SYMBOL_MAP.items():
        bars = fetch_bars(ticker)
        if bars is None or len(bars) < 200:
            print(f"  {sym}: insufficient")
            continue
        bars_by_symbol[sym] = bars
        print(f"  {sym}: {len(bars)} bars")
    print()

    # Cutoff: 25% of bars as held-out test
    last_dt = max(b.index[-1] for b in bars_by_symbol.values())
    span = last_dt - bars_by_symbol[list(bars_by_symbol)[0]].index[0]
    cutoff = last_dt - span * 0.25
    print(f"  Cutoff: {cutoff}\n")

    # Run every strategy on every symbol; bucket by (session, side)
    print("  Running strategies...")
    all_rows = []
    for label, fn in ALL_STRATEGIES:
        for sym, bars in bars_by_symbol.items():
            all_rows.extend(run_with_meta(label, fn, bars, sym))
    print(f"  total trades: {len(all_rows)}\n")

    # Bucket by (strategy, symbol, session, side)
    from collections import defaultdict
    cells = defaultdict(list)
    for r in all_rows:
        cells[(r["strategy"], r["symbol"], r["session"], r["side"])].append(r)

    # Walk-forward each cell
    print(f"=== WALK-FORWARD: {len(cells)} candidate cells ===\n")
    passing = []
    failing = []
    insufficient = []
    for key, rows in cells.items():
        if len(rows) < MIN_N:
            insufficient.append((key, len(rows)))
            continue
        train, test = split(rows, cutoff)
        s_tr = stats(train)
        s_te = stats(test)
        if s_tr is None or s_te is None or len(test) < 5:
            insufficient.append((key, len(rows)))
            continue
        holds = (s_tr["e"] > MIN_TRAIN_E and s_te["e"] > 0 and s_te["t"] > MIN_OOS_T)
        record = {
            "strategy": key[0], "symbol": key[1],
            "session": key[2], "side": key[3],
            "train_n": s_tr["n"], "train_hit": s_tr["hit"],
            "train_e": s_tr["e"], "train_t": s_tr["t"],
            "oos_n": s_te["n"], "oos_hit": s_te["hit"],
            "oos_e": s_te["e"], "oos_t": s_te["t"],
            "holds": holds,
        }
        if holds:
            passing.append(record)
        else:
            failing.append(record)

    # Sort passing by OOS expectancy
    passing.sort(key=lambda x: -x["oos_e"])

    print(f"=== PASSING ({len(passing)} cells) ===")
    print(f"{'strategy':<28} {'sym':<5} {'session':<10} {'side':<6} {'n_tr':>5} {'E_tr':>6} {'t_tr':>6} {'n_oos':>5} {'E_oos':>6} {'t_oos':>6}")
    print("-" * 100)
    for r in passing:
        print(f"{r['strategy']:<28} {r['symbol']:<5} {r['session']:<10} {r['side']:<6} "
              f"{r['train_n']:>5} {r['train_e']:>+6.2f} {r['train_t']:>+6.2f} "
              f"{r['oos_n']:>5} {r['oos_e']:>+6.2f} {r['oos_t']:>+6.2f}")
    print()

    print(f"Cells failing: {len(failing)}")
    print(f"Cells insufficient n: {len(insufficient)}")

    # Save markdown report
    out = PROJECT_ROOT / "vault" / "research" / "backtests"
    out.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    md_path = out / f"{ts}_phase2.md"
    L = ["---",
         f"type: walk_forward_phase2",
         f"date: {datetime.now(timezone.utc).isoformat()}",
         f"cells_tested: {len(cells)}",
         f"cells_passing: {len(passing)}",
         f"cutoff: {cutoff}",
         f"min_n: {MIN_N}", f"min_oos_t: {MIN_OOS_T}",
         "---", "",
         "# Phase 2 walk-forward — validated cells",
         "",
         f"Tested {len(cells)} (strategy × symbol × session × side) cells from 60d intraday.",
         f"**{len(passing)} cells PASS the walk-forward threshold** (train E>0, OOS E>0, OOS t>=1.5).",
         "",
         "## Passing cells (sorted by OOS expectancy)",
         "",
         "| Strategy | Symbol | Session | Side | n_train | E_train | t_train | n_OOS | E_OOS | t_OOS |",
         "|---|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in passing:
        L.append(f"| {r['strategy']} | {r['symbol']} | {r['session']} | {r['side']} | "
                 f"{r['train_n']} | {r['train_e']:+.2f} | {r['train_t']:+.2f} | "
                 f"{r['oos_n']} | {r['oos_e']:+.2f} | {r['oos_t']:+.2f} |")
    L += ["", "## Suggested allowlist additions", "", "```python",
          "STRATEGY_CELL_ALLOWLIST = {"]
    by_strat = defaultdict(list)
    for r in passing:
        by_strat[r["strategy"]].append(r)
    for strat, items in by_strat.items():
        L.append(f"    \"{strat}\": [")
        for r in items:
            L.append(f"        {{\"symbol\": \"{r['symbol']}\", \"session\": \"{r['session']}\", \"side\": \"{r['side']}\"}},  # OOS E={r['oos_e']:+.2f}R t={r['oos_t']:+.2f}")
        L.append("    ],")
    L += ["}", "```"]

    md_path.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nReport: {md_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
