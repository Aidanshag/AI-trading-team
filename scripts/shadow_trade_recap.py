"""Shadow-trade recap.

Reads resolved shadow trades from the SQLite store and produces a
hypothetical-performance recap that the CIO and Quant Researcher use to
decide whether to add new symbols/strategies to the active universe.

Output formats:
  - markdown report to vault/research/shadow_recap_YYYY-MM-DD.md
  - terminal summary
  - candidate-list JSON to vault/_meta/shadow_candidates.json

Promotion criteria (the symbol/strategy combos worth adding):

  GREEN  — promote to active focus universe
    n ≥ 8 resolved shadow trades AND
    win_rate ≥ 0.55 AND avg_R ≥ 0.7

  YELLOW — keep shadow-tracking; insufficient data
    3 ≤ n < 8 OR (win_rate ≥ 0.50 AND avg_R ≥ 0.5)

  RED    — drop from shadow scan; not productive
    n ≥ 8 AND (win_rate < 0.40 OR avg_R < 0.0)

Usage:
  python -m scripts.shadow_trade_recap [--days 14] [--out vault/research/]
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from state.db import get_db


def _classify(n: int, win_rate: float, avg_r: float) -> str:
    if n >= 8 and win_rate >= 0.55 and avg_r >= 0.7:
        return "GREEN"
    if n >= 8 and (win_rate < 0.40 or avg_r < 0.0):
        return "RED"
    return "YELLOW"


def _build_report(rows: list[dict], days: int) -> tuple[str, list[dict]]:
    """Return (markdown_text, candidate_list)."""
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    lines = [
        f"# Shadow-Trade Recap — {today}",
        "",
        f"Window: last **{days}** days. Resolved trades only.",
        "",
        "Shadow trades are TRIGGERs the team flagged on tickers outside the",
        "active focus universe (or otherwise unactionable). They cost no",
        "capital. Use this recap to decide whether to PROMOTE a symbol/",
        "strategy combo to the active set.",
        "",
        "## Per-(symbol, strategy) performance",
        "",
        "`Theo R` = idealized stop-vs-target outcome (research view).",
        "`Exec R` = what production would actually realize after "
        "slippage + fees + profit_lock + hard_flatten "
        "(see `tools/exec_mirror.py`). Promotion tier uses `Exec R`.",
        "",
        "| Symbol | Strategy | n | Wins | HR | Theo R | Exec R | Gap | Tier |",
        "|---|---|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    candidates: list[dict] = []
    if not rows:
        lines.append("| _no resolved shadow trades in window_ | | | | | | | | |")
    for r in rows:
        n = int(r["n"]); wins = int(r["wins"] or 0)
        hr = wins / n if n else 0.0
        avg_r = float(r["avg_r"] or 0.0)
        exec_r = float(r["exec_avg_r"] or 0.0) if r.get("exec_avg_r") is not None else None
        # Tier uses exec_mirror if available (more conservative); falls back
        # to theoretical if not yet populated.
        tier_input = exec_r if exec_r is not None else avg_r
        tier = _classify(n, hr, tier_input)
        gap_str = f"{(exec_r - avg_r):+.2f}" if exec_r is not None else "_n/a_"
        exec_str = f"{exec_r:+.2f}" if exec_r is not None else "_n/a_"
        lines.append(
            f"| {r['symbol']} | {r['strategy']} | {n} | {wins} | "
            f"{hr:.0%} | {avg_r:+.2f} | {exec_str} | {gap_str} | **{tier}** |"
        )
        candidates.append({
            "symbol": r["symbol"], "strategy": r["strategy"],
            "n": n, "win_rate": hr,
            "avg_r": avg_r, "exec_avg_r": exec_r,
            "tier": tier,
        })

    greens = [c for c in candidates if c["tier"] == "GREEN"]
    yellows = [c for c in candidates if c["tier"] == "YELLOW"]
    reds = [c for c in candidates if c["tier"] == "RED"]

    lines += [
        "",
        "## Promotion recommendations",
        "",
        f"**GREEN — promote to active focus** ({len(greens)} combos):",
    ]
    if greens:
        for c in greens:
            lines.append(f"- `{c['symbol']}` / `{c['strategy']}` "
                         f"({c['n']} trades, {c['win_rate']:.0%} win, "
                         f"{c['avg_r']:+.2f} avg R)")
    else:
        lines.append("- _none yet_")

    lines += ["", f"**YELLOW — keep shadow-tracking** ({len(yellows)} combos):"]
    if yellows:
        for c in yellows[:10]:  # cap noise
            lines.append(f"- `{c['symbol']}` / `{c['strategy']}` "
                         f"({c['n']} trades, {c['win_rate']:.0%} win, "
                         f"{c['avg_r']:+.2f} avg R)")
        if len(yellows) > 10:
            lines.append(f"- _…and {len(yellows) - 10} more_")
    else:
        lines.append("- _none_")

    lines += ["", f"**RED — drop from shadow scan** ({len(reds)} combos):"]
    if reds:
        for c in reds:
            lines.append(f"- `{c['symbol']}` / `{c['strategy']}` "
                         f"({c['n']} trades, {c['win_rate']:.0%} win, "
                         f"{c['avg_r']:+.2f} avg R)")
    else:
        lines.append("- _none_")

    lines += [
        "",
        "## Action items",
        "",
        "- CIO: review GREEN list at next session brief; add to focus universe",
        "  via `config/focus_universe.yaml` if backtest-aligned.",
        "- Quant Researcher: cross-check GREEN combos against literature",
        "  priors in `tools/strategy_performance.py` before promotion.",
        "- Edge Hunter: continue shadow-tracking YELLOW; deprioritize RED.",
        "",
        f"_Generated by `scripts/shadow_trade_recap.py` at {datetime.now(tz=timezone.utc).isoformat(timespec='seconds')}._",
        "",
    ]
    return "\n".join(lines), candidates


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=14)
    p.add_argument("--out", type=Path, default=Path("vault/research"))
    p.add_argument("--candidates-out", type=Path,
                   default=Path("vault/_meta/shadow_candidates.json"))
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()

    db = get_db()
    rows = db.shadow_trade_stats(days=args.days)

    md, candidates = _build_report(rows, args.days)

    args.out.mkdir(parents=True, exist_ok=True)
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    md_path = args.out / f"shadow_recap_{today}.md"
    md_path.write_text(md, encoding="utf-8")

    args.candidates_out.parent.mkdir(parents=True, exist_ok=True)
    args.candidates_out.write_text(
        json.dumps({"generated_at": datetime.now(tz=timezone.utc).isoformat(),
                    "window_days": args.days,
                    "candidates": candidates}, indent=2),
        encoding="utf-8",
    )

    if not args.quiet:
        print(md)
        print(f"\nWrote: {md_path}")
        print(f"Wrote: {args.candidates_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
