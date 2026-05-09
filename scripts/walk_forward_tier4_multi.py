"""Tier 4 parameter sweeps on multiple strategies.

Sweeps fair_value_gap and liquidity_sweep across (param_combo, symbol,
session, side). Discovers cells where non-default parameters yield
validated edge. Mirrors walk_forward_tier4_order_block.py's approach.

Output:
  - vault/research/backtests/<ts>_tier4_multi_sweep.md
  - vault/research/backtests/<ts>_tier4_multi_sweep.json
"""
from __future__ import annotations

import json
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


FOCUS_TO_YF = {
    "GC":  "GC=F",  "MCL": "CL=F", "NG":  "NG=F",
    "MNQ": "NQ=F",  "MES": "ES=F",
    "ZN":  "ZN=F",  "ZB":  "ZB=F", "ZT":  "ZT=F", "ZF": "ZF=F",
    "6E":  "6E=F",  "6B":  "6B=F", "6J":  "6J=F", "6A": "6A=F", "6C": "6C=F",
}

# Per-strategy parameter grids
SWEEPS: dict[str, dict] = {
    "fair_value_gap": {
        "fn": strats.fair_value_gap,
        "grid": {
            "min_gap_atr":  (0.10, 0.20, 0.30, 0.50, 0.75),
            "max_age_bars": (15, 30, 60),
            "rr_target":    (1.5, 2.0, 2.5),
        },
    },
    "liquidity_sweep": {
        "fn": strats.liquidity_sweep,
        "grid": {
            "swing_lookback": (5, 10, 15, 20, 30),
            "rr_target":      (1.5, 2.0, 2.5),
        },
    },
}


def session_bucket(et_hour: float) -> str:
    if 9.5 <= et_hour < 16:    return "RTH"
    if 4 <= et_hour < 9.5:     return "London"
    if 16 <= et_hour < 20:     return "PostClose"
    return "Asian"


def fetch_bars(ticker: str):
    df = yf.download(ticker, period="60d", interval="5m",
                     progress=False, auto_adjust=False)
    if df.empty:
        return None
    if hasattr(df.columns, "get_level_values"):
        df.columns = df.columns.get_level_values(0)
    keep = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    df = df[keep].copy().dropna()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert("America/New_York")
    return df


def collect_trades(strat_fn, bars, sym, params):
    try:
        result = backtest_strategy(strat_fn, bars, symbol=sym, params=params)
    except Exception:
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
        rows.append({"symbol": sym, "entry_et": et,
                     "side": t.side, "r": float(t.r_multiple),
                     "session": session_bucket(et.hour + et.minute / 60)})
    return rows


def stats(rows):
    n = len(rows)
    if n == 0: return None
    rs = [r["r"] for r in rows]
    hit = sum(1 for r in rs if r > 0) / n
    e = mean(rs)
    sd = stdev(rs) if n > 1 else 0
    t = (e / (sd / (n ** 0.5))) if (sd > 0 and n > 1) else 0
    return {"n": n, "hit": round(hit, 3), "e": round(e, 3), "t": round(t, 2)}


def split_at(rows, cutoff):
    return ([r for r in rows if r["entry_et"] < cutoff],
            [r for r in rows if r["entry_et"] >= cutoff])


def grid_combos(grid: dict) -> list[dict]:
    """Cartesian product of param grid → list of param dicts."""
    keys = list(grid.keys())
    combos: list[dict] = [{}]
    for k in keys:
        vals = grid[k]
        next_combos = []
        for c in combos:
            for v in vals:
                d = dict(c); d[k] = v
                next_combos.append(d)
        combos = next_combos
    return combos


def main():
    ts = datetime.now(timezone.utc)
    print(f"=== TIER 4 MULTI-STRATEGY SWEEP — {ts:%Y-%m-%d %H:%M UTC} ===\n")

    bars_by = {}
    for sym, ticker in FOCUS_TO_YF.items():
        b = fetch_bars(ticker)
        if b is not None and len(b) >= 100:
            bars_by[sym] = b
    print(f"Symbols loaded: {len(bars_by)}\n")

    all_passing = []   # all validated combos across strategies

    for strat_name, cfg in SWEEPS.items():
        fn = cfg["fn"]
        combos = grid_combos(cfg["grid"])
        print(f"=== {strat_name}: {len(combos)} param combos × {len(bars_by)} symbols ===")
        passing = []
        for ci, params in enumerate(combos, 1):
            for sym, bars in bars_by.items():
                rows = collect_trades(fn, bars, sym, params)
                if not rows:
                    continue
                span = bars.index[-1] - bars.index[0]
                cutoff = bars.index[-1] - span * 0.25
                for session in ("Asian", "London", "RTH", "PostClose"):
                    for side in ("long", "short"):
                        cell = [r for r in rows
                                if r["session"] == session and r["side"] == side]
                        if not cell:
                            continue
                        _, test = split_at(cell, cutoff)
                        s_oos = stats(test)
                        if (s_oos and s_oos["e"] > 0
                                and s_oos["n"] >= 25
                                and s_oos["t"] >= 1.5):
                            passing.append({
                                "strategy": strat_name, "params": params,
                                "symbol": sym, "session": session, "side": side,
                                "oos": s_oos,
                            })
            if ci % 5 == 0:
                print(f"  ...combo {ci}/{len(combos)}")

        # Best params per (sym, session, side)
        best = {}
        for p in passing:
            key = (p["symbol"], p["session"], p["side"])
            if key not in best or p["oos"]["e"] > best[key]["oos"]["e"]:
                best[key] = p

        print(f"  validated combos: {len(passing)}, unique cells: {len(best)}")
        for k in sorted(best, key=lambda x: -best[x]["oos"]["e"]):
            b = best[k]; o = b["oos"]; pp = b["params"]
            print(f"  {strat_name:>16} {b['symbol']:>4} {b['session']:>9} {b['side']:>5}  "
                  f"params={pp}  OOS n={o['n']:>3} E={o['e']:+.2f}R t={o['t']:+.2f}")
        all_passing.extend(best.values())
        print()

    # Report
    L = ["---", "type: walk_forward_tier4_multi",
         f"date: {ts.isoformat()}",
         f"unique_validated_cells: {len(all_passing)}",
         "---", "",
         "# Tier 4 parameter sweeps — fair_value_gap + liquidity_sweep", ""]

    for strat in SWEEPS:
        cells = [p for p in all_passing if p["strategy"] == strat]
        L += [f"## {strat} ({len(cells)} validated cells)", ""]
        if not cells:
            L += ["No validated cells at any tested parameter combination.", ""]
            continue
        L += ["| Symbol | Session | Side | Params | n_OOS | E_OOS | t_OOS |",
              "|---|---|---|---|---:|---:|---:|"]
        for c in sorted(cells, key=lambda x: -x["oos"]["e"]):
            o = c["oos"]
            params_str = " ".join(f"{k}={v}" for k, v in c["params"].items())
            L.append(f"| {c['symbol']} | {c['session']} | {c['side']} | "
                     f"{params_str} | {o['n']} | {o['e']:+.2f} | {o['t']:+.2f} |")
        L.append("")

    out_dir = PROJECT_ROOT / "vault" / "research" / "backtests"
    out_dir.mkdir(parents=True, exist_ok=True)
    md = out_dir / f"{ts:%Y-%m-%d_%H%M}_tier4_multi_sweep.md"
    md.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nReport: {md.relative_to(PROJECT_ROOT)}")

    js = out_dir / f"{ts:%Y-%m-%d_%H%M}_tier4_multi_sweep.json"
    js.write_text(json.dumps(all_passing, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
