"""Tier 3 walk-forward: extend the validated gap_fill edge to neighboring
symbols and timeframes.

Currently validated (CLAUDE.md): gap_fill on ZN, NG, 6E at 5m intraday.
Test extensions:
  - Treasury cousins: ZB (30y), ZF (5y), ZT (2y) — same gap-fill mean
    reversion logic as ZN (10y)
  - FX cousins: 6B, 6J, 6A, 6C — same logic as 6E
  - Energy cousins: CL (with MCL price-pattern equivalence)
  - Timeframes: 15m and 30m bars on the already-validated symbols (ZN, NG, 6E)

Output:
  - vault/research/backtests/<ts>_tier3_gapfill_extensions.md
  - JSON of new validated combinations
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


# Symbol → yfinance ticker
SYMBOL_TO_YF = {
    # Validated already
    "ZN": "ZN=F",
    "NG": "NG=F",
    "6E": "6E=F",
    # Treasury cousins of ZN
    "ZB": "ZB=F",   # 30-year
    "ZF": "ZF=F",   # 5-year
    "ZT": "ZT=F",   # 2-year
    # FX cousins of 6E
    "6B": "6B=F",   # GBP/USD
    "6J": "6J=F",   # JPY/USD
    "6A": "6A=F",   # AUD/USD
    "6C": "6C=F",   # CAD/USD
    # Energy cousin
    "CL": "CL=F",
}

# Timeframes (in minutes) to test
TIMEFRAMES = [5, 15, 30]


def fetch_bars(ticker: str, interval: str, period: str = "60d"):
    df = yf.download(ticker, period=period, interval=interval,
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


def collect_trades(bars, sym):
    try:
        result = backtest_strategy(strats.gap_fill, bars, symbol=sym, params={})
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
        rows.append({"symbol": sym, "entry_et": et, "side": t.side, "r": t.r_multiple})
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
    if s_oos["n"] < 20:
        return False, f"n={s_oos['n']}<20"
    if s_oos["t"] >= 1.5:
        return True, "PASS"
    return False, f"t={s_oos['t']:+.2f}<1.5"


def main():
    ts = datetime.now(timezone.utc)
    print(f"=== TIER 3 GAP_FILL EXTENSIONS — {ts:%Y-%m-%d %H:%M UTC} ===\n")

    L = ["---", "type: walk_forward_tier3_gapfill_extensions",
         f"date: {ts.isoformat()}", "---", "",
         "# Tier 3 — gap_fill extensions to cousin symbols + timeframes",
         "",
         "Pass: OOS E>0, OOS n>=20, OOS t>=1.5.",
         "",
         "## All combinations tested",
         "",
         "| Symbol | TF | n_train | E_train | t_train | n_oos | E_oos | t_oos | Verdict |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---|"]

    passing = []

    for sym, ticker in SYMBOL_TO_YF.items():
        for tf in TIMEFRAMES:
            interval = f"{tf}m"
            bars = fetch_bars(ticker, interval)
            if bars is None or len(bars) < 60:
                print(f"  {sym:>3} {tf:>2}m: insufficient bars")
                L.append(f"| {sym} | {tf}m | - | - | - | - | - | - | NO BARS |")
                continue

            rows, err = collect_trades(bars, sym)
            if err:
                print(f"  {sym:>3} {tf:>2}m: ERR — {err}")
                continue

            span = bars.index[-1] - bars.index[0]
            cutoff = bars.index[-1] - span * 0.25
            train, test = split_at(rows, cutoff)
            s_tr = stats(train)
            s_te = stats(test)
            holds, why = verdict(s_te)
            mark = "✓" if holds else "✗"
            print(f"  {sym:>3} {tf:>2}m  TRAIN: {fmt(s_tr)}  OOS: {fmt(s_te)}  {mark} {why}")

            tr_str = (f"{s_tr['n']} | {s_tr['e']:+.2f} | {s_tr['t']:+.2f}"
                      if s_tr else "0 | - | -")
            te_str = (f"{s_te['n']} | {s_te['e']:+.2f} | {s_te['t']:+.2f}"
                      if s_te else "0 | - | -")
            L.append(f"| {sym} | {tf}m | {tr_str} | {te_str} | {mark} {why} |")

            if holds:
                passing.append({
                    "symbol": sym, "timeframe": f"{tf}m",
                    "train": s_tr, "oos": s_te,
                })

    L += ["", f"## Summary: {len(passing)} validated combinations", ""]
    if passing:
        passing.sort(key=lambda x: -x["oos"]["e"])
        for p in passing:
            L.append(f"- `gap_fill` × `{p['symbol']}` × `{p['timeframe']}`  "
                     f"OOS E={p['oos']['e']:+.2f}R t={p['oos']['t']:+.2f} n={p['oos']['n']}")
    else:
        L.append("- None of the extensions hold OOS at default params.")

    out = PROJECT_ROOT / "vault" / "research" / "backtests"
    out.mkdir(parents=True, exist_ok=True)
    md_path = out / f"{ts:%Y-%m-%d_%H%M}_tier3_gapfill_extensions.md"
    md_path.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\n{len(passing)} validated combinations")
    print(f"Report: {md_path.relative_to(PROJECT_ROOT)}")

    json_path = out / f"{ts:%Y-%m-%d_%H%M}_tier3_gapfill_extensions.json"
    json_path.write_text(json.dumps(passing, indent=2, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
