"""Tests for the 5 new risk hook rules added 2026-04-29:
  - strategy blacklist
  - active lessons
  - post-stop cooldown
  - high-impact event blackout
  - daily target lock (profit lock-in)
"""
from __future__ import annotations
import importlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


@pytest.fixture
def hook(monkeypatch, tmp_path):
    """Reset risk_gate module and point CONFIG_ROOT at tmp."""
    mod = importlib.import_module("hooks.risk_gate")
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    monkeypatch.setattr(mod, "CONFIG_ROOT", cfg_dir)
    return mod


# ── Strategy blacklist ────────────────────────────────────────────

def test_strategy_blacklist_blocks_listed_combo(hook):
    limits = {"strategy_blacklist": [
        {"symbol": "ZN", "strategy": "opening_range_breakout",
         "reason": "thin overnight"}
    ]}
    v = hook._check_strategy_blacklist(
        tool_name="x",
        order={"symbol": "ZN", "strategy": "opening_range_breakout"},
        agent="X", limits=limits, topstep={}, symbols={}, snap=None, positions=[],
    )
    assert v is not None
    assert v["rule"] == "strategy_blacklist"
    assert "thin overnight" in v["reason"]


def test_strategy_blacklist_allows_unlisted_combo(hook):
    limits = {"strategy_blacklist": [
        {"symbol": "ZN", "strategy": "opening_range_breakout"}
    ]}
    v = hook._check_strategy_blacklist(
        tool_name="x",
        order={"symbol": "ZN", "strategy": "vol_regime_trend"},
        agent="X", limits=limits, topstep={}, symbols={}, snap=None, positions=[],
    )
    assert v is None


def test_strategy_blacklist_handles_topstep_contract_id(hook):
    """ProjectX form 'CON.F.US.TYA.M26' must resolve to ZN root."""
    limits = {"strategy_blacklist": [
        {"symbol": "ZN", "strategy": "opening_range_breakout"}
    ]}
    v = hook._check_strategy_blacklist(
        tool_name="x",
        order={"symbol": "CON.F.US.TYA.M26", "strategy": "opening_range_breakout"},
        agent="X", limits=limits, topstep={}, symbols={}, snap=None, positions=[],
    )
    assert v is not None


def test_strategy_blacklist_skipped_when_empty(hook):
    v = hook._check_strategy_blacklist(
        tool_name="x", order={"symbol": "ZN", "strategy": "orb"},
        agent="X", limits={}, topstep={}, symbols={}, snap=None, positions=[],
    )
    assert v is None


# ── Daily target lock ─────────────────────────────────────────────

def test_daily_hard_target_blocks_new_entry(hook):
    limits = {"combine_pacing": {"daily_hard_target_usd": 400}}
    snap = {"realized_pl_day_usd": 450.0}
    v = hook._check_daily_target_lock(
        tool_name="x", order={}, agent="X",
        limits=limits, topstep={}, symbols={}, snap=snap, positions=[],
    )
    assert v is not None
    assert v["rule"] == "daily_target_lock_hard"


def test_daily_target_below_hard_threshold_passes(hook):
    limits = {"combine_pacing": {"daily_hard_target_usd": 400}}
    snap = {"realized_pl_day_usd": 250.0}
    v = hook._check_daily_target_lock(
        tool_name="x", order={}, agent="X",
        limits=limits, topstep={}, symbols={}, snap=snap, positions=[],
    )
    assert v is None


def test_daily_target_lock_skipped_with_no_pacing_config(hook):
    v = hook._check_daily_target_lock(
        tool_name="x", order={}, agent="X",
        limits={}, topstep={}, symbols={},
        snap={"realized_pl_day_usd": 1000}, positions=[],
    )
    assert v is None


# ── Post-stop cooldown ────────────────────────────────────────────

