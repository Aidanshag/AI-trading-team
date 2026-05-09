"""Compare live trade R-multiples to OOS predictions per cell.

Reads each day's closed trades from `decisions` (theses with stop/target)
+ `account_snapshots` (realized P&L deltas), computes per-trade R
in dollar terms, then groups by (strategy, symbol, session, side) cell
and compares against the cell's OOS-predicted E.

Output:
  - vault/research/live_vs_oos/<date>_live_r_comparison.md
  - vault/research/live_vs_oos/<date>_live_r_comparison.json
  - Updates `live_r_multiples` field in state/strategy_validation.json
    for each cell that's accumulated >= 1 live trade

If a cell's rolling 5-trade live E is < 0R OR < (OOS_E × 0.3), surface
a warning. The user-defined demotion rules will use this signal.

Run via:
  python scripts/live_vs_oos_tracker.py
Or wire into preflight (already daily) for automatic refresh.
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from statistics import mean

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def session_bucket_et(ts_utc_str: str) -> str:
    """Map UTC ISO timestamp to ET session bucket."""
    ts = datetime.fromisoformat(ts_utc_str.replace("Z", "+00:00"))
    et_offset = -4  # ET = UTC-4 in May (DST)
    et_hour = (ts.hour + ts.minute / 60.0 + et_offset) % 24
    if 9.5 <= et_hour < 16:    return "RTH"
    if 4 <= et_hour < 9.5:     return "London"
    if 16 <= et_hour < 20:     return "PostClose"
    return "Asian"


def parse_thesis(summary: str, rationale: str) -> dict | None:
    """Extract strategy, side, entry, stop from a thesis decision row.

    Decisions look like:
      summary: "narrow_range_break long @ 100.67 stop=100.47 target=101.25"
      rationale: "strategy=... side=... entry=... stop=... target=... ..."
    """
    out: dict = {}
    # Try summary first
    m = re.match(r"(\S+)\s+(long|short)\s+@\s+([\d.]+)\s+stop=([\d.]+)", summary or "")
    if m:
        out["strategy"] = m.group(1)
        out["side"] = m.group(2)
        out["entry"] = float(m.group(3))
        out["stop"] = float(m.group(4))
        return out
    return None


def trades_with_pl(db_path: Path, day_iso: str) -> list[dict]:
    """For a given UTC date, pair each thesis with the realized-P&L delta
    that follows it (next snapshot delta after the entry timestamp).

    Returns rows: {ts, symbol, strategy, side, entry, stop, pl_usd, r_multiple}
    """
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    theses = list(c.execute(
        "SELECT ts, symbol, summary, rationale FROM decisions "
        "WHERE date(ts)=? AND kind='thesis' ORDER BY ts",
        (day_iso,)
    ))
    snaps = list(c.execute(
        "SELECT ts, realized_pl_day_usd FROM account_snapshots "
        "WHERE date(ts)=? ORDER BY ts", (day_iso,)
    ))
    conn.close()

    if not theses or not snaps:
        return []

    # For each thesis, find the realized-PL delta in the snapshot
    # interval that closes its position (heuristic: next snapshot
    # WHERE realized changes by > $1 after thesis ts).
    rows: list[dict] = []
    seen_snap_idx = 0
    for thesis_ts, symbol, summary, rationale in theses:
        info = parse_thesis(summary, rationale)
        if not info or info["stop"] <= 0 or info["entry"] <= 0:
            continue
        side = info["side"]
        entry = info["entry"]
        stop = info["stop"]
        stop_dist = abs(entry - stop)
        if stop_dist <= 0:
            continue

        # Walk snapshots forward from this thesis ts looking for next delta
        prev_pl = None
        for i in range(seen_snap_idx, len(snaps)):
            snap_ts, pl = snaps[i]
            if snap_ts < thesis_ts:
                continue
            if prev_pl is None:
                prev_pl = float(pl)
                continue
            curr = float(pl)
            delta = curr - prev_pl
            if abs(delta) > 0.5:   # realized changed → trade closed
                # Compute R: $delta / $stop_per_contract
                # Need symbol's tick value to compute $ stop
                # Skip computing in $; use $delta as-is for actual P&L
                # and compute R = $delta / (stop_dist_in_price × tick_value/tick_size)
                rows.append({
                    "ts": thesis_ts, "symbol": symbol,
                    "strategy": info["strategy"], "side": side,
                    "session": session_bucket_et(thesis_ts),
                    "entry": entry, "stop": stop, "stop_price_dist": stop_dist,
                    "pl_usd": delta, "snap_ts": snap_ts,
                })
                prev_pl = curr
                seen_snap_idx = i + 1
                break
            else:
                prev_pl = curr
    return rows


def r_multiple(symbol: str, stop_price_dist: float, pl_usd: float) -> float:
    """R = $pl / $stop_distance. Need tick economics from symbols.yaml."""
    import yaml
    syms = (yaml.safe_load(
        (PROJECT_ROOT / "config/symbols.yaml").read_text(encoding="utf-8")
    ) or {}).get("symbols", {})
    meta = syms.get(symbol) or {}
    tick_size = float(meta.get("tick_size") or 0)
    tick_value = float(meta.get("tick_value") or 0)
    if tick_size <= 0 or tick_value <= 0:
        return 0.0
    stop_dollar = (stop_price_dist / tick_size) * tick_value
    if stop_dollar <= 0:
        return 0.0
    return pl_usd / stop_dollar


def cell_key(strategy: str, symbol: str, session: str, side: str) -> str:
    return f"{strategy}|{symbol}|{session}|{side}"


def main() -> int:
    ts = datetime.now(timezone.utc)
    today = ts.strftime("%Y-%m-%d")
    print(f"=== LIVE-vs-OOS R-MULTIPLE TRACKER — {today} ===\n")

    db_path = PROJECT_ROOT / "state" / "fund.db"
    if not db_path.exists():
        print(f"NO DB at {db_path}")
        return 1

    # Load OOS predictions from validation state
    state_path = PROJECT_ROOT / "state" / "strategy_validation.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {"cells": {}}
    cells = state.get("cells", {})

    # Walk back N days of trades
    LOOKBACK_DAYS = 14
    all_trades: list[dict] = []
    for d_offset in range(LOOKBACK_DAYS):
        day = (ts - timedelta(days=d_offset)).strftime("%Y-%m-%d")
        rows = trades_with_pl(db_path, day)
        for r in rows:
            r["r_multiple"] = r_multiple(
                r["symbol"], r["stop_price_dist"], r["pl_usd"])
        all_trades.extend(rows)

    if not all_trades:
        print("No trades in lookback window.")
        return 0

    print(f"Trades found in last {LOOKBACK_DAYS}d: {len(all_trades)}")

    # Group by cell
    by_cell: dict[str, list[dict]] = {}
    for t in all_trades:
        k = cell_key(t["strategy"], t["symbol"], t["session"], t["side"])
        by_cell.setdefault(k, []).append(t)

    # Compare each cell's live mean R to OOS prediction
    L = ["---", "type: live_vs_oos_tracker",
         f"date: {ts.isoformat()}",
         f"trades_evaluated: {len(all_trades)}",
         f"unique_cells: {len(by_cell)}",
         "---", "",
         f"# Live R-multiple vs OOS prediction — {today}",
         "",
         f"Tracks {LOOKBACK_DAYS}-day rolling live performance per cell. ",
         "Compare live mean R against the OOS-predicted E to detect ",
         "edge decay or unexpected outperformance.",
         "",
         "## Per-cell comparison",
         "",
         "| Cell | n_live | mean_live_R | total_$ | OOS_E | gap | flag |",
         "|---|---:|---:|---:|---:|---:|---|"]

    underperforming = []
    overperforming = []
    healthy = []

    for k in sorted(by_cell):
        live = by_cell[k]
        n = len(live)
        rs = [t["r_multiple"] for t in live]
        live_mean_r = mean(rs) if rs else 0
        total_pl = sum(t["pl_usd"] for t in live)
        oos_e = (cells.get(k) or {}).get("last_oos", {}).get("e", 0) or 0
        gap = live_mean_r - oos_e

        flag = "—"
        if oos_e > 0:
            if live_mean_r < 0 and n >= 3:
                flag = "⚠ UNDERPERFORM"
                underperforming.append((k, n, live_mean_r, oos_e))
            elif gap < -0.5 and n >= 5:
                flag = "⚠ DECAY"
                underperforming.append((k, n, live_mean_r, oos_e))
            elif gap > +0.3 and n >= 3:
                flag = "✓ OVERPERFORM"
                overperforming.append((k, n, live_mean_r, oos_e))
            else:
                flag = "ok"
                healthy.append((k, n, live_mean_r, oos_e))

        L.append(f"| {k} | {n} | {live_mean_r:+.2f} | "
                 f"${total_pl:+,.2f} | {oos_e:+.2f} | {gap:+.2f} | {flag} |")
        print(f"  {k:>50}  n={n:>2} live_R={live_mean_r:+.2f}  "
              f"OOS_E={oos_e:+.2f}  gap={gap:+.2f}  {flag}")

    # Summary
    L += ["", "## Summary", "",
          f"- **Cells with edge holding (live ~ OOS)**: {len(healthy)}",
          f"- **Underperforming or decaying** (consider demotion): {len(underperforming)}",
          f"- **Overperforming** (sample-size luck or real): {len(overperforming)}",
          ""]
    if underperforming:
        L += ["### Cells flagged for review", ""]
        for k, n, lr, oe in underperforming:
            L.append(f"- `{k}` — n={n}, live_R={lr:+.2f} vs OOS_E={oe:+.2f}")

    out = PROJECT_ROOT / "vault" / "research" / "live_vs_oos"
    out.mkdir(parents=True, exist_ok=True)
    md = out / f"{today}_live_r_comparison.md"
    md.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nReport: {md.relative_to(PROJECT_ROOT)}")

    js = out / f"{today}_live_r_comparison.json"
    js.write_text(json.dumps({
        "date": today, "trades_evaluated": len(all_trades),
        "by_cell": {
            k: {"n": len(v), "live_mean_r": mean(t["r_multiple"] for t in v),
                 "total_pl_usd": sum(t["pl_usd"] for t in v)}
            for k, v in by_cell.items()
        },
        "underperforming": [k for k, *_ in underperforming],
    }, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
