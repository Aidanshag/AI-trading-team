"""Agent scorecards — weekly performance + confidence calibration.

Per-agent metrics over a rolling 100-trade window:
  - hit_rate, avg_R, n_trades
  - tier (Top / Standard / Watch / Bench) per agent_performance.yaml
  - confidence calibration: high/med/low conviction labels vs realized
    hit-rate (are the labels actually informative?)

Output: vault/_meta/agent_scorecards.md

Usage:
  python -m scripts.agent_scorecards [--window 100] [--days 30]
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

from state.db import get_db


PERF_YAML = Path("config/agent_performance.yaml")
OUT_PATH = Path("vault/_meta/agent_scorecards.md")


def _conviction_from_rationale(rationale: str) -> str | None:
    """Extract conviction=<low|med|high> token if present."""
    if not rationale:
        return None
    m = re.search(r"conviction\s*[:=]\s*(low|med|medium|high)", rationale, re.I)
    if not m:
        return None
    v = m.group(1).lower()
    return "med" if v == "medium" else v


def _agent_trades(db, agent: str, window: int) -> list[dict]:
    """Return last N closed trades originated by `agent`.

    Closed trades = orders with status='filled' that have a matching
    post_trade decision (meaning the position closed). We approximate
    pnl_R via the post_trade summary if it carries '+1.5R' style notation.
    """
    rows = db.connect().execute(
        """SELECT d.id, d.ts, d.symbol, d.summary, d.rationale, d.kind
             FROM decisions d
            WHERE d.agent = ?
              AND d.kind IN ('thesis', 'order_proposal')
            ORDER BY d.id DESC
            LIMIT ?""",
        (agent, window * 3),  # over-fetch; not every thesis became a trade
    ).fetchall()
    out = []
    for r in rows:
        rationale = r["rationale"] or ""
        # pnl_R extraction from a post_trade decision linked by symbol+timing
        post = db.connect().execute(
            """SELECT summary FROM decisions
                WHERE kind = 'post_trade' AND symbol = ?
                  AND ts > ?
                ORDER BY id ASC LIMIT 1""",
            (r["symbol"], r["ts"]),
        ).fetchone()
        if not post:
            continue
        m = re.search(r"([+\-]?\d+(\.\d+)?)\s*R\b", post[0] or "")
        if not m:
            continue
        pnl_r = float(m.group(1))
        out.append({
            "ts": r["ts"], "symbol": r["symbol"], "pnl_r": pnl_r,
            "conviction": _conviction_from_rationale(rationale),
            "rationale": rationale,
        })
        if len(out) >= window:
            break
    return out


def _classify_tier(hit_rate: float, avg_r: float, n: int, thresholds: dict) -> str:
    if n < int(thresholds.get("minimum_trades_for_tiering", 20)):
        return "insufficient_sample"
    t = thresholds["thresholds"]
    if (hit_rate >= t["top_tier_win_rate"] and avg_r >= t["top_tier_avg_r"]):
        return "top"
    if (hit_rate >= t["standard_tier_win_rate"] and avg_r >= t["standard_tier_avg_r"]):
        return "standard"
    if hit_rate >= t["watch_tier_win_rate"]:
        return "watch"
    return "bench_candidate"


def _calibration_table(trades: list[dict]) -> dict[str, dict]:
    """Group by conviction label, compute per-bucket hit rate + avg R.

    A well-calibrated agent has high > med > low in both metrics.
    """
    buckets: dict[str, list[float]] = defaultdict(list)
    for t in trades:
        c = t.get("conviction") or "unlabeled"
        buckets[c].append(float(t["pnl_r"]))
    out = {}
    for c, rs in buckets.items():
        if not rs:
            continue
        wins = sum(1 for r in rs if r > 0)
        out[c] = {
            "n": len(rs),
            "hit_rate": wins / len(rs),
            "avg_r": sum(rs) / len(rs),
        }
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--window", type=int, default=100)
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()

    if not PERF_YAML.exists():
        print(f"missing {PERF_YAML}")
        return 2
    perf_cfg = yaml.safe_load(PERF_YAML.read_text(encoding="utf-8"))
    tracked = perf_cfg.get("tracked_agents", [])
    db = get_db()

    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    lines = [
        f"# Agent Scorecards — {today}",
        "",
        f"Rolling {args.window}-trade window. Min sample for tiering: "
        f"{perf_cfg.get('minimum_trades_for_tiering', 20)} closed trades.",
        "",
        "## Performance + tier",
        "",
        "| Agent | n | Hit-rate | Avg R | Tier |",
        "|---|---:|---:|---:|:---:|",
    ]
    calibration_out: dict[str, dict] = {}
    for agent in tracked:
        trades = _agent_trades(db, agent, args.window)
        n = len(trades)
        if n == 0:
            lines.append(f"| {agent} | 0 | — | — | _no closed trades_ |")
            continue
        wins = sum(1 for t in trades if t["pnl_r"] > 0)
        hit_rate = wins / n
        avg_r = sum(t["pnl_r"] for t in trades) / n
        tier = _classify_tier(hit_rate, avg_r, n, perf_cfg)
        lines.append(
            f"| {agent} | {n} | {hit_rate:.0%} | {avg_r:+.2f} | **{tier}** |"
        )
        calibration_out[agent] = _calibration_table(trades)

    lines += ["", "## Confidence calibration",
              "", "Are conviction labels predictive? "
              "Well-calibrated → `high > med > low` on both hit-rate and avg R. "
              "If high < med, the labels are noise — re-train the agent.", ""]
    for agent, buckets in calibration_out.items():
        if not buckets:
            continue
        lines += [f"### {agent}", "",
                  "| Conviction | n | Hit-rate | Avg R |",
                  "|---|---:|---:|---:|"]
        for c in ("high", "med", "low", "unlabeled"):
            b = buckets.get(c)
            if not b:
                continue
            lines.append(
                f"| {c} | {b['n']} | {b['hit_rate']:.0%} | {b['avg_r']:+.2f} |"
            )
        # Calibration verdict
        h, m, lo = buckets.get("high"), buckets.get("med"), buckets.get("low")
        if h and m and lo:
            ok = h["hit_rate"] >= m["hit_rate"] >= lo["hit_rate"]
            verdict = ("✓ calibrated" if ok else
                       "✗ MISCALIBRATED — labels are noise")
            lines.append(f"\n**Calibration:** {verdict}")
        lines.append("")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    if not args.quiet:
        print("\n".join(lines))
        print(f"\nWrote: {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
