"""Tests for autonomous-mode guardrails:

  1. max_trades_per_day cap (in risk hook, gated by fund.yaml flag)
  2. autonomy wake count cap (in orchestrator wake_agent)
  3. autonomy daily $ spend cap (in orchestrator wake_agent)
  4. auto-halt re-engage at session close (writes risk_limits.yaml)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from hooks.risk_gate import _check_daily_trade_count
from runtime.orchestrator import (
    _check_autonomy_wake_budget,
    re_engage_auto_halt,
)


# --------------------------------------------------------------
# Helpers
# --------------------------------------------------------------

def _limits_with_cap(cap: int = 8) -> dict:
    return {
        "hard_rules": {"trading_halted": False},
        "account": {"max_trades_per_day": cap},
    }


class _FakeDB:
    """Minimal stand-in for state.db.Database — exposes only what the
    guardrails read."""
    def __init__(self, *, wakes_today: int = 0, usd_today: float = 0.0,
                 risk_pass_today: int = 0):
        self._wakes = wakes_today
        self._usd = usd_today
        self._pass = risk_pass_today
        self.events = []

    def connect(self):
        return self

    def execute(self, sql: str, params=()):
        s = sql.strip().upper()
        if "FROM DECISIONS" in s and "KIND = 'WAKE'" in s.upper().replace("'WAKE'", "'WAKE'"):
            return _Cur(self._wakes)
        if "FROM COSTS" in s:
            return _Cur(self._usd)
        if "FROM RISK_EVENTS" in s:
            return _Cur(self._pass)
        return _Cur(0)

    def record_risk_event(self, **kw):
        self.events.append(kw)


class _Cur:
    def __init__(self, n): self.n = n
    def fetchone(self): return [self.n]


# --------------------------------------------------------------
# 1. max_trades_per_day (risk hook)
# --------------------------------------------------------------

def _setup_config_root(monkeypatch, tmp_path: Path, autonomous: bool) -> None:
    """Make tmp_path/config the CONFIG_ROOT for the risk_gate module.
    Has to use importlib because hooks/__init__.py re-exports the function
    `risk_gate` under the name `hooks.risk_gate`, shadowing the module.
    """
    import importlib
    mod = importlib.import_module("hooks.risk_gate")
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "fund.yaml").write_text(f"autonomous_mode: {str(autonomous).lower()}\n")
    monkeypatch.setattr(mod, "CONFIG_ROOT", cfg)


def test_trade_cap_supervised_mode_skips_check(monkeypatch, tmp_path):
    """When autonomous_mode=False, the cap is not enforced (supervised:
    Risk Manager judges instead)."""
    _setup_config_root(monkeypatch, tmp_path, autonomous=False)
    verdict = _check_daily_trade_count(
        tool_name="x", order={}, agent="X",
        limits=_limits_with_cap(2), topstep={}, symbols={},
        snap=None, positions=[],
    )
    assert verdict is None


def test_trade_cap_autonomous_under_limit_allows(monkeypatch, tmp_path):
    _setup_config_root(monkeypatch, tmp_path, autonomous=True)
    fake_db = _FakeDB(risk_pass_today=3)
    import importlib
    mod = importlib.import_module("hooks.risk_gate")
    monkeypatch.setattr(mod, "get_db", lambda: fake_db)
    verdict = _check_daily_trade_count(
        tool_name="x", order={}, agent="X",
        limits=_limits_with_cap(8), topstep={}, symbols={},
        snap=None, positions=[],
    )
    assert verdict is None


def test_trade_cap_autonomous_at_limit_blocks(monkeypatch, tmp_path):
    _setup_config_root(monkeypatch, tmp_path, autonomous=True)
    fake_db = _FakeDB(risk_pass_today=8)
    import importlib
    mod = importlib.import_module("hooks.risk_gate")
    monkeypatch.setattr(mod, "get_db", lambda: fake_db)
    verdict = _check_daily_trade_count(
        tool_name="x", order={}, agent="X",
        limits=_limits_with_cap(8), topstep={}, symbols={},
        snap=None, positions=[],
    )
    assert verdict is not None
    assert verdict["rule"] == "max_trades_per_day"


# --------------------------------------------------------------
# 2 + 3. wake-budget caps (orchestrator)
# --------------------------------------------------------------

def test_wake_budget_supervised_skips(monkeypatch):
    monkeypatch.setattr("runtime.orchestrator._load_fund_yaml",
                        lambda: {"autonomous_mode": False})
    fake_db = _FakeDB(wakes_today=999, usd_today=999)
    assert _check_autonomy_wake_budget(fake_db, "CIO") is None


def test_wake_budget_under_caps_allows(monkeypatch):
    monkeypatch.setattr("runtime.orchestrator._load_fund_yaml", lambda: {
        "autonomous_mode": True,
        "autonomy_guardrails": {"max_wakes_per_day": 60, "max_usd_per_day": 5.0},
    })
    fake_db = _FakeDB(wakes_today=10, usd_today=1.20)
    assert _check_autonomy_wake_budget(fake_db, "CIO") is None


def test_wake_budget_count_cap_refuses(monkeypatch):
    monkeypatch.setattr("runtime.orchestrator._load_fund_yaml", lambda: {
        "autonomous_mode": True,
        "autonomy_guardrails": {"max_wakes_per_day": 60, "max_usd_per_day": 5.0},
    })
    fake_db = _FakeDB(wakes_today=60, usd_today=1.20)
    result = _check_autonomy_wake_budget(fake_db, "CIO")
    assert result is not None
    assert result.get("refused") is True
    assert "wake count cap" in result["reason"]


def test_wake_budget_spend_cap_refuses(monkeypatch):
    monkeypatch.setattr("runtime.orchestrator._load_fund_yaml", lambda: {
        "autonomous_mode": True,
        "autonomy_guardrails": {"max_wakes_per_day": 60, "max_usd_per_day": 5.0},
    })
    fake_db = _FakeDB(wakes_today=10, usd_today=5.01)
    result = _check_autonomy_wake_budget(fake_db, "CIO")
    assert result is not None
    assert result.get("refused") is True
    assert "spend cap" in result["reason"]


# --------------------------------------------------------------
# 4. auto-halt re-engage at session close
# --------------------------------------------------------------

def test_auto_halt_disabled_returns_none(monkeypatch):
    monkeypatch.setattr("runtime.orchestrator._load_fund_yaml",
                        lambda: {"auto_halt_at_session_close": False})
    assert re_engage_auto_halt() is None


def test_auto_halt_writes_future_timestamp(monkeypatch, tmp_path):
    """When enabled, writes risk_limits.yaml with a future trading_halt_until."""
    monkeypatch.setattr("runtime.orchestrator._load_fund_yaml", lambda: {
        "auto_halt_at_session_close": True,
        "auto_halt_resume_offset_hours": 16,
    })
    cfg = tmp_path / "config"
    cfg.mkdir()
    risk_yaml = cfg / "risk_limits.yaml"
    risk_yaml.write_text(
        "hard_rules:\n"
        '  trading_halt_until: "2024-01-01T00:00:00Z"\n'
        "  trading_halted: false\n"
    )
    monkeypatch.chdir(tmp_path)

    new_ts = re_engage_auto_halt()
    assert new_ts is not None
    # Parse + verify it's ~16h in the future (within 1 minute slack)
    from datetime import datetime, timezone, timedelta
    parsed = datetime.fromisoformat(new_ts.replace("Z", "+00:00"))
    expected = datetime.now(tz=timezone.utc) + timedelta(hours=16)
    assert abs((parsed - expected).total_seconds()) < 60

    # Verify the file was actually rewritten
    new_text = risk_yaml.read_text()
    assert new_ts in new_text
    assert "2024-01-01" not in new_text  # old value gone
