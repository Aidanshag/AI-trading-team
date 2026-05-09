"""P&L attribution by strategy + symbol.

Joins post_trade decisions with their originating thesis to produce:

  Strategy                     n   Wins   Hit%   Avg R    Total R
  -------------------------------------------------------------
  vol_regime_trend             8   5      62%    +1.4     +11.2
  opening_range_breakout       3   1      33%    -0.6      -1.8
  ...

Tells you which strategies pay the bills, which bleed, and which ones
have insufficient sample. Output: vault/_meta/pnl_attribution.md.

Usage:
  python -m scripts.pnl_attribution [--days 30]
"""
from __future__ import annotations

import argparse
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from state.db import get_db


OUT = Path("vault/_meta/pnl_attribution.md")


def _strategy_from_rationale(text: str) -> str | None:
    if not text:
        return None
    m = re.search(r"strategy\s*[:=]\s*([a-z_]+)", text, re.I)
    return m.group(1).lower() if m else None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()

    db = get_db()
    from datetime import timedelta
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=args.days)
              ).isoformat(timespec="seconds")

    # 1. Pull all post_trade decisions in window
    posts = db.connect().execute(
        """SELECT id, ts, symbol, summary, rationale FROM decisions
            WHERE kind = 'post_trade' AND ts >= ?
            ORDER BY id""",
        (cutoff,),
    ).fetchall()

    by_strategy: dict[str, list[float]] = defaultdict(list)
    by_symbol: dict[str, list[float]] = defaultdict(list)
    by_combo: dict[tuple[str, str], list[float]] = defaultdict(list)

    for row in posts:
        # Extract pnl_R
        m = re.search(r"([+\-]?\d+(?:\.\d+)?)\s*R\b", row["summary"] or "")
        if not m:
            continue
        pnl_r = float(m.group(1))

        # Walk backwards to find the originating thesis for this symbol
        thesis = db.connect().execute(
            """SELECT rationale FROM decisions
                WHERE kind IN ('thesis', 'order_proposal')
                  AND symbol = ?
                  AND ts <= ?
                ORDER BY id DESC LIMIT 1""",
            (row["symbol"], row["ts"]),
        ).fetchone()
        strategy = _strategy_from_rationale(
            thesis["rationale"] if thesis else None
        ) or "unattributed"

        by_strategy[strategy].append(pnl_r)
        by_symbol[row["symbol"] or "unknown"].append(pnl_r)
        by_combo[(row["symbol"] or "unknown", strategy)].append(pnl_r)

    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    lines = [f"# P&L Attribution — {today}",
             "", f"Window: last **{args.days}** days. Closed trades only.",
             "", "## By strategy", "",
             "| Strategy | n | Wins | Hit% | Avg R | Total R |",
             "|---|---:|---:|---:|---:|---:|"]
    if not by_strategy:
        lines.append("| _no closed trades in window_ | | | | | |")
    for strat, rs in sorted(by_strategy.items(), key=lambda x: -sum(x[1])):
        n = len(rs); wins = sum(1 for r in rs if r > 0)
        lines.append(f"| {strat} | {n} | {wins} | {wins/n:.0%} | "
                     f"{sum(rs)/n:+.2f} | **{sum(rs):+.2f}** |")

    lines += ["", "## By symbol", "",
              "| Symbol | n | Wins | Hit% | Avg R | Total R |",
              "|---|---:|---:|---:|---:|---:|"]
    for sym, rs in sorted(by_symbol.items(), key=lambda x: -sum(x[1])):
        n = len(rs); wins = sum(1 for r in rs if r > 0)
        lines.append(f"| {sym} | {n} | {wins} | {wins/n:.0%} | "
                     f"{sum(rs)/n:+.2f} | **{sum(rs):+.2f}** |")

    lines += ["", "## Top 10 symbol/strategy combos", "",
              "| Symbol | Strategy | n | Total R |",
              "|---|---|---:|---:|"]
    top = sorted(by_combo.items(), key=lambda x: -sum(x[1]))[:10]
    for (sym, strat), rs in top:
        lines.append(f"| {sym} | {strat} | {len(rs)} | **{sum(rs):+.2f}** |")

    lines += ["", "## Bottom 5 (bleeding combos)",
              "", "| Symbol | Strategy | n | Total R |",
              "|---|---|---:|---:|"]
    bot = sorted(by_combo.items(), key=lambda x: sum(x[1]))[:5]
    for (sym, strat), rs in bot:
        if sum(rs) >= 0:
            continue
        lines.append(f"| {sym} | {strat} | {len(rs)} | **{sum(rs):+.2f}** |")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    if not args.quiet:
        print("\n".join(lines))
        print(f"\nWrote: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
