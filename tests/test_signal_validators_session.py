"""Session-aware MIN_SIGNAL_R_TICKS tests for tools/signal_validators."""
from __future__ import annotations

from tools.signal_validators import (
    signal_passes_min_r_gate,
    min_r_ticks_for_session,
    MIN_SIGNAL_R_TICKS_BY_SESSION,
    DEFAULT_MIN_SIGNAL_R_TICKS,
)


def test_min_r_ticks_for_known_sessions():
    assert min_r_ticks_for_session("Asian") == 4
    assert min_r_ticks_for_session("London") == 6
    assert min_r_ticks_for_session("RTH") == 6
    assert min_r_ticks_for_session("PostClose") == 5


def test_min_r_ticks_default_for_unknown_or_missing():
    assert min_r_ticks_for_session("Tokyo") == DEFAULT_MIN_SIGNAL_R_TICKS
    assert min_r_ticks_for_session(None) == DEFAULT_MIN_SIGNAL_R_TICKS
    assert min_r_ticks_for_session("") == DEFAULT_MIN_SIGNAL_R_TICKS


def test_asian_session_accepts_5tick_stop_that_rth_rejects():
    """MGC stop 5 ticks below entry: passes Asian (4-tick floor),
    fails RTH (6-tick floor). Captures the Pattern B fix."""
    sig = {"price": 4500.0, "stop": 4499.5, "target": 4501.5}  # 5t stop, 15t target
    ok_asian, _ = signal_passes_min_r_gate(sig, "MGC", session="Asian")
    ok_rth, reason_rth = signal_passes_min_r_gate(sig, "MGC", session="RTH")
    assert ok_asian, "Asian (4t floor) should accept a 5-tick stop"
    assert not ok_rth, "RTH (6t floor) should reject a 5-tick stop"
    assert "too close" in reason_rth.lower()


def test_explicit_min_r_ticks_overrides_session():
    """When caller passes min_r_ticks=N explicitly, ignore session."""
    sig = {"price": 4500.0, "stop": 4499.5, "target": 4501.5}  # 5t stop
    ok, _ = signal_passes_min_r_gate(sig, "MGC", min_r_ticks=3,
                                       session="RTH")
    assert ok, "Explicit min_r_ticks=3 should override RTH default of 6"


def test_default_when_no_session_passed():
    """Backward-compat: callers not passing session get DEFAULT (6t)."""
    sig = {"price": 4500.0, "stop": 4499.5, "target": 4500.5}  # 5t stop, 5t target
    ok, _ = signal_passes_min_r_gate(sig, "MGC")
    assert not ok, "Default 6t floor should reject 5t stop"


def test_short_side_distance_is_symmetric():
    """Short signal: stop above entry, same min_r logic.
    Uses integer ticks (MGC tick=0.10, integer multiples for clean FP)."""
    # Stop 5 ticks above entry, target 8 ticks below (short)
    sig = {"price": 4500.0, "stop": 4500.5, "target": 4499.2}
    ok_asian, _ = signal_passes_min_r_gate(sig, "MGC", session="Asian")
    assert ok_asian, "Asian 4t floor accepts a 5-tick short stop"
    ok_rth, _ = signal_passes_min_r_gate(sig, "MGC", session="RTH")
    assert not ok_rth, "RTH 6t floor rejects a 5-tick short stop"
