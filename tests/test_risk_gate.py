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
    _check_autonomous_rth_window,
    _check_broker_can_trade,
    _check_combine_defensive_ladder,
    _check_consistency_rule,
    _check_daily_loss_limit,
    _check_kill_switch,
    _check_no_naked_shorts,
    _check_per_symbol_limits,
    _check_session_window,
    _check_snapshot_freshness,
    _check_stop_required,
    _check_thin_tape_regime,
    _check_trailing_drawdown,
    _is_outright_short_future,
    _has_stop,
    _proposed_worst_case_usd,
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
    """Confirm the core 3-step ladder in config matches our agreed values.
    The -$750 emergency_flatten level may be temporarily disabled (see the
    'TEMPORARY USER OVERRIDE' comment in risk_limits.yaml); not asserted."""
    import yaml
    from pathlib import Path
    cfg = yaml.safe_load(Path("config/risk_limits.yaml").read_text())
    ladder = cfg.get("combine_defense", {}).get("ladder", [])
    levels = [step["threshold_usd"] for step in ladder]
    assert -150 in levels, "warn at -$150 missing"
    assert -300 in levels, "restrict at -$300 missing"
    assert -500 in levels, "lockdown at -$500 missing"


# ── Pre-trade projection helpers ────────────────────────────────
@pytest.fixture
def base_symbols():
    return {
        "MCL": {"sector": "energies", "tick_size": 0.01, "tick_value": 1.00},
        "ES":  {"sector": "index_macro", "tick_size": 0.25, "tick_value": 12.50},
    }


def test_proposed_worst_case_from_stop_and_limit(base_limits, base_symbols):
    """MCL: limit 78.50, stop 78.00 → 50 ticks × $1.00 × 1 contract = $50."""
    order = {"symbol": "MCL", "side": "buy", "qty": 1,
             "limit_price": 78.50, "stop_price": 78.00}
    worst = _proposed_worst_case_usd(order, base_symbols, base_limits, snap=None)
    assert abs(worst - 50.0) < 0.01


def test_proposed_worst_case_falls_back_to_pct(base_limits, base_account_snapshot, base_symbols):
    """No stop/limit → fall back to per_trade_risk_pct × balance ($250 on $50K)."""
    order = {"symbol": "MCL", "side": "buy", "qty": 1}
    worst = _proposed_worst_case_usd(order, base_symbols, base_limits,
                                      snap=base_account_snapshot)
    assert abs(worst - 250.0) < 0.01


def test_dll_blocks_projected_breach(base_limits, base_account_snapshot, base_symbols):
    """Day P&L is -$760 (within DLL); proposed $250 trade would push to -$1010 → BLOCK."""
    snap = dict(base_account_snapshot, realized_pl_day_usd=-760, unrealized_pl_usd=0)
    order = {"symbol": "MCL", "side": "buy", "qty": 1,
             "limit_price": 78.50, "stop_price": 76.00}  # 250 ticks × $1 = $250
    verdict = _check_daily_loss_limit(
        tool_name="x", order=order, agent="X",
        limits=base_limits, topstep={}, symbols=base_symbols,
        snap=snap, positions=[],
    )
    assert verdict is not None
    assert verdict["rule"] == "daily_loss_limit_projected"


def test_dll_allows_when_projection_inside_limit(base_limits, base_account_snapshot, base_symbols):
    """Day P&L -$200, $250 worst → projected -$450, well inside $1000 DLL."""
    snap = dict(base_account_snapshot, realized_pl_day_usd=-200, unrealized_pl_usd=0)
    order = {"symbol": "MCL", "side": "buy", "qty": 1,
             "limit_price": 78.50, "stop_price": 76.00}
    verdict = _check_daily_loss_limit(
        tool_name="x", order=order, agent="X",
        limits=base_limits, topstep={}, symbols=base_symbols,
        snap=snap, positions=[],
    )
    assert verdict is None


def test_tdd_blocks_projected_breach(base_limits, base_account_snapshot, base_symbols):
    """Current TDD $1800 + $250 worst would push to $2050 ≥ $2000 limit → BLOCK."""
    snap = dict(base_account_snapshot, trailing_dd_usd=1800)
    order = {"symbol": "MCL", "side": "buy", "qty": 1,
             "limit_price": 78.50, "stop_price": 76.00}
    verdict = _check_trailing_drawdown(
        tool_name="x", order=order, agent="X",
        limits=base_limits, topstep={}, symbols=base_symbols,
        snap=snap, positions=[],
    )
    assert verdict is not None
    assert verdict["rule"] == "trailing_drawdown_projected"


