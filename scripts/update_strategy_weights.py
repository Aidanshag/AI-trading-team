"""Update vault/_meta/strategy_performance.md from current trade history.

Runs autonomously every Nth tick + after each closed trade. Safe to call
frequently — the analysis is fast (DB read + math).

Usage:
  .\.venv\Scripts\python.exe scripts/update_strategy_weights.py
"""
from __future__ import annotations
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from tools.strategy_performance import (
    get_strategy_stats,
    render_markdown_report,
    rank_strategies,
)


def main():
    print("Pulling trade history + computing strategy stats...")
    stats = get_strategy_stats()
    total_n = sum(s.n_observed for s in stats.values())
    print(f"  Total observed trades: {total_n}")

    # Write the report
    out_path = Path("vault/_meta/strategy_performance.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_markdown_report(stats), encoding="utf-8")
    print(f"  Wrote: {out_path}")

    # Print top 5 + bottom 3 for quick view
    ranked = rank_strategies(stats)
    print()
    print("Top 5 by blended expectancy:")
    for i, s in enumerate(ranked[:5], 1):
        print(f"  {i}. {s.name:<28} E={s.blended_expectancy_r:+.2f}R "
              f"hit={s.blended_hit*100:.0f}% n={s.n_observed} ({s.confidence})")
    print()
    print("Bottom 3:")
    for s in ranked[-3:]:
        print(f"  - {s.name:<28} E={s.blended_expectancy_r:+.2f}R "
              f"hit={s.blended_hit*100:.0f}% n={s.n_observed} ({s.confidence})")


if __name__ == "__main__":
    main()
