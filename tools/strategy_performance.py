"""Per-strategy performance tracker with Bayesian shrinkage.

The team uses literature-derived priors for each strategy (hit rate, avg
winner, avg loser, expectancy) until enough actual trades accumulate.
This module:

1. Pulls all closed trades from state.fund.db (joined to theses for
   strategy attribution).
2. Computes observed hit rate, avg winner R, avg loser R, expectancy
   per strategy.
3. Applies Bayesian shrinkage: weighted average of prior + observed,
   where the prior weight equals the prior_n setting (default 30 trades).
4. Returns per-strategy stats with confidence intervals.

Until per-strategy n >= 20, treat results as advisory.
At n >= 50, observed ~ 70% weight; trust empirically.
"""
from __future__ import annotations
import math
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Literature-derived priors per strategy (hit_rate, avg_winner_R, avg_loser_R)
# These are the starting expectations; actual data updates them via Bayesian
# shrinkage as it accumulates.
LITERATURE_PRIORS: dict[str, dict[str, float]] = {
    # ── PRICE-ACTION (fund's primary focus, 2026-05-04) ──
    # Higher priors than classical TA — pattern-based microstructure
    # edge that works 24/5. FVG is the designated lead strategy.
    "fair_value_gap":            {"hit": 0.580, "win_r": 1.6, "loss_r": 1.0, "freq": "med"},
    "order_block":               {"hit": 0.560, "win_r": 1.8, "loss_r": 1.0, "freq": "low"},
    "liquidity_sweep":           {"hit": 0.550, "win_r": 1.5, "loss_r": 1.0, "freq": "med"},
    # ── CLASSICAL TA (backstop tier) ──
    # Trend / breakout
    "donchian_breakout":         {"hit": 0.375, "win_r": 2.0, "loss_r": 1.0, "freq": "low"},
    "volatility_breakout":       {"hit": 0.350, "win_r": 2.5, "loss_r": 1.0, "freq": "low"},
    "vol_regime_trend":          {"hit": 0.500, "win_r": 2.0, "loss_r": 1.0, "freq": "med"},
    "keltner_breakout":          {"hit": 0.450, "win_r": 1.8, "loss_r": 1.0, "freq": "med"},
    "bollinger_squeeze_break":   {"hit": 0.450, "win_r": 2.0, "loss_r": 1.0, "freq": "low"},
    # Mean reversion
    "bollinger_mean_reversion":  {"hit": 0.600, "win_r": 0.7, "loss_r": 1.0, "freq": "med"},
    "range_mean_reversion":      {"hit": 0.600, "win_r": 0.8, "loss_r": 1.0, "freq": "med"},
    "rsi2_extreme_reversion":    {"hit": 0.650, "win_r": 0.5, "loss_r": 1.0, "freq": "high"},
    # vwap_reversion REMOVED 2026-05-04 — confirmed broken in 60d walk-forward
    # (see scripts/walk_forward_gapfill.py and the 2026-05-04 deep analysis).
    # Pullback / continuation
    "pullback_in_trend":         {"hit": 0.550, "win_r": 1.5, "loss_r": 1.0, "freq": "med"},
    # Cadence / structure
    "opening_range_breakout":    {"hit": 0.400, "win_r": 1.5, "loss_r": 1.0, "freq": "med"},
    "narrow_range_break":        {"hit": 0.450, "win_r": 1.5, "loss_r": 1.0, "freq": "low"},
    "inside_bar_break":          {"hit": 0.500, "win_r": 1.3, "loss_r": 1.0, "freq": "med"},
    # Vol
    "vol_spike_fade":            {"hit": 0.550, "win_r": 1.0, "loss_r": 1.0, "freq": "low"},
    "volume_spike_reversal":     {"hit": 0.550, "win_r": 1.5, "loss_r": 1.0, "freq": "low"},
    # Levels / patterns
    "support_resistance_bounce": {"hit": 0.550, "win_r": 1.5, "loss_r": 1.0, "freq": "med"},
    # gap_fill priors UPGRADED 2026-05-04 after walk-forward validation:
    # ZN: train hit=65.7% E=+0.87R t=+15.21 | OOS hit=69.9% E=+1.20R t=+10.88
    # 6E: train E=+1.50R | OOS E=+2.65R — edge holds out-of-sample
    # NG: train E=+0.64R | OOS E=+0.83R — edge holds (borderline)
    # gap_fill is symbol-gated to {ZN, NG, 6E} via STRATEGY_SYMBOL_ALLOWLIST.
    "gap_fill":                  {"hit": 0.670, "win_r": 1.5, "loss_r": 1.0, "freq": "med"},
    "pivot_reversal":            {"hit": 0.500, "win_r": 1.5, "loss_r": 1.0, "freq": "med"},
}