def test_defensive_ladder_blocks_projected_lockdown(base_account_snapshot, base_symbols):
    """Day P&L -$300; proposed $250 worst pushes to -$550 → triggers $-500 lockdown step."""
    limits = {
        "combine_defense": {"ladder": [
            {"threshold_usd": -150, "action": "warn", "description": ""},
            {"threshold_usd": -300, "action": "restrict", "description": ""},
            {"threshold_usd": -500, "action": "lockdown", "description": "flat the book"},
            {"threshold_usd": -750, "action": "emergency_flatten", "description": ""},
        ]},
        "account": {"per_trade_risk_pct_of_equity": 0.005},
    }
    snap = dict(base_account_snapshot, realized_pl_day_usd=-300, unrealized_pl_usd=0)
    order = {"symbol": "MCL", "side": "buy", "qty": 1,
             "limit_price": 78.50, "stop_price": 76.00}  # $250 worst
    verdict = _check_combine_defensive_ladder(
        tool_name="x", order=order, agent="X",
        limits=limits, topstep={}, symbols=base_symbols,
        snap=snap, positions=[],
    )
    assert verdict is not None
    assert verdict["rule"] == "defensive_ladder_projected"


# ── Broker canTrade flag ────────────────────────────────────────
def test_can_trade_pass_when_no_snapshot(base_limits, mcl_long_order):
    """Cold start (no snapshot yet) → other checks handle it, this passes."""
    verdict = _check_broker_can_trade(
        tool_name="x", order=mcl_long_order, agent="X",
        limits=base_limits, topstep={}, symbols={},
        snap=None, positions=[],
    )
    assert verdict is None


def test_can_trade_pass_when_true(base_limits, base_account_snapshot, mcl_long_order):
    snap = dict(base_account_snapshot, can_trade=1)
    verdict = _check_broker_can_trade(
        tool_name="x", order=mcl_long_order, agent="X",
        limits=base_limits, topstep={}, symbols={},
        snap=snap, positions=[],
    )
    assert verdict is None


def test_can_trade_pass_when_column_missing(base_limits, base_account_snapshot, mcl_long_order):
    """Older snapshots predate the migration; default-permissive."""
    snap = dict(base_account_snapshot)  # no can_trade key
    verdict = _check_broker_can_trade(
        tool_name="x", order=mcl_long_order, agent="X",
        limits=base_limits, topstep={}, symbols={},
        snap=snap, positions=[],
    )
    assert verdict is None


def test_can_trade_blocks_when_false(base_limits, base_account_snapshot, mcl_long_order):
    snap = dict(base_account_snapshot, can_trade=0)
    verdict = _check_broker_can_trade(
        tool_name="x", order=mcl_long_order, agent="X",
        limits=base_limits, topstep={}, symbols={},
        snap=snap, positions=[],
    )
    assert verdict is not None
    assert verdict["rule"] == "broker_can_trade_false"


# ── Consistency rule (advisory) ─────────────────────────────────
def _make_consistency_db_mock(*, history_total: float, has_history_rows: bool):
    """Build a get_db() return value that satisfies the consistency check."""
    mock_db = MagicMock()
    mock_db.total_realized_to_date.return_value = history_total
    mock_db.daily_pl_history.return_value = (
        [{"day": "2026-04-28", "realized_pl_usd": history_total}]
        if has_history_rows else []
    )
    return mock_db


def test_consistency_rule_passes_with_no_history(base_limits, base_account_snapshot):
    """Day 1 of a Combine: no history → no advisory (would be noisy)."""
    snap = dict(base_account_snapshot, realized_pl_day_usd=600)
    with patch("hooks.risk_gate.get_db",
               return_value=_make_consistency_db_mock(
                   history_total=0, has_history_rows=False)):
        verdict = _check_consistency_rule(
            tool_name="x", order={}, agent="X",
            limits=base_limits, topstep={}, symbols={},
            snap=snap, positions=[],
        )
    assert verdict is None  # advisory never blocks; no warn either


