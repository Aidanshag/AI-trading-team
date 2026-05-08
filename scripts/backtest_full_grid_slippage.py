"""Full grid backtest with slippage sensitivity per strategy.

Same scope as backtest_full_grid.py but stores per-trade economics
(n_contracts, tick_value) so slippage can be applied analytically at
multiple levels in one pass.
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

SKIP_STRATEGIES = {
    "fair_value_gap_tuned", "liquidity_sweep_tuned",
    "order_block_d1", "cross_asset_divergence_zn",
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
        return event["entry"], "no_data"
    for ts, row in forward.iterrows():
        hi, lo = float(row["High"]), float(row["Low"])
        if event["side"] == "long":
            if lo <= event["stop"]: return event["stop"], "stop"
            if event.get("target") and hi >= event["target"]:
                return event["target"], "target"
        else:
            if hi >= event["stop"]: return event["stop"], "stop"
            if event.get("target") and lo <= event["target"]:
                return event["target"], "target"
        if (ts - event["ts"]) > timedelta(hours=8):
            return float(row["Close"]), "timeout"
    return float(forward.iloc[-1]["Close"]), "eod"


def size(stop_dollars):
    if stop_dollars <= 0: return 0
    return max(0, min(math.floor(PER_TRADE_LOSS_CAP_USD / stop_dollars), 5))


def main():
    print("=" * 78)
    print("FULL GRID with SLIPPAGE SENSITIVITY")
    print("=" * 78)

    bars_by_sym = {}
    for sym, spec in SYMBOL_SPECS.items():
        try:
            bars = fetch_bars(spec["yf"])
            if len(bars) >= 100:
                bars_by_sym[sym] = bars
                print(f"  {sym}: {len(bars)} bars")
        except Exception as e:
            print(f"  {sym}: error {e}")

    strategy_names = sorted(s for s in strats.STRATEGY_REGISTRY
                            if s not in SKIP_STRATEGIES)
    print(f"\nRunning {len(strategy_names)} strategies × {len(bars_by_sym)} symbols")
    all_trades = []

    for strat_name in strategy_names:
        fn = strats.STRATEGY_REGISTRY[strat_name]
        for sym, bars in bars_by_sym.items():
            spec = SYMBOL_SPECS[sym]
            try:
                sigs = list(fn(bars))
            except Exception:
                continue
            for s in sigs:
                if s.kind != "entry": continue
                if not s.stop: continue
                stop_dist_price = abs(s.price - s.stop)
                stop_dollars = (stop_dist_price / spec["tick_size"]) * spec["tick_value"]
                n_contracts = size(stop_dollars)
                if n_contracts == 0: continue
                ts = s.date if s.date.tzinfo else s.date.tz_localize("UTC")
                ts_et = ts.tz_convert("America/New_York")
                event = {"ts": ts_et, "side": s.side, "entry": s.price,
                         "stop": s.stop, "target": s.target}
                exit_price, reason = simulate_outcome(event, bars)
                if s.side == "long":
                    pnl_price = exit_price - s.price
                else:
                    pnl_price = s.price - exit_price
                pnl_dollars_clean = (pnl_price / spec["tick_size"]) * spec["tick_value"]
                pnl_clean = pnl_dollars_clean * n_contracts - RT_FEE * n_contracts
                all_trades.append({
                    "strategy": strat_name, "symbol": sym,
                    "n_contracts": n_contracts, "tick_value": spec["tick_value"],
                    "pnl_clean": pnl_clean,
                })
        print(f"  [{strat_name}] {sum(1 for t in all_trades if t['strategy']==strat_name)} trades total")

    df = pd.DataFrame(all_trades)
    print(f"\nTotal trades simulated: {len(df)}")

    print("\n" + "=" * 78)
    print("STRATEGY SUMMARY at multiple slippage levels")
    print("=" * 78)
    print("(slippage applied per-side; total round-trip = 2× listed value)")
    print()

    SLIPPAGES = [0.0, 0.25, 0.5, 1.0]

    # Compute per-trade slippage dollars at each level
    for slip_per_side in SLIPPAGES:
        df[f"pnl_slip_{slip_per_side}"] = (
            df["pnl_clean"]
            - slip_per_side * df["tick_value"] * 2 * df["n_contracts"]
        )

    # Strategy summary table
    cols_header = "strategy".ljust(28) + "  n   "
    for slip in SLIPPAGES:
        cols_header += f"slip{slip:>4}     "
    print(cols_header)
    print("-" * 80)

    by_strat = df.groupby("strategy")
    rows = []
    for name, g in by_strat:
        row = {"strategy": name, "n": len(g)}
        for slip in SLIPPAGES:
            col = f"pnl_slip_{slip}"
            row[f"total_{slip}"] = g[col].sum()
        rows.append(row)
    rows.sort(key=lambda r: r[f"total_{SLIPPAGES[1]}"], reverse=True)  # sort by 0.25 slippage
    for r in rows:
        line = r["strategy"].ljust(28) + f" {r['n']:>5} "
        for slip in SLIPPAGES:
            line += f" {r[f'total_{slip}']:>+10,.0f}"
        print(line)

    # ─── Which strategies remain profitable at each slippage level ───
    print("\n" + "=" * 78)
    print("STRATEGIES STILL PROFITABLE at each slippage level")
    print("=" * 78)
    for slip in SLIPPAGES:
        winners = sorted(
            [r for r in rows if r[f"total_{slip}"] > 0],
            key=lambda r: r[f"total_{slip}"], reverse=True,
        )
        print(f"\n  Slippage {slip} per side ({slip*2} round-trip):")
        if not winners:
            print(f"    (NONE — every strategy is unprofitable at this slippage)")
            continue
        for w in winners:
            print(f"    {w['strategy']:<28} n={w['n']:>5}  total=${w[f'total_{slip}']:>+10,.0f}")

    # ─── Per-cell winners at realistic 0.25 slippage ─────────────────
    print("\n" + "=" * 78)
    print("TOP 20 (strategy × symbol) cells at REALISTIC 0.25 slippage per side")
    print("=" * 78)
    df_realistic = df[df["pnl_slip_0.25"].notna()].copy()
    cell = df_realistic.groupby(["strategy", "symbol"]).agg(
        n=("pnl_slip_0.25", "size"),
        total_clean=("pnl_clean", "sum"),
        total_slip=("pnl_slip_0.25", "sum"),
    ).reset_index()
    cell = cell[cell["n"] >= 30].sort_values("total_slip", ascending=False).head(20)
    print(f"  {'cell':<32} {'n':>5} {'clean':>10} {'realistic':>10}")
    for _, r in cell.iterrows():
        c = f"{r['strategy']}|{r['symbol']}"
        print(f"  {c:<32} {int(r['n']):>5} {r['total_clean']:>+10,.0f} {r['total_slip']:>+10,.0f}")


if __name__ == "__main__":
    main()
