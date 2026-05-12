"""Unit tests for tools/daily_profit_cap.py + tools/account_stage.py."""
from __future__ import annotations

from pathlib import Path

import pytest

from tools import daily_profit_cap as dpc
from tools import account_stage as stg


def setup_function(_):
    """Clear the day-state file between tests."""
    if dpc.DAY_STATE_FILE.exists():
        dpc.DAY_STATE_FILE.unlink()


def teardown_function(_):
    if dpc.DAY_STATE_FILE.exists():
        dpc.DAY_STATE_FILE.unlink()


# ── account_stage helpers ──────────────────────────────────────

def test_stage_defaults_to_combine_when_config_missing(monkeypatch, tmp_path):
    """If config file is missing, stage defaults to 'combine' (safest)."""
    monkeypatch.setattr(stg, "_CONFIG_FILE", tmp_path / "nope.yaml")
    assert stg.current_stage() == "combine"
    assert stg.is_combine() is True


def test_stage_reads_from_yaml(monkeypatch, tmp_path):
    """`stage: xfa` in yaml means is_combine() returns False."""
    cfg = tmp_path / "stage.yaml"
    cfg.write_text("stage: xfa\ncombine_daily_profit_cap_usd: 600\n")
    monkeypatch.setattr(stg, "_CONFIG_FILE", cfg)
    assert stg.current_stage() == "xfa"
    assert stg.is_combine() is False


def test_combine_cap_disabled_when_stage_not_combine(monkeypatch, tmp_path):
    """combine_daily_profit_cap_usd() returns None when stage != combine."""
    cfg = tmp_path / "stage.yaml"
    cfg.write_text("stage: xfa\ncombine_daily_profit_cap_usd: 600\n")
    monkeypatch.setattr(stg, "_CONFIG_FILE", cfg)
    assert stg.combine_daily_profit_cap_usd() is None


def test_combine_cap_active_when_stage_combine(monkeypatch, tmp_path):
    """combine_daily_profit_cap_usd() returns float value when stage=combine."""
    cfg = tmp_path / "stage.yaml"
    cfg.write_text("stage: combine\ncombine_daily_profit_cap_usd: 600\n")
    monkeypatch.setattr(stg, "_CONFIG_FILE", cfg)
    assert stg.combine_daily_profit_cap_usd() == 600.0


def test_combine_cap_can_be_disabled_via_zero(monkeypatch, tmp_path):
    """Explicit cap of 0 disables the cap even in combine."""
    cfg = tmp_path / "stage.yaml"
    cfg.write_text("stage: combine\ncombine_daily_profit_cap_usd: 0\n")
    monkeypatch.setattr(stg, "_CONFIG_FILE", cfg)
    assert stg.combine_daily_profit_cap_usd() is None


# ── day-start balance tracking ─────────────────────────────────

def test_day_start_balance_records_on_first_call(monkeypatch, tmp_path):
    """First call records current balance as the day's start."""
    state_file = tmp_path / "day_state.json"
    monkeypatch.setattr(dpc, "DAY_STATE_FILE", state_file)
    start = dpc.get_day_start_balance(50000.0)
    assert start == 50000.0
    assert state_file.exists()


def test_day_start_balance_is_idempotent_within_window(monkeypatch, tmp_path):
    """Same day window -> same start balance even with different current
    balance values passed in."""
    state_file = tmp_path / "day_state.json"
    monkeypatch.setattr(dpc, "DAY_STATE_FILE", state_file)
    dpc.get_day_start_balance(50000.0)
    assert dpc.get_day_start_balance(51000.0) == 50000.0
    assert dpc.get_day_start_balance(49500.0) == 50000.0


def test_compute_day_pnl_subtracts_start_balance(monkeypatch, tmp_path):
    """day_pnl = current - start."""
    state_file = tmp_path / "day_state.json"
    monkeypatch.setattr(dpc, "DAY_STATE_FILE", state_file)
    dpc.get_day_start_balance(50000.0)  # records start
    assert dpc.compute_day_pnl(50600.0) == 600.0
    assert dpc.compute_day_pnl(49800.0) == -200.0


# ── check_and_enforce — the main path ──────────────────────────

class _FakeClient:
    """Minimal broker stand-in."""
    def __init__(self, balance: float = 50000.0, positions=None):
        self._balance = balance
        self._positions = positions or []
        self.placed: list[dict] = []
    def get_accounts(self):
        return [{"id": 22115080, "balance": self._balance}]
    def get_positions(self, account_id):
        return self._positions
    def place_order(self, **kwargs):
        self.placed.append(kwargs)
        return {"orderId": 999}


def test_check_and_enforce_no_action_below_cap(monkeypatch, tmp_path):
    """Balance below cap → no trigger, no flatten."""
    state_file = tmp_path / "day_state.json"
    monkeypatch.setattr(dpc, "DAY_STATE_FILE", state_file)
    # Record day start
    dpc.get_day_start_balance(50000.0)
    client = _FakeClient(balance=50300.0)  # day P&L = +$300
    result = dpc.check_and_enforce(client, account_id=22115080, cap_usd=600.0)
    assert result["triggered"] is False
    assert result["day_pnl"] == pytest.approx(300.0)
    assert client.placed == []


def test_check_and_enforce_triggers_at_cap(monkeypatch, tmp_path):
    """Balance at/over cap → triggered, flattens positions."""
    state_file = tmp_path / "day_state.json"
    monkeypatch.setattr(dpc, "DAY_STATE_FILE", state_file)
    dpc.get_day_start_balance(50000.0)
    client = _FakeClient(
        balance=50800.0,  # day P&L = +$800, over cap of $600
        positions=[{"contractId": "CON.F.US.GCE.M26", "size": 1, "type": 1}],
    )
    result = dpc.check_and_enforce(client, 22115080, cap_usd=600.0)
    assert result["triggered"] is True
    assert result["day_pnl"] == pytest.approx(800.0)
    assert len(client.placed) == 1
    assert client.placed[0]["side"] == "sell"  # closing long
    assert client.placed[0]["order_type"] == "market"


def test_check_and_enforce_disabled_with_none_cap(monkeypatch, tmp_path):
    """cap_usd=None → no action even with huge profit."""
    state_file = tmp_path / "day_state.json"
    monkeypatch.setattr(dpc, "DAY_STATE_FILE", state_file)
    dpc.get_day_start_balance(50000.0)
    client = _FakeClient(balance=99999.0)
    result = dpc.check_and_enforce(client, 22115080, cap_usd=None)
    assert result["triggered"] is False
    assert client.placed == []


def test_check_and_enforce_handles_broker_error(monkeypatch, tmp_path):
    """If broker fetch fails, return triggered=False (fail-open)."""
    state_file = tmp_path / "day_state.json"
    monkeypatch.setattr(dpc, "DAY_STATE_FILE", state_file)
    class Bad:
        def get_accounts(self):
            raise RuntimeError("broker down")
    result = dpc.check_and_enforce(Bad(), 1, cap_usd=600.0)
    assert result["triggered"] is False