def test_consistency_rule_passes_on_losing_day(base_limits, base_account_snapshot):
    """Today P&L ≤ 0 cannot breach the cap."""
    snap = dict(base_account_snapshot, realized_pl_day_usd=-100)
    with patch("hooks.risk_gate.get_db") as mock_get_db:
        verdict = _check_consistency_rule(
            tool_name="x", order={}, agent="X",
            limits=base_limits, topstep={}, symbols={},
            snap=snap, positions=[],
        )
        # Should short-circuit before touching the DB at all.
        mock_get_db.assert_not_called()
    assert verdict is None


def test_consistency_rule_warns_when_today_exceeds_50pct(base_limits, base_account_snapshot):
    """History +$200, today +$600 → today is 75% of $800 → warn-level event,
    but advisory mode means NO BLOCK (verdict still None)."""
    snap = dict(base_account_snapshot, realized_pl_day_usd=600)
    mock_db = _make_consistency_db_mock(history_total=200, has_history_rows=True)
    with patch("hooks.risk_gate.get_db", return_value=mock_db):
        verdict = _check_consistency_rule(
            tool_name="x", order={}, agent="X",
            limits=base_limits, topstep={}, symbols={},
            snap=snap, positions=[],
        )
    assert verdict is None  # advisory: never blocks
    # But it MUST have logged a warn-severity event.
    mock_db.record_risk_event.assert_called_once()
    call_kwargs = mock_db.record_risk_event.call_args
    # First positional arg or kwarg = severity
    severity = call_kwargs.kwargs.get("severity") or call_kwargs.args[0]
    rule = call_kwargs.kwargs.get("rule") or (
        call_kwargs.args[1] if len(call_kwargs.args) > 1 else None)
    assert severity == "warn"
    assert rule == "consistency_rule_advisory"


def test_consistency_rule_silent_when_today_under_50pct(base_limits, base_account_snapshot):
    """History +$1000, today +$300 → today is 23% of $1300 → no warn."""
    snap = dict(base_account_snapshot, realized_pl_day_usd=300)
    mock_db = _make_consistency_db_mock(history_total=1000, has_history_rows=True)
    with patch("hooks.risk_gate.get_db", return_value=mock_db):
        verdict = _check_consistency_rule(
            tool_name="x", order={}, agent="X",
            limits=base_limits, topstep={}, symbols={},
            snap=snap, positions=[],
        )
    assert verdict is None
    mock_db.record_risk_event.assert_not_called()


def test_consistency_rule_passes_when_history_is_negative(base_limits, base_account_snapshot):
    """History -$500, today +$100 → grand total -$400, rule does not bind."""
    snap = dict(base_account_snapshot, realized_pl_day_usd=100)
    mock_db = _make_consistency_db_mock(history_total=-500, has_history_rows=True)
    with patch("hooks.risk_gate.get_db", return_value=mock_db):
        verdict = _check_consistency_rule(
            tool_name="x", order={}, agent="X",
            limits=base_limits, topstep={}, symbols={},
            snap=snap, positions=[],
        )
    assert verdict is None
    mock_db.record_risk_event.assert_not_called()


# ── Thin-tape regime + autonomous RTH gates ─────────────────────
def _build_regime_limits(*, enabled: bool, start_et: str, end_et: str):
    return {
        "regime_gates": {
            "thin_tape": {
                "enabled": enabled,
                "start_et": start_et,
                "end_et": end_et,
                "reason": "test",
            }
        }
    }


def test_thin_tape_regime_blocks_when_enabled_and_in_window(monkeypatch):
    """Thin-tape gate: block when current ET is in the window."""
    # Construct a window that wraps midnight and definitely includes "now"
    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo as _ZI
    now_et = _dt.now(tz=_ZI("America/New_York"))
    # Window from 1 hour ago to 1 hour from now (covers now)
    start = ((now_et.hour - 1) % 24, now_et.minute)
    end = ((now_et.hour + 1) % 24, now_et.minute)
    limits = _build_regime_limits(
        enabled=True,
        start_et=f"{start[0]:02d}:{start[1]:02d}",
        end_et=f"{end[0]:02d}:{end[1]:02d}",
    )
    verdict = _check_thin_tape_regime(
        tool_name="x", order={}, agent="X",
        limits=limits, topstep={}, symbols={},
        snap=None, positions=[],
    )
    assert verdict is not None
    assert verdict["rule"] == "thin_tape_regime"


