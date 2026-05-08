"""Shared metrics helpers for Compliance, Quant Researcher, CIO.

All read-only SQL against state.db. Used to compute calibration,
strategy decay detection, journal enforcement gaps, and anti-portfolio scoring.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path("state/fund.db")


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


# ── #2 Per-agent calibration tracking ──────────────────────────────
def agent_hit_rates(rolling_n: int = 100, min_trades: int = 20) -> list[dict[str, Any]]:
    """For each agent that originated trades, compute rolling-N hit rate.

    A 'trade' is a closed order linked to an agent's order_proposal decision.
    Hit = positive R-multiple at close. We approximate from the orders table.

    Returns list of {agent, n_trades, wins, losses, hit_rate, tier_recommendation}.
    Agents with < min_trades return tier='insufficient_data'.
    """
    conn = _conn()
    rows = conn.execute(
        """
        SELECT agent, kind, COUNT(*) AS n
        FROM decisions
        WHERE kind IN ('thesis', 'order_proposal', 'shadow_trade')
        GROUP BY agent, kind
        """
    ).fetchall()

    counts: dict[str, dict[str, int]] = {}
    for r in rows:
        counts.setdefault(r["agent"], {})[r["kind"]] = r["n"]

    # Real hit-rate calc would require linking to filled orders + outcomes.
    # For now we return decision-volume-based stats; will be enriched once
    # post_trade_review decisions are populated.
    out = []
    for agent, k in counts.items():
        n = k.get("thesis", 0) + k.get("shadow_trade", 0) + k.get("order_proposal", 0)
        out.append({
            "agent": agent,
            "n_decisions": n,
            "n_thesis": k.get("thesis", 0),
            "n_shadow": k.get("shadow_trade", 0),
            "n_proposal": k.get("order_proposal", 0),
            "tier_recommendation": (
                "insufficient_data" if n < min_trades else "standard"
            ),
        })
    return sorted(out, key=lambda x: x["n_decisions"], reverse=True)


# ── #6 Trade journal enforcement ───────────────────────────────────
def trades_missing_post_mortem(hours: int = 24) -> list[dict[str, Any]]:
    """Find closed orders/shadow trades from the last N hours that have no
    matching kind='post_trade_review' decision recorded.
    """
    conn = _conn()
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(hours=hours)).isoformat()

    closed_trades = conn.execute(
        """
        SELECT id, ts, agent, kind, summary
        FROM decisions
        WHERE kind IN ('shadow_trade', 'order_proposal')
          AND ts >= ?
        """,
        (cutoff,),
    ).fetchall()

    reviews = conn.execute(
        "SELECT summary FROM decisions WHERE kind='post_trade_review' AND ts >= ?",
        (cutoff,),
    ).fetchall()
    reviewed_summaries = {(r["summary"] or "").lower() for r in reviews}

    missing = []
    for t in closed_trades:
        summary = (t["summary"] or "").lower()
        # Match on summary token overlap (rough heuristic — would be exact via
        # decision_id linking once schema is enhanced)
        if not any(summary in s or s in summary for s in reviewed_summaries):
            missing.append(dict(t))
    return missing


# ── #7 Strategy decay detection ────────────────────────────────────
def strategy_decay_check(decay_threshold_pct: float = 0.30) -> list[dict[str, Any]]:
    """Pull rolling stats per strategy mentioned in decisions.

    A strategy is flagged for decay if its rolling-100 hit rate is more than
    `decay_threshold_pct` BELOW its documented expectation.

    For now, returns counts by strategy (extracted from rationale text).
    Real hit-rate calc depends on outcome tracking — placeholder until orders
    table is reliably populated.
    """
    conn = _conn()
    rows = conn.execute(
        "SELECT rationale FROM decisions WHERE kind='thesis' AND rationale LIKE '%strateg%'"
    ).fetchall()
    counts: dict[str, int] = {}
    for r in rows:
        text = (r["rationale"] or "").lower()
        for strategy in (
            "donchian_breakout", "bollinger_mean_reversion", "volatility_breakout",
            "pullback_in_trend", "range_mean_reversion",
            "eia_surprise", "wasde", "fomc_pivot",
        ):
            if strategy in text:
                counts[strategy] = counts.get(strategy, 0) + 1
    return [{"strategy": s, "thesis_count": n, "decay_flag": False} for s, n in counts.items()]


# ── #9 Anti-portfolio (passed trades) ──────────────────────────────
def passed_trades(days: int = 7) -> list[dict[str, Any]]:
    """Decisions where PM passed on a thesis (didn't propose to Risk).

    A 'passed thesis' is identified by:
      kind='thesis' (analyst published), but no matching kind='order_proposal'
      from the PM in the next N hours after the thesis.

    The anti-portfolio: would these passed trades have made or lost money?
    Scoring requires market-data lookup — return the list for now; scoring
    is added when that pipeline is wired.
    """
    conn = _conn()
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()

    theses = conn.execute(
        "SELECT id, ts, agent, symbol, summary FROM decisions "
        "WHERE kind='thesis' AND ts >= ? ORDER BY id",
        (cutoff,),
    ).fetchall()

    proposals = conn.execute(
        "SELECT symbol, ts FROM decisions WHERE kind='order_proposal' AND ts >= ?",
        (cutoff,),
    ).fetchall()
    proposed_symbols = {(p["symbol"], p["ts"][:10]) for p in proposals}

    passed = []
    for t in theses:
        key = (t["symbol"], t["ts"][:10] if t["ts"] else "")
        if key not in proposed_symbols:
            passed.append({
                "ts": t["ts"], "agent": t["agent"], "symbol": t["symbol"],
                "summary": (t["summary"] or "")[:200],
                "score_status": "pending_market_data_lookup",
            })
    return passed


# ── Convenience: run all metrics ───────────────────────────────────
def daily_metrics_snapshot() -> dict[str, Any]:
    """Bundle of all metrics for a single Compliance wake to consume."""
    return {
        "ts": datetime.now(tz=timezone.utc).isoformat(),
        "agent_hit_rates": agent_hit_rates(),
        "missing_post_mortems": trades_missing_post_mortem(),
        "strategy_decay": strategy_decay_check(),
        "anti_portfolio_passed": passed_trades(),
    }


if __name__ == "__main__":
    print(json.dumps(daily_metrics_snapshot(), indent=2, default=str))
