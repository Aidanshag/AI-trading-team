"""Unit tests for tools/shadow_realism.py.

These verify the math gives sensible numbers AND match today's actual
live trades within reasonable tolerance.
"""
from __future__ import annotations

import pytest

from tools import shadow_realism as sr


# ── Basic math ────────────────────────────────────────────────

def test_realistic_usd_winner_subtracts_friction():
    """+1.5R on $200 risk → gross $300 minus slippage minus fees."""
    # MES: tick_value=$1.25, slippage 1.5 round trip × $1.25 = $1.88
    # fees per round trip = $0.74
    out = sr.realistic_usd(pnl_r=1.5, risk_usd=200.0, symbol="MES")
    # gross = $300, slip = $1.88, fees = $0.74 → $297.38
    assert out == pytest.approx(297.38, abs=0.05)


def test_realistic_usd_loser_adds_friction_to_loss():
    """-1R on $200 risk → gross -$200 minus slippage minus fees."""
    out = sr.realistic_usd(pnl_r=-1.0, risk_usd=200.0, symbol="MES")
    # gross = -$200, slip = $1.88, fees = $0.74 → -$202.62
    assert out == pytest.approx(-202.62, abs=0.05)


def test_realistic_usd_returns_none_on_missing_inputs():
    assert sr.realistic_usd(None, 200.0, "GC") is None
    assert sr.realistic_usd(1.0, None, "GC") is None


def test_slippage_cost_default_one_and_a_half_ticks_round_trip():
    """Default slippage is 1.5 tick round-trip × tick_value."""
    # GC tick_value = $10 → slippage = $15
    assert sr.slippage_cost_usd("GC") == pytest.approx(15.0)
    # MNQ tick_value = $0.50 → slippage = $0.75
    assert sr.slippage_cost_usd("MNQ") == pytest.approx(0.75)


def test_realistic_usd_qty_scales_friction():
    """qty=2 doubles slippage and fees."""
    one = sr.realistic_usd(1.0, 100.0, "GC", qty=1)
    two = sr.realistic_usd(1.0, 100.0, "GC", qty=2)
    # Friction doubles when qty doubles; gross stays at $100 (R math)
    # one = 100 - 15 - 5 = 80; two = 100 - 30 - 10 = 60
    assert one == pytest.approx(80.0, abs=0.1)
    assert two == pytest.approx(60.0, abs=0.1)


# ── Verification vs today's actual live trades ─────────────────

def test_verify_gc_trade_1_under_predicts_actual():
    """Today's GC long #1: $550 risk, +4.76R idealized, actual P&L was +$2,616.
    With pessimistic 1.5-tick slippage, prediction should be LOWER than actual
    (we want to under-predict so we don't over-promote)."""
    predicted = sr.realistic_usd(pnl_r=4.76, risk_usd=550.0, symbol="GC")
    actual = 2616.0
    assert predicted < actual, f"predicted {predicted} should be < actual {actual}"
    # ...but not WAY off — within $30
    assert abs(predicted - actual) < 30


def test_verify_gc_trade_2_under_predicts_actual():
    """Today's GC long #2: $600 risk, +0.59R, actual +$356."""
    predicted = sr.realistic_usd(pnl_r=0.59, risk_usd=600.0, symbol="GC")
    actual = 356.0
    assert predicted < actual
    assert abs(predicted - actual) < 30


def test_verify_gc_trade_3_under_predicts_actual():
    """Today's GC short: $460 risk, +0.82R, actual +$376."""
    predicted = sr.realistic_usd(pnl_r=0.82, risk_usd=460.0, symbol="GC")
    actual = 376.0
    assert predicted < actual
    assert abs(predicted - actual) < 30


def test_breakdown_returns_components():
    """realistic_usd_breakdown shows gross + slippage + fees."""
    out = sr.realistic_usd_breakdown(pnl_r=2.0, risk_usd=500.0, symbol="GC")
    assert out["gross_usd"] == pytest.approx(1000.0)
    assert out["slippage_usd"] == pytest.approx(-15.0)  # 1.5 ticks × $10
    assert out["fees_usd"] == pytest.approx(-5.0)
    assert out["realistic_usd"] == pytest.approx(980.0)
