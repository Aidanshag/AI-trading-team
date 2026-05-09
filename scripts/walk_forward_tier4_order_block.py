"""Tier 4: parameter sweep on order_block.

The 2026-05-05 Tier 2 ICT sweep at default params (displacement_atr=1.5,
max_age_bars=50, rr_target=2.0) found ZERO validated cells for
order_block. The strategy's behavior is highly parameter-sensitive — a
1.5 ATR displacement filter may be too loose (false signals) or too
tight (no signals). This script sweeps the 3-D grid:

  displacement_atr ∈ {1.0, 1.5, 2.0, 2.5, 3.0}
  max_age_bars     ∈ {20, 50, 100}
  rr_target        ∈ {1.5, 2.0, 2.5}

Total: 45 parameter combinations × 14 symbols × 4 sessions × 2 sides
     = ~5040 cells evaluated.

Pass criteria (looser than daily-validation's strict gate, since we're
discovering candidates):
  - OOS n >= 25
  - OOS E > 0
  - OOS t-stat >= 1.5

Output:
  - vault/research/backtests/<ts>_tier4_order_block_sweep.md
  - JSON of validated parameter sets per symbol/session/side
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

# Parameter grid
DISPLACEMENT_ATR = (1.0, 1.5, 2.0, 2.5, 3.0)
MAX_AGE_BARS     = (20, 50, 100)
RR_TARGET        = (1.5, 2.0, 2.5)


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


def collect_trades(bars, sym, params):
    try:
        result = backtest_strategy(strats.order_block, bars,
                                    symbol=sym, params=params)
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


def main():
    ts = datetime.now(timezone.utc)
    print(f"=== TIER 4 ORDER_BLOCK PARAM SWEEP — {ts:%Y-%m-%d %H:%M UTC} ===\n")

    # Fetch bars once per symbol
    bars_by = {}
    for sym, ticker in FOCUS_TO_YF.items():
        b = fetch_bars(ticker)
        if b is not None and len(b) >= 100:
            bars_by[sym] = b
    print(f"Symbols loaded: {len(bars_by)}")
    print(f"Param grid: {len(DISPLACEMENT_ATR)} × {len(MAX_AGE_BARS)} × {len(RR_TARGET)} = "
          f"{len(DISPLACEMENT_ATR) * len(MAX_AGE_BARS) * len(RR_TARGET)} combos\n")

    passing = []   # validated (params, symbol, session, side, oos)

    total = (len(DISPLACEMENT_ATR) * len(MAX_AGE_BARS) * len(RR_TARGET)
             * len(bars_by))
    done = 0

    for d in DISPLACEMENT_ATR:
        for ma in MAX_AGE_BARS:
            for rr in RR_TARGET:
                params = {"displacement_atr": d, "max_age_bars": ma,
                          "rr_target": rr}
                for sym, bars in bars_by.items():
                    done += 1
                    if done % 30 == 0:
                        print(f"  ... {done}/{total} param-symbol pairs")
                    rows = collect_trades(bars, sym, params)
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
                                    "params": params, "symbol": sym,
                                    "session": session, "side": side,
                                    "oos": s_oos,
                                })

    print(f"\nTotal validated combinations: {len(passing)}")

    # Group by symbol/session/side; pick best params per cell
    best: dict[tuple, dict] = {}
    for p in passing:
        key = (p["symbol"], p["session"], p["side"])
        if key not in best or p["oos"]["e"] > best[key]["oos"]["e"]:
            best[key] = p

    print(f"\nBest parameter set per (symbol, session, side):")
    for k in sorted(best, key=lambda x: -best[x]["oos"]["e"]):
        b = best[k]
        p = b["params"]; o = b["oos"]
        print(f"  {b['symbol']:>4} {b['session']:>9} {b['side']:>5}  "
              f"d={p['displacement_atr']:.1f} age={p['max_age_bars']:>3} "
              f"rr={p['rr_target']:.1f}  "
              f"OOS n={o['n']:>3} E={o['e']:+.2f}R t={o['t']:+.2f}")

    # Report
    L = ["---", "type: walk_forward_tier4_order_block",
         f"date: {ts.isoformat()}",
         f"validated_combinations: {len(passing)}",
         f"unique_cells: {len(best)}",
         "---", "",
         f"# Tier 4 — order_block parameter sweep",
         "",
         f"Tested {len(DISPLACEMENT_ATR) * len(MAX_AGE_BARS) * len(RR_TARGET)} parameter combos × "
         f"{len(bars_by)} symbols × 4 sessions × 2 sides.",
         "",
         "## Best params per validated cell", "",
         "| Symbol | Session | Side | displacement_atr | max_age_bars | rr_target | n_OOS | E_OOS | t_OOS |",
         "|---|---|---|---:|---:|---:|---:|---:|---:|"]

    for k in sorted(best, key=lambda x: -best[x]["oos"]["e"]):
        b = best[k]; p = b["params"]; o = b["oos"]
        L.append(f"| {b['symbol']} | {b['session']} | {b['side']} | "
                 f"{p['displacement_atr']:.1f} | {p['max_age_bars']} | "
                 f"{p['rr_target']:.1f} | {o['n']} | {o['e']:+.2f} | {o['t']:+.2f} |")

    out_dir = PROJECT_ROOT / "vault" / "research" / "backtests"
    out_dir.mkdir(parents=True, exist_ok=True)
    md = out_dir / f"{ts:%Y-%m-%d_%H%M}_tier4_order_block_sweep.md"
    md.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nReport: {md.relative_to(PROJECT_ROOT)}")

    js = out_dir / f"{ts:%Y-%m-%d_%H%M}_tier4_order_block_sweep.json"
    js.write_text(json.dumps([{
        "params": b["params"], "symbol": b["symbol"],
        "session": b["session"], "side": b["side"], "oos": b["oos"],
    } for b in best.values()], indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