def test_post_stop_cooldown_blocks_within_window(hook, tmp_path, monkeypatch):
    # Use an isolated DB. The cooldown now reads typed signals only:
    # primary = risk_events.rule='stop_hit_observed', emitted by the
    # reconciler when a broker stop-order fill closes a position.
    from state.db import Database
    test_db = Database(tmp_path / "test.db")
    test_db.init_schema()
    test_db.record_risk_event(
        severity="info", rule="stop_hit_observed",
        agent="reconciler",
        detail={"symbol": "ZN", "closed_position_side": "long"},
    )
    monkeypatch.setattr(hook, "get_db", lambda: test_db)
    limits = {"anti_tilt": {"post_stop_cooldown_minutes": 15}}
    v = hook._check_post_stop_cooldown(
        tool_name="x", order={}, agent="X",
        limits=limits, topstep={}, symbols={}, snap=None, positions=[],
    )
    assert v is not None
    assert v["rule"] == "post_stop_cooldown"


def test_post_stop_cooldown_legacy_decisions_kind(hook, tmp_path, monkeypatch):
    """Legacy fallback: decisions row with kind='stop_hit' (no LIKE match).
    Loose summary text alone no longer triggers — the typed kind is required."""
    from state.db import Database
    test_db = Database(tmp_path / "test.db")
    test_db.init_schema()
    test_db.record_decision(
        agent="orchestrator", kind="stop_hit",
        summary="ZN stop fill", rationale="stop_hit",
    )
    monkeypatch.setattr(hook, "get_db", lambda: test_db)
    limits = {"anti_tilt": {"post_stop_cooldown_minutes": 15}}
    v = hook._check_post_stop_cooldown(
        tool_name="x", order={}, agent="X",
        limits=limits, topstep={}, symbols={}, snap=None, positions=[],
    )
    assert v is not None


def test_post_stop_cooldown_ignores_loose_summary(hook, tmp_path, monkeypatch):
    """Verifies the LIKE-match brittleness is gone: a 'post_trade' row whose
    summary contains 'stopped out' must NOT trigger the cooldown anymore."""
    from state.db import Database
    test_db = Database(tmp_path / "test.db")
    test_db.init_schema()
    test_db.record_decision(
        agent="orchestrator", kind="post_trade",
        summary="ZN stopped out at -1R",
        rationale="random text mentioning stop_hit",
    )
    monkeypatch.setattr(hook, "get_db", lambda: test_db)
    limits = {"anti_tilt": {"post_stop_cooldown_minutes": 15}}
    v = hook._check_post_stop_cooldown(
        tool_name="x", order={}, agent="X",
        limits=limits, topstep={}, symbols={}, snap=None, positions=[],
    )
    assert v is None


def test_post_stop_cooldown_skipped_when_disabled(hook):
    limits = {"anti_tilt": {"post_stop_cooldown_minutes": 0}}
    v = hook._check_post_stop_cooldown(
        tool_name="x", order={}, agent="X",
        limits=limits, topstep={}, symbols={}, snap=None, positions=[],
    )
    assert v is None


# ── Active lessons ────────────────────────────────────────────────

