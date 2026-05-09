"""Tests for the combine defensive ladder enforcement."""

import pytest

from hooks.risk_gate import _check_combine_defensive_ladder


def _ladder_limits():
    return {
        "combine_defense": {
            "ladder": [
                {"threshold_usd": -150, "action": "warn", "description": "alert CIO"},
                {"threshold_usd": -300, "action": "restrict", "description": "tighten"},
                {"threshold_usd": -500, "action": "lockdown", "description": "flatten"},
                {"threshold_usd": -750, "action": "emergency_flatten", "description": "halt"},
            ]
        }
    }


def _snap(realized: float = 0.0, unrealized: float = 0.0):
    return {
        "id": 1, "ts": "2026-04-25T15:00:00Z", "environment": "combine",
        "balance_usd": 50000.0,
        "realized_pl_day_usd": realized,
        "unrealized_pl_usd": unrealized,
        "trailing_dd_usd": 0.0, "open_contracts_total": 0,
    }


def test_no_ladder_no_block():
    """No ladder defined or no snapshot — pass."""
    v = _check_combine_defensive_ladder(
        tool_name="x", order={}, agent="X",
        limits={}, topstep={}, symbols={}, snap=_snap(), positions=[],
    )
    assert v is None


def test_above_warn_threshold_no_block():
    """Day P&L flat or positive — no ladder triggered."""
    v = _check_combine_defensive_ladder(
        tool_name="x", order={}, agent="X",
        limits=_ladder_limits(), topstep={}, symbols={},
        snap=_snap(realized=100), positions=[],
    )
    assert v is None


def test_warn_level_does_not_hard_block():
    """At -$150, warn is triggered but order is not blocked at hook level."""
    v = _check_combine_defensive_ladder(
        tool_name="x", order={}, agent="X",
        limits=_ladder_limits(), topstep={}, symbols={},
        snap=_snap(realized=-160), positions=[],
    )
    assert v is None  # warn doesn't hard-block; PM/Risk Manager handle sizing


def test_restrict_level_does_not_hard_block():
    """At -$300, restrict is triggered but order is not hard-blocked."""
    v = _check_combine_defensive_ladder(
        tool_name="x", order={}, agent="X",
        limits=_ladder_limits(), topstep={}, symbols={},
        snap=_snap(realized=-310), positions=[],
    )
    assert v is None  # restrict tightens cap, doesn't ban


def test_lockdown_blocks():
    """At -$500, lockdown engages. New entries blocked."""
    v = _check_combine_defensive_ladder(
        tool_name="x", order={}, agent="X",
        limits=_ladder_limits(), topstep={}, symbols={},
        snap=_snap(realized=-510), positions=[],
    )
    assert v is not None
    assert v["rule"] == "defensive_ladder"
    assert "lockdown" in v["reason"]


def test_emergency_blocks():
    """At -$750, emergency flatten engages. New entries blocked."""
    v = _check_combine_defensive_ladder(
        tool_name="x", order={}, agent="X",
        limits=_ladder_limits(), topstep={}, symbols={},
        snap=_snap(realized=-760), positions=[],
    )
    assert v is not None
    assert "emergency_flatten" in v["reason"]


def test_unrealized_loss_counts():
    """Unrealized P&L counts toward day P&L for ladder."""
    v = _check_combine_defensive_ladder(
        tool_name="x", order={}, agent="X",
        limits=_ladder_limits(), topstep={}, symbols={},
        snap=_snap(realized=-100, unrealized=-450), positions=[],   # total -550
    )
    assert v is not None
    assert "lockdown" in v["reason"]
