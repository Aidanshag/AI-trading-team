"""Walk-forward validation of the gap_fill ZN edge surfaced by the deep
analysis. Splits 60 days of 5m bars into train (first 45d) and held-out
test (last 15d). If the edge holds in the test window, gap_fill ZN is
safe to promote to Tier 1. If not, the edge is a curve-fit artifact and
shouldn't be deployed.

Tests:
- gap_fill on ZN, all sessions
- gap_fill on ZN, Asian session only
- gap_fill on ZN, PostClose session only
- gap_fill on all 7 symbols (sanity)

Plus: confirms inside_bar_break MES RTH and rejects vwap_reversion.

Usage:
    python scripts/walk_forward_gapfill.py
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
    except Exception as exc:
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


def split_by_date(rows, cutoff):
    train, test = [], []
    for r in rows:
        (train if r["entry_et"] < cutoff else test).append(r)
    return train, test


def report(label, rows, cutoff):
    train, test = split_by_date(rows, cutoff)
    s_all = stats(rows)
    s_tr = stats(train)
    s_te = stats(test)
    if s_all is None:
        print(f"  {label}: NO TRADES")
        return None
    def fmt(s):
        if s is None: return f"{'(empty)':>30}"
        return f"n={s['n']:>4} hit={s['hit']*100:>5.1f}% E={s['e']:>+5.2f}R t={s['t']:>+5.2f}"
    print(f"  {label:<40}")
    print(f"    full   : {fmt(s_all)}")
    print(f"    train  : {fmt(s_tr)}")
    print(f"    OOS    : {fmt(s_te)}")
    holds = (s_tr is not None and s_te is not None and
             s_tr['e'] > 0 and s_te['e'] > 0 and s_te['t'] > 1.5)
    print(f"    verdict: {'HOLDS OOS ✓' if holds else 'fails OOS ✗'}")
    print()
    return {"label": label, "all": s_all, "train": s_tr, "oos": s_te, "holds": holds}


def main():
    print(f"=== WALK-FORWARD VALIDATION — {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC} ===")
    print(f"  60d of 5m bars, split: first 45d=train, last 15d=held-out test")
    print(f"  Threshold: edge HOLDS if both train E>0 AND OOS E>0 AND OOS t>1.5")
    print()

    bars_by_symbol = {}
    for sym, ticker in SYMBOL_MAP.items():
        bars = fetch_bars(ticker)
        if bars is None or len(bars) < 200:
            print(f"  {sym}: insufficient")
            continue
        bars_by_symbol[sym] = bars
        print(f"  {sym}: {len(bars)} bars  [{bars.index[0]} → {bars.index[-1]}]")
    print()

    # Cutoff: 15 days before the last bar
    last_dt = max(b.index[-1] for b in bars_by_symbol.values())
    cutoff = last_dt - (last_dt - bars_by_symbol[list(bars_by_symbol)[0]].index[0]) * (15 / 60)
    print(f"  Cutoff: {cutoff}\n")

    results = []

    # ── gap_fill: the headline finding ──
    print("=== gap_fill — the headline finding ===\n")

    # All ZN
    rows = run_with_meta("gap_fill", strats.gap_fill, bars_by_symbol["ZN"], "ZN")
    results.append(report("gap_fill on ZN — ALL sessions", rows, cutoff))

    # ZN Asian only
    rows_asian = [r for r in rows if r["session"] == "Asian"]
    results.append(report("gap_fill on ZN — Asian only", rows_asian, cutoff))

    # ZN PostClose only
    rows_pc = [r for r in rows if r["session"] == "PostClose"]
    results.append(report("gap_fill on ZN — PostClose only", rows_pc, cutoff))

    # ZN Asian+PostClose combined
    rows_overnight = [r for r in rows if r["session"] in ("Asian", "PostClose")]
    results.append(report("gap_fill on ZN — Asian+PostClose combined", rows_overnight, cutoff))

    # gap_fill on all symbols
    print("=== gap_fill — other symbols (sanity check) ===\n")
    for sym in SYMBOL_MAP:
        if sym == "ZN" or sym not in bars_by_symbol: continue
        rows = run_with_meta("gap_fill", strats.gap_fill, bars_by_symbol[sym], sym)
        if len(rows) >= 30:
            results.append(report(f"gap_fill on {sym} — all", rows, cutoff))

    # ── inside_bar_break MES RTH (the secondary candidate) ──
    print("=== inside_bar_break MES RTH (secondary candidate) ===\n")
    rows = run_with_meta("inside_bar_break", strats.inside_bar_break, bars_by_symbol["MES"], "MES")
    rth_rows = [r for r in rows if r["session"] == "RTH"]
    results.append(report("inside_bar_break MES — RTH only", rth_rows, cutoff))

    # ── vwap_reversion: confirm it's broken ──
    print("=== vwap_reversion (confirming brokenness) ===\n")
    for sym in ("MES", "MNQ"):
        if sym not in bars_by_symbol: continue
        rows = run_with_meta("vwap_reversion", strats.vwap_reversion,
                             bars_by_symbol[sym], sym)
        results.append(report(f"vwap_reversion {sym} — all sessions", rows, cutoff))

    # Save report
    out = PROJECT_ROOT / "vault" / "research" / "backtests"
    out.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    md_path = out / f"{ts}_walk_forward_validation.md"

    L = ["---",
         f"type: walk_forward_validation",
         f"date: {datetime.now(timezone.utc).isoformat()}",
         f"cutoff: {cutoff}",
         "---",
         "",
         "# Walk-forward validation of gap_fill ZN edge",
         "",
         "Splits 60d of 5m bars into 45d train + 15d held-out test.",
         "Edge HOLDS if BOTH train and OOS E>0 AND OOS t>1.5.",
         "",
         "## Results",
         "",
         "| Label | n_train | E_train | t_train | n_oos | E_oos | t_oos | Holds |",
         "|---|---:|---:|---:|---:|---:|---:|---|"]
    for r in results:
        if r is None: continue
        tr, te = r["train"], r["oos"]
        L.append(f"| {r['label']} | "
                 f"{tr['n'] if tr else 0} | {tr['e']:+.2f}R if tr else 0 | "
                 f"{tr['t']:+.2f} if tr else 0 | "
                 f"{te['n'] if te else 0} | {te['e']:+.2f}R if te else 0 | "
                 f"{te['t']:+.2f} if te else 0 | "
                 f"{'✓ HOLDS' if r['holds'] else '✗ fails'} |")

    md_path.write_text("\n".join(L) + "\n", encoding="utf-8")

    # ── Final verdict ──
    print("=" * 70)
    print("VERDICT SUMMARY")
    print("=" * 70)
    for r in results:
        if r is None: continue
        print(f"  {'✓' if r['holds'] else '✗'} {r['label']}")
    print()
    print(f"Report: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
