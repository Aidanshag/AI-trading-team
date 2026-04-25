"""Tests for the PreToolUse risk hook (hooks/risk_gate.py).

The hook is the safety floor — every rule that lives in
config/risk_limits.yaml must be exercised here. If a rule isn't tested,
it isn't real.

Run from project root:  pytest tests/ -v
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from hooks.risk_gate import (
    ORDER_TOOLS,
    _check_daily_loss_limit,
    _check_kill_switch,
    _check_no_naked_shorts,
    _check_per_symbol_limits,
    _check_session_window,
    _check_stop_required,
    _is_outright_short_future,
    _has_stop,
    risk_gate,
)


# ── Fixtures ────────────────────────────────────────────────────
@pytest.fixture
def base_limits():
    return {
        "hard_rules": {
            "no_naked_shorts": True,
            "require_stop_on_every_trade": True,
            "trading_halted": False,
        },
        "account": {
            "starting_balance": 50000,
            "daily_loss_limit_pct": 0.02,
            "daily_loss_limit_usd": 1000,
            "trailing_drawdown_usd": 2000,
            "max_open_contracts_total": 5,
            "consistency_cap_pct": 0.50,
            "per_trade_risk_pct_of_equity": 0.005,
            "warn_daily_loss_pct": 0.30,
            "warn_trailing_dd_pct": 0.40,
            "internal_dll_target_usd": 500,
        },
        "per_symbol": {
            "default": {"max_contracts": 1, "max_notional_usd": 75000, "required_stop_ticks": 20},
            "MCL": {"max_contracts": 2, "max_notional_usd": 8000, "required_stop_ticks": 20},
        },
        "sessions": {"no_new_positions_after_local_time": "15:45"},
    }


@pytest.fixture
def base_account_snapshot():
    return {
        "id": 1,
        "ts": "2026-04-25T15:00:00+00:00",
        "environment": "combine",
        "balance_usd": 50000.0,
        "unrealized_pl_usd": 0.0,
        "realized_pl_day_usd": 0.0,
        "trailing_dd_usd": 0.0,
        "open_contracts_total": 0,
    }


@pytest.fixture
def mcl_long_order():
    return {
        "symbol": "MCL",
        "side": "buy",
        "qty": 1,
        "order_type": "limit",
        "limit_price": 78.50,
        "stop_price": 78.00,
    }


@pytest.fixture
def mcl_naked_short_order():
    return {
        "symbol": "MCL",
        "side": "sell",
        "qty": 1,
        "order_type": "market",
        "stop_price": None,        # no stop
        "structure_id": None,      # not part of a structure
    }


# ── Unit tests on the helpers ──────────────────────────────────
def test_is_outright_short_future_true(mcl_naked_short_order):
    assert _is_outright_short_future(mcl_naked_short_order) is True


def test_is_outright_short_future_false_with_structure(mcl_naked_short_order):
    o = dict(mcl_naked_short_order, structure_id=42)
    assert _is_outright_short_future(o) is False


def test_is_outright_short_future_false_for_long(mcl_long_order):
    assert _is_outright_short_future(mcl_long_order) is False


def test_has_stop_true(mcl_long_order):
    assert _has_stop(mcl_long_order) is True


def test_has_stop_false_when_none(mcl_naked_short_order):
    assert _has_stop(mcl_naked_short_order) is False


# ── Individual rule checks ─────────────────────────────────────
def test_kill_switch_blocks_when_halted(base_limits, mcl_long_order):
    base_limits["hard_rules"]["trading_halted"] = True
    verdict = _check_kill_switch(
        tool_name="x", order=mcl_long_order, agent="X",
        limits=base_limits, topstep={}, symbols={},
        snap=None, positions=[],
    )
    assert verdict is not None
    assert verdict["rule"] == "kill_switch"


def test_kill_switch_allows_when_not_halted(base_limits, mcl_long_order):
    verdict = _check_kill_switch(
        tool_name="x", order=mcl_long_order, agent="X",
        limits=base_limits, topstep={}, symbols={},
        snap=None, positions=[],
    )
    assert verdict is None


def test_naked_short_screen_blocks_outright_short(base_limits, mcl_naked_short_order):
    verdict = _check_no_naked_shorts(
        tool_name="x", order=mcl_naked_short_order, agent="X",
        limits=base_limits, topstep={}, symbols={},
        snap=None, positions=[],
    )
    assert verdict is not None
    assert verdict["rule"] == "naked_short_future"


def test_naked_short_screen_allows_long(base_limits, mcl_long_order):
    verdict = _check_no_naked_shorts(
        tool_name="x", order=mcl_long_order, agent="X",
        limits=base_limits, topstep={}, symbols={},
        snap=None, positions=[],
    )
    assert verdict is None


def test_naked_short_screen_allows_short_with_structure(base_limits, mcl_naked_short_order):
    o = dict(mcl_naked_short_order, structure_id=42)
    verdict = _check_no_naked_shorts(
        tool_name="x", order=o, agent="X",
        limits=base_limits, topstep={}, symbols={},
        snap=None, positions=[],
    )
    assert verdict is None


def test_stop_required_blocks_when_missing(base_limits):
    o = {"symbol": "MCL", "side": "buy", "qty": 1, "stop_price": None, "structure_id": None}
    verdict = _check_stop_required(
        tool_name="x", order=o, agent="X",
        limits=base_limits, topstep={}, symbols={},
        snap=None, positions=[],
    )
    assert verdict is not None
    assert verdict["rule"] == "missing_stop"


def test_stop_required_allows_when_present(base_limits, mcl_long_order):
    verdict = _check_stop_required(
        tool_name="x", order=mcl_long_order, agent="X",
        limits=base_limits, topstep={}, symbols={},
        snap=None, positions=[],
    )
    assert verdict is None


def test_stop_required_skipped_for_structures(base_limits):
    o = {"symbol": "MCL", "side": "buy", "qty": 1, "stop_price": None, "structure_id": 42}
    verdict = _check_stop_required(
        tool_name="x", order=o, agent="X",
        limits=base_limits, topstep={}, symbols={},
        snap=None, positions=[],
    )
    assert verdict is None  # defined-risk structure, no stop needed


def test_dll_blocks_when_breach(base_limits, base_account_snapshot, mcl_long_order):
    """Day P&L below DLL → block."""
    snap = dict(base_account_snapshot)
    snap["realized_pl_day_usd"] = -1100  # breached the $1000 DLL
    verdict = _check_daily_loss_limit(
        tool_name="x", order=mcl_long_order, agent="X",
        limits=base_limits, topstep={}, symbols={},
        snap=snap, positions=[],
    )
    assert verdict is not None
    assert verdict["rule"] == "daily_loss_limit"


def test_dll_allows_when_within_limit(base_limits, base_account_snapshot, mcl_long_order):
    snap = dict(base_account_snapshot)
    snap["realized_pl_day_usd"] = -200  # well within DLL
    verdict = _check_daily_loss_limit(
        tool_name="x", order=mcl_long_order, agent="X",
        limits=base_limits, topstep={}, symbols={},
        snap=snap, positions=[],
    )
    assert verdict is None


def test_per_symbol_limits_block_oversize(base_limits, mcl_long_order):
    """Trying to add 3 contracts when cap is 2 should block."""
    o = dict(mcl_long_order, qty=3)
    verdict = _check_per_symbol_limits(
        tool_name="x", order=o, agent="X",
        limits=base_limits, topstep={}, symbols={},
        snap=None, positions=[],
    )
    assert verdict is not None
    assert verdict["rule"] == "per_symbol_max_contracts"


def test_per_symbol_limits_allow_at_cap(base_limits, mcl_long_order):
    """Exactly at cap is allowed."""
    o = dict(mcl_long_order, qty=2)
    verdict = _check_per_symbol_limits(
        tool_name="x", order=o, agent="X",
        limits=base_limits, topstep={}, symbols={},
        snap=None, positions=[],
    )
    assert verdict is None


def test_per_symbol_limits_block_over_when_existing_position(base_limits, mcl_long_order):
    """1 existing + 2 new = 3, cap is 2 → block."""
    existing = [{"symbol": "MCL", "side": "long", "contracts": 1}]
    o = dict(mcl_long_order, qty=2)
    verdict = _check_per_symbol_limits(
        tool_name="x", order=o, agent="X",
        limits=base_limits, topstep={}, symbols={},
        snap=None, positions=existing,
    )
    assert verdict is not None


# ── Integration: the full hook entry point ─────────────────────
@pytest.mark.asyncio
async def test_hook_passes_through_for_non_order_tools():
    """Tools that aren't order-placement should pass without check."""
    input_data = {
        "tool_name": "mcp__market_data__get_quote",
        "tool_input": {"symbol": "ES"},
    }
    with patch("hooks.risk_gate.get_db") as mock_db:
        result = await risk_gate(input_data, None, None)
    assert result == {}  # empty = pass


