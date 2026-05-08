"""Tier 2 walk-forward: per-symbol/session/side validation for the ICT
strategies (fair_value_gap, order_block, liquidity_sweep) at default params.

Phase 2 already found:
  fair_value_gap   → GC Asian short  (E=+0.50R t=+1.91)
  liquidity_sweep  → 6E London long, MES RTH long, MNQ RTH long
  order_block      → no validated cell at default params

This script re-runs at the cell level on fresh 60d 5m bars to confirm
those cells still hold (data drift check) and to surface any new cells
that became validated in the most recent month.

Output:
  - vault/research/backtests/<ts>_tier2_ict_sweep.md
  - JSON of newly-validated cells
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
    "GC":  "GC=F",
    "MCL": "CL=F",
    "NG":  "NG=F",
    "MNQ": "NQ=F",
    "MES": "ES=F",
    "ZN":  "ZN=F",
    "6E":  "6E=F",
}

STRATS = {
    "fair_value_gap":  strats.fair_value_gap,
    "order_block":     strats.order_block,
    "liquidity_sweep": strats.liquidity_sweep,
}


def session_bucket(et_hour: float) -> str:
    if 9.5 <= et_hour < 16:    return "RTH"
    if 4 <= et_hour < 9.5:     return "London"
    if 16 <= et_hour < 20:     return "PostClose"
    return "Asian"


def fetch_bars(ticker: str, period: str = "60d"):
    df = yf.download(ticker, period=period, interval="5m", progress=False, auto_adjust=False)
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


def collect_trades(label, fn, bars, sym):
    try:
        result = backtest_strategy(fn, bars, symbol=sym, params={})
    except Exception as exc:
        return [], str(exc)
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
            "strategy": label, "symbol": sym, "entry_et": et,
            "side": t.side, "r": t.r_multiple,
            "session": session_bucket(et.hour + et.minute / 60),
        })
    return rows, None


def stats(rows):
    n = len(rows)
    if n == 0:
        return None
    rs = [r["r"] for r in rows]
    hit = sum(1 for r in rs if r > 0) / n
    e = mean(rs)
    sd = stdev(rs) if n > 1 else 0
    t = (e / (sd / (n ** 0.5))) if (sd > 0 and n > 1) else 0
    return {"n": n, "hit": hit, "e": e, "t": t}


def split_at(rows, cutoff):
    return ([r for r in rows if r["entry_et"] < cutoff],
            [r for r in rows if r["entry_et"] >= cutoff])


def fmt(s):
    if s is None:
        return "(empty)"
    return f"n={s['n']:>3} E={s['e']:>+.2f}R t={s['t']:>+.2f}"


def verdict(s_oos):
    if s_oos is None:
        return False, "no OOS"
    if s_oos["e"] <= 0:
        return False, f"E={s_oos['e']:+.2f}<=0"
    if s_oos["n"] < 8:
        return False, f"n={s_oos['n']}<8"
    if s_oos["t"] >= 1.5:
        return True, "PASS"
    return False, f"t={s_oos['t']:+.2f}<1.5"


def main():
    ts = datetime.now(timezone.utc)
    print(f"=== TIER 2 ICT SWEEP — {ts:%Y-%m-%d %H:%M UTC} ===\n")

    bars_by_sym = {}
    for sym, ticker in FOCUS_TO_YF.items():
        bars = fetch_bars(ticker)
        if bars is None or len(bars) < 100:
            continue
        bars_by_sym[sym] = bars
    print(f"Symbols loaded: {sorted(bars_by_sym)}\n")

    if not bars_by_sym:
        print("NO BARS — abort")
        return 1

    anchor = next(iter(bars_by_sym.values()))
    span = anchor.index[-1] - anchor.index[0]
    cutoff = anchor.index[-1] - span * 0.25

    L = ["---", "type: walk_forward_tier2_ict",
         f"date: {ts.isoformat()}", f"cutoff: {cutoff}", "---", "",
         "# Tier 2 ICT walk-forward — per-cell validation",
         "",
         "Strategies: `fair_value_gap`, `order_block`, `liquidity_sweep`",
         "Cells: symbol × session × side.",
         "Pass: OOS E>0, OOS n>=8, OOS t>=1.5.",
         "",
         "## Validated cells (sorted by OOS E)",
         "",
         "| Strategy | Symbol | Session | Side | n_train | E_train | t_train | n_oos | E_oos | t_oos |",
         "|---|---|---|---|---:|---:|---:|---:|---:|---:|"]

    passing = []
    for strat_name, strat_fn in STRATS.items():
        for sym, bars in bars_by_sym.items():
            rows, err = collect_trades(strat_name, strat_fn, bars, sym)
            if err:
                continue
            for session in ("Asian", "London", "RTH", "PostClose"):
                for side in ("long", "short"):
                    cell = [r for r in rows
                            if r["session"] == session and r["side"] == side]
                    if not cell:
                        continue
                    train, test = split_at(cell, cutoff)
                    s_tr = stats(train)
                    s_te = stats(test)
                    holds, why = verdict(s_te)
                    if holds:
                        passing.append({
                            "strategy": strat_name, "symbol": sym,
                            "session": session, "side": side,
                            "train": s_tr, "oos": s_te,
                        })

    passing.sort(key=lambda x: -x["oos"]["e"])
    for p in passing:
        L.append(f"| {p['strategy']} | {p['symbol']} | {p['session']} | "
                 f"{p['side']} | "
                 f"{p['train']['n']} | {p['train']['e']:+.2f} | {p['train']['t']:+.2f} | "
                 f"{p['oos']['n']} | {p['oos']['e']:+.2f} | {p['oos']['t']:+.2f} |")
        print(f"  {p['strategy']} {p['symbol']} {p['session']:>9} {p['side']:>5}  "
              f"TRAIN: {fmt(p['train'])}  OOS: {fmt(p['oos'])}")

    print(f"\n{len(passing)} validated cells")

    if passing:
        L += ["", "## Suggested STRATEGY_CELL_ALLOWLIST additions", "", "```python"]
        for p in passing:
            L.append(f'    {{"symbol": "{p["symbol"]}", "session": "{p["session"]}", '
                     f'"side": "{p["side"]}"}},  # {p["strategy"]} OOS '
                     f'E={p["oos"]["e"]:+.2f}R t={p["oos"]["t"]:+.2f}')
        L.append("```")

    out = PROJECT_ROOT / "vault" / "research" / "backtests"
    out.mkdir(parents=True, exist_ok=True)
    md_path = out / f"{ts:%Y-%m-%d_%H%M}_tier2_ict_sweep.md"
    md_path.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nReport: {md_path.relative_to(PROJECT_ROOT)}")

    json_path = out / f"{ts:%Y-%m-%d_%H%M}_tier2_ict_sweep.json"
    json_path.write_text(json.dumps(passing, indent=2, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
