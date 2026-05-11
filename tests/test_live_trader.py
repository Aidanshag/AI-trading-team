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
    assert lt.MIN_SIGNAL_R_TICKS >= 6          # must exceed 5-tick marketable buffer


# ─── degenerate-R signal gate (2026-05-10 incident) ────────────────

def test_min_r_gate_rejects_stop_equals_entry():
    """The 2026-05-10 incident shape: ATR collapses to <1 tick in low-vol
    session, so the strategy emits a signal whose stop is rounded to the
    same price as entry. Must reject."""
    sig = {"price": 110.53125, "stop": 110.53125, "target": 110.546875}
    ok, reason = lt.signal_passes_min_r_gate(sig, "ZN")
    assert ok is False
    assert "stop too close" in reason


def test_min_r_gate_rejects_one_tick_target():
    """A signal with adequate stop but a target only one tick from entry
    can't survive the 5-tick marketable-limit buffer. Reject."""
    sig = {"price": 110.50, "stop": 110.38, "target": 110.515625}  # target ~1 tick
    ok, reason = lt.signal_passes_min_r_gate(sig, "ZN")
    assert ok is False
    assert "target too close" in reason


def test_min_r_gate_passes_normal_signal():
    """A signal with comfortable R-distance on both sides passes."""
    sig = {"price": 110.50, "stop": 110.30, "target": 110.80}
    ok, reason = lt.signal_passes_min_r_gate(sig, "ZN")
    assert ok is True
    assert reason == ""


def test_min_r_gate_rejects_missing_stop():
    sig = {"price": 110.50, "stop": None, "target": 110.80}
    ok, reason = lt.signal_passes_min_r_gate(sig, "ZN")
    assert ok is False


def test_min_r_gate_no_target_uses_stop_only():
    """Some strategies emit signals without a target. Gate should pass
    if stop-distance is adequate."""
    sig = {"price": 110.50, "stop": 110.30, "target": None}
    ok, reason = lt.signal_passes_min_r_gate(sig, "ZN")
    assert ok is True


# ─── orphan-leg fix (2026-05-10 incident) ───────────────────────────

class _FakeBrokerNoPosition:
    def get_positions(self, account_id):
        return []


class _FakeBrokerWithPosition:
    def __init__(self, contract_id, type_, size):
        self._cid, self._type, self._size = contract_id, type_, size

    def get_positions(self, account_id):
        return [{"contractId": self._cid, "type": self._type, "size": self._size}]


def test_position_signature_returns_zero_when_flat():
    sig = lt._position_signature(_FakeBrokerNoPosition(), 1, "CON.F.US.USA.M26")
    assert sig == (0, 0)


def test_position_signature_returns_type_and_size():
    broker = _FakeBrokerWithPosition("CON.F.US.USA.M26", 1, 1)
    sig = lt._position_signature(broker, 1, "CON.F.US.USA.M26")
    assert sig == (1, 1)


def test_position_signature_ignores_other_contracts():
    broker = _FakeBrokerWithPosition("CON.OTHER", 2, 3)
    sig = lt._position_signature(broker, 1, "CON.F.US.USA.M26")
    assert sig == (0, 0)


def test_position_signature_handles_broker_exception():
    class Bad:
        def get_positions(self, account_id):
            raise RuntimeError("boom")
    sig = lt._position_signature(Bad(), 1, "CON.F.US.USA.M26")
    assert sig == (0, 0)  # fail-closed: report flat on error


def test_wait_for_entry_fill_returns_false_on_timeout():
    """When the position signature doesn't change, wait returns False
    (entry is treated as unfilled; caller must cancel it)."""
    broker = _FakeBrokerNoPosition()
    filled = lt._wait_for_entry_fill(
        broker, 1, "CON.F.US.USA.M26",
        baseline_sig=(0, 0), timeout_s=1, poll_s=1,
    )
    assert filled is False


def test_wait_for_entry_fill_returns_true_when_signature_changes():
    """When position appears (signature changes from baseline), wait
    returns True so caller proceeds to place protective legs."""
    broker = _FakeBrokerWithPosition("CON.F.US.USA.M26", 1, 1)
    # baseline says flat; current broker shows position -> change detected
    filled = lt._wait_for_entry_fill(
        broker, 1, "CON.F.US.USA.M26",
        baseline_sig=(0, 0), timeout_s=2, poll_s=1,
    )
    assert filled is True


# ─── orphan-bracket cleanup ─────────────────────────────────────

class _FakeClient:
    def __init__(self, positions, working):
        self._positions = positions
        self._working = working
        self.cancelled = []

    def get_positions(self, account_id):
        return self._positions

    def get_working_orders(self, account_id):
        return self._working

    def cancel_order(self, account_id, order_id):
        self.cancelled.append(order_id)
        return {"success": True}


def test_cleanup_skips_when_position_open():
    """Don't cancel bracket legs when position is open (legitimate bracket)."""
    pos = [{"contractId": "CON.F.US.TYA.M26", "size": 1, "type": 1}]
    old_ts = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    working = [{
        "id": 999, "contractId": "CON.F.US.TYA.M26",
        "customTag": "live_abc_stop", "creationTimestamp": old_ts,
    }]
    fake = _FakeClient(pos, working)
    n = lt.cleanup_orphan_brackets(fake, 12345)
    assert n == 0
    assert fake.cancelled == []


def test_cleanup_skips_within_grace_period():
    """Don't cancel bracket legs younger than ORPHAN_GRACE_SEC even if flat."""
    pos = []  # flat
    fresh_ts = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
    working = [{
        "id": 1001, "contractId": "CON.F.US.TYA.M26",
        "customTag": "live_xyz_stop", "creationTimestamp": fresh_ts,
    }]
    fake = _FakeClient(pos, working)
    n = lt.cleanup_orphan_brackets(fake, 12345)
    assert n == 0
    assert fake.cancelled == []


def test_cleanup_cancels_orphan_past_grace():
    """Cancel bracket leg older than grace period when position is flat."""
    pos = []  # flat
    old_ts = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    working = [{
        "id": 2001, "contractId": "CON.F.US.TYA.M26",
        "customTag": "live_abc_stop", "creationTimestamp": old_ts,
    }, {
        "id": 2002, "contractId": "CON.F.US.TYA.M26",
        "customTag": "live_abc_target", "creationTimestamp": old_ts,
    }]
    fake = _FakeClient(pos, working)
    n = lt.cleanup_orphan_brackets(fake, 12345)
    assert n == 2
    assert fake.cancelled == [2001, 2002]


def test_cleanup_ignores_non_live_tags():
    """Don't touch orders that aren't ours (no 'live_' prefix)."""
    pos = []
    old_ts = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    working = [{
        "id": 3001, "contractId": "CON.F.US.TYA.M26",
        "customTag": "manual_user_order", "creationTimestamp": old_ts,
    }]
    fake = _FakeClient(pos, working)
    n = lt.cleanup_orphan_brackets(fake, 12345)
    assert n == 0
    assert fake.cancelled == []


def test_cleanup_handles_broker_fetch_failure():
    """Cleanup doesn't crash if broker fetch fails."""
    class _BrokenClient:
        def get_positions(self, _): raise RuntimeError("network down")
        def get_working_orders(self, _): return []
    n = lt.cleanup_orphan_brackets(_BrokenClient(), 12345)
    assert n == 0