def test_thin_tape_regime_passes_when_disabled():
    """When enabled=false, the gate is a no-op."""
    limits = _build_regime_limits(enabled=False, start_et="00:00", end_et="23:59")
    v = _check_thin_tape_regime(
        tool_name="x", order={}, agent="X",
        limits=limits, topstep={}, symbols={},
        snap=None, positions=[],
    )
    assert v is None


def test_snapshot_freshness_blocks_with_stale_snapshot(monkeypatch, tmp_path):
    """If autonomous_mode and snapshot >5min old, block."""
    fund_yaml = tmp_path / "fund.yaml"
    fund_yaml.write_text(
        "autonomous_mode: true\n"
        "autonomous_restrictions:\n"
        "  require_snapshot_within_minutes: 5\n"
    )
    monkeypatch.chdir(tmp_path)
    # Now in a sandbox; create config dir with this fund.yaml
    import shutil
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    shutil.move(str(fund_yaml), str(cfg_dir / "fund.yaml"))
    # Stale snapshot (10 min old)
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz
    stale_ts = (_dt.now(tz=_tz.utc) - _td(minutes=10)).isoformat()
    snap = {"ts": stale_ts, "balance_usd": 50000}
    v = _check_snapshot_freshness(
        tool_name="x", order={}, agent="X",
        limits={}, topstep={}, symbols={},
        snap=snap, positions=[],
    )
    assert v is not None
    assert v["rule"] == "snapshot_freshness"


def test_snapshot_freshness_passes_with_fresh_snapshot(monkeypatch, tmp_path):
    """Snapshot 1 min old → fine."""
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "fund.yaml").write_text(
        "autonomous_mode: true\n"
        "autonomous_restrictions:\n"
        "  require_snapshot_within_minutes: 5\n"
    )
    monkeypatch.chdir(tmp_path)
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz
    fresh_ts = (_dt.now(tz=_tz.utc) - _td(minutes=1)).isoformat()
    snap = {"ts": fresh_ts, "balance_usd": 50000}
    v = _check_snapshot_freshness(
        tool_name="x", order={}, agent="X",
        limits={}, topstep={}, symbols={},
        snap=snap, positions=[],
    )
    assert v is None


def test_snapshot_freshness_skipped_when_autonomous_off(monkeypatch, tmp_path):
    """When autonomous_mode is false, the check is skipped entirely."""
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "fund.yaml").write_text("autonomous_mode: false\n")
    monkeypatch.chdir(tmp_path)
    v = _check_snapshot_freshness(
        tool_name="x", order={}, agent="X",
        limits={}, topstep={}, symbols={},
        snap=None, positions=[],
    )
    assert v is None


def test_every_per_symbol_has_a_sector_in_sector_limits():
    """Every symbol with per_symbol limits must map to a configured sector.
    A mismatch (e.g. symbols.yaml says 'grains' but sector_limits only has
    'ag') silently disables the basket cap for those symbols."""
    import yaml
    from pathlib import Path
    risk = yaml.safe_load(Path("config/risk_limits.yaml").read_text())
    syms = yaml.safe_load(Path("config/symbols.yaml").read_text())["symbols"]
    sector_limits = set(risk.get("sector_limits", {}).keys())
    bad = []
    for s in risk.get("per_symbol", {}):
        if s == "default":
            continue
        sec = (syms.get(s) or {}).get("sector")
        if sec is None:
            bad.append((s, "missing in symbols.yaml or no sector"))
        elif sec not in sector_limits:
            bad.append((s, f"sector '{sec}' has no sector_limits entry"))
    assert not bad, f"Sector coverage gaps: {bad}"


def test_internal_dll_is_at_most_half_of_topstep():
    """Internal DLL target must be ≤ 50% of Topstep DLL.
    User directive: agents should "essentially never hit" Topstep's DLL.
    May be tightened below 50% post-incident (e.g., 25% on first day after
    a breach) — that's fine; the floor is "no looser than 50%"."""
    import yaml
    from pathlib import Path
    cfg = yaml.safe_load(Path("config/risk_limits.yaml").read_text())
    acct = cfg["account"]
    assert acct["internal_dll_target_usd"] * 2 <= acct["daily_loss_limit_usd"], (
        f"internal_dll_target_usd ({acct['internal_dll_target_usd']}) "
        f"must be ≤ 50% of Topstep DLL ({acct['daily_loss_limit_usd']})"
    )