# Bayesian shrinkage parameters
PRIOR_N = 30           # weight given to literature priors (in trade-equivalents)
ADVISORY_N = 20        # below this, results are advisory only
TRUST_N = 50           # at/above this, trust observed numbers heavily

# R-multiple normalization: assume average risk per trade is $200
# (matches our typical Kelly-lite + single-micro-floor sizing).
ASSUMED_R_USD = 200.0


@dataclass
class StrategyStats:
    name: str
    n_observed: int = 0
    observed_hit: float = 0.0
    observed_win_r: float = 0.0
    observed_loss_r: float = 0.0
    blended_hit: float = 0.0
    blended_win_r: float = 0.0
    blended_loss_r: float = 0.0
    blended_expectancy_r: float = 0.0
    confidence: str = "ADVISORY"   # ADVISORY | PATTERN | RULE | HARD
    note: str = ""

    def __repr__(self) -> str:
        return (f"<{self.name}: n={self.n_observed} hit={self.blended_hit:.0%} "
                f"E={self.blended_expectancy_r:+.2f}R [{self.confidence}]>")


def _bayes_blend(prior: float, prior_n: int, observed: float, observed_n: int) -> float:
    """Weighted blend of prior + observed."""
    if observed_n == 0:
        return prior
    return (prior * prior_n + observed * observed_n) / (prior_n + observed_n)


def _confidence_level(n: int) -> str:
    if n < ADVISORY_N: return "ADVISORY"
    if n < TRUST_N:    return "PATTERN"
    if n < 100:        return "RULE"
    return "HARD"


