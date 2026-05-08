"""Tests for the auto-tuning strategy performance engine."""
from __future__ import annotations
import sqlite3
from pathlib import Path

import pytest


def test_priors_have_all_strategies():
    from tools.strategy_performance import LITERATURE_PRIORS
    expected = {
        # Tier 1: price-action (added 2026-05-04, demoted same day pending validation)
        "fair_value_gap", "order_block", "liquidity_sweep",
        # Headline edge (validated 2026-05-04 walk-forward)
        "gap_fill",
        # Tier 2: classical TA (backstop)
        "donchian_breakout", "bollinger_mean_reversion", "volatility_breakout",
        "pullback_in_trend", "range_mean_reversion", "bollinger_squeeze_break",
        "keltner_breakout", "vol_regime_trend", "vol_spike_fade",
        "opening_range_breakout", "narrow_range_break", "inside_bar_break",
        "rsi2_extreme_reversion", "volume_spike_reversal",
        "support_resistance_bounce", "pivot_reversal",
        # vwap_reversion REMOVED 2026-05-04 — backtest+walk-forward confirmed broken
    }
    assert set(LITERATURE_PRIORS) == expected
    for name, p in LITERATURE_PRIORS.items():
        assert 0 < p["hit"] < 1
        assert p["win_r"] > 0
        assert p["loss_r"] > 0


def test_bayes_blend_with_zero_observations_returns_prior():
    from tools.strategy_performance import _bayes_blend
    assert _bayes_blend(0.50, 30, 0.0, 0) == 0.50


def test_bayes_blend_with_many_observations_dominates():
    from tools.strategy_performance import _bayes_blend
    # n=100 observations should pull blend toward observed
    blended = _bayes_blend(prior=0.50, prior_n=30, observed=0.70, observed_n=100)
    # Observed weight = 100/(30+100) = 77%
    assert 0.65 < blended < 0.69


def test_confidence_thresholds():
    from tools.strategy_performance import _confidence_level
    assert _confidence_level(0) == "ADVISORY"
    assert _confidence_level(19) == "ADVISORY"
    assert _confidence_level(20) == "PATTERN"
    assert _confidence_level(49) == "PATTERN"
    assert _confidence_level(50) == "RULE"
    assert _confidence_level(99) == "RULE"
    assert _confidence_level(100) == "HARD"
    assert _confidence_level(500) == "HARD"


def test_get_strategy_stats_empty_db_returns_priors(tmp_path):
    """With no DB, all strategies should fall back to literature priors."""
    from tools.strategy_performance import get_strategy_stats, LITERATURE_PRIORS
    stats = get_strategy_stats(tmp_path / "no_such_file.db")
    assert len(stats) == len(LITERATURE_PRIORS)
    for name, s in stats.items():
        assert s.n_observed == 0
        assert s.confidence == "ADVISORY"
        # Expectancy formula sanity check
        p = LITERATURE_PRIORS[name]
        expected_e = p["hit"] * p["win_r"] - (1 - p["hit"]) * p["loss_r"]
        assert abs(s.blended_expectancy_r - expected_e) < 1e-6


def test_render_markdown_report_runs(tmp_path):
    from tools.strategy_performance import get_strategy_stats, render_markdown_report
    stats = get_strategy_stats(tmp_path / "x.db")
    md = render_markdown_report(stats)
    assert "Strategy Performance" in md
    assert "ADVISORY" in md
    assert "Bias guidance" in md
    assert "Methodology" in md


def test_rank_strategies_descends_by_expectancy():
    from tools.strategy_performance import get_strategy_stats, rank_strategies
    stats = get_strategy_stats(Path("does_not_exist.db"))
    ranked = rank_strategies(stats)
    for i in range(len(ranked) - 1):
        assert ranked[i].blended_expectancy_r >= ranked[i+1].blended_expectancy_r


def test_priors_match_known_archetype_signs():
    """Top performers (vol_regime_trend, etc) should be positive expectancy.
    Known weak (rsi2_extreme_reversion at +0.5R win, 1R loss) should be near-zero."""
    from tools.strategy_performance import _stats_from_prior
    assert _stats_from_prior("vol_regime_trend").blended_expectancy_r > 0.30
    assert _stats_from_prior("pullback_in_trend").blended_expectancy_r > 0.20
    # rsi2 archetype is hit×win - (1-hit)×loss = 0.65×0.5 - 0.35×1.0 = -0.025R
    assert -0.10 < _stats_from_prior("rsi2_extreme_reversion").blended_expectancy_r < 0.10
