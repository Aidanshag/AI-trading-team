"""Tests for the shadow-trade screening system."""
from __future__ import annotations

import pytest

from state.db import Database
from scripts.resolve_shadow_trades import _evaluate_path
from scripts.shadow_trade_recap import _classify, _build_report


@pytest.fixture
def db(tmp_path):
    d = Database(tmp_path / "test.db")
    d.init_schema()
    yield d
    d.close()


def test_record_and_resolve_shadow_trade(db):
    sid = db.record_shadow_trade(
        agent="Edge Hunter", symbol="CL", strategy="vol_regime_trend",
        side="long", entry_price=72.0, stop_price=71.5, target_price=73.0,
        shadow_reason="focus_universe_blocked", rr_planned=2.0,
        conviction="med", horizon="intraday",
    )
    assert sid > 0

    pending = db.unresolved_shadow_trades(age_min_minutes=0)
    assert len(pending) == 1
    assert pending[0]["symbol"] == "CL"

    db.resolve_shadow_trade(sid, outcome="target_hit", pnl_r=2.0)

    pending2 = db.unresolved_shadow_trades(age_min_minutes=0)
    assert len(pending2) == 0


def test_shadow_stats_aggregation(db):
    # 3 trades on CL/ORB: 2 wins, 1 loss
    for outcome, pnl in [("target_hit", 2.0), ("target_hit", 2.0), ("stop_hit", -1.0)]:
        sid = db.record_shadow_trade(
            agent="Edge Hunter", symbol="CL", strategy="opening_range_breakout",
            side="long", entry_price=72.0, stop_price=71.5, target_price=73.0,
            shadow_reason="focus_universe_blocked",
        )
        db.resolve_shadow_trade(sid, outcome=outcome, pnl_r=pnl)

    stats = db.shadow_trade_stats(days=30)
    assert len(stats) == 1
    row = stats[0]
    assert row["symbol"] == "CL"
    assert row["n"] == 3
    assert row["wins"] == 2
    assert row["avg_r"] == pytest.approx((2 + 2 - 1) / 3)


def test_evaluate_path_target_hit_long():
    bars = [
        {"t": "1", "o": 72.0, "h": 72.05, "l": 71.95, "c": 72.0},
        {"t": "2", "o": 72.0, "h": 72.20, "l": 71.95, "c": 72.10},  # entry @ 72
        {"t": "3", "o": 72.10, "h": 73.05, "l": 72.05, "c": 73.0},  # target hit
    ]
    outcome, pnl_r, _ = _evaluate_path(
        bars, side="long", entry=72.0, stop=71.5, target=73.0,
    )
    assert outcome == "target_hit"
    assert pnl_r == pytest.approx(2.0)  # (73-72) / (72-71.5) = 2.0


def test_evaluate_path_stop_hit_long():
    bars = [
        {"t": "1", "o": 72.0, "h": 72.10, "l": 72.0, "c": 72.05},
        {"t": "2", "o": 72.05, "h": 72.10, "l": 71.45, "c": 71.50},  # stop @ 71.5
    ]
    outcome, pnl_r, _ = _evaluate_path(
        bars, side="long", entry=72.0, stop=71.5, target=73.0,
    )
    assert outcome == "stop_hit"
    assert pnl_r == -1.0


def test_evaluate_path_short_target_hit():
    bars = [
        {"t": "1", "o": 72.0, "h": 72.10, "l": 71.95, "c": 71.95},  # entry @ 72 (short, fills on touch)
        {"t": "2", "o": 71.95, "h": 72.0, "l": 70.95, "c": 71.0},   # short target @ 71.0
    ]
    outcome, pnl_r, _ = _evaluate_path(
        bars, side="short", entry=72.0, stop=72.5, target=71.0,
    )
    assert outcome == "target_hit"
    assert pnl_r == pytest.approx(2.0)  # (72-71)/(72.5-72)=2


def test_evaluate_path_time_stopped():
    # neither stop nor target — time stop with mark-to-market
    bars = [
        {"t": "1", "o": 72.0, "h": 72.10, "l": 71.95, "c": 72.05},  # entry filled
        {"t": "2", "o": 72.05, "h": 72.20, "l": 71.95, "c": 72.15},
    ]
    outcome, pnl_r, _ = _evaluate_path(
        bars, side="long", entry=72.0, stop=71.5, target=73.0,
    )
    assert outcome == "time_stopped"
    assert pnl_r == pytest.approx((72.15 - 72.0) / 0.5)


def test_evaluate_path_no_bars():
    outcome, pnl_r, _ = _evaluate_path(
        [], side="long", entry=72.0, stop=71.5, target=73.0,
    )
    assert outcome == "invalidated"


def test_evaluate_path_zero_risk_invalid():
    bars = [{"t": "1", "o": 72.0, "h": 73.0, "l": 71.0, "c": 72.0}]
    outcome, _, _ = _evaluate_path(
        bars, side="long", entry=72.0, stop=72.0, target=73.0,
    )
    assert outcome == "invalidated"


def test_classify_green():
    assert _classify(n=10, win_rate=0.60, avg_r=1.0) == "GREEN"


def test_classify_red():
    assert _classify(n=10, win_rate=0.30, avg_r=-0.2) == "RED"


def test_classify_yellow_low_n():
    assert _classify(n=4, win_rate=0.80, avg_r=1.5) == "YELLOW"


def test_build_report_no_data():
    md, candidates = _build_report([], days=14)
    assert "Shadow-Trade Recap" in md
    assert candidates == []


def test_build_report_with_green():
    rows = [{"symbol": "CL", "strategy": "ORB", "n": 10, "wins": 7,
             "avg_r": 1.2, "min_r": -1.0, "max_r": 3.0}]
    md, candidates = _build_report(rows, days=14)
    assert "CL" in md
    assert "GREEN" in md
    assert candidates[0]["tier"] == "GREEN"