def get_strategy_stats(db_path: str | Path = "state/fund.db") -> dict[str, StrategyStats]:
    """Compute per-strategy stats by joining trades to theses."""
    db_path = Path(db_path)
    if not db_path.exists():
        return {name: _stats_from_prior(name) for name in LITERATURE_PRIORS}

    c = sqlite3.connect(str(db_path))
    c.row_factory = sqlite3.Row

    # Pull executed trades + match to thesis via decision proximity.
    # Schema may vary — defensive read.
    try:
        rows = c.execute("""
            SELECT d.id AS thesis_id, d.symbol, d.rationale, d.summary
            FROM decisions d
            WHERE d.kind = 'thesis'
            ORDER BY d.id ASC
        """).fetchall()
    except Exception:
        return {name: _stats_from_prior(name) for name in LITERATURE_PRIORS}

    # For each thesis, determine the strategy and look for the corresponding
    # closed trade outcome (from order_proposal -> execution chain).
    by_strategy: dict[str, list[dict]] = {name: [] for name in LITERATURE_PRIORS}

    for row in rows:
        rat = (row["rationale"] or "") + " " + (row["summary"] or "")
        # Find the strategy name in the rationale
        matched_strat = None
        for strat_name in LITERATURE_PRIORS:
            if strat_name in rat:
                matched_strat = strat_name
                break
        if not matched_strat:
            continue

        # Find the resulting closed trade P&L for this thesis.
        # Heuristic: find the next 'execution' decision after this thesis
        # that has the same symbol, then look for its P&L in costs/decisions.
        exec_row = c.execute("""
            SELECT id, rationale FROM decisions
            WHERE id > ? AND kind = 'execution' AND symbol = ?
            ORDER BY id ASC LIMIT 1
        """, (row["thesis_id"], row["symbol"])).fetchone()
        if not exec_row:
            continue

        # Extract realized P&L if recorded in rationale
        import re as _re
        pnl_match = _re.search(
            r"(?:realized|p&l|pnl|profit)\s*[:=]?\s*\$?(-?\d+(?:\.\d+)?)",
            (exec_row["rationale"] or ""), _re.IGNORECASE,
        )
        pnl_usd = float(pnl_match.group(1)) if pnl_match else None
        if pnl_usd is None:
            continue

        # Convert to R-multiple (negative if loss, positive if win)
        r_multiple = pnl_usd / ASSUMED_R_USD
        by_strategy[matched_strat].append({
            "pnl_usd": pnl_usd,
            "r_multiple": r_multiple,
            "thesis_id": row["thesis_id"],
        })

    # Compute stats per strategy
    out: dict[str, StrategyStats] = {}
    for name, prior in LITERATURE_PRIORS.items():
        observed = by_strategy.get(name, [])
        n = len(observed)
        if n == 0:
            out[name] = _stats_from_prior(name)
            continue
        wins = [t["r_multiple"] for t in observed if t["r_multiple"] > 0]
        losses = [t["r_multiple"] for t in observed if t["r_multiple"] <= 0]
        obs_hit = len(wins) / n
        obs_win_r = sum(wins) / len(wins) if wins else 0.0
        obs_loss_r = abs(sum(losses) / len(losses)) if losses else 0.0

        blended_hit = _bayes_blend(prior["hit"], PRIOR_N, obs_hit, n)
        blended_win = _bayes_blend(prior["win_r"], PRIOR_N, obs_win_r, n)
        blended_loss = _bayes_blend(prior["loss_r"], PRIOR_N, obs_loss_r, n)
        expectancy = blended_hit * blended_win - (1 - blended_hit) * blended_loss

        out[name] = StrategyStats(
            name=name,
            n_observed=n,
            observed_hit=obs_hit,
            observed_win_r=obs_win_r,
            observed_loss_r=obs_loss_r,
            blended_hit=blended_hit,
            blended_win_r=blended_win,
            blended_loss_r=blended_loss,
            blended_expectancy_r=expectancy,
            confidence=_confidence_level(n),
            note=f"n={n}, blend prior×{PRIOR_N}/observed×{n}",
        )
    return out


def _stats_from_prior(name: str) -> StrategyStats:
    """Generate stats with no observed data — pure prior."""
    p = LITERATURE_PRIORS[name]
    expectancy = p["hit"] * p["win_r"] - (1 - p["hit"]) * p["loss_r"]
    return StrategyStats(
        name=name,
        n_observed=0,
        blended_hit=p["hit"],
        blended_win_r=p["win_r"],
        blended_loss_r=p["loss_r"],
        blended_expectancy_r=expectancy,
        confidence="ADVISORY",
        note="no observed data — using literature prior",
    )


def rank_strategies(stats: dict[str, StrategyStats]) -> list[StrategyStats]:
    """Sort strategies by expectancy DESC; ties broken by confidence."""
    return sorted(
        stats.values(),
        key=lambda s: (s.blended_expectancy_r, s.n_observed),
        reverse=True,
    )