def test_active_lesson_rule_tier_vetoes(hook, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    lessons = tmp_path / "vault" / "lessons"
    lessons.mkdir(parents=True)
    (lessons / "zn_orb.md").write_text(
        "---\nconfidence: RULE\napplies_to_symbol: zn\n---\nZN ORB fails overnight\n",
        encoding="utf-8",
    )
    v = hook._check_active_lessons(
        tool_name="x",
        order={"symbol": "ZN", "strategy": "opening_range_breakout"},
        agent="X", limits={}, topstep={}, symbols={}, snap=None, positions=[],
    )
    assert v is not None
    assert v["rule"] == "active_lesson_veto"


def test_active_lesson_advisory_tier_passes(hook, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    lessons = tmp_path / "vault" / "lessons"
    lessons.mkdir(parents=True)
    (lessons / "low_tier.md").write_text(
        "---\nconfidence: ADVISORY\napplies_to_symbol: zn\n---\n",
        encoding="utf-8",
    )
    v = hook._check_active_lessons(
        tool_name="x", order={"symbol": "ZN"},
        agent="X", limits={}, topstep={}, symbols={}, snap=None, positions=[],
    )
    assert v is None


def test_active_lesson_no_lessons_dir(hook, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    v = hook._check_active_lessons(
        tool_name="x", order={"symbol": "ZN"},
        agent="X", limits={}, topstep={}, symbols={}, snap=None, positions=[],
    )
    assert v is None


# ── High-impact blackout ──────────────────────────────────────────

def test_high_impact_blackout_blocks_within_window(hook, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cal = tmp_path / "vault" / "economic_calendar"
    cal.mkdir(parents=True)
    now_iso = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
    import json
    (cal / "today.json").write_text(
        json.dumps([{"ts_utc": now_iso, "impact": "high", "event": "CPI"}]),
        encoding="utf-8",
    )
    limits = {"sessions": {"high_impact_blackout_minutes": 5}}
    v = hook._check_high_impact_blackout(
        tool_name="x", order={}, agent="X",
        limits=limits, topstep={}, symbols={}, snap=None, positions=[],
    )
    assert v is not None
    assert v["rule"] == "high_impact_blackout"


def test_high_impact_blackout_skipped_with_no_calendar(hook, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    limits = {"sessions": {"high_impact_blackout_minutes": 5}}
    v = hook._check_high_impact_blackout(
        tool_name="x", order={}, agent="X",
        limits=limits, topstep={}, symbols={}, snap=None, positions=[],
    )
    assert v is None


def test_session_window_blocks_only_maintenance_break(hook, monkeypatch):
    """Bug fix 2026-04-29: session_window used to block every hour after
    15:55 CT — killed all overnight trading. Fixed to only block the
    actual 15:55–17:00 CT Globex maintenance break."""
    from datetime import time as _time

    # 16:30 CT — INSIDE maintenance break → block
    monkeypatch.setattr(hook, "_now_chicago", lambda: _time(16, 30))
    v = hook._check_session_window(
        tool_name="x", order={}, agent="X",
        limits={"sessions": {"no_new_positions_after_local_time": "15:55"}},
        topstep={}, symbols={}, snap=None, positions=[],
    )
    assert v is not None
    assert v["rule"] == "session_cutoff"


def test_session_window_allows_overnight(hook, monkeypatch):
    """22:30 CT — well after the maintenance break has ended → allow."""
    from datetime import time as _time
    monkeypatch.setattr(hook, "_now_chicago", lambda: _time(22, 30))
    v = hook._check_session_window(
        tool_name="x", order={}, agent="X",
        limits={"sessions": {"no_new_positions_after_local_time": "15:55"}},
        topstep={}, symbols={}, snap=None, positions=[],
    )
    assert v is None


def test_session_window_allows_pre_break_hours(hook, monkeypatch):
    """10:00 CT — well before maintenance break → allow."""
    from datetime import time as _time
    monkeypatch.setattr(hook, "_now_chicago", lambda: _time(10, 0))
    v = hook._check_session_window(
        tool_name="x", order={}, agent="X",
        limits={"sessions": {"no_new_positions_after_local_time": "15:55"}},
        topstep={}, symbols={}, snap=None, positions=[],
    )
    assert v is None


def test_session_window_skipped_with_no_cutoff(hook):
    v = hook._check_session_window(
        tool_name="x", order={}, agent="X",
        limits={"sessions": {}}, topstep={}, symbols={},
        snap=None, positions=[],
    )
    assert v is None


def test_high_impact_blackout_far_event_passes(hook, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cal = tmp_path / "vault" / "economic_calendar"
    cal.mkdir(parents=True)
    far_future = (datetime.now(tz=timezone.utc) + timedelta(hours=8)
                  ).isoformat(timespec="seconds")
    import json
    (cal / "today.json").write_text(
        json.dumps([{"ts_utc": far_future, "impact": "high", "event": "NFP"}]),
        encoding="utf-8",
    )
    limits = {"sessions": {"high_impact_blackout_minutes": 5}}
    v = hook._check_high_impact_blackout(
        tool_name="x", order={}, agent="X",
        limits=limits, topstep={}, symbols={}, snap=None, positions=[],
    )
    assert v is None
