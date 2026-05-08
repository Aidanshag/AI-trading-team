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


# ── Per-symbol tick economics for $-conversion ────────────────
# Used to convert per-trade prices into dollar P&L and to convert
# slippage in ticks/side into a dollar cost per round-trip.
TICK_ECONOMICS = {
    # symbol: (tick_size, tick_value_usd)
    "ZN": (0.015625, 15.625), "ZB": (0.03125, 31.25),
    "ZT": (0.0078125, 15.625), "ZF": (0.0078125, 7.8125),
    "NG": (0.001, 10.0),
    "GC": (0.10, 10.0), "SI": (0.005, 25.0), "HG": (0.0005, 12.5),
    "MES": (0.25, 1.25), "MNQ": (0.25, 0.50),
    "ES": (0.25, 12.50), "NQ": (0.25, 5.00),
    "MCL": (0.01, 1.00), "CL": (0.01, 10.00),
    "RB": (0.0001, 4.20), "HO": (0.0001, 4.20),
    "6E": (0.00005, 6.25), "6B": (0.0001, 6.25),
    "6J": (0.0000005, 6.25), "6A": (0.0001, 10.00), "6C": (0.0001, 10.00),
}


def _round_trip_slip_cost_usd(symbol: str, slip_ticks_per_side: float) -> float:
    """Total slippage cost for one round trip = entry slip + exit slip.
    Slippage applies to BOTH legs (entry crosses spread, exit crosses spread).
    """
    _, tick_value = TICK_ECONOMICS.get(symbol, (0.01, 1.0))
    return 2.0 * slip_ticks_per_side * tick_value


def run_strategy(strategy_fn, bars, symbol: str, params: dict) -> list[dict]:
    """Invoke the strategy; return per-trade rows with R-multiples AND
    dollar metrics. Mirrors the existing walk_forward_*.py pattern but
    augments each row with:
        gross_usd     — raw $ result from entry/exit prices
        risk_ticks    — distance from entry to stop in ticks (for sanity)

    Slippage-adjusted columns are computed at summary time per slip level.
    """
    from tools.backtest.engine import backtest_strategy
    try:
        result = backtest_strategy(strategy_fn, bars, symbol=symbol, params=params)
    except Exception as e:
        print(f"  err: backtest_strategy failed for {symbol}/{params}: "
              f"{type(e).__name__}: {e}", file=sys.stderr)
        return []
    rows = []
    tick_size, tick_value = TICK_ECONOMICS.get(symbol, (0.01, 1.0))
    for t in result.trades:
        if t.is_open:
            continue
        et = t.entry_date
        if et.tz is None:
            et = et.tz_localize("UTC").tz_convert("America/New_York")
        else:
            et = et.tz_convert("America/New_York")
        # Compute gross $ from entry + exit prices (1 contract assumed).
        gross_usd = 0.0
        try:
            entry = float(t.entry_price)
            exit_p = float(t.exit_price)
            if t.side == "long":
                gross_usd = (exit_p - entry) / tick_size * tick_value
            else:
                gross_usd = (entry - exit_p) / tick_size * tick_value
        except Exception:
            gross_usd = 0.0
        # Risk distance in ticks (for sanity / "is the stop 1 tick or 100?")
        risk_ticks = 0.0
        try:
            entry = float(t.entry_price); stop = float(t.stop_price)
            risk_ticks = abs(entry - stop) / tick_size
        except Exception:
            pass
        rows.append({
            "symbol": symbol, "entry_et": et, "side": t.side,
            "r": t.r_multiple,
            "gross_usd": gross_usd,
            "risk_ticks": risk_ticks,
            "session": session_for_hour_minute(et.hour + et.minute / 60),
        })
    return rows


# ── Walk-forward stats ─────────────────────────────────────────

# Slippage levels we report at: 0 (paper), 0.25 (best-case live),
# 0.5 (typical Topstep gap_fill_wide), 1.0 (worst-case).
SLIP_LEVELS_TICKS = [0.0, 0.25, 0.5, 1.0]


