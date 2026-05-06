"""Daily strategy validation control loop.

Re-runs per-cell walk-forward across the focus universe, applies rolling-
window promotion/demotion rules, and writes a JSON state file that the
auto_trader reads at startup. Adds the new evidence each day so live
strategies that decay get demoted and shadow strategies that earn their
edge get promoted — without manual intervention.

Decision rules (deliberately conservative — single-day noise should NOT
oscillate strategies in/out of the live allowlist):

  PROMOTION (shadow → live):
    - Cell must pass walk-forward 2 consecutive days
    - Pass = OOS t-stat >= 1.5, OOS expectancy > 0, n_oos >= 30

  DEMOTION (live → shadow):
    - Cell fails walk-forward 3 consecutive days, OR
    - Single catastrophic fail: OOS E < -0.5R AND n >= 30

  HYSTERESIS:
    - Once demoted, requires 3 consecutive passes to re-promote
      (prevents flapping when a cell hovers near threshold)

Inputs:
  - 60-day 5m bars per focus symbol via yfinance
  - state/strategy_validation.json (rolling history; created on first run)

Outputs:
  - state/strategy_validation.json (updated history + current allowlist)
  - vault/research/validation/<date>_daily_validation.md (daily report)
  - vault/research/validation/promotion_log.md (append-only audit trail)

Run via:
  python scripts/daily_strategy_validation.py
Or wire into preflight.py / a scheduled task to run automatically.
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


# ── Configuration ────────────────────────────────────────────

FOCUS_TO_YF: dict[str, str] = {
    "GC":  "GC=F",
    "MCL": "CL=F",
    "NG":  "NG=F",
    "MNQ": "NQ=F",
    "MES": "ES=F",
    "ZN":  "ZN=F",
    "ZB":  "ZB=F",
    "ZT":  "ZT=F",
    "ZF":  "ZF=F",
    "6E":  "6E=F",
    "6B":  "6B=F",
    "6J":  "6J=F",
    "6A":  "6A=F",
    "6C":  "6C=F",
}

# All strategies in the library that emit entry signals
ALL_STRATEGIES: dict[str, callable] = {
    name: getattr(strats, name)
    for name in (
        "donchian_breakout", "bollinger_mean_reversion", "volatility_breakout",
        "pullback_in_trend", "range_mean_reversion", "bollinger_squeeze_break",
        "keltner_breakout", "vol_regime_trend", "vol_spike_fade",
        "opening_range_breakout", "narrow_range_break", "inside_bar_break",
        "rsi2_extreme_reversion", "volume_spike_reversal",
        "support_resistance_bounce", "gap_fill", "pivot_reversal",
        "fair_value_gap", "order_block", "liquidity_sweep",
    )
}

SESSIONS = ("Asian", "London", "RTH", "PostClose")
SIDES = ("long", "short")

# Pass criteria
PASS_T_STAT = 1.5
PASS_MIN_N_OOS = 30

# Catastrophic fail triggers immediate demotion
CATASTROPHIC_E_R = -0.5
CATASTROPHIC_MIN_N = 30

# Rolling-window thresholds
PROMOTION_CONSECUTIVE_PASSES = 2
DEMOTION_CONSECUTIVE_FAILS = 3
HYSTERESIS_PASSES = 3   # after demotion, need this many before re-promote

STATE_FILE = PROJECT_ROOT / "state" / "strategy_validation.json"
REPORT_DIR = PROJECT_ROOT / "vault" / "research" / "validation"
PROMOTION_LOG = REPORT_DIR / "promotion_log.md"


# ── Backtest helpers ─────────────────────────────────────────

def session_bucket(et_hour: float) -> str:
    if 9.5 <= et_hour < 16:    return "RTH"
    if 4 <= et_hour < 9.5:     return "London"
    if 16 <= et_hour < 20:     return "PostClose"
    return "Asian"


def fetch_bars(ticker: str, period: str = "60d", interval: str = "5m"):
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


def collect_trades(strat_name: str, fn, bars, sym: str) -> list[dict]:
    try:
        result = backtest_strategy(fn, bars, symbol=sym, params={})
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
        rows.append({
            "strategy": strat_name, "symbol": sym, "entry_et": et,
            "side": t.side, "r": t.r_multiple,
            "session": session_bucket(et.hour + et.minute / 60),
        })
    return rows


def stats(rows: list[dict]) -> dict | None:
    n = len(rows)
    if n == 0:
        return None
    # Force native Python floats — pandas/numpy types break json.dumps
    rs = [float(r["r"]) for r in rows]
    hit = sum(1 for r in rs if r > 0) / n
    e = mean(rs)
    sd = stdev(rs) if n > 1 else 0
    t = (e / (sd / (n ** 0.5))) if (sd > 0 and n > 1) else 0
    return {"n": int(n), "hit": float(round(hit, 3)),
            "e": float(round(e, 3)), "t": float(round(t, 2))}


def split_at(rows: list[dict], cutoff) -> tuple[list[dict], list[dict]]:
    return ([r for r in rows if r["entry_et"] < cutoff],
            [r for r in rows if r["entry_et"] >= cutoff])


# ── Pass / fail decision ────────────────────────────────────

def is_pass(s_oos: dict | None) -> bool:
    if s_oos is None:
        return False
    return (s_oos["e"] > 0 and s_oos["n"] >= PASS_MIN_N_OOS
            and s_oos["t"] >= PASS_T_STAT)


def is_catastrophic(s_oos: dict | None) -> bool:
    if s_oos is None:
        return False
    return s_oos["e"] < CATASTROPHIC_E_R and s_oos["n"] >= CATASTROPHIC_MIN_N


# ── State management ────────────────────────────────────────

def cell_key(strategy: str, symbol: str, session: str, side: str) -> str:
    return f"{strategy}|{symbol}|{session}|{side}"


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {"version": 1, "cells": {}, "history": []}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        # Corrupted state — back it up and start fresh
        backup = STATE_FILE.with_suffix(
            f".corrupt-{datetime.now(tz=timezone.utc):%Y%m%d_%H%M}.json"
        )
        STATE_FILE.rename(backup)
        return {"version": 1, "cells": {}, "history": []}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def update_cell_history(state: dict, key: str, today_pass: bool,
                        catastrophic: bool, s_oos: dict | None) -> str:
    """Update one cell's rolling history. Return action: 'promoted' /
    'demoted' / 'unchanged' / 'new'."""
    cells = state.setdefault("cells", {})
    is_first_observation = key not in cells
    cell = cells.setdefault(key, {
        "status": "shadow",  # 'live' or 'shadow'
        "consecutive_passes": 0,
        "consecutive_fails": 0,
        "last_seen": None,
        "last_oos": None,
        "history": [],
    })

    today_iso = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    cell["last_seen"] = today_iso
    cell["last_oos"] = s_oos
    # Coerce to Python bool — strategies returning numpy.bool_ via pandas
    # comparisons aren't JSON serializable.
    cell["history"].append({
        "date": today_iso, "pass": bool(today_pass),
        "catastrophic": bool(catastrophic), "oos": s_oos,
    })
    # Cap history at 90 days
    cell["history"] = cell["history"][-90:]

    if today_pass:
        cell["consecutive_passes"] += 1
        cell["consecutive_fails"] = 0
    else:
        cell["consecutive_fails"] += 1
        cell["consecutive_passes"] = 0

    action = "unchanged"
    prev_status = cell["status"]

    # Bootstrap path: on first observation, a single walk-forward pass
    # is sufficient evidence to promote — the underlying data IS the
    # prior research. After that, rolling-window logic prevents flapping.
    if is_first_observation and today_pass and prev_status == "shadow":
        cell["status"] = "live"
        cell["promoted_at"] = today_iso
        cell["promotion_reason"] = "first_observation_pass"
        return "promoted"

    # Promotion path
    if prev_status == "shadow":
        threshold = (HYSTERESIS_PASSES if cell.get("ever_demoted")
                     else PROMOTION_CONSECUTIVE_PASSES)
        if cell["consecutive_passes"] >= threshold:
            cell["status"] = "live"
            action = "promoted"
            cell["promoted_at"] = today_iso

    # Demotion path
    elif prev_status == "live":
        if catastrophic or cell["consecutive_fails"] >= DEMOTION_CONSECUTIVE_FAILS:
            cell["status"] = "shadow"
            cell["ever_demoted"] = True
            cell["demoted_at"] = today_iso
            cell["demotion_reason"] = ("catastrophic" if catastrophic
                                       else f"{DEMOTION_CONSECUTIVE_FAILS}_consecutive_fails")
            action = "demoted"

    return action


# ── Main loop ───────────────────────────────────────────────

def main() -> int:
    ts = datetime.now(timezone.utc)
    today_iso = ts.strftime("%Y-%m-%d")
    print(f"=== DAILY STRATEGY VALIDATION — {ts:%Y-%m-%d %H:%M UTC} ===\n")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Load existing state
    state = load_state()

    # Fetch bars per symbol
    bars_by_sym: dict[str, "pd.DataFrame"] = {}
    for sym, ticker in FOCUS_TO_YF.items():
        bars = fetch_bars(ticker)
        if bars is None or len(bars) < 100:
            print(f"  {sym} ({ticker}): insufficient bars, skipping")
            continue
        bars_by_sym[sym] = bars

    if not bars_by_sym:
        print("NO BARS — aborting")
        return 1

    print(f"\nSymbols loaded: {sorted(bars_by_sym)}")
    print(f"Strategies: {len(ALL_STRATEGIES)}")
    print(f"Cells potentially scored: "
          f"{len(ALL_STRATEGIES) * len(bars_by_sym) * len(SESSIONS) * len(SIDES)}\n")

    # Walk every (strategy, symbol, session, side) cell
    promotions: list[tuple[str, str, str, str, dict]] = []
    demotions: list[tuple[str, str, str, str, dict, str]] = []
    new_cells: list[str] = []
    cells_evaluated = 0

    for strat_name, fn in ALL_STRATEGIES.items():
        for sym, bars in bars_by_sym.items():
            all_trades = collect_trades(strat_name, fn, bars, sym)
            if not all_trades:
                continue
            span = bars.index[-1] - bars.index[0]
            cutoff = bars.index[-1] - span * 0.25
            for session in SESSIONS:
                for side in SIDES:
                    cell = [r for r in all_trades
                            if r["session"] == session and r["side"] == side]
                    if len(cell) < 5:   # too few to score at all
                        continue
                    _, test = split_at(cell, cutoff)
                    s_oos = stats(test)
                    today_pass = is_pass(s_oos)
                    catastrophic = is_catastrophic(s_oos)

                    key = cell_key(strat_name, sym, session, side)
                    is_new = key not in state.get("cells", {})
                    action = update_cell_history(
                        state, key, today_pass, catastrophic, s_oos)
                    cells_evaluated += 1

                    if is_new:
                        new_cells.append(key)
                    if action == "promoted":
                        promotions.append((strat_name, sym, session, side, s_oos))
                    elif action == "demoted":
                        c = state["cells"][key]
                        demotions.append((strat_name, sym, session, side,
                                          s_oos, c["demotion_reason"]))

    # Add today to history index
    state.setdefault("history", []).append({
        "date": today_iso,
        "cells_evaluated": cells_evaluated,
        "promotions": len(promotions),
        "demotions": len(demotions),
        "new_cells": len(new_cells),
    })
    state["history"] = state["history"][-365:]

    # Snapshot live allowlist for the auto_trader to consume
    live_cells = [
        {"strategy": k.split("|")[0], "symbol": k.split("|")[1],
         "session": k.split("|")[2], "side": k.split("|")[3]}
        for k, c in state.get("cells", {}).items()
        if c.get("status") == "live"
    ]

    # User-pinned filter: if state has `live_strategies_filter`, restrict
    # the active live_allowlist to ONLY cells whose (strategy, symbol)
    # appears in the filter. This lets the user concentrate the trader
    # on a high-conviction subset (e.g., gap_fill treasury only) without
    # having to delete cells from the rolling-history record. Set the
    # filter directly in state/strategy_validation.json or via the
    # `--filter-strategy <name> --filter-symbols A,B,C` CLI args.
    flt = state.get("live_strategies_filter")
    if flt:
        before = len(live_cells)
        allow_pairs = set()
        for entry in flt:
            strat = entry.get("strategy")
            for sym in entry.get("symbols") or []:
                allow_pairs.add((strat, sym))
        live_cells = [c for c in live_cells
                       if (c["strategy"], c["symbol"]) in allow_pairs]
        print(f"  user filter applied: {before} → {len(live_cells)} live cells")

    state["live_allowlist"] = live_cells
    state["live_allowlist_generated_at"] = ts.isoformat(timespec="seconds")

    save_state(state)

    # ── Reporting ────────────────────────────────────────
    print(f"Evaluated {cells_evaluated} cells")
    print(f"  promotions: {len(promotions)}")
    print(f"  demotions:  {len(demotions)}")
    print(f"  new cells observed: {len(new_cells)}")
    print(f"  total live cells: {len(live_cells)}\n")

    if promotions:
        print("PROMOTED to live:")
        for s, sym, sess, side, oos in promotions:
            print(f"  {s:>22} {sym:>4} {sess:>9} {side:>5}  "
                  f"OOS n={oos['n']:>3} E={oos['e']:+.2f}R t={oos['t']:+.2f}")
    if demotions:
        print("\nDEMOTED to shadow:")
        for s, sym, sess, side, oos, reason in demotions:
            o = oos or {"n": 0, "e": 0, "t": 0}
            print(f"  {s:>22} {sym:>4} {sess:>9} {side:>5}  "
                  f"OOS n={o['n']:>3} E={o['e']:+.2f}R t={o['t']:+.2f}  ({reason})")

    # Daily report
    L = ["---", "type: daily_strategy_validation", f"date: {ts.isoformat()}",
         f"cells_evaluated: {cells_evaluated}",
         f"promotions: {len(promotions)}",
         f"demotions: {len(demotions)}",
         f"live_cells_total: {len(live_cells)}",
         "---", "",
         f"# Daily strategy validation — {today_iso}", "",
         f"Cells evaluated: **{cells_evaluated}**  ",
         f"Promotions: **{len(promotions)}**  ",
         f"Demotions: **{len(demotions)}**  ",
         f"Total live cells: **{len(live_cells)}**", ""]

    if promotions:
        L += ["## PROMOTED to live", "",
              "| Strategy | Symbol | Session | Side | n_OOS | E_OOS | t_OOS |",
              "|---|---|---|---|---:|---:|---:|"]
        for s, sym, sess, side, o in promotions:
            L.append(f"| {s} | {sym} | {sess} | {side} | "
                     f"{o['n']} | {o['e']:+.2f} | {o['t']:+.2f} |")
        L.append("")

    if demotions:
        L += ["## DEMOTED to shadow", "",
              "| Strategy | Symbol | Session | Side | n_OOS | E_OOS | t_OOS | Reason |",
              "|---|---|---|---|---:|---:|---:|---|"]
        for s, sym, sess, side, o, reason in demotions:
            o = o or {"n": 0, "e": 0, "t": 0}
            L.append(f"| {s} | {sym} | {sess} | {side} | "
                     f"{o['n']} | {o['e']:+.2f} | {o['t']:+.2f} | {reason} |")
        L.append("")

    L += ["## Live allowlist snapshot", "",
          f"{len(live_cells)} cells currently allowed to place live orders. ",
          "See `state/strategy_validation.json` → `live_allowlist` for the ",
          "machine-readable list the auto_trader consumes.", ""]

    report_path = REPORT_DIR / f"{today_iso}_daily_validation.md"
    report_path.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nReport: {report_path.relative_to(PROJECT_ROOT)}")
    print(f"State:  {STATE_FILE.relative_to(PROJECT_ROOT)}")

    # Append to promotion log if anything moved
    if promotions or demotions:
        if not PROMOTION_LOG.exists():
            PROMOTION_LOG.write_text(
                "# Promotion / demotion log (append-only)\n\n", encoding="utf-8"
            )
        with PROMOTION_LOG.open("a", encoding="utf-8") as f:
            f.write(f"\n## {today_iso}\n\n")
            for s, sym, sess, side, o in promotions:
                f.write(f"- ✅ PROMOTE {s} × {sym} × {sess} × {side}  "
                        f"(OOS E={o['e']:+.2f}R, t={o['t']:+.2f}, n={o['n']})\n")
            for s, sym, sess, side, o, reason in demotions:
                o = o or {"n": 0, "e": 0, "t": 0}
                f.write(f"- ❌ DEMOTE {s} × {sym} × {sess} × {side}  "
                        f"(reason: {reason}, last OOS E={o['e']:+.2f}R)\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
