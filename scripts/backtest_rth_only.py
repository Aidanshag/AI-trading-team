"""RTH-only simulation: what would gap_fill on treasuries look like 9 AM - 4 PM ET?

We have ~zero validated RTH data (2 shadow cells, n=2 and n=5).
This script runs gap_fill across 60d on ZN/ZB/ZT/ZF and shows what
the P&L looks like restricted to RTH hours only.

Compares: gap_fill in RTH vs gap_fill aggregate vs gap_fill in Asian (the headliner).
"""
from __future__ import annotations

import math
import sys
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from statistics import mean, median

import pandas as pd
import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.backtest import strategies as strats  # noqa: E402

SYMBOL_SPECS = {
    "ZN": {"tick_size": 0.015625, "tick_value": 15.625, "yf": "ZN=F"},
    "ZB": {"tick_size": 0.03125,  "tick_value": 31.25,  "yf": "ZB=F"},
    "ZT": {"tick_size": 0.0078125, "tick_value": 15.625, "yf": "ZT=F"},
    "ZF": {"tick_size": 0.0078125, "tick_value": 7.8125, "yf": "ZF=F"},
}

PER_TRADE_LOSS_CAP_USD = 150.0
RT_FEE = 4.80


def session_for(ts_et) -> str:
    h = ts_et.hour
    if 18 <= h or h < 4: return "Asian"
    if 4 <= h < 9: return "London"
    if 9 <= h < 16: return "RTH"
    return "PostClose"


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
            if hi >= event["target"]:
                return event["target"], "target", ts
        else:
            if hi >= event["stop"]:
                return event["stop"], "stop", ts
            if lo <= event["target"]:
                return event["target"], "target", ts
        if (ts - event["ts"]) > timedelta(hours=8):
            return float(row["Close"]), "timeout", ts
    return float(forward.iloc[-1]["Close"]), "eod", forward.index[-1]


def size(stop_dollars):
    if stop_dollars <= 0: return 0
    return max(0, min(math.floor(PER_TRADE_LOSS_CAP_USD / stop_dollars), 5))


def main():
    print("=" * 72)
    print("RTH-only simulation: gap_fill on ZN/ZB/ZT/ZF, 9 AM - 4 PM ET")
    print("=" * 72)

    by_session = defaultdict(list)  # session -> list of trade dicts
    for sym, spec in SYMBOL_SPECS.items():
        print(f"  fetching {sym}...", end="", flush=True)
        bars = fetch_bars(spec["yf"])
        print(f" {len(bars)} bars")
        sigs = list(strats.gap_fill(bars))
        for s in sigs:
            if s.kind != "entry": continue
            ts = s.date if s.date.tzinfo else s.date.tz_localize("UTC")
            ts_et = ts.tz_convert("America/New_York")
            sess = session_for(ts_et)
            stop_price = abs(s.price - s.stop)
            stop_dollars = (stop_price / spec["tick_size"]) * spec["tick_value"]
            n_contracts = size(stop_dollars)
            if n_contracts == 0:
                continue
            event = {"ts": ts_et, "symbol": sym, "side": s.side,
                     "entry": s.price, "stop": s.stop, "target": s.target}
            exit_price, reason, exit_ts = simulate_outcome(event, bars)
            if s.side == "long":
                pnl_price = exit_price - s.price
            else:
                pnl_price = s.price - exit_price
            pnl_dollars = (pnl_price / spec["tick_size"]) * spec["tick_value"]
            pnl_total = pnl_dollars * n_contracts - RT_FEE * n_contracts
            by_session[sess].append({
                "symbol": sym, "side": s.side, "ts": ts_et,
                "n": n_contracts, "pnl": pnl_total, "reason": reason,
            })

    print("\n" + "=" * 72)
    print("RESULTS BY SESSION")
    print("=" * 72)

    for sess in ["RTH", "Asian", "London", "PostClose"]:
        trades = by_session[sess]
        print(f"\n--- {sess} ({len(trades)} trades over 60d) ---")
        if not trades:
            print("  no trades")
            continue
        wins = [t for t in trades if t["pnl"] > 0]
        losses = [t for t in trades if t["pnl"] < 0]
        hit = len(wins) / len(trades)
        avg_w = mean(t["pnl"] for t in wins) if wins else 0
        avg_l = mean(t["pnl"] for t in losses) if losses else 0
        e = mean(t["pnl"] for t in trades)
        total = sum(t["pnl"] for t in trades)
        med = median(t["pnl"] for t in trades)
        # By symbol/side
        by_cell = defaultdict(list)
        for t in trades:
            by_cell[f"{t['symbol']}|{t['side']}"].append(t)
        print(f"  Hit rate:        {hit*100:.1f}% ({len(wins)}W / {len(losses)}L)")
        print(f"  Avg win:        ${avg_w:+.2f}   Avg loss: ${avg_l:+.2f}")
        print(f"  Expectancy:     ${e:+.2f}/trade   median ${med:+.2f}")
        print(f"  Total 60d:      ${total:+.2f}")
        print(f"  Per-day avg:    ${total/60:+.2f}")
        print(f"  Cells:")
        for k in sorted(by_cell):
            cs = by_cell[k]
            h = sum(1 for t in cs if t["pnl"] > 0) / len(cs)
            tot = sum(t["pnl"] for t in cs)
            avg = mean(t["pnl"] for t in cs)
            print(f"    {k:<14} n={len(cs):>3}  hit={h*100:>3.0f}%  avg=${avg:>+6.2f}  total=${tot:>+8.2f}")

    # Side-by-side summary
    print("\n" + "=" * 72)
    print("SIDE-BY-SIDE COMPARISON (per-day P&L)")
    print("=" * 72)
    print(f"{'session':<10} {'n':>4} {'hit%':>6} {'E/trade':>10} {'per_day':>10} {'total':>10}")
    for sess in ["Asian", "London", "RTH", "PostClose"]:
        trades = by_session[sess]
        if not trades:
            print(f"{sess:<10} {0:>4} {'-':>6} {'-':>10} {'-':>10} {'-':>10}")
            continue
        hit = sum(1 for t in trades if t["pnl"] > 0) / len(trades)
        e = mean(t["pnl"] for t in trades)
        total = sum(t["pnl"] for t in trades)
        print(f"{sess:<10} {len(trades):>4} {hit*100:>5.1f}% ${e:>+8.2f} ${total/60:>+8.2f} ${total:>+9.2f}")

    print(f"\nTotal RTH-only P&L over 60d: ${sum(t['pnl'] for t in by_session['RTH']):+.2f}")
    print(f"Total Asian P&L over 60d:    ${sum(t['pnl'] for t in by_session['Asian']):+.2f}")
    print(f"\nIf we ADDED RTH cells to live allowlist, change in 60d total P&L:")
    print(f"  +${sum(t['pnl'] for t in by_session['RTH']):.2f} (vs current ~$12,400 from non-RTH cells)")


if __name__ == "__main__":
    main()