def stats(rows: list[dict], symbol: str | None = None) -> dict | None:
    """Compute R-multiple stats AND slippage-adjusted dollar metrics.

    Output schema additions vs original:
      mean_$_at_slip_<X>   — mean per-trade NET $ at X ticks/side slippage
      hit_rate_at_slip_<X> — share of trades that net positive at X slippage
      breakeven_slip_ticks — slippage level where mean_$ crosses 0 (or None)
    """
    if not rows:
        return None
    rs = [r["r"] for r in rows]
    n = len(rs)
    hit = sum(1 for r in rs if r > 0) / n
    e = mean(rs)
    sd = stdev(rs) if n > 1 else 0.0
    t = (e / (sd / (n ** 0.5))) if (sd > 0 and n > 1) else 0.0

    out = {"n": n, "hit": hit, "e": e, "t": t}

    # Dollar metrics (only when symbol/economics available)
    sym = symbol or (rows[0].get("symbol") if rows else None)
    if sym and sym in TICK_ECONOMICS:
        gross_dollars = [r.get("gross_usd", 0.0) for r in rows]
        out["mean_gross_usd"] = mean(gross_dollars) if gross_dollars else 0.0
        out["mean_risk_ticks"] = (mean([r.get("risk_ticks", 0) for r in rows])
                                  if rows else 0)
        for slip in SLIP_LEVELS_TICKS:
            cost = _round_trip_slip_cost_usd(sym, slip)
            net_dollars = [g - cost for g in gross_dollars]
            mean_net = mean(net_dollars) if net_dollars else 0.0
            hit_net = (sum(1 for g in net_dollars if g > 0) / len(net_dollars)
                       if net_dollars else 0)
            tag = f"{slip}".replace(".", "_")
            out[f"mean_net_usd_at_slip_{tag}"] = mean_net
            out[f"hit_rate_at_slip_{tag}"] = hit_net

        # Breakeven slippage — bisect between 0 and 2.0 ticks/side
        # to find where mean_net crosses zero. None if always positive
        # or always negative.
        def _net_at(slip):
            cost = _round_trip_slip_cost_usd(sym, slip)
            return mean([g - cost for g in gross_dollars])
        if gross_dollars:
            net_0 = _net_at(0); net_2 = _net_at(2.0)
            if net_0 <= 0:
                out["breakeven_slip_ticks"] = 0.0
            elif net_2 > 0:
                out["breakeven_slip_ticks"] = None  # tolerates >2 ticks
            else:
                lo, hi = 0.0, 2.0
                for _ in range(20):  # bisect ~6 decimal places
                    mid = (lo + hi) / 2
                    if _net_at(mid) > 0:
                        lo = mid
                    else:
                        hi = mid
                out["breakeven_slip_ticks"] = round((lo + hi) / 2, 3)
        else:
            out["breakeven_slip_ticks"] = None
    return out


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
            s_tr = stats(train, symbol=sym)
            s_oos = stats(oos, symbol=sym)
            results.append({
                "strategy": strategy_name, "symbol": sym,
                "params": params, "cutoff": str(cutoff),
                "train": s_tr, "oos": s_oos,
                "n_trades_total": len(rows),
            })
            params_str = ", ".join(f"{k}={v}" for k, v in params.items())
            # Print line includes BOTH R-multiple and slippage-adjusted
            # $ at 0.25 ticks/side (typical live slippage).
            def _fmt(s):
                if not s: return "(empty)"
                base = f"n={s['n']} E={s['e']:+.2f} t={s['t']:+.2f}"
                if "mean_net_usd_at_slip_0_25" in s:
                    bk = s.get("breakeven_slip_ticks")
                    bk_str = "∞" if bk is None else f"{bk:.2f}"
                    return (base + f" $@.25={s['mean_net_usd_at_slip_0_25']:+.0f}"
                            f" be@{bk_str}t")
                return base
            print(f"  {sym} {params_str:<30s}  TRAIN: {_fmt(s_tr)}  "
                  f"OOS: {_fmt(s_oos)}")
    return results


# ── Output ─────────────────────────────────────────────────────

