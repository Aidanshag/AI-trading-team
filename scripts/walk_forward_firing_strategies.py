"""Walk-forward validation for the strategies that are actually firing live
without prior OOS validation.

Today (2026-05-05) the auto_trader fired:
  GC  narrow_range_break  (×2)
  MCL narrow_range_break  (×2)
  NG  inside_bar_break    (×1)
  MNQ narrow_range_break  (×2 attempts; didn't fill)

Of these, 4 of 5 fills lost. The user directive: only let strategies trade
that have a confirmed walk-forward edge.

Test design:
  - 60-day 5m bars per symbol (yfinance)
  - 75/25 train/OOS split
  - For each (strategy, symbol): n, hit-rate, expectancy in R, t-stat
  - Verdict HOLDS if: OOS t-stat > 2.0 AND OOS E > 0 AND n_oos >= 30
                     OR OOS t-stat > 1.5 AND n_oos >= 50 (small-n grace)

Output:
  - vault/research/backtests/<ts>_firing_strategy_validation.md
  - Console table for stdout
  - Returns dict {strategy: {symbol: holds_bool}} for downstream gating
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


# Focus universe → yfinance proxy. Micros use the full-size underlying;
# strategies are price-pattern-based so signals transfer.
FOCUS_TO_YF = {
    "GC":  "GC=F",
    "MCL": "CL=F",   # micro CL uses full CL bars
    "NG":  "NG=F",
    "MNQ": "NQ=F",   # micro NQ uses full NQ bars
    "MES": "ES=F",   # micro ES uses full ES bars
    "ZN":  "ZN=F",
    "6E":  "6E=F",
}

# Strategies firing live without OOS validation
STRATEGIES_UNDER_TEST = {
    "narrow_range_break": strats.narrow_range_break,
    "inside_bar_break":   strats.inside_bar_break,
}


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
        rows.append({"strategy": label, "symbol": sym,
                     "entry_et": et, "side": t.side, "r": t.r_multiple})
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
    return (f"n={s['n']:>4} hit={s['hit']*100:>5.1f}% "
            f"E={s['e']:>+5.2f}R t={s['t']:>+5.2f}")


def verdict(s_oos):
    """Strict gate: OOS t > 2.0, OOS E > 0, n >= 30. Small-n grace at t>1.5,n>=50."""
    if s_oos is None:
        return False, "no OOS trades"
    if s_oos["e"] <= 0:
        return False, f"OOS E={s_oos['e']:+.2f}R <= 0"
    if s_oos["n"] < 30:
        return False, f"n_oos={s_oos['n']} < 30"
    if s_oos["t"] >= 2.0:
        return True, "t>=2.0 strict pass"
    if s_oos["t"] >= 1.5 and s_oos["n"] >= 50:
        return True, "t>=1.5 + n>=50 grace"
    return False, f"t={s_oos['t']:+.2f} < threshold"


def main():
    ts = datetime.now(timezone.utc)
    print(f"=== FIRING-STRATEGY WALK-FORWARD VALIDATION — "
          f"{ts:%Y-%m-%d %H:%M UTC} ===\n")

    # Fetch bars per symbol once
    bars_by_symbol = {}
    for sym, ticker in FOCUS_TO_YF.items():
        bars = fetch_bars(ticker)
        if bars is None or len(bars) < 100:
            print(f"  {sym} ({ticker}): FETCH FAILED or insufficient bars")
            continue
        bars_by_symbol[sym] = bars
        print(f"  {sym} ({ticker}): {len(bars)} bars  "
              f"[{bars.index[0]:%Y-%m-%d} → {bars.index[-1]:%Y-%m-%d}]")
    print()

    if not bars_by_symbol:
        print("NO USABLE BARS — aborting")
        return 1

    # Cutoff = last 25% of timeline (use any symbol's range as anchor)
    anchor = next(iter(bars_by_symbol.values()))
    span = anchor.index[-1] - anchor.index[0]
    cutoff = anchor.index[-1] - span * 0.25
    print(f"Walk-forward cutoff: {cutoff}\n")

    L = ["---", "type: walk_forward_firing_strategies",
         f"date: {ts.isoformat()}",
         f"cutoff: {cutoff}", "---", "",
         "# Walk-forward validation — strategies firing live without OOS proof",
         "",
         "Strategies tested: `narrow_range_break`, `inside_bar_break`",
         "Symbols: " + ", ".join(bars_by_symbol.keys()), "",
         "Verdict criteria: OOS t-stat ≥ 2.0 (strict) OR (t ≥ 1.5 AND n_oos ≥ 50).",
         "Both require OOS expectancy > 0 and n_oos ≥ 30.",
         "",
         "## Per (strategy, symbol) results",
         "",
         "| Strategy | Symbol | Train | OOS | Verdict | Reason |",
         "|---|---|---|---|---|---|"]

    results: dict[str, dict[str, bool]] = {}

    for strat_name, strat_fn in STRATEGIES_UNDER_TEST.items():
        print("=" * 70)
        print(f"STRATEGY: {strat_name}")
        print("=" * 70)
        results[strat_name] = {}
        for sym, bars in bars_by_symbol.items():
            rows, err = collect_trades(strat_name, strat_fn, bars, sym)
            if err:
                print(f"  {sym}: ERR — {err}")
                L.append(f"| {strat_name} | {sym} | err | err | ✗ | {err[:60]} |")
                results[strat_name][sym] = False
                continue
            train, test = split_at(rows, cutoff)
            s_tr, s_te = stats(train), stats(test)
            holds, why = verdict(s_te)
            results[strat_name][sym] = holds
            mark = "✓ HOLDS" if holds else "✗ fails"
            print(f"  {sym:>4}  TRAIN: {fmt(s_tr)}  OOS: {fmt(s_te)}  {mark}  ({why})")
            L.append(f"| {strat_name} | {sym} | {fmt(s_tr)} | {fmt(s_te)} | "
                     f"{mark} | {why} |")
        print()

    # Summary section
    L += ["", "## Validated combinations (will be added to STRATEGY_SYMBOL_ALLOWLIST)", ""]
    any_held = False
    for strat_name, by_sym in results.items():
        for sym, holds in by_sym.items():
            if holds:
                any_held = True
                L.append(f"- `{strat_name}` × `{sym}`")
    if not any_held:
        L.append("**NONE.** Both strategies fail OOS on every symbol tested. "
                 "Recommendation: remove from auto_trader's active strategy "
                 "set until parameter tuning produces an OOS-validated variant.")

    out = PROJECT_ROOT / "vault" / "research" / "backtests"
    out.mkdir(parents=True, exist_ok=True)
    md_path = out / f"{ts:%Y-%m-%d_%H%M}_firing_strategy_validation.md"
    md_path.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nReport: {md_path.relative_to(PROJECT_ROOT)}")

    # Also dump JSON for downstream gating
    json_path = out / f"{ts:%Y-%m-%d_%H%M}_firing_strategy_validation.json"
    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"JSON:   {json_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
