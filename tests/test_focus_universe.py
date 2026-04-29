"""Tests for the focus-universe risk gate."""
from __future__ import annotations
import importlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml


def _setup_focus_config(tmp_path: Path, monkeypatch, *,
                         active: bool = True,
                         hours_until_expiry: float = 24,
                         allowed: dict | None = None) -> None:
    """Create a focus_universe.yaml in tmp_path/config and point CONFIG_ROOT there."""
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir(exist_ok=True)
    expiry = datetime.now(tz=timezone.utc) + timedelta(hours=hours_until_expiry)
    payload = {
        "focus_period_active": active,
        "focus_period_expires": expiry.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "allowed_symbols": allowed or {"energies": ["NG"], "rates": ["ZN"]},
    }
    (cfg_dir / "focus_universe.yaml").write_text(
        yaml.safe_dump(payload), encoding="utf-8"
    )
    mod = importlib.import_module("hooks.risk_gate")
    monkeypatch.setattr(mod, "CONFIG_ROOT", cfg_dir)


def test_focus_active_blocks_disallowed_symbol(monkeypatch, tmp_path):
    _setup_focus_config(monkeypatch=monkeypatch, tmp_path=tmp_path)
    from hooks.risk_gate import _check_focus_universe
    verdict = _check_focus_universe(
        tool_name="x", order={"symbol": "ES"}, agent="X",
        limits={}, topstep={}, symbols={}, snap=None, positions=[],
    )
    assert verdict is not None
    assert verdict["rule"] == "focus_universe"


def test_focus_active_allows_listed_symbol(monkeypatch, tmp_path):
    _setup_focus_config(monkeypatch=monkeypatch, tmp_path=tmp_path)
    from hooks.risk_gate import _check_focus_universe
    verdict = _check_focus_universe(
        tool_name="x", order={"symbol": "NG"}, agent="X",
        limits={}, topstep={}, symbols={}, snap=None, positions=[],
    )
    assert verdict is None


def test_focus_inactive_skips_check(monkeypatch, tmp_path):
    _setup_focus_config(monkeypatch=monkeypatch, tmp_path=tmp_path, active=False)
    from hooks.risk_gate import _check_focus_universe
    verdict = _check_focus_universe(
        tool_name="x", order={"symbol": "ES"}, agent="X",
        limits={}, topstep={}, symbols={}, snap=None, positions=[],
    )
    assert verdict is None  # not active → no block


def test_focus_expired_skips_check(monkeypatch, tmp_path):
    _setup_focus_config(monkeypatch=monkeypatch, tmp_path=tmp_path,
                         hours_until_expiry=-1)
    from hooks.risk_gate import _check_focus_universe
    verdict = _check_focus_universe(
        tool_name="x", order={"symbol": "ES"}, agent="X",
        limits={}, topstep={}, symbols={}, snap=None, positions=[],
    )
    assert verdict is None  # expired → no block


def test_focus_with_topstep_contract_id(monkeypatch, tmp_path):
    """Risk hook must handle ProjectX contract-id form like CON.F.US.NG.M26."""
    _setup_focus_config(monkeypatch=monkeypatch, tmp_path=tmp_path)
    from hooks.risk_gate import _check_focus_universe
    verdict = _check_focus_universe(
        tool_name="x", order={"symbol": "CON.F.US.NG.M26"}, agent="X",
        limits={}, topstep={}, symbols={}, snap=None, positions=[],
    )
    assert verdict is None


def test_focus_with_normalized_root(monkeypatch, tmp_path):
    """ZN as 'TYA' (Topstep root) should resolve through normalize."""
    _setup_focus_config(monkeypatch=monkeypatch, tmp_path=tmp_path)
    from hooks.risk_gate import _check_focus_universe
    # CON.F.US.TYA.M26 (Topstep's ZN id) should match 'ZN' in allowlist
    verdict = _check_focus_universe(
        tool_name="x", order={"symbol": "CON.F.US.TYA.M26"}, agent="X",
        limits={}, topstep={}, symbols={}, snap=None, positions=[],
    )
    assert verdict is None


def test_focus_empty_allowlist_skips_check(monkeypatch, tmp_path):
    """Empty allowed_symbols should not block (graceful no-op)."""
    _setup_focus_config(monkeypatch=monkeypatch, tmp_path=tmp_path,
                         allowed={"energies": [], "rates": []})
    from hooks.risk_gate import _check_focus_universe
    verdict = _check_focus_universe(
        tool_name="x", order={"symbol": "ES"}, agent="X",
        limits={}, topstep={}, symbols={}, snap=None, positions=[],
    )
    assert verdict is None
