"""Tests for tools/hard_flatten_clock — 3:10 PM CT Topstep enforcement."""
from __future__ import annotations

from datetime import datetime

import pytest

from tools import hard_flatten_clock as hfc


def _ct(year, month, day, hh, mm) -> datetime:
    """Build a CT-aware datetime at (year, month, day, hh, mm)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime(year, month, day, hh, mm, tzinfo=ZoneInfo("America/Chicago"))
    except Exception:
        from datetime import timezone, timedelta
        return datetime(year, month, day, hh, mm, tzinfo=timezone(timedelta(hours=-5)))


# ── current_window() ────────────────────────────────────────────

def test_window_normal_before_2_55_pm_ct():
    """Before 14:55 CT on a weekday → normal trading."""
    assert hfc.current_window(_ct(2026, 5, 12, 9, 0)) == "normal"
    assert hfc.current_window(_ct(2026, 5, 12, 14, 54)) == "normal"


def test_window_no_new_entries_at_2_55_pm_ct():
    """14:55–15:04 CT → block entries, allow positions to run."""
    assert hfc.current_window(_ct(2026, 5, 12, 14, 55)) == "no_new_entries"
    assert hfc.current_window(_ct(2026, 5, 12, 15, 4)) == "no_new_entries"


def test_window_flatten_at_3_05_pm_ct():
    """15:05–15:09 CT → proactive flatten window."""
    assert hfc.current_window(_ct(2026, 5, 12, 15, 5)) == "flatten"
    assert hfc.current_window(_ct(2026, 5, 12, 15, 9)) == "flatten"


def test_window_past_deadline_at_3_10_pm_ct():
    """15:10–15:29 CT → past deadline (anything still open is rule violation tail)."""
    assert hfc.current_window(_ct(2026, 5, 12, 15, 10)) == "past_deadline"
    assert hfc.current_window(_ct(2026, 5, 12, 15, 29)) == "past_deadline"


def test_window_normal_again_after_3_30_pm_ct():
    """After 15:30 CT: Topstep's overnight 23-hour session resumes."""
    assert hfc.current_window(_ct(2026, 5, 12, 15, 30)) == "normal"
    assert hfc.current_window(_ct(2026, 5, 12, 18, 0)) == "normal"
    assert hfc.current_window(_ct(2026, 5, 12, 21, 0)) == "normal"
    assert hfc.current_window(_ct(2026, 5, 12, 23, 59)) == "normal"


def test_window_weekend_no_enforcement():
    """Saturday/Sunday should not flatten (no RTH session)."""
    sat = _ct(2026, 5, 16, 15, 30)  # Saturday
    sun = _ct(2026, 5, 17, 15, 30)  # Sunday
    assert hfc.current_window(sat) == "normal"
    assert hfc.current_window(sun) == "normal"


# ── should_block_new_entries() ─────────────────────────────────

def test_block_entries_logic():
    """should_block_new_entries returns True only during the closing window
    (2:55–3:29 CT). After 3:30 CT overnight trading resumes."""
    assert hfc.should_block_new_entries(_ct(2026, 5, 12, 12, 0)) is False
    assert hfc.should_block_new_entries(_ct(2026, 5, 12, 14, 55)) is True
    assert hfc.should_block_new_entries(_ct(2026, 5, 12, 15, 5)) is True
    assert hfc.should_block_new_entries(_ct(2026, 5, 12, 15, 29)) is True
    # After 3:30 CT — overnight session, no longer blocking
    assert hfc.should_block_new_entries(_ct(2026, 5, 12, 15, 30)) is False
    assert hfc.should_block_new_entries(_ct(2026, 5, 12, 21, 0)) is False


def test_should_flatten_logic():
    """should_flatten_now returns True from 15:05 through 15:29 CT."""
    assert hfc.should_flatten_now(_ct(2026, 5, 12, 14, 59)) is False
    assert hfc.should_flatten_now(_ct(2026, 5, 12, 15, 5)) is True
    assert hfc.should_flatten_now(_ct(2026, 5, 12, 15, 29)) is True
    # After 3:30 CT — back to normal, no forced flatten
    assert hfc.should_flatten_now(_ct(2026, 5, 12, 15, 30)) is False


# ── enforce_hard_flatten() ─────────────────────────────────────

class _FakeClient:
    def __init__(self, positions=None, working_orders=None):
        self._positions = positions or []
        self._working = working_orders or []
        self.placed: list[dict] = []
        self.cancelled: list = []
    def get_positions(self, _aid):
        return self._positions
    def get_working_orders(self, _aid):
        return self._working
    def place_order(self, **kwargs):
        self.placed.append(kwargs)
        return {"orderId": 999}
    def cancel_order(self, _aid, oid):
        self.cancelled.append(oid)
        return {"success": True}


def test_enforce_noop_before_flatten_window():
    """Outside the flatten window, no positions are closed."""
    client = _FakeClient(positions=[{"contractId": "CON.F.US.GCE.M26",
                                       "size": 1, "type": 1}])
    result = hfc.enforce_hard_flatten(client, 1, now=_ct(2026, 5, 12, 12, 0))
    assert result["flattened"] == []
    assert client.placed == []


def test_enforce_flattens_in_window():
    """At 15:05 CT with an open position, market-close fires."""
    client = _FakeClient(
        positions=[{"contractId": "CON.F.US.GCE.M26", "size": 1, "type": 1}],
        working_orders=[{"id": 12345}],
    )
    result = hfc.enforce_hard_flatten(client, 1, now=_ct(2026, 5, 12, 15, 5))
    assert len(result["flattened"]) == 1
    assert result["cancelled"] == 1
    assert len(client.placed) == 1
    assert client.placed[0]["side"] == "sell"  # closing long
    assert client.placed[0]["order_type"] == "market"


def test_enforce_short_position_buys_to_close():
    """Short position (type=2) closes via buy."""
    client = _FakeClient(
        positions=[{"contractId": "CON.F.US.GCE.M26", "size": 1, "type": 2}],
    )
    result = hfc.enforce_hard_flatten(client, 1, now=_ct(2026, 5, 12, 15, 6))
    assert len(result["flattened"]) == 1
    assert client.placed[0]["side"] == "buy"


def test_enforce_past_deadline_still_flattens():
    """If we're past 15:10 but before 15:30, still flatten anything open."""
    client = _FakeClient(
        positions=[{"contractId": "CON.F.US.GCE.M26", "size": 1, "type": 1}],
    )
    result = hfc.enforce_hard_flatten(client, 1, now=_ct(2026, 5, 12, 15, 20))
    assert result["window"] == "past_deadline"
    assert len(result["flattened"]) == 1


def test_enforce_overnight_session_no_flatten():
    """After 3:30 PM CT, overnight session resumes — no flatten."""
    client = _FakeClient(
        positions=[{"contractId": "CON.F.US.GCE.M26", "size": 1, "type": 1}],
    )
    result = hfc.enforce_hard_flatten(client, 1, now=_ct(2026, 5, 12, 21, 0))
    assert result["window"] == "normal"
    assert result["flattened"] == []


def test_enforce_handles_broker_error():
    """If get_positions raises, fail safely without crashing."""
    class Bad:
        def get_working_orders(self, _aid):
            return []
        def get_positions(self, _aid):
            raise RuntimeError("broker offline")
    result = hfc.enforce_hard_flatten(Bad(), 1, now=_ct(2026, 5, 12, 15, 5))
    assert result["flattened"] == []
