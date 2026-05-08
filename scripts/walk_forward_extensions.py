"""Two extension validations:

1. narrow_range_break on GC during Asian session — the strategy that
   produced the 2026-04-29 winner. Deep analysis showed t=+2.85 over 30d.
   Walk-forward to confirm it holds OOS.

2. Parameter variant sweep on gap_fill ZN — try (min_gap_atr × rr_target)
   combinations to see if a non-default parameter set has better OOS edge.

Output: vault/research/backtests/<date>_extensions.md
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


def run_with_meta(label, fn, bars, sym, params=None):
    try:
        result = backtest_strategy(fn, bars, symbol=sym, params=params or {})
    except Exception as exc:
        print(f"  ERR: {exc}")
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


def fmt(s):
    if s is None: return "(empty)"
    return f"n={s['n']:>4} hit={s['hit']*100:>5.1f}% E={s['e']:>+5.2f}R t={s['t']:>+5.2f}"


def main():
    print(f"=== EXTENSION VALIDATIONS — {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC} ===\n")

    # Fetch ZN + GC bars
    bars_zn = fetch_bars("ZN=F")
    bars_gc = fetch_bars("GC=F")
    if not (bars_zn is not None and bars_gc is not None):
        print("FETCH FAILED")
        return 1
    print(f"  ZN: {len(bars_zn)} bars  [{bars_zn.index[0]} → {bars_zn.index[-1]}]")
    print(f"  GC: {len(bars_gc)} bars  [{bars_gc.index[0]} → {bars_gc.index[-1]}]")

    # Cutoff = last 25% as held-out test
    span = bars_zn.index[-1] - bars_zn.index[0]
    cutoff = bars_zn.index[-1] - span * 0.25
    print(f"  Cutoff for walk-forward: {cutoff}\n")

    L = ["---", f"type: walk_forward_extensions",
         f"date: {datetime.now(timezone.utc).isoformat()}", f"cutoff: {cutoff}",
         "---", "", "# Walk-forward extensions"]

    # ── EXTENSION 1: narrow_range_break GC Asian ──
    print("=" * 68)
    print("EXTENSION 1: narrow_range_break GC — Asian session only")
    print("=" * 68)
    rows = run_with_meta("narrow_range_break", strats.narrow_range_break, bars_gc, "GC")
    rows_asian = [r for r in rows if r["session"] == "Asian"]
    rows_long = [r for r in rows_asian if r["side"] == "long"]
    rows_short = [r for r in rows_asian if r["side"] == "short"]

    L += ["", "## Extension 1: narrow_range_break GC Asian (the 2026-04-29 winner pattern)",
          "", "| Slice | Train | OOS | Verdict |", "|---|---|---|---|"]
    print()
    for label, sub in [("All Asian (long+short)", rows_asian),
                       ("Asian LONG only (matches 4/29 winner)", rows_long),
                       ("Asian SHORT only", rows_short)]:
        train, test = split(sub, cutoff)
        s_tr, s_te = stats(train), stats(test)
        s_all = stats(sub)
        holds = (s_tr is not None and s_te is not None and
                 s_tr['e'] > 0 and s_te['e'] > 0 and s_te['t'] > 1.5)
        print(f"  {label}")
        print(f"    full : {fmt(s_all)}")
        print(f"    train: {fmt(s_tr)}")
        print(f"    OOS  : {fmt(s_te)}")
        print(f"    verdict: {'HOLDS ✓' if holds else 'fails ✗'}\n")
        v = "✓ HOLDS" if holds else "✗ fails"
        L.append(f"| {label} | {fmt(s_tr)} | {fmt(s_te)} | {v} |")

    # ── EXTENSION 2: gap_fill ZN parameter sweep ──
    print("=" * 68)
    print("EXTENSION 2: gap_fill ZN parameter sweep (walk-forward)")
    print("=" * 68)
    print()
    L += ["", "## Extension 2: gap_fill ZN parameter variants (walk-forward)", "",
          "| min_gap_atr | rr_target | n_train | E_train | t_train | n_oos | E_oos | t_oos | Holds |",
          "|---:|---:|---:|---:|---:|---:|---:|---:|---|"]

    candidates = []
    for min_gap in (0.50, 0.75, 1.00, 1.25):
        for rr in (1.0, 1.5, 2.0):
            params = {"min_gap_atr": min_gap, "rr_target": rr}
            label = f"gf gap={min_gap} rr={rr}"
            rows = run_with_meta("gap_fill", strats.gap_fill, bars_zn, "ZN", params)
            train, test = split(rows, cutoff)
            s_tr, s_te = stats(train), stats(test)
            holds = (s_tr is not None and s_te is not None and
                     s_tr['e'] > 0 and s_te['e'] > 0 and s_te['t'] > 1.5)
            tr_str = fmt(s_tr); te_str = fmt(s_te)
            print(f"  {label:<24}  TRAIN: {tr_str}  OOS: {te_str}  {'✓' if holds else '✗'}")
            L.append(f"| {min_gap} | {rr} | "
                     f"{s_tr['n'] if s_tr else 0} | {s_tr['e']:+.2f} | {s_tr['t']:+.2f} | "
                     f"{s_te['n'] if s_te else 0} | {s_te['e']:+.2f} | {s_te['t']:+.2f} | "
                     f"{'✓' if holds else '✗'} |")
            if holds and s_te["e"] > 0.5:
                candidates.append({
                    "min_gap": min_gap, "rr": rr,
                    "oos_n": s_te["n"], "oos_e": s_te["e"], "oos_t": s_te["t"],
                    "train_e": s_tr["e"], "train_t": s_tr["t"],
                })

    # Best variant
    if candidates:
        candidates.sort(key=lambda x: -x["oos_e"])
        best = candidates[0]
        print(f"\n  BEST VARIANT: min_gap_atr={best['min_gap']} rr_target={best['rr']}")
        print(f"  TRAIN: E={best['train_e']:+.2f}R t={best['train_t']:+.2f}")
        print(f"  OOS  : n={best['oos_n']} E={best['oos_e']:+.2f}R t={best['oos_t']:+.2f}")
    else:
        print("\n  No variant clearly beats default (min_gap=0.75 rr=1.5)")

    out = PROJECT_ROOT / "vault" / "research" / "backtests"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    md_path = out / f"{ts}_extensions.md"
    md_path.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nReport: {md_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