def render_markdown_report(stats: dict[str, StrategyStats]) -> str:
    """Generate the strategy_performance.md report content."""
    from datetime import datetime, timezone
    ranked = rank_strategies(stats)
    total_n = sum(s.n_observed for s in stats.values())
    confidence_counts: dict[str, int] = {}
    for s in stats.values():
        confidence_counts[s.confidence] = confidence_counts.get(s.confidence, 0) + 1

    lines: list[str] = []
    lines.append("---")
    lines.append("type: meta")
    lines.append("status: active")
    lines.append("applies_to: [Edge Hunter, Quant Researcher, Portfolio Manager, all analysts]")
    lines.append(f"updated: {datetime.now(tz=timezone.utc).isoformat(timespec='minutes')}")
    lines.append(f"total_observed_trades: {total_n}")
    lines.append("---")
    lines.append("")
    lines.append("# Strategy Performance — auto-tuning ranking")
    lines.append("")
    lines.append(
        "This document is **machine-generated** from actual closed trades + "
        "literature priors via Bayesian shrinkage. Updates automatically as "
        "trades close. Read on every wake — bias toward top-ranked strategies."
    )
    lines.append("")
    lines.append("**How to read:**")
    lines.append("- Strategies sorted by expectancy (highest first).")
    lines.append("- `n` = observed trades for this strategy.")
    lines.append("- `confidence`: ADVISORY (n<20), PATTERN (20-49), RULE (50-99), HARD (≥100).")
    lines.append(f"- ADVISORY = informational, use literature priors; PATTERN = some weight; RULE = trust empirical.")
    lines.append("")
    lines.append("## Confidence summary")
    lines.append("")
    for level in ("HARD", "RULE", "PATTERN", "ADVISORY"):
        n = confidence_counts.get(level, 0)
        lines.append(f"- **{level}**: {n} strategies")
    lines.append("")
    lines.append(f"**Total observed trades across all strategies: {total_n}**")
    lines.append("")
    lines.append("## Ranking")
    lines.append("")
    lines.append("| Rank | Strategy | Expectancy | Hit% | n | Conf |")
    lines.append("|---:|---|---:|---:|---:|---|")
    for i, s in enumerate(ranked, 1):
        marker = ""
        if s.blended_expectancy_r > 0.30: marker = " ⭐"
        if s.blended_expectancy_r > 0.45: marker = " ⭐⭐"
        if s.blended_expectancy_r < 0.05: marker = " ⚠️"
        lines.append(
            f"| {i} | `{s.name}`{marker} | {s.blended_expectancy_r:+.2f}R "
            f"| {s.blended_hit*100:.0f}% | {s.n_observed} | {s.confidence} |"
        )
    lines.append("")
    lines.append("## Bias guidance for analysts")
    lines.append("")
    top5 = ranked[:5]
    bottom3 = ranked[-3:]
    lines.append("**Prefer (top 5 by expectancy):**")
    for s in top5:
        lines.append(f"- `{s.name}` — E={s.blended_expectancy_r:+.2f}R, hit {s.blended_hit*100:.0f}% (n={s.n_observed}, {s.confidence})")
    lines.append("")
    lines.append("**Avoid / restrict (bottom 3 by expectancy):**")
    for s in bottom3:
        lines.append(f"- `{s.name}` — E={s.blended_expectancy_r:+.2f}R, hit {s.blended_hit*100:.0f}% (n={s.n_observed}, {s.confidence})")
    lines.append("")
    lines.append("## Methodology")
    lines.append("")
    lines.append(f"- **Bayesian shrinkage**: blended = (prior × {PRIOR_N} + observed × n) / ({PRIOR_N} + n)")
    lines.append(f"- **Prior weight**: {PRIOR_N} trade-equivalents from literature.")
    lines.append(f"- **R-normalization**: ${ASSUMED_R_USD:.0f}/R assumed for converting $ P&L to R-multiples.")
    lines.append("- **Confidence ladder:**")
    lines.append(f"  - n < {ADVISORY_N}: ADVISORY (use literature defaults; observed too noisy)")
    lines.append(f"  - {ADVISORY_N} ≤ n < {TRUST_N}: PATTERN (moderate weight)")
    lines.append(f"  - {TRUST_N} ≤ n < 100: RULE (trust empirical)")
    lines.append(f"  - n ≥ 100: HARD (codify as gate)")
    lines.append("")
    return "\n".join(lines)
