"""Full grid analysis: every strategy × every focus symbol × every hour-of-day.

Output:
- Top cells (strategy × symbol × hour) by P&L
- Best hour-of-day across all strategies
- Best strategy across all hours
- Optimal 24-hour rotation
"""
from __future__ import annotations

import math
import sys
import warnings
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from statistics import mean

import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.backtest import strategies as strats  # noqa: E402

SYMBOL_SPECS = {
    "ZN": {"tick_size": 0.015625, "tick_value": 15.625, "yf": "ZN=F"},
    "ZB": {"tick_size": 0.03125,  "tick_value": 31.25,  "yf": "ZB=F"},
    "ZT": {"tick_size": 0.0078125, "tick_value": 15.625, "yf": "ZT=F"},
    "ZF": {"tick_size": 0.0078125, "tick_value": 7.8125, "yf": "ZF=F"},
    "NG": {"tick_size": 0.001,    "tick_value": 10.00,  "yf": "NG=F"},
    "GC": {"tick_size": 0.10,     "tick_value": 10.00,  "yf": "GC=F"},
    "6E": {"tick_size": 0.00005,  "tick_value": 6.25,   "yf": "6E=F"},
    "ES": {"tick_size": 0.25,     "tick_value": 12.50,  "yf": "ES=F"},
    "NQ": {"tick_size": 0.25,     "tick_value": 5.00,   "yf": "NQ=F"},
    "CL": {"tick_size": 0.01,     "tick_value": 10.00,  "yf": "CL=F"},
}

# Strategies that require special args — skip from broad sweep
SKIP_STRATEGIES = {
    "fair_value_gap_tuned",       # needs kwargs
    "liquidity_sweep_tuned",      # needs kwargs
    "order_block_d1",             # needs kwargs
    "cross_asset_divergence_zn",  # needs partner_bars
}

PER_TRADE_LOSS_CAP_USD = 150.0
RT_FEE = 4.80


def fetch_bars(yf_ticker: str) -> pd.DataFrame:
    df = yf.download(yf_ticker, period="60d", interval="5m",
                     progress=False, auto_adjust=False)
    if hasattr(df.columns, "get_level_values"):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert("America/New_York")
    return df


def simulate_outcome(event, bars):
    forward = bars[bars.index > event["ts"]]
    if len(forward) == 0:
        return event["entry"], "no_data", event["ts"]
    for ts, row in forward.iterrows():
        hi, lo = float(row["High"]), float(row["Low"])
        if event["side"] == "long":
            if lo <= event["stop"]:
                return event["stop"], "stop", ts
            if event.get("target") and hi >= event["target"]:
                return event["target"], "target", ts
        else:
            if hi >= event["stop"]:
                return event["stop"], "stop", ts
            if event.get("target") and lo <= event["target"]:
                return event["target"], "target", ts
        if (ts - event["ts"]) > timedelta(hours=8):
            return float(row["Close"]), "timeout", ts
    return float(forward.iloc[-1]["Close"]), "eod", forward.index[-1]


def size(stop_dollars):
    if stop_dollars <= 0:
        return 0
    return max(0, min(math.floor(PER_TRADE_LOSS_CAP_USD / stop_dollars), 5))