def write_csv(out_path: Path, results: list[dict]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not results:
        out_path.write_text("strategy,symbol\n", encoding="utf-8")
        return
    # Discover all param keys to flatten into columns
    param_keys = sorted({k for r in results for k in r["params"]})
    slip_tags = ["0_0", "0_25", "0_5", "1_0"]
    base_headers = ["strategy", "symbol"] + [f"p_{k}" for k in param_keys] + [
        "n_trades_total",
        "train_n", "train_hit", "train_e", "train_t",
        "train_mean_gross_usd", "train_mean_risk_ticks",
        "oos_n", "oos_hit", "oos_e", "oos_t",
        "oos_mean_gross_usd", "oos_mean_risk_ticks",
        "oos_breakeven_slip_ticks",
    ]
    # Per-slip dollar columns for OOS (the deployment-relevant slice)
    slip_headers = []
    for slip in slip_tags:
        slip_headers += [f"oos_mean_net_usd_at_slip_{slip}",
                         f"oos_hit_rate_at_slip_{slip}"]
    headers = base_headers + slip_headers

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
                            f"{s['e']:.4f}", f"{s['t']:.4f}",
                            f"{s.get('mean_gross_usd', 0):.2f}",
                            f"{s.get('mean_risk_ticks', 0):.2f}"]
                else:
                    row += ["", "", "", "", "", ""]
            # OOS-specific: breakeven_slip + per-slip $ columns
            oos = r.get("oos") or {}
            bk = oos.get("breakeven_slip_ticks")
            row.append("∞" if bk is None else f"{bk:.3f}")
            for slip in slip_tags:
                row.append(f"{oos.get(f'mean_net_usd_at_slip_{slip}', 0):.2f}")
                row.append(f"{oos.get(f'hit_rate_at_slip_{slip}', 0):.4f}")
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

    # NEW (per CC's redirect 2026-05-08): rank by SLIPPAGE-ADJUSTED
    # NET $ at 0.25 ticks/side, not by R-multiple. R-multiples are
    # slippage-blind — a +2.80R cell with 1-tick stops loses money to
    # 0.5 ticks of round-trip slippage. Net dollars tells the truth.

    L.append("## Best variant per symbol — slippage-adjusted (OOS, n≥30, t≥1.5)")
    L.append("")
    L.append("Ranked by `mean_net_usd_at_slip_0.25` (typical live slippage).")
    L.append("")
    L += ["| Symbol | Best params | OOS_n | OOS_E (R) | OOS_t | $@slip=0.25 | $@slip=0.5 | $@slip=1.0 | breakeven_slip_ticks | mean_risk_ticks |",
          "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    by_sym: dict[str, list[dict]] = {}
    for r in results:
        by_sym.setdefault(r["symbol"], []).append(r)
    for sym in sorted(by_sym):
        candidates = [r for r in by_sym[sym]
                      if r.get("oos") and r["oos"].get("n", 0) >= 30
                      and r["oos"].get("t", 0) >= 1.5]
        if not candidates:
            L.append(f"| {sym} | _(no qualifying variant)_ |  |  |  |  |  |  |  |  |")
            continue
        # Rank by slippage-adjusted dollar at 0.25 ticks/side
        def _key(r):
            return r["oos"].get("mean_net_usd_at_slip_0_25", -9999)
        best = max(candidates, key=_key)
        params_str = ", ".join(f"{k}={v}" for k, v in best["params"].items())
        oos = best["oos"]
        bk = oos.get("breakeven_slip_ticks")
        bk_s = "∞" if bk is None else f"{bk:.2f}"
        L.append(f"| {sym} | `{params_str}` | {oos['n']} "
                 f"| {oos['e']:+.2f} | {oos['t']:+.2f} "
                 f"| {oos.get('mean_net_usd_at_slip_0_25', 0):+.0f} "
                 f"| {oos.get('mean_net_usd_at_slip_0_5', 0):+.0f} "
                 f"| {oos.get('mean_net_usd_at_slip_1_0', 0):+.0f} "
                 f"| {bk_s} | {oos.get('mean_risk_ticks', 0):.1f} |")

    L += ["", "## All combinations — slippage-adjusted dollars (OOS only)", ""]
    L += ["| Symbol | Params | OOS n | OOS E (R) | OOS t | $@0 | $@0.25 | $@0.5 | $@1.0 | breakeven |",
          "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in results:
        params_str = ", ".join(f"{k}={v}" for k, v in r["params"].items())
        oos = r.get("oos")
        if not oos:
            L.append(f"| {r['symbol']} | `{params_str}` | 0 | — | — | — | — | — | — | — |")
            continue
        bk = oos.get("breakeven_slip_ticks")
        bk_s = "∞" if bk is None else f"{bk:.2f}"
        L.append(f"| {r['symbol']} | `{params_str}` "
                 f"| {oos['n']} | {oos['e']:+.2f} | {oos['t']:+.2f} "
                 f"| {oos.get('mean_net_usd_at_slip_0_0', 0):+.0f} "
                 f"| {oos.get('mean_net_usd_at_slip_0_25', 0):+.0f} "
                 f"| {oos.get('mean_net_usd_at_slip_0_5', 0):+.0f} "
                 f"| {oos.get('mean_net_usd_at_slip_1_0', 0):+.0f} "
                 f"| {bk_s} |")

    L += ["",
          "## How to read",
          "",
          "- `OOS E (R)` is the per-trade R-multiple — slippage-blind.",
          "- `$@slip=X` is the NET dollar per trade after X ticks/side of"
          " round-trip slippage (entry + exit each cost X ticks).",
          "- `breakeven_slip_ticks` is the slippage level at which mean"
          " net $ crosses zero. ∞ means the cell stays profitable beyond 2 ticks/side.",
          "- A cell with high R but low `$@slip=0.25` is a trap: paper"
          " edge that doesn't survive realistic slippage.",
          "- A cell with low R but high `breakeven_slip_ticks` is robust:"
          " the per-trade $ edge is large enough to absorb realistic costs.",
          "",
          "Per the slippage-mitigation playbook (`vault/research/slippage_mitigation_playbook.md`)"
          " typical Topstep slippage on gap_fill_wide is 0.25-0.5 ticks/side. The"
          " `$@slip=0.25` column is the deployment-relevant metric."]

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
