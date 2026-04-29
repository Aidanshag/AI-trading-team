"""Tests for the auto-halt expiry mechanism."""

from datetime import datetime, timedelta, timezone

import pytest

from hooks.risk_gate import _check_kill_switch


def _limits(halted: bool = False, halt_until: str | None = None) -> dict:
    return {
        "hard_rules": {
            "trading_halted": halted,
            "trading_halt_until": halt_until,
        }
    }


def test_no_halt_no_block():
    verdict = _check_kill_switch(
        tool_name="x", order={}, agent="X",
        limits=_limits(), topstep={}, symbols={}, snap=None, positions=[],
    )
    assert verdict is None


def test_manual_halt_blocks():
    verdict = _check_kill_switch(
        tool_name="x", order={}, agent="X",
        limits=_limits(halted=True), topstep={}, symbols={},
        snap=None, positions=[],
    )
    assert verdict is not None
    assert verdict["rule"] == "kill_switch"


def test_auto_halt_in_future_blocks():
    """Halt timestamp 1 hour in the future → block."""
    future = (datetime.now(tz=timezone.utc) + timedelta(hours=1)).isoformat()
    verdict = _check_kill_switch(
        tool_name="x", order={}, agent="X",
        limits=_limits(halt_until=future), topstep={}, symbols={},
        snap=None, positions=[],
    )
    assert verdict is not None
    assert verdict["rule"] == "auto_halt"


def test_auto_halt_in_past_does_not_block():
    """Halt timestamp 1 hour in the past → halt has expired → trade allowed."""
    past = (datetime.now(tz=timezone.utc) - timedelta(hours=1)).isoformat()
    verdict = _check_kill_switch(
        tool_name="x", order={}, agent="X",
        limits=_limits(halt_until=past), topstep={}, symbols={},
        snap=None, positions=[],
    )
    assert verdict is None


def test_malformed_halt_timestamp_fails_closed():
    """Bug fix 2026-04-29: malformed kill-switch timestamps now fail
    CLOSED rather than silently passing the order through. A typo in
    the YAML must not allow trades — it must force investigation."""
    verdict = _check_kill_switch(
        tool_name="x", order={}, agent="X",
        limits=_limits(halt_until="not a real timestamp"), topstep={}, symbols={},
        snap=None, positions=[],
    )
    assert verdict is not None
    assert verdict["rule"] == "kill_switch_malformed"
    assert "unparseable" in verdict["reason"]


def test_manual_halt_overrides_expired_auto():
    """Even if auto-halt has expired, manual halt still blocks."""
    past = (datetime.now(tz=timezone.utc) - timedelta(hours=1)).isoformat()
    verdict = _check_kill_switch(
        tool_name="x", order={}, agent="X",
        limits=_limits(halted=True, halt_until=past), topstep={}, symbols={},
        snap=None, positions=[],
    )
    assert verdict is not None
    assert verdict["rule"] == "kill_switch"
