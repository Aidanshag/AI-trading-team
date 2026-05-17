"""Tests for tools/cooldown_policy."""
from __future__ import annotations

import pytest

from tools.cooldown_policy import (
    classify_outcome,
    cooldown_minutes,
    cooldown_decision,
    BASE_COOLDOWN_MIN,
    SYMBOL_FACTORS,
    BIG_LOSS_R_THRESHOLD,
)


def test_classify_outcome_winners():
    assert classify_outcome(1.5, "target_hit") == "win"
    assert classify_outcome(0.5, "trailing_lock") == "win"
    assert classify_outcome(0.01, "any") == "win"


def test_classify_outcome_big_loss():
    assert classify_outcome(-2.0, "stop_hit") == "big_loss"
    assert classify_outcome(BIG_LOSS_R_THRESHOLD, "x") == "big_loss"
    assert classify_outcome(-3.5, "broker_stop") == "big_loss"


def test_classify_outcome_small_loss_with_trailing_lock():
    """Small loss with trailing lock isn't 'clean' — it's a give-back."""
    assert classify_outcome(-0.5, "trailing_lock") == "small_loss"
    assert classify_outcome(-1.0, "time_decay") == "small_loss"
    assert classify_outcome(-1.0, "reversal_exit") == "small_loss"


def test_classify_outcome_stop_clean():
    assert classify_outcome(-1.0, "stop_hit") == "stop_clean"
    assert classify_outcome(-0.8, "broker_stop") == "stop_clean"
    # But a BIG loss is big_loss even if from a clean stop
    assert classify_outcome(-2.0, "stop_hit") == "big_loss"


def test_classify_outcome_unknown_for_none():
    assert classify_outcome(None, None) == "unknown"
    assert classify_outcome(None, "stop_hit") == "unknown"


def test_cooldown_minutes_for_full_size_symbol():
    """Non-micro symbols use base cooldown directly."""
    assert cooldown_minutes("GC", "win") == BASE_COOLDOWN_MIN["win"]
    assert cooldown_minutes("GC", "big_loss") == BASE_COOLDOWN_MIN["big_loss"]
    assert cooldown_minutes("GC", "stop_clean") == BASE_COOLDOWN_MIN["stop_clean"]
    assert cooldown_minutes("GC", None) == BASE_COOLDOWN_MIN["unknown"]


def test_cooldown_minutes_for_micros_uses_factor():
    """Micros use the 0.33× factor."""
    assert cooldown_minutes("MGC", "win") == round(BASE_COOLDOWN_MIN["win"] * 0.33)
    assert cooldown_minutes("MGC", "big_loss") == round(
        BASE_COOLDOWN_MIN["big_loss"] * 0.33)
    # MNQ in SYMBOL_FACTORS
    assert cooldown_minutes("MNQ", "small_loss") == round(
        BASE_COOLDOWN_MIN["small_loss"] * 0.33)


def test_cooldown_minutes_explicit_override():
    """`symbol_factor_override` wins over the table."""
    assert cooldown_minutes("MGC", "win", symbol_factor_override=1.0) == \
        BASE_COOLDOWN_MIN["win"]


def test_cooldown_minutes_floor_is_1():
    """Even with a tiny factor + short base, always >= 1 minute."""
    assert cooldown_minutes("MGC", "win", symbol_factor_override=0.01) >= 1


def test_cooldown_decision_unblocks_after_win_sooner():
    """After a winner on GC: live (45min flat) still blocks at 20min,
    policy v1 (15min for win) does not."""
    d = cooldown_decision("GC", live_cooldown_min=45,
                          last_outcome="win", minutes_since_last=20.0)
    assert d["live_block"] is True
    assert d["policy_v1_block"] is False
    assert d["delta_min"] == 15 - 45  # -30 = unblocked sooner


def test_cooldown_decision_blocks_longer_after_big_loss():
    """After big_loss: live (45min) unblocks at 50min, policy v1 (90min) still blocks."""
    d = cooldown_decision("GC", live_cooldown_min=45,
                          last_outcome="big_loss", minutes_since_last=50.0)
    assert d["live_block"] is False
    assert d["policy_v1_block"] is True
    assert d["delta_min"] == 90 - 45  # +45 = blocked longer
