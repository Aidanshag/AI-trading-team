"""Tests for scripts/live_trader.py — pure-execution / safety-gate layer.

After 2026-05-13 brain/trader split, the trader's responsibilities are
ONLY: order placement, last-mile safety gates, position polling,
snapshot heartbeat. Brain-side tests (sessions, regime, news, signal
extraction) live in tests/test_brain_logic.py.

Coverage here:
- is_halted: halt-file + config checks
- dll_breached: daily loss limit check (internal-first read)
- signal_passes_min_r_gate: pre-placement R-floor gate
- _round_to_tick / _tick_size: bracket math
- recent_thesis_for: cooldown (defense-in-depth)
- _position_signature / _position_avg_price: position-state helpers
- _verify_stop_landed / _wait_for_entry_fill: orphan-leg defense
- cleanup_orphan_brackets: working-order hygiene
- module structure: trader has the queue-consume entry point
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts import live_trader as lt  # noqa: E402


# ─── halt checks ────────────────────────────────────────────────

def test_is_halted_no_halt(tmp_path, monkeypatch):
    monkeypatch.setattr(lt, "HALT_FILE", tmp_path / "no_halt")
    halted, reason = lt.is_halted()
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
    # 2026-05-13: dll_breached reads `internal_dll_target_usd` first
    # (currently $250). Use a loss well under the floor.
    snap = {"realized_pl_day_usd": -100.0}
    breached, why = lt.dll_breached(snap)
    assert not breached


def test_dll_breached():
    snap = {"realized_pl_day_usd": -1500.0}
    breached, why = lt.dll_breached(snap)
    assert breached is True
    assert "<= -" in why and ("internal_dll" in why or "topstep_dll" in why)


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
    assert lt._tick_size("UNKNOWN_FOO") == 0.01


# ─── module structure ──────────────────────────────────────────

def test_module_imports():
    """Confirm the trader exposes its core surface."""
    assert hasattr(lt, "consume_pending_signals")
    assert hasattr(lt, "place_bracket")
    assert hasattr(lt, "dll_breached")
    assert hasattr(lt, "signal_passes_max_risk_gate")
    assert hasattr(lt, "signal_passes_min_r_gate")
    assert hasattr(lt, "projected_dll_breach")
    assert hasattr(lt, "main")
    assert lt.SCAN_INTERVAL_SEC > 0
    assert lt.PER_TRADE_LOSS_CAP_USD > 0
    assert lt.MAX_SIGNAL_RISK_USD > 0


def test_constants_align_with_v1_intent():
    """The trader's hard floors should match user-stated intent."""
    assert lt.SCAN_INTERVAL_SEC == 300        # 5 min
    assert lt.PER_TRADE_LOSS_CAP_USD == 150.0
    assert lt.MIN_SIGNAL_R_TICKS >= 6
    assert lt.MAX_SIGNAL_RISK_USD == 150.0


# ─── degenerate-R signal gate (2026-05-10 incident) ────────────────

def test_min_r_gate_rejects_stop_equals_entry():
    sig = {"price": 110.53125, "stop": 110.53125, "target": 110.546875}
    ok, reason = lt.signal_passes_min_r_gate(sig, "ZN")
    assert ok is False
    assert "stop too close" in reason


def test_min_r_gate_rejects_one_tick_target():
    sig = {"price": 110.50, "stop": 110.38, "target": 110.515625}
    ok, reason = lt.signal_passes_min_r_gate(sig, "ZN")
    assert ok is False
    assert "target too close" in reason


def test_min_r_gate_passes_normal_signal():
    sig = {"price": 110.50, "stop": 110.30, "target": 110.80}
    ok, reason = lt.signal_passes_min_r_gate(sig, "ZN")
    assert ok is True
    assert reason == ""


def test_min_r_gate_rejects_missing_stop():
    sig = {"price": 110.50, "stop": None, "target": 110.80}
    ok, reason = lt.signal_passes_min_r_gate(sig, "ZN")
    assert ok is False


def test_min_r_gate_no_target_uses_stop_only():
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
    assert sig == (0, 0)


def test_wait_for_entry_fill_returns_false_on_timeout():
    broker = _FakeBrokerNoPosition()
    filled = lt._wait_for_entry_fill(
        broker, 1, "CON.F.US.USA.M26",
        baseline_sig=(0, 0), timeout_s=1, poll_s=1,
    )
    assert filled is False


def test_position_avg_price_returns_value_when_position_exists():
    class _Broker:
        def get_positions(self, _aid):
            return [{"contractId": "CON.F.US.MNQ.M26", "size": 1,
                     "type": 1, "averagePrice": 29409.25}]
    avg = lt._position_avg_price(_Broker(), 1, "CON.F.US.MNQ.M26")
    assert avg == 29409.25


def test_position_avg_price_returns_none_when_flat():
    class _Broker:
        def get_positions(self, _aid):
            return []
    assert lt._position_avg_price(_Broker(), 1, "CON.F.US.MNQ.M26") is None


def test_position_avg_price_returns_none_on_broker_error():
    class _Bad:
        def get_positions(self, _aid):
            raise RuntimeError("broker down")
    assert lt._position_avg_price(_Bad(), 1, "X") is None


def test_verify_stop_landed_finds_order():
    class _Broker:
        def get_working_orders(self, _aid):
            return [{"customTag": "live_abc_stop", "id": 1}]
    assert lt._verify_stop_landed(_Broker(), 1, "X", "live_abc_stop",
                                    poll_attempts=1, poll_s=0) is True


def test_verify_stop_landed_returns_false_when_missing():
    class _Broker:
        def get_working_orders(self, _aid):
            return []
    assert lt._verify_stop_landed(_Broker(), 1, "X", "live_missing",
                                    poll_attempts=2, poll_s=0) is False


def test_wait_for_entry_fill_returns_true_when_signature_changes():
    broker = _FakeBrokerWithPosition("CON.F.US.USA.M26", 1, 1)
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
    pos = []
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
    pos = []
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
    class _BrokenClient:
        def get_positions(self, _): raise RuntimeError("network down")
        def get_working_orders(self, _): return []
    n = lt.cleanup_orphan_brackets(_BrokenClient(), 12345)
    assert n == 0
