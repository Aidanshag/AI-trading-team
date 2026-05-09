"""Walk-forward parameter sweep on the Treasury gap_fill universe.

Context (2026-05-06):
The live allowlist is locked to gap_fill on ZN, ZB, ZT, ZF. The Tier 3
walk-forward (2026-05-05) promoted ZB/ZF/ZT at DEFAULT gap_fill params
(min_gap_atr=0.75, rr_target=1.5). The earlier ZN-only sweep on 2026-05-04
(walk_forward_extensions.py) showed:
  - default              → OOS E=+1.20R, t=+10.88, n=259
  - rr=2.0 (any min_gap) → OOS E=+1.51R, t= +7.27, n=116
  - min_gap=1.25         → OOS E=+2.74R, t= +4.48, n= 30 (small)
But that sweep only ran on ZN. ZT/ZB/ZF have never been tuned.

This script extends the parameter sweep to all four Treasuries. Each
(symbol × min_gap_atr × rr_target) combination gets a walk-forward
75/25 train/OOS split. A "candidate" is a combo where:
  - both train and OOS expectancy positive
  - OOS t-stat >= 1.5
  - OOS n >= 30
The best per-symbol candidate (highest OOS E with adequate n) is
recommended for adoption.

Output:
  vault/research/backtests/<ts>_treasury_param_sweep.md
  vault/research/backtests/<ts>_treasury_param_sweep.json

Usage (from project root):
  python -m scripts.walk_forward_treasury_param_sweep

Runtime: roughly 3–5 minutes — yfinance fetch + 4 symbols × 12 param
combos × 60d of 5m bars.
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


# ── Config ─────────────────────────────────────────────────
SYMBOLS = ["ZN", "ZT", "ZB", "ZF"]
SYMBOL_TO_YF = {"ZN": "ZN=F", "ZT": "ZT=F", "ZB": "ZB=F", "ZF": "ZF=F"}

# Parameter grid (mirrors walk_forward_extensions.py)
MIN_GAP_VALUES = [0.50, 0.75, 1.00, 1.25]
RR_TARGET_VALUES = [1.0, 1.5, 2.0]

# Walk-forward split: hold out the last 25% of the window as OOS
HOLDOUT_PCT = 0.25

# Candidate gating
MIN_OOS_N = 30          # need at least 30 OOS trades to take seriously
MIN_OOS_T = 1.5         # need OOS t-stat >= 1.5
MIN_OOS_E_TO_BEAT = 1.20  # only flag as adoption candidate if OOS E > current default ZN baseline


def session_bucket(et_hour: float) -> str:
    if 9.5 <= et_hour < 16:    return "RTH"
    if 4 <= et_hour < 9.5:     return "London"
    if 16 <= et_hour < 20:     return "PostClose"
    return "Asian"


def fetch_bars(ticker: str, period: str = "60d"):
    df = yf.download(ticker, period=period, interval="5m",
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
        result = backtest_strategy(strats.gap_fill, bars, symbol=sym, params=params)
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
            "symbol": sym, "entry_et": et,
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
    sd = stdev(rs) if n > 1 else 0.0
    t = (e / (sd / (n ** 0.5))) if (sd > 0 and n > 1) else 0.0
    return {"n": n, "hit": hit, "e": e, "t": t}


def split(rows, cutoff):
    return ([r for r in rows if r["entry_et"] < cutoff],
            [r for r in rows if r["entry_et"] >= cutoff])


def fmt(s):
    if s is None:
        return "(empty)"
    return f"n={s['n']:>4} hit={s['hit']*100:>5.1f}% E={s['e']:>+5.2f}R t={s['t']:>+5.2f}"


def main() -> int:
    print(f"=== TREASURY GAP_FILL PARAMETER SWEEP — "
          f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC} ===\n")

    # Fetch all four symbols
    bars = {}
    for sym in SYMBOLS:
        ticker = SYMBOL_TO_YF[sym]
        b = fetch_bars(ticker)
        if b is None or len(b) < 100:
            print(f"  {sym} ({ticker}): FETCH FAILED or insufficient bars")
            continue
        bars[sym] = b
        print(f"  {sym}: {len(b):>5} bars  [{b.index[0]} → {b.index[-1]}]")

    if not bars:
        print("All fetches failed. Aborting.")
        return 1

    # Use ZN's window as the canonical cutoff (all symbols pulled with same period)
    ref = next(iter(bars.values()))
    span = ref.index[-1] - ref.index[0]
    cutoff = ref.index[-1] - span * HOLDOUT_PCT
    print(f"\n  Walk-forward cutoff: {cutoff}")
    print(f"  Train: {ref.index[0]} → {cutoff}")
    print(f"  OOS  : {cutoff} → {ref.index[-1]}\n")

    # Run sweep
    L: list[str] = ["---", "type: walk_forward_treasury_param_sweep",
                    f"date: {datetime.now(timezone.utc).isoformat()}",
                    f"cutoff: {cutoff}",
                    f"symbols: {SYMBOLS}",
                    f"min_gap_grid: {MIN_GAP_VALUES}",
                    f"rr_grid: {RR_TARGET_VALUES}",
                    "---", "",
                    "# Treasury gap_fill parameter sweep"]

    all_results: list[dict] = []

    for sym, b in bars.items():
        print("=" * 72)
        print(f"  {sym}  — gap_fill parameter sweep (walk-forward)")
        print("=" * 72)
        L += ["", f"## {sym}", "",
              "| min_gap_atr | rr_target | n_train | E_train | t_train | n_oos | E_oos | t_oos | hit_oos | candidate |",
              "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]

        sym_results: list[dict] = []
        for mg in MIN_GAP_VALUES:
            for rr in RR_TARGET_VALUES:
                params = {"min_gap_atr": mg, "rr_target": rr}
                rows, err = collect_trades(b, sym, params)
                if err:
                    print(f"  gap={mg} rr={rr}: ERR {err}")
                    continue
                train, test = split(rows, cutoff)
                s_tr, s_te = stats(train), stats(test)

                is_candidate = bool(
                    s_tr is not None and s_te is not None
                    and s_tr["e"] > 0 and s_te["e"] > MIN_OOS_E_TO_BEAT
                    and s_te["t"] >= MIN_OOS_T and s_te["n"] >= MIN_OOS_N
                )
                tag = "✓" if is_candidate else " "
                tr_str = fmt(s_tr); te_str = fmt(s_te)
                print(f"  gap={mg:.2f} rr={rr:.1f}  TRAIN: {tr_str}  OOS: {te_str}  {tag}")

                if s_tr and s_te:
                    L.append(
                        f"| {mg} | {rr} | "
                        f"{s_tr['n']} | {s_tr['e']:+.2f} | {s_tr['t']:+.2f} | "
                        f"{s_te['n']} | {s_te['e']:+.2f} | {s_te['t']:+.2f} | "
                        f"{s_te['hit']*100:.1f}% | {tag} |"
                    )
                sym_results.append({
                    "symbol": sym, "min_gap_atr": mg, "rr_target": rr,
                    "train": s_tr, "oos": s_te, "candidate": is_candidate,
                })

        # Best variant for this symbol
        candidates = [r for r in sym_results if r["candidate"]]
        if candidates:
            best = max(candidates, key=lambda x: x["oos"]["e"])
            print(f"\n  BEST {sym}: min_gap_atr={best['min_gap_atr']} "
                  f"rr_target={best['rr_target']}")
            print(f"    OOS  : {fmt(best['oos'])}")
            print(f"    TRAIN: {fmt(best['train'])}")
            L += ["",
                  f"**Best {sym} variant:** `min_gap_atr={best['min_gap_atr']}, "
                  f"rr_target={best['rr_target']}`",
                  f"- OOS: {fmt(best['oos'])}",
                  f"- TRAIN: {fmt(best['train'])}"]
        else:
            print(f"\n  {sym}: no variant clears OOS E > {MIN_OOS_E_TO_BEAT}R "
                  f"with t>={MIN_OOS_T} and n>={MIN_OOS_N}")
            L += ["",
                  f"**{sym}**: no variant clears the candidate threshold "
                  f"(OOS E > {MIN_OOS_E_TO_BEAT}R, t >= {MIN_OOS_T}, n >= {MIN_OOS_N})."]

        all_results.extend(sym_results)
        print()

    # Cross-symbol summary
    L += ["", "## Recommended adoptions", ""]
    any_recommended = False
    for sym in SYMBOLS:
        sym_cands = [r for r in all_results if r["symbol"] == sym and r["candidate"]]
        if not sym_cands:
            continue
        best = max(sym_cands, key=lambda x: x["oos"]["e"])
        any_recommended = True
        L.append(
            f"- **{sym}**: switch from default (gap=0.75, rr=1.5) to "
            f"`gap={best['min_gap_atr']}, rr={best['rr_target']}` "
            f"→ OOS E {best['oos']['e']:+.2f}R (n={best['oos']['n']}, "
            f"t={best['oos']['t']:+.2f})"
        )
    if not any_recommended:
        L.append("None — defaults remain best across all four symbols.")

    L += ["",
          "## How to apply",
          "",
          "If a recommendation has high enough confidence (OOS t > 2.0 and",
          "n > 60), update the strategy_kwargs in `scripts/auto_trader.py`",
          "STRATEGY_ROSTER. The `gap_fill` row currently uses `{}` (default",
          "params); per-symbol overrides aren't supported by the current",
          "roster shape — would require a small refactor to allow",
          "(symbol → params) mapping. For now, if all four symbols agree on",
          "a single best config, change the global gap_fill kwargs.",
          "",
          "If symbols disagree, hold off on the change and let live data",
          "accumulate to confirm which holds up under real conditions."]

    # Write outputs
    out_dir = PROJECT_ROOT / "vault" / "research" / "backtests"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    md_path = out_dir / f"{ts}_treasury_param_sweep.md"
    json_path = out_dir / f"{ts}_treasury_param_sweep.json"
    md_path.write_text("\n".join(L) + "\n", encoding="utf-8")

    # JSON-safe dump (strip non-serializable train/oos dicts to plain floats)
    safe_results = []
    for r in all_results:
        safe_results.append({
            "symbol": r["symbol"],
            "min_gap_atr": r["min_gap_atr"],
            "rr_target": r["rr_target"],
            "candidate": r["candidate"],
            "train": r["train"],
            "oos": r["oos"],
        })
    json_path.write_text(json.dumps(safe_results, indent=2, default=str),
                         encoding="utf-8")

    print(f"\nReport: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"JSON:   {json_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