def main():
    print("=" * 78)
    print("FULL GRID: 21 strategies × 10 symbols × 24 hours-of-day")
    print("=" * 78)

    # Fetch bars once per symbol
    bars_by_sym = {}
    for sym, spec in SYMBOL_SPECS.items():
        try:
            print(f"  fetching {sym}...", end="", flush=True)
            bars = fetch_bars(spec["yf"])
            if len(bars) < 100:
                print(f" SKIP ({len(bars)} bars)")
                continue
            bars_by_sym[sym] = bars
            print(f" {len(bars)} bars")
        except Exception as e:
            print(f" ERROR: {e}")

    # Build trades grid: list of dicts with strategy/symbol/hour/pnl
    all_trades = []
    strategy_names = sorted(s for s in strats.STRATEGY_REGISTRY if s not in SKIP_STRATEGIES)

    print(f"\nRunning {len(strategy_names)} strategies × {len(bars_by_sym)} symbols = "
          f"{len(strategy_names)*len(bars_by_sym)} cell-runs:")

    for strat_name in strategy_names:
        fn = strats.STRATEGY_REGISTRY[strat_name]
        print(f"  [{strat_name}] ", end="", flush=True)
        for sym, bars in bars_by_sym.items():
            spec = SYMBOL_SPECS[sym]
            try:
                sigs = list(fn(bars))
            except Exception as e:
                print(f"{sym}!", end="", flush=True)
                continue
            n_sigs = 0
            for s in sigs:
                if s.kind != "entry":
                    continue
                ts = s.date if s.date.tzinfo else s.date.tz_localize("UTC")
                ts_et = ts.tz_convert("America/New_York")
                if not s.stop:
                    continue
                stop_price = abs(s.price - s.stop)
                stop_dollars = (stop_price / spec["tick_size"]) * spec["tick_value"]
                n_contracts = size(stop_dollars)
                if n_contracts == 0:
                    continue
                event = {"ts": ts_et, "side": s.side, "entry": s.price,
                         "stop": s.stop, "target": s.target}
                exit_price, reason, _ = simulate_outcome(event, bars)
                if s.side == "long":
                    pnl_price = exit_price - s.price
                else:
                    pnl_price = s.price - exit_price
                pnl_dollars = (pnl_price / spec["tick_size"]) * spec["tick_value"]
                pnl_total = pnl_dollars * n_contracts - RT_FEE * n_contracts
                all_trades.append({
                    "strategy": strat_name, "symbol": sym, "side": s.side,
                    "hour": ts_et.hour, "pnl": pnl_total,
                })
                n_sigs += 1
            print(f"{sym}({n_sigs}) ", end="", flush=True)
        print()

    if not all_trades:
        print("No trades generated.")
        return

    df = pd.DataFrame(all_trades)
    print(f"\nTotal trades simulated: {len(df)}")

    # ─── Top 30 cells by total P&L ─────────────────────────────
    print("\n" + "=" * 78)
    print("TOP 30 CELLS by total P&L (60d)  [strategy × symbol × hour]")
    print("=" * 78)
    cell = df.groupby(["strategy", "symbol", "hour"]).agg(
        n=("pnl", "size"),
        wins=("pnl", lambda x: (x > 0).sum()),
        total=("pnl", "sum"),
        avg=("pnl", "mean"),
    ).reset_index()
    cell["hit"] = cell["wins"] / cell["n"] * 100
    cell = cell[cell["n"] >= 5].sort_values("total", ascending=False)
    print(f"{'strategy':<28} {'sym':<4} {'hr':>3} {'n':>4} {'hit%':>5} {'avg$':>8} {'total$':>10}")
    for _, r in cell.head(30).iterrows():
        print(f"{r['strategy']:<28} {r['symbol']:<4} {int(r['hour']):>3} "
              f"{int(r['n']):>4} {r['hit']:>4.0f}% {r['avg']:>+7.2f} {r['total']:>+10.2f}")

    # ─── Best hour-of-day across ALL strategies/symbols ────────
    print("\n" + "=" * 78)
    print("HOUR-OF-DAY P&L (ET) — aggregated across all strategies × symbols")
    print("=" * 78)
    hr = df.groupby("hour").agg(
        n=("pnl", "size"),
        wins=("pnl", lambda x: (x > 0).sum()),
        total=("pnl", "sum"),
        avg=("pnl", "mean"),
    )
    hr["hit"] = hr["wins"] / hr["n"] * 100
    print(f"{'hr_ET':>5} {'n':>5} {'hit%':>6} {'avg$':>8} {'total$':>10}  bar")
    max_abs = max(abs(hr["total"].min()), hr["total"].max(), 1)
    for h in range(24):
        if h not in hr.index:
            print(f"{h:>5} {0:>5} {'—':>6} {'—':>8} {'—':>10}")
            continue
        r = hr.loc[h]
        bar_n = int(abs(r["total"]) / max_abs * 30)
        bar = ("+" if r["total"] >= 0 else "-") * bar_n
        print(f"{h:>5} {int(r['n']):>5} {r['hit']:>5.0f}% {r['avg']:>+7.2f} "
              f"{r['total']:>+10.2f}  {bar}")

    # ─── Best strategy per hour ───────────────────────────────
    print("\n" + "=" * 78)
    print("BEST STRATEGY PER HOUR (by P&L, n>=10)")
    print("=" * 78)
    sh = df.groupby(["hour", "strategy"]).agg(
        n=("pnl", "size"),
        total=("pnl", "sum"),
        avg=("pnl", "mean"),
    ).reset_index()
    sh = sh[sh["n"] >= 10]
    print(f"{'hr_ET':>5}  {'best strategy':<28} {'n':>4} {'avg$':>8} {'total$':>10}")
    for h in range(24):
        candidates = sh[sh["hour"] == h]
        if candidates.empty:
            print(f"{h:>5}  (no candidates with n>=10)")
            continue
        top = candidates.sort_values("total", ascending=False).iloc[0]
        print(f"{h:>5}  {top['strategy']:<28} {int(top['n']):>4} "
              f"{top['avg']:>+7.2f} {top['total']:>+10.2f}")

    # ─── Strategy summary across all hours ────────────────────
    print("\n" + "=" * 78)
    print("STRATEGY SUMMARY across all hours/symbols")
    print("=" * 78)
    st = df.groupby("strategy").agg(
        n=("pnl", "size"),
        wins=("pnl", lambda x: (x > 0).sum()),
        total=("pnl", "sum"),
        avg=("pnl", "mean"),
    )
    st["hit"] = st["wins"] / st["n"] * 100
    st = st.sort_values("total", ascending=False)
    print(f"{'strategy':<28} {'n':>5} {'hit%':>6} {'avg$':>8} {'total$':>10}")
    for name, r in st.iterrows():
        print(f"{name:<28} {int(r['n']):>5} {r['hit']:>5.0f}% {r['avg']:>+7.2f} {r['total']:>+10.2f}")

    # ─── Optimal 24-hour rotation ────────────────────────────
    print("\n" + "=" * 78)
    print("OPTIMAL 24-HOUR ROTATION")
    print("=" * 78)
    print("If we picked the SINGLE best (strategy × symbol × hour) cell each hour:")
    cell_sorted = cell.sort_values("total", ascending=False)
    rotation = []
    used_pairs = set()
    for h in range(24):
        for _, r in cell_sorted.iterrows():
            if int(r["hour"]) != h:
                continue
            if r["total"] <= 0:
                break
            rotation.append({
                "hour": h, "strategy": r["strategy"], "symbol": r["symbol"],
                "n": int(r["n"]), "hit": r["hit"], "total": r["total"], "avg": r["avg"],
            })
            break
    if rotation:
        print(f"{'hr':>3}  {'strategy':<28} {'sym':<4} {'n':>4} {'hit%':>5} {'avg$':>8} {'total$':>10}")
        rot_total = 0
        for r in rotation:
            print(f"{r['hour']:>3}  {r['strategy']:<28} {r['symbol']:<4} "
                  f"{r['n']:>4} {r['hit']:>4.0f}% {r['avg']:>+7.2f} {r['total']:>+10.2f}")
            rot_total += r["total"]
        print(f"{'':>3}  {'OPTIMAL ROTATION TOTAL':<37} {'':>10} {rot_total:>+10.2f}")
        print(f"   (per-day: ${rot_total/60:+.2f} | per-month: ${rot_total/2:+.2f})")

    # ─── Save full grid to CSV for follow-up ──────────────────
    out_csv = PROJECT_ROOT / "vault" / "research" / "backtests" / "2026-05-08_full_grid.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    cell.to_csv(out_csv, index=False)
    print(f"\nFull cell grid saved to: {out_csv.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