@pytest.mark.asyncio
async def test_hook_recognizes_order_tools():
    """Order tools must be in the gated set."""
    assert "mcp__topstep__topstep_place_order" in ORDER_TOOLS
    assert "mcp__topstep__topstep_flatten_all" in ORDER_TOOLS


# ── Smoke: defensive ladder thresholds ──────────────────────────
def test_defensive_ladder_thresholds_match_yaml():
    """Confirm the 4-step ladder in config matches our agreed values."""
    import yaml
    from pathlib import Path
    cfg = yaml.safe_load(Path("config/risk_limits.yaml").read_text())
    ladder = cfg.get("combine_defense", {}).get("ladder", [])
    levels = [step["threshold_usd"] for step in ladder]
    assert -150 in levels, "warn at -$150 missing"
    assert -300 in levels, "restrict at -$300 missing"
    assert -500 in levels, "lockdown at -$500 missing"
    assert -750 in levels, "emergency_flatten at -$750 missing"


def test_internal_dll_is_half_of_topstep():
    """Internal DLL target should be 50% of Topstep DLL — non-negotiable per user."""
    import yaml
    from pathlib import Path
    cfg = yaml.safe_load(Path("config/risk_limits.yaml").read_text())
    acct = cfg["account"]
    assert acct["internal_dll_target_usd"] * 2 == acct["daily_loss_limit_usd"]
