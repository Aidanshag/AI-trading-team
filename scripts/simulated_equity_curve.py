"""Simulated equity curve — real + shadow combined.

Question this answers: "What if every shadow trade had also fired —
would we be making more money, less, or the same?"

If shadow contributes positively → focus universe is leaving alpha on
the table; expand it. If shadow drags negatively → focus is doing its
job; the wider screen is noise.

Output: vault/_meta/simulated_equity_curve.md with two cumulative R
series side by side: REAL (filled trades) vs SIM (real + shadow).

Usage:
  python -m scripts.simulated_equity_curve [--days 30]
"""
from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

from state.db import get_db


OUT = Path("vault/_meta/simulated_equity_curve.md")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()

    db = get_db()
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=args.days)
              ).isoformat(timespec="seconds")

    # 1. Real trade series — pnl_r extracted from post_trade summaries
    real_rows = db.connect().execute(
        """SELECT ts, symbol, summary FROM decisions
            WHERE kind = 'post_trade' AND ts >= ?
            ORDER BY ts""",
        (cutoff,),
    ).fetchall()

    real_series: list[tuple[str, str, float, str]] = []
    for r in real_rows:
        m = re.search(r"([+\-]?\d+(?:\.\d+)?)\s*R\b", r["summary"] or "")
        if m:
            real_series.append((r["ts"], r["symbol"] or "?",
                                float(m.group(1)), "REAL"))

    # 2. Shadow series
    shadow_rows = db.connect().execute(
        """SELECT ts_signal, symbol, pnl_r, strategy FROM shadow_trades
            WHERE outcome IS NOT NULL
              AND ts_signal >= ?
            ORDER BY ts_signal""",
        (cutoff,),
    ).fetchall()
    shadow_series = [
        (r["ts_signal"], r["symbol"], float(r["pnl_r"] or 0.0), "SHADOW")
        for r in shadow_rows
    ]

    # 3. Build combined timeline
    all_events = sorted(real_series + shadow_series, key=lambda e: e[0])

    cum_real = 0.0
    cum_sim = 0.0
    rows: list[tuple[str, str, float, str, float, float]] = []
    for ts, sym, r, kind in all_events:
        cum_sim += r
        if kind == "REAL":
            cum_real += r
        rows.append((ts, sym, r, kind, cum_real, cum_sim))

    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    lines = [f"# Simulated Equity Curve — {today}",
             "", f"Window: last **{args.days}** days. Cumulative R-multiples.",
             "",
             f"- **REAL** trades: {len(real_series)} closed; total R = {sum(e[2] for e in real_series):+.2f}",
             f"- **SHADOW** trades: {len(shadow_series)} resolved; total R = {sum(e[2] for e in shadow_series):+.2f}",
             "",
             f"**Verdict:** ", ""]
    sim_total = cum_sim
    real_total = cum_real
    delta = sim_total - real_total
    if abs(delta) < 0.5:
        verdict = ("Shadow scan is roughly flat — focus universe is appropriately "
                   "scoped. No signal to expand.")
    elif delta > 0:
        verdict = (f"Shadow trades ADD **{delta:+.2f}R** to the curve. "
                   f"Focus universe may be too narrow — review the shadow "
                   f"recap and consider promoting GREEN combos.")
    else:
        verdict = (f"Shadow trades SUBTRACT **{delta:+.2f}R**. The wider "
                   f"screen is noise — focus universe is doing its job.")
    lines[-2] = f"**Verdict:** {verdict}"

    lines += ["",
              "## Recent events (last 50)", "",
              "| ts | sym | kind | R | cum_real | cum_sim |",
              "|---|---|:---:|---:|---:|---:|"]
    for ts, sym, r, kind, cr, cs in rows[-50:]:
        lines.append(f"| {ts[:16]} | {sym} | {kind} | {r:+.2f} | "
                     f"{cr:+.2f} | {cs:+.2f} |")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    if not args.quiet:
        print("\n".join(lines))
        print(f"\nWrote: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
