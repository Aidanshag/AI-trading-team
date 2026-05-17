"""Generate the canonical shadow-trading dashboard at
`vault/_meta/shadow_dashboard.md`.

One file, always current, navigable in Obsidian. Replaces the scattered
shadow_candidates.json / shadow_recap_*.md / futures/shadow_trades
files for "what's currently in shadow + how is it doing."

Run daily via FundVaultMaintenance (already scheduled) — append
`python -m scripts.shadow_dashboard` to that task. Or invoke manually
any time:
    .venv/Scripts/python.exe -m scripts.shadow_dashboard
"""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "state" / "fund.db"
VALIDATION_FILE = PROJECT_ROOT / "state" / "strategy_validation.json"
OUT_PATH = PROJECT_ROOT / "vault" / "_meta" / "shadow_dashboard.md"


def cell_key(c: dict) -> str:
    return f"{c.get('strategy')}/{c.get('symbol')}/{c.get('session')}/{c.get('side')}"


def fetch_shadow_stats(conn: sqlite3.Connection, days: int = 30) -> dict[str, dict]:
    """Per-cell shadow performance from the shadow_trades table."""
    cutoff_iso = (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT symbol, strategy, side, outcome, pnl_r, exec_mirror_pnl_r, ts_signal
        FROM shadow_trades
        WHERE outcome IS NOT NULL AND outcome != '' AND ts_signal >= ?
    """, (cutoff_iso,)).fetchall()
    by_cell: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        sym, strat, side, outcome, pnl_r, ex_pnl_r, ts = r
        # Cell key doesn't have session in shadow_trades — use stratsymside
        key = f"{strat}/{sym}/{side}"
        by_cell[key].append({
            'outcome': outcome, 'pnl_r': pnl_r,
            'ex_pnl_r': ex_pnl_r, 'ts': ts,
        })
    stats = {}
    for key, trades in by_cell.items():
        n = len(trades)
        pnls = [t['pnl_r'] for t in trades if t['pnl_r'] is not None]
        expnls = [t['ex_pnl_r'] for t in trades if t['ex_pnl_r'] is not None]
        if not pnls:
            continue
        hit = sum(1 for r in pnls if r > 0) / n
        avg_r = sum(pnls) / n
        avg_ex_r = (sum(expnls) / len(expnls)) if expnls else None
        stats[key] = {
            'n': n, 'hit': hit, 'avg_r': avg_r,
            'avg_ex_r': avg_ex_r,
        }
    return stats


def main() -> int:
    with open(VALIDATION_FILE) as f:
        val = json.load(f)
    allow = val.get('live_allowlist', [])
    live = [c for c in allow if not c.get('experimental')]
    shadow = [c for c in allow if c.get('experimental')]

    conn = sqlite3.connect(str(DB_PATH))
    try:
        shadow_stats_30d = fetch_shadow_stats(conn, days=30)
        shadow_stats_7d = fetch_shadow_stats(conn, days=7)
        # Totals
        total_shadow = conn.cursor().execute(
            "SELECT COUNT(*) FROM shadow_trades"
        ).fetchone()[0]
        resolved = conn.cursor().execute(
            "SELECT COUNT(*) FROM shadow_trades "
            "WHERE outcome IS NOT NULL AND outcome != ''"
        ).fetchone()[0]
        since_friday = conn.cursor().execute(
            "SELECT COUNT(*) FROM shadow_trades "
            "WHERE ts_signal >= datetime('now', '-3 day')"
        ).fetchone()[0]
    finally:
        conn.close()

    now_iso = datetime.now(tz=timezone.utc).isoformat()
    today = datetime.now(tz=timezone.utc).strftime('%Y-%m-%d')

    lines = []
    lines.append("---")
    lines.append("type: dashboard")
    lines.append(f"date: {today}")
    lines.append(f"generated_at: {now_iso}")
    lines.append("auto_generated_by: scripts/shadow_dashboard.py")
    lines.append("---")
    lines.append("")
    lines.append("# Shadow trading dashboard")
    lines.append("")
    lines.append("_Auto-generated. Single source of truth for what's currently "
                  "in shadow + how each cell is performing in real-market "
                  "conditions. Updated daily via `FundVaultMaintenance`._")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Live cells (real fills):** {len(live)}")
    lines.append(f"- **Shadow cells (recording only):** {len(shadow)}")
    lines.append(f"- **Total `shadow_trades` rows in DB:** {total_shadow}")
    lines.append(f"- **Resolved (graded):** {resolved}")
    lines.append(f"- **Signals in last 3 days:** {since_friday}")
    lines.append("")

    # ─── Cells currently in shadow ──────────────────────────────
    lines.append("## Cells currently in shadow")
    lines.append("")
    lines.append("Each shadow cell records signals to `shadow_trades` without "
                  "placing real orders. After 2-4 weeks of positive live data, "
                  "candidates can be promoted to `experimental:false` (real fills).")
    lines.append("")
    if shadow:
        lines.append("| Strategy | Symbol | Session | Side | Source | 30d shadow n | 30d hit | 30d avg R | 30d avg R (friction) |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for c in sorted(shadow, key=lambda x: cell_key(x)):
            sym = c.get('symbol', '?')
            strat = c.get('strategy', '?')
            sess = c.get('session', '?')
            side = c.get('side', '?')
            source = (c.get('shadow_reason') or 'older')[:35]
            sk = f"{strat}/{sym}/{side}"
            s = shadow_stats_30d.get(sk)
            if s:
                n = s['n']
                hit = f"{s['hit']*100:.0f}%"
                avg_r = f"{s['avg_r']:+.2f}"
                avg_ex_r = f"{s['avg_ex_r']:+.2f}" if s['avg_ex_r'] is not None else "n/a"
            else:
                n, hit, avg_r, avg_ex_r = 0, "-", "-", "-"
            lines.append(f"| {strat} | {sym} | {sess} | {side} | {source} | {n} | {hit} | {avg_r} | {avg_ex_r} |")
    else:
        lines.append("_No shadow cells._")
    lines.append("")

    # ─── Live cells (for reference) ─────────────────────────────
    lines.append("## Cells currently live (real fills)")
    lines.append("")
    if live:
        lines.append("| Strategy | Symbol | Session | Side | Promoted |")
        lines.append("|---|---|---|---|---|")
        for c in sorted(live, key=lambda x: cell_key(x)):
            sym = c.get('symbol', '?')
            strat = c.get('strategy', '?')
            sess = c.get('session', '?')
            side = c.get('side', '?')
            promoted = (c.get('promoted_at') or '')[:10]
            lines.append(f"| {strat} | {sym} | {sess} | {side} | {promoted} |")
    else:
        lines.append("_No live cells._")
    lines.append("")

    # ─── Promotion candidates (≥25 trades + positive avg_ex_r) ──
    lines.append("## Promotion candidates")
    lines.append("")
    lines.append("Shadow cells with **n≥25** in last 30 days AND **positive "
                  "avg_ex_r** (friction-adjusted). These cells have enough "
                  "live data to consider promoting to real fills.")
    lines.append("")
    candidates = []
    for c in shadow:
        sk = f"{c['strategy']}/{c['symbol']}/{c['side']}"
        s = shadow_stats_30d.get(sk)
        if s and s['n'] >= 25 and (s['avg_ex_r'] or 0) > 0:
            candidates.append((c, s))
    if candidates:
        candidates.sort(key=lambda x: x[1]['avg_ex_r'] or 0, reverse=True)
        lines.append("| Cell | n | Hit | Avg R | Avg R (friction) |")
        lines.append("|---|---|---|---|---|")
        for c, s in candidates:
            label = cell_key(c)
            lines.append(f"| {label} | {s['n']} | {s['hit']*100:.0f}% | "
                          f"{s['avg_r']:+.2f} | {s['avg_ex_r']:+.2f} |")
    else:
        lines.append("_No cells with enough data yet (need n≥25 in 30 days)._")
    lines.append("")

    # ─── 7-day pulse ────────────────────────────────────────────
    lines.append("## 7-day pulse (active firing)")
    lines.append("")
    lines.append("Shadow cells that fired in the last 7 days. Quick check on "
                  "whether the staged cells are actually emitting signals.")
    lines.append("")
    active_7d = []
    for c in shadow:
        sk = f"{c['strategy']}/{c['symbol']}/{c['side']}"
        s = shadow_stats_7d.get(sk)
        if s and s['n'] > 0:
            active_7d.append((c, s))
    if active_7d:
        active_7d.sort(key=lambda x: x[1]['n'], reverse=True)
        lines.append("| Cell | 7d signals | Hit | Avg R |")
        lines.append("|---|---|---|---|")
        for c, s in active_7d:
            label = cell_key(c)
            lines.append(f"| {label} | {s['n']} | {s['hit']*100:.0f}% | "
                          f"{s['avg_r']:+.2f} |")
    else:
        lines.append("_No shadow cells fired in the last 7 days._")
    lines.append("")

    # ─── Pre-fix cleanup history ────────────────────────────────
    lines.append("## Recent cleanup history")
    lines.append("")
    lines.append("- 2026-05-17: removed 28 pre-fix gap_fill / gap_fill_wide "
                  "cells flagged with `shadow_caveat` (Pattern B inflation). "
                  "Only post-fix honest cells remain.")
    lines.append("")
    lines.append("## How to read this")
    lines.append("")
    lines.append("- **shadow_reason** tells you why the cell was staged "
                  "(`universal discovery`, `ag post-fix`, etc.)")
    lines.append("- **30d hit** below 30% is normal for trend-followers — "
                  "look at **avg R** for true edge")
    lines.append("- **avg R (friction)** is the realistic number after "
                  "slippage + fees. Cells with positive `avg_r` but negative "
                  "`avg_r_friction` are NOT profitable in reality")
    lines.append("- Cells in **Promotion candidates** are ready for user "
                  "review to flip `experimental:false` for real fills")
    lines.append("")
    lines.append("## Source of truth")
    lines.append("")
    lines.append("- `state/strategy_validation.json:live_allowlist` — cell config")
    lines.append("- `state/fund.db:shadow_trades` — every signal recorded")
    lines.append("- `scripts/cell_auto_promote.py` — auto-promote logic")
    lines.append("- `scripts/resolve_shadow_trades.py` — nightly grader")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")
    print(f"  Shadow cells: {len(shadow)}")
    print(f"  Live cells: {len(live)}")
    print(f"  Promotion candidates: {len(candidates)}")
    print(f"  7-day active: {len(active_7d)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
