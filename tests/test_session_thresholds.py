"""Tests for tools/session_thresholds."""
from __future__ import annotations

import pytest

from tools.session_thresholds import (
    volume_spike_mult_for_session,
    atr_mult_for_session,
    VOLUME_SPIKE_MULT_BY_SESSION,
    ATR_FLOOR_BY_SESSION,
    DEFAULT_VOLUME_SPIKE_MULT,
    DEFAULT_ATR_MULT,
)


def test_asian_volume_spike_higher_than_rth():
    """Asian sessions need a higher multiplier — that's the whole point."""
    assert volume_spike_mult_for_session("Asian") > volume_spike_mult_for_session("RTH")


def test_known_sessions_return_calibrated_values():
    assert volume_spike_mult_for_session("Asian") == 4.0
    assert volume_spike_mult_for_session("London") == 3.0
    assert volume_spike_mult_for_session("RTH") == 3.0
    assert volume_spike_mult_for_session("PostClose") == 3.5


def test_unknown_session_returns_default():
    assert volume_spike_mult_for_session("Tokyo") == DEFAULT_VOLUME_SPIKE_MULT
    assert volume_spike_mult_for_session(None) == DEFAULT_VOLUME_SPIKE_MULT
    assert volume_spike_mult_for_session("") == DEFAULT_VOLUME_SPIKE_MULT


def test_atr_mult_asian_widest():
    """Asian bars need wider ATR multiplier for stops to escape noise."""
    assert atr_mult_for_session("Asian") > atr_mult_for_session("RTH")


def test_atr_mult_known_sessions():
    assert atr_mult_for_session("Asian") == 1.5
    assert atr_mult_for_session("London") == 1.0
    assert atr_mult_for_session("RTH") == 1.0
    assert atr_mult_for_session("PostClose") == 1.2


def test_atr_mult_default():
    assert atr_mult_for_session("Tokyo") == DEFAULT_ATR_MULT
    assert atr_mult_for_session(None) == DEFAULT_ATR_MULT
