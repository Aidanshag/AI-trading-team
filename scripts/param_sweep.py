"""Generic walk-forward parameter sweep framework.

Takes (strategy_name × param_grid × symbol_list × period × interval),
runs walk-forward backtest for every combination, writes results to
`vault/research/param_sweeps/<strategy>_<date>.csv` (+ a markdown
summary).

Replaces the pattern of writing a new walk_forward_*.py script for each
sweep (walk_forward_extensions, walk_forward_tier3, etc.). Now any
strategy in tools/backtest/strategies.py registry can be swept with one
command.

URGENT USE-CASE (per cowork_coordination.md 2026-05-08, item #2):
The CLI agent's slippage finding showed gap_fill is extremely sensitive
to slippage — survives at near-zero slippage, fails at 0.25 tick/side.
We need a gap_fill parameterization with enough per-trade R to absorb
realistic 0.25-0.5 tick slippage. First sweep:
  --strategy gap_fill
  --params 'min_gap_atr=0.5,0.75,1.0,1.5; rr_target=1.0,1.25,1.5,2.0'
  --symbols ZN,ZT,ZB,ZF
= 4 × 4 × 4 = 64 runs.

USAGE:
  python -m scripts.param_sweep --strategy gap_fill \
    --params 'min_gap_atr=0.5,0.75,1.0,1.5;rr_target=1.0,1.25,1.5,2.0' \
    --symbols ZN,ZT,ZB,ZF
  python -m scripts.param_sweep --help

REQUIRES: yfinance (for bar fetch). Won't run in network-restricted
sandboxes; intended to run on the trading host.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, stdev

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── Symbol → yfinance ticker ───────────────────────────────────
SYMBOL_TO_YF = {
    # Treasury
    "ZN": "ZN=F", "ZT": "ZT=F", "ZB": "ZB=F", "ZF": "ZF=F",
    # Energy
    "NG": "NG=F", "CL": "CL=F", "MCL": "CL=F", "RB": "RB=F", "HO": "HO=F",
    # Index
    "MES": "ES=F", "MNQ": "NQ=F", "ES": "ES=F", "NQ": "NQ=F",
    # FX
    "6E": "6E=F", "6B": "6B=F", "6J": "6J=F", "6A": "6A=F", "6C": "6C=F",
    # Metals
    "GC": "GC=F", "SI": "SI=F", "HG": "HG=F",
}


# ── Bar fetch ──────────────────────────────────────────────────

def fetch_bars(symbol: str, interval: str = "5m", period: str = "60d"):
    """Pull bars via yfinance. Returns DataFrame indexed by ET timestamp,
    columns: Open/High/Low/Close/Volume. None on failure."""
    try:
        import yfinance as yf
    except ImportError:
        print("ERROR: yfinance not installed. Run: pip install yfinance",
              file=sys.stderr)
        return None
    ticker = SYMBOL_TO_YF.get(symbol, f"{symbol}=F")
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


def session_for_hour_minute(h: float) -> str:
    if 9.5 <= h < 16:    return "RTH"
    if 4 <= h < 9.5:     return "London"
    if 16 <= h < 20:     return "PostClose"
    return "Asian"


# ── Strategy invocation ────────────────────────────────────────

def get_strategy_fn(strategy_name: str):
    """Look up the strategy callable in tools/backtest/strategies.py."""
    from tools.backtest import strategies as strats
    fn = getattr(strats, strategy_name, None)
    if fn is None or not callable(fn):
        raise ValueError(f"strategy '{strategy_name}' not found in "
                         f"tools.backtest.strategies")
    return fn


def run_strategy(strategy_fn, bars, symbol: str, params: dict) -> list[dict]:
    """Invoke the strategy; return per-trade rows with R-multiples.
    Mirrors the existing walk_forward_*.py pattern."""
    from tools.backtest.engine import backtest_strategy
    try:
        result = backtest_strategy(strategy_fn, bars, symbol=symbol, params=params)
    except Exception as e:
        print(f"  err: backtest_strategy failed for {symbol}/{params}: "
              f"{type(e).__name__}: {e}", file=sys.stderr)
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
        rows.append({
            "symbol": symbol, "entry_et": et, "side": t.side,
            "r": t.r_multiple,
            "session": session_for_hour_minute(et.hour + et.minute / 60),
        })
    return rows


# ── Walk-forward stats ─────────────────────────────────────────

def stats(rows: list[dict]) -> dict | None:
    if not rows:
        return None
    rs = [r["r"] for r in rows]
    n = len(rs)
    hit = sum(1 for r in rs if r > 0) / n
    e = mean(rs)
    sd = stdev(rs) if n > 1 else 0.0
    t = (e / (sd / (n ** 0.5))) if (sd > 0 and n > 1) else 0.0
    return {"n": n, "hit": hit, "e": e, "t": t}


def split_train_oos(rows: list[dict], holdout_pct: float, ref_index):
    """Split rows by entry timestamp. Cutoff = ref_index[-1] − span × holdout_pct."""
    if not ref_index.size:
        return rows, []
    span = ref_index[-1] - ref_index[0]
    cutoff = ref_index[-1] - span * holdout_pct
    train = [r for r in rows if r["entry_et"] < cutoff]
    oos = [r for r in rows if r["entry_et"] >= cutoff]
    return train, oos, cutoff


# ── Param-grid expansion ───────────────────────────────────────

def parse_param_grid(spec: str) -> dict[str, list]:
    """Parse 'min_gap_atr=0.5,0.75,1.0; rr_target=1.5,2.0' into a dict
    of param-name → list-of-values. Numeric strings are parsed as floats
    when possible, else left as strings."""
    grid: dict[str, list] = {}
    for chunk in spec.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" not in chunk:
            raise ValueError(f"param chunk missing '=': {chunk!r}")
        name, vals = chunk.split("=", 1)
        name = name.strip()
        parsed: list = []
        for v in vals.split(","):
            v = v.strip()
            try:
                parsed.append(float(v))
            except ValueError:
                parsed.append(v)
        grid[name] = parsed
    return grid


def grid_combinations(grid: dict[str, list]) -> list[dict]:
    """Expand the grid into a list of param dicts."""
    if not grid:
        return [{}]
    keys = list(grid.keys())
    values = [grid[k] for k in keys]
    out = []
    for combo in itertools.product(*values):
        out.append(dict(zip(keys, combo)))
    return out


# ── Walk-forward run ───────────────────────────────────────────

def run_sweep(strategy_name: str, grid: dict[str, list],
              symbols: list[str], period: str, interval: str,
              holdout_pct: float) -> list[dict]:
    """Run the full sweep. Returns list of result dicts."""
    print(f"=== PARAM SWEEP — {strategy_name} ===")
    print(f"  symbols: {symbols}")
    print(f"  grid: {grid}")
    n_combos = len(grid_combinations(grid))
    print(f"  combos: {n_combos} × {len(symbols)} symbols = "
          f"{n_combos * len(symbols)} runs")
    print()

    strategy_fn = get_strategy_fn(strategy_name)

    # Fetch bars once per symbol
    bars_by_sym: dict = {}
    for sym in symbols:
        b = fetch_bars(sym, interval=interval, period=period)
        if b is None or len(b) < 100:
            print(f"  {sym}: FETCH FAILED or insufficient bars")
            continue
        bars_by_sym[sym] = b
        print(f"  {sym}: {len(b)} bars  "
              f"[{b.index[0]} → {b.index[-1]}]")

    print()
    results: list[dict] = []
    for sym, b in bars_by_sym.items():
        for params in grid_combinations(grid):
            rows = run_strategy(strategy_fn, b, sym, params)
            train, oos, cutoff = split_train_oos(rows, holdout_pct, b.index)
            s_tr = stats(train)
            s_oos = stats(oos)
            results.append({
                "strategy": strategy_name, "symbol": sym,
                "params": params, "cutoff": str(cutoff),
                "train": s_tr, "oos": s_oos,
                "n_trades_total": len(rows),
            })
            params_str = ", ".join(f"{k}={v}" for k, v in params.items())
            tr_str = (f"n={s_tr['n']} E={s_tr['e']:+.2f} t={s_tr['t']:+.2f}"
                      if s_tr else "(empty)")
            oos_str = (f"n={s_oos['n']} E={s_oos['e']:+.2f} t={s_oos['t']:+.2f}"
                       if s_oos else "(empty)")
            print(f"  {sym} {params_str:<30s}  TRAIN: {tr_str}  OOS: {oos_str}")
    return results


# ── Output ─────────────────────────────────────────────────────

def write_csv(out_path: Path, results: list[dict]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not results:
        out_path.write_text("strategy,symbol\n", encoding="utf-8")
        return
    # Discover all param keys to flatten into columns
    param_keys = sorted({k for r in results for k in r["params"]})
    headers = ["strategy", "symbol"] + [f"p_{k}" for k in param_keys] + [
        "n_trades_total",
        "train_n", "train_hit", "train_e", "train_t",
        "oos_n", "oos_hit", "oos_e", "oos_t",
    ]
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers)
        for r in results:
            row = [r["strategy"], r["symbol"]]
            for k in param_keys:
                row.append(r["params"].get(k, ""))
            row.append(r.get("n_trades_total", 0))
            for slice_name in ("train", "oos"):
                s = r.get(slice_name)
                if s:
                    row += [s["n"], f"{s['hit']:.4f}",
                            f"{s['e']:.4f}", f"{s['t']:.4f}"]
                else:
                    row += ["", "", "", ""]
            w.writerow(row)


def write_summary_md(out_path: Path, results: list[dict],
                     strategy_name: str, grid: dict[str, list],
                     symbols: list[str]) -> None:
    """Write a markdown summary identifying best variants per symbol."""
    L = ["---", "type: param_sweep_summary",
         f"date: {datetime.now(timezone.utc).isoformat()}",
         f"strategy: {strategy_name}",
         f"grid: {grid}",
         f"symbols: {symbols}",
         "---", "",
         f"# Param sweep — {strategy_name}",
         ""]

    if not results:
        L.append("_(no results)_")
        out_path.write_text("\n".join(L) + "\n", encoding="utf-8")
        return

    # Best variant per symbol by OOS expectancy with sufficient n
    L.append("## Best variant per symbol (OOS E, n≥30, t≥1.5)\n")
    L += ["| Symbol | Best params | OOS_n | OOS_E | OOS_t | TRAIN_E | TRAIN_t |",
          "|---|---|---:|---:|---:|---:|---:|"]
    by_sym: dict[str, list[dict]] = {}
    for r in results:
        by_sym.setdefault(r["symbol"], []).append(r)
    for sym in sorted(by_sym):
        candidates = [r for r in by_sym[sym]
                      if r.get("oos") and r["oos"]["n"] >= 30
                      and r["oos"]["t"] >= 1.5]
        if not candidates:
            L.append(f"| {sym} | _(no qualifying variant)_ |  |  |  |  |  |")
            continue
        best = max(candidates, key=lambda r: r["oos"]["e"])
        params_str = ", ".join(f"{k}={v}" for k, v in best["params"].items())
        oos = best["oos"]; tr = best["train"] or {"e": 0, "t": 0}
        L.append(f"| {sym} | `{params_str}` | {oos['n']} "
                 f"| {oos['e']:+.2f} | {oos['t']:+.2f} "
                 f"| {tr['e']:+.2f} | {tr['t']:+.2f} |")

    L += ["", "## All combinations (full grid)", ""]
    L += ["| Symbol | Params | TRAIN n | TRAIN E | TRAIN t | OOS n | OOS E | OOS t |",
          "|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in results:
        params_str = ", ".join(f"{k}={v}" for k, v in r["params"].items())
        tr = r.get("train"); oos = r.get("oos")
        tr_n = tr["n"] if tr else 0
        tr_e = f"{tr['e']:+.2f}" if tr else "—"
        tr_t = f"{tr['t']:+.2f}" if tr else "—"
        oos_n = oos["n"] if oos else 0
        oos_e = f"{oos['e']:+.2f}" if oos else "—"
        oos_t = f"{oos['t']:+.2f}" if oos else "—"
        L.append(f"| {r['symbol']} | `{params_str}` "
                 f"| {tr_n} | {tr_e} | {tr_t} | {oos_n} | {oos_e} | {oos_t} |")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(L) + "\n", encoding="utf-8")


# ── main ───────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--strategy", required=True,
                   help="Strategy name from tools/backtest/strategies.py.")
    p.add_argument("--params", default="",
                   help="Param grid: 'name=v1,v2;name2=v1,v2'. "
                        "Empty = use strategy defaults.")
    p.add_argument("--symbols", required=True,
                   help="Comma-separated, e.g. 'ZN,ZT,ZB,ZF'.")
    p.add_argument("--period", default="60d",
                   help="yfinance period (default 60d).")
    p.add_argument("--interval", default="5m",
                   help="yfinance interval (default 5m).")
    p.add_argument("--holdout-pct", type=float, default=0.25,
                   help="Walk-forward OOS share (default 0.25 = last 25%%).")
    p.add_argument("--out-dir", default="vault/research/param_sweeps",
                   help="Output directory for CSV + MD report.")
    args = p.parse_args()

    grid = parse_param_grid(args.params)
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if not symbols:
        print("ERROR: --symbols list is empty", file=sys.stderr)
        return 2

    results = run_sweep(args.strategy, grid, symbols, args.period,
                        args.interval, args.holdout_pct)

    out_dir = PROJECT_ROOT / args.out_dir
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    csv_path = out_dir / f"{args.strategy}_{ts}.csv"
    md_path  = out_dir / f"{args.strategy}_{ts}.md"
    write_csv(csv_path, results)
    write_summary_md(md_path, results, args.strategy, grid, symbols)
    print()
    print(f"Wrote {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {md_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
