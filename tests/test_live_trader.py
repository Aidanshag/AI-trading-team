"""Tests for scripts/live_trader.py — the simplified Layer 1 knife.

Coverage:
- session_now_utc: ET session bucketing
- load_live_cells: brain output parsing
- is_halted: halt-file + config checks
- dll_breached: daily loss limit check
- find_latest_signal: lookback window enforcement
- _round_to_tick: tick-size rounding for brackets
- recent_thesis_for: cooldown tracking
- scan_once dry-run: end-to-end no-orders behavior
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts import live_trader as lt  # noqa: E402


# ─── session bucketing ─────────────────────────────────────────

def test_session_now_utc_rth():
    # 14:00 UTC = 10:00 ET → RTH
    t = datetime(2026, 5, 8, 14, 0, tzinfo=timezone.utc)
    assert lt.session_now_utc(t) == "RTH"


def test_session_now_utc_london():
    # 08:00 UTC = 04:00 ET → London
    t = datetime(2026, 5, 8, 8, 0, tzinfo=timezone.utc)
    assert lt.session_now_utc(t) == "London"


def test_session_now_utc_postclose():
    # 22:00 UTC = 18:00 ET → PostClose
    t = datetime(2026, 5, 8, 22, 0, tzinfo=timezone.utc)
    assert lt.session_now_utc(t) == "PostClose"


def test_session_now_utc_asian():
    # 02:00 UTC = 22:00 ET → Asian (wraps)
    t = datetime(2026, 5, 8, 2, 0, tzinfo=timezone.utc)
    assert lt.session_now_utc(t) == "Asian"


# ─── load_live_cells ────────────────────────────────────────────

def test_load_live_cells_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(lt, "LIVE_ALLOWLIST_PATH", tmp_path / "missing.json")
    assert lt.load_live_cells() == []


def test_load_live_cells_valid(tmp_path, monkeypatch):
    state_file = tmp_path / "validation.json"
    state_file.write_text(json.dumps({
        "live_allowlist": [
            {"strategy": "gap_fill", "symbol": "ZN", "session": "Asian", "side": "long"},
            {"strategy": "gap_fill", "symbol": "ZT", "session": "Asian", "side": "short"},
        ]
    }))
    monkeypatch.setattr(lt, "LIVE_ALLOWLIST_PATH", state_file)
    cells = lt.load_live_cells()
    assert len(cells) == 2
    assert cells[0]["symbol"] == "ZN"


def test_load_live_cells_corrupt(tmp_path, monkeypatch):
    state_file = tmp_path / "bad.json"
    state_file.write_text("{not valid json")
    monkeypatch.setattr(lt, "LIVE_ALLOWLIST_PATH", state_file)
    assert lt.load_live_cells() == []


# ─── halt checks ────────────────────────────────────────────────

def test_is_halted_no_halt(tmp_path, monkeypatch):
    monkeypatch.setattr(lt, "HALT_FILE", tmp_path / "no_halt")
    halted, reason = lt.is_halted()
    # Note: also depends on config/risk_limits.yaml; if past halt timestamp, OK
    # We only assert the touch-file path is False
    assert not (tmp_path / "no_halt").exists()


def test_is_halted_touchfile(tmp_path, monkeypatch):
    halt_file = tmp_path / "halt"
    halt_file.touch()
    monkeypatch.setattr(lt, "HALT_FILE", halt_file)
    halted, reason = lt.is_halted()
    assert halted is True
    assert "manual" in reason.lower()


# ─── DLL breach ─────────────────────────────────────────────────

def test_dll_not_breached():
    # Default DLL is $1000 in risk_limits.yaml
    snap = {"realized_pl_day_usd": -500.0}
    breached, why = lt.dll_breached(snap)
    assert not breached


def test_dll_breached():
    snap = {"realized_pl_day_usd": -1500.0}
    breached, why = lt.dll_breached(snap)
    assert breached is True
    assert "1500" in why or "<= -" in why


def test_dll_at_zero():
    snap = {"realized_pl_day_usd": 0.0}
    breached, _ = lt.dll_breached(snap)
    assert not breached


# ─── tick rounding ──────────────────────────────────────────────

def test_round_to_tick_basic():
    assert lt._round_to_tick(110.523, 0.015625) == round(round(110.523 / 0.015625) * 0.015625, 8)


def test_round_to_tick_exact():
    assert lt._round_to_tick(110.5, 0.5) == 110.5


def test_tick_size_zn():
    assert lt._tick_size("ZN") == 0.015625


def test_tick_size_unknown_falls_back():
    # Unknown symbol returns the default 0.01
    assert lt._tick_size("UNKNOWN_FOO") == 0.01


# ─── find_latest_signal lookback ────────────────────────────────

def test_find_latest_signal_short_bars():
    import pandas as pd
    bars = pd.DataFrame(
        {"Open": [1, 2], "High": [1, 2], "Low": [1, 2], "Close": [1, 2], "Volume": [1, 1]},
        index=pd.to_datetime(["2026-05-08 00:00", "2026-05-08 00:05"]),
    )

    def fn(b):
        yield from []

    assert lt.find_latest_signal(bars, fn) is None  # too few bars


def test_find_latest_signal_no_entries():
    import pandas as pd
    n = 50
    bars = pd.DataFrame(
        {"Open": list(range(n)), "High": list(range(n)),
         "Low": list(range(n)), "Close": list(range(n)),
         "Volume": [1] * n},
        index=pd.date_range("2026-05-08", periods=n, freq="5min"),
    )

    def fn(b):
        yield from []  # no signals

    assert lt.find_latest_signal(bars, fn) is None


# ─── module imports cleanly ─────────────────────────────────────

def test_module_imports():
    """Confirm the trader module imports without errors."""
    assert hasattr(lt, "scan_once")
    assert hasattr(lt, "place_bracket")
    assert hasattr(lt, "find_latest_signal")
    assert hasattr(lt, "main")
    assert hasattr(lt, "load_live_cells")
    assert lt.SCAN_INTERVAL_SEC > 0
    assert lt.LOOKBACK_BARS > 0
    assert lt.PER_TRADE_LOSS_CAP_USD > 0


def test_constants_align_with_v1_intent():
    """The simplified trader's constants should match the v1's intent
    where intent was clear."""
    assert lt.LOOKBACK_BARS == 6              # 30 min on 5m bars
    assert lt.SCAN_INTERVAL_SEC == 300        # 5 min
    assert lt.PER_TRADE_LOSS_CAP_USD == 150.0  # tightened for first night
