"""peak_capture_per_cell — per-cell peak-capture efficiency report.

Backlog P1 (proposed 2026-05-15): "Continuous % peak captured per closed
trade, fed back into per-cell scoring. Would have caught last week's
giveback pattern in real-time."

The sentinel.check_peak_capture_weekly aggregates capture rate across ALL
closes. This script disaggregates by (symbol, strategy, session, side) so
we can see which cells are bleeding peaks and which are clean.

Method:
  1. Query decisions table for profit_lock closes with peak_pct_captured
  2. Match each to its entry order (same symbol, ts_filled before ts_close)
     to recover the cell metadata (strategy, session, side)
  3. Aggregate per cell: avg capture, n trades, std of capture
  4. Flag cells with avg_capture < 30% as REVIEW (need exit-rule tuning
     or demotion to shadow)

Output:
  - vault/_meta/peak_capture_per_cell.md (rolling report)
  - state/peak_capture_metrics.json (machine-readable for scoring)

Re-run nightly (added to preflight or a separate scheduled task).
"""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "state" / "fund.db"
REPORT_PATH = ROOT / "vault" / "_meta" / "peak_capture_per_cell.md"
METRICS_PATH = ROOT / "state" / "peak_capture_metrics.json"


def parse_rationale(rationale: str) -> dict:
    """Extract peak / realized / peak_pct_captured / reason from rationale."""
    out = {}
    for token in rationale.split("|"):
        token = token.strip()
        if "=" not in token:
            continue
        k, v = token.split("=", 1)
        k = k.strip(); v = v.strip()
        out[k] = v
    return out


def parse_pct(s: str) -> float | None:
    if not s:
        return None
    s = s.strip().rstrip("%")
    try:
        return float(s)
    except Exception:
        return None


def collect_per_cell(conn, hours: int = 168) -> dict:
    """Group closes by (symbol, strategy, session, side) — strategy/session/side
    recovered from the matching entry order via cell_key in notes (if available).

    Returns {(sym, strat, sess, side): [list of pct_capture]}.
    """
    cur = conn.cursor()
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(hours=hours)).isoformat()
    rows = cur.execute(
        "SELECT ts, symbol, rationale FROM decisions "
        "WHERE agent='profit_lock' AND kind='close' AND ts >= ?",
        (cutoff,),
    ).fetchall()
    per_cell: dict[tuple, list[float]] = defaultdict(list)
    for ts, symbol, rationale in rows:
        if not rationale:
            continue
        parts = parse_rationale(rationale)
        pct = parse_pct(parts.get("peak_pct_captured"))
        if pct is None or pct < 0:
            continue
        # Recover cell metadata from matching entry order
        # Match: same symbol, status=filled, ts_filled within 6h before this close
        ts_dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        window_start = (ts_dt - timedelta(hours=6)).isoformat()
        entry = cur.execute(
            "SELECT side, client_order_id FROM orders "
            "WHERE symbol=? AND status='filled' AND ts_filled <= ? "
            "AND ts_filled >= ? AND agent='live_trader' "
            "AND client_order_id NOT LIKE '%_stop' "
            "AND client_order_id NOT LIKE '%_target' "
            "ORDER BY ts_filled DESC LIMIT 1",
            (symbol, ts, window_start),
        ).fetchone()
        if not entry:
            continue
        side = "long" if str(entry[0] or "").lower() == "buy" else "short"
        # We don't have strategy/session on the order row (those live
        # on the pending_signals queue and aren't persisted). Bucket
        # by (symbol, side) only as the best available granularity.
        per_cell[(symbol, side)].append(pct)
    return per_cell


def compute_metrics(per_cell: dict) -> dict:
    """For each cell: n, mean, std, min, classification."""
    from statistics import mean, stdev
    metrics = {}
    for cell, captures in per_cell.items():
        if not captures:
            continue
        n = len(captures)
        m = mean(captures)
        s = stdev(captures) if n > 1 else 0.0
        mn = min(captures)
        # Classification
        cls = "HEALTHY"
        if m < 0.30:
            cls = "REVIEW"  # avg under 30% capture — bleeding peaks
        elif m < 0.45:
            cls = "WATCH"
        metrics[f"{cell[0]}_{cell[1]}"] = {
            "symbol": cell[0],
            "side": cell[1],
            "n": n,
            "mean_capture": round(m, 3),
            "std": round(s, 3),
            "min_capture": round(mn, 3),
            "class": cls,
        }
    return metrics


def main() -> int:
    if not DB_PATH.exists():
        print(f"ABORT: {DB_PATH} missing")
        return 2
    conn = sqlite3.connect(str(DB_PATH))
    try:
        per_cell = collect_per_cell(conn, hours=168)
    finally:
        conn.close()
    if not per_cell:
        print("No closes in last 7 days — nothing to report")
        # Still write empty metrics so downstream tools don't crash
        METRICS_PATH.write_text(json.dumps({"updated_at": datetime.now(tz=timezone.utc).isoformat(), "metrics": {}}, indent=2))
        return 0
    metrics = compute_metrics(per_cell)

    # Write JSON
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(
        json.dumps({
            "updated_at": datetime.now(tz=timezone.utc).isoformat(),
            "window_hours": 168,
            "metrics": metrics,
        }, indent=2),
        encoding="utf-8",
    )

    # Write Markdown report
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    lines = [
        "---", "type: report", f"updated: {today}",
        "purpose: Per-cell peak-capture efficiency (rolling 7-day)",
        "---", "",
        "# Peak-capture efficiency — per-cell rolling 7-day",
        "",
        f"Auto-generated by `scripts/peak_capture_per_cell.py`.",
        "",
        "**Classification:**",
        "- `HEALTHY`: mean capture ≥ 45%",
        "- `WATCH`: mean capture 30-45% (monitor)",
        "- `REVIEW`: mean capture < 30% — exit rule may need tuning or demote to shadow",
        "",
        "| Symbol | Side | n | Mean capture | Std | Min | Class |",
        "|---|---|---|---|---|---|---|",
    ]
    for key, m in sorted(metrics.items(), key=lambda x: x[1]["mean_capture"]):
        lines.append(
            f"| {m['symbol']} | {m['side']} | {m['n']} | "
            f"{m['mean_capture']*100:.0f}% | "
            f"{m['std']*100:.0f}% | {m['min_capture']*100:.0f}% | "
            f"{m['class']} |"
        )
    reviews = [m for m in metrics.values() if m["class"] == "REVIEW"]
    if reviews:
        lines += [
            "", "## REVIEW cells (under 30% capture)", "",
            "These cells are consistently giving back >70% of their peak. ",
            "Options:",
            "1. Tune the exit rule (tighter floor, faster reversal trigger)",
            "2. Demote to shadow_only=True for re-validation",
            "3. Veto the cell entirely if pattern persists ≥2 weeks",
            "",
        ]
        for m in reviews:
            lines.append(
                f"- `{m['symbol']}/{m['side']}`: {m['mean_capture']*100:.0f}% "
                f"avg over n={m['n']}"
            )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report: {REPORT_PATH}")
    print(f"Metrics: {METRICS_PATH}")
    print(f"Cells analyzed: {len(metrics)}, in REVIEW: {len(reviews)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
