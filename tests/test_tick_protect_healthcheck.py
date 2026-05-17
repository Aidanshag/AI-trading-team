"""Tests for tools/tick_protect_healthcheck."""
from __future__ import annotations

import pytest


def test_healthcheck_passes_on_clean_system():
    """End-to-end: synthetic position → tick → close fires within 2s."""
    from tools.tick_protect_healthcheck import run_healthcheck
    r = run_healthcheck(timeout_s=2.0)
    assert r["passed"] is True
    assert r["close_fired"] is True
    assert r["latency_ms"] is not None
    assert r["latency_ms"] < 1000  # well under 1s
    assert r["errors"] == []


def test_healthcheck_returns_structured_result():
    from tools.tick_protect_healthcheck import run_healthcheck
    r = run_healthcheck()
    assert set(r.keys()) >= {"passed", "close_fired", "latency_ms", "errors"}
    assert isinstance(r["errors"], list)


def test_healthcheck_does_not_pollute_state():
    """After healthcheck, no synthetic positions or peak data remain."""
    from tools.tick_protect_healthcheck import run_healthcheck
    from tools import tick_protect, profit_protect
    # Set known state before
    profit_protect._position_high_water["REAL_long"] = 100.0
    tick_protect.register_position(
        contract_id="CON.F.US.REAL.M26", symbol="REAL",
        side="long", size=1, avg_price=100.0,
        tick_size=0.1, tick_value=1.0, account_id=42,
    )
    pre_positions = tick_protect.tracked_positions()
    run_healthcheck()
    post_positions = tick_protect.tracked_positions()
    # Synthetic HEALTHCHECK contract should not be in tracked positions
    assert "CON.F.US.HEALTHCHECK.SYNTH" not in post_positions
    # Real positions preserved
    assert "CON.F.US.REAL.M26" in post_positions or pre_positions == post_positions
    # Real peak data preserved
    assert profit_protect._position_high_water.get("REAL_long") == 100.0
    # Cleanup
    tick_protect.reset_for_test()
    profit_protect._position_high_water.clear()
