"""Tests for tools/options/black_scholes.py — cross-checked against
py_vollib when available, against known textbook values otherwise."""
from __future__ import annotations

import math

import pytest

from tools.options import black_scholes as bs


def test_call_price_textbook_hull_example():
    """Hull Ch.15 Example 15.6: S=42, K=40, r=10%, sigma=20%, T=0.5
    → call price ≈ 4.76."""
    p = bs.call_price(S=42, K=40, T=0.5, r=0.10, sigma=0.20)
    assert p == pytest.approx(4.7594, abs=0.01)


def test_put_price_textbook_hull_example():
    """Same inputs, put price ≈ 0.81."""
    p = bs.put_price(S=42, K=40, T=0.5, r=0.10, sigma=0.20)
    assert p == pytest.approx(0.8086, abs=0.01)


def test_put_call_parity():
    """C - P = S*e^(-qT) - K*e^(-rT)."""
    S, K, T, r, sigma, q = 100, 105, 0.25, 0.05, 0.30, 0.02
    c = bs.call_price(S, K, T, r, sigma, q)
    p = bs.put_price(S, K, T, r, sigma, q)
    lhs = c - p
    rhs = S * math.exp(-q * T) - K * math.exp(-r * T)
    assert lhs == pytest.approx(rhs, abs=1e-6)


def test_delta_atm_call_about_half():
    """ATM call delta ≈ 0.5 - 0.6 for short-dated options."""
    d = bs.delta("c", S=100, K=100, T=0.25, r=0.05, sigma=0.20)
    assert 0.50 < d < 0.65


def test_delta_atm_put_about_minus_half():
    """ATM put delta is between -0.40 and -0.50 for short-dated options
    with non-zero risk-free rate (r shifts delta toward call dominance)."""
    d = bs.delta("p", S=100, K=100, T=0.25, r=0.05, sigma=0.20)
    assert -0.40 > d > -0.50


def test_gamma_same_for_call_and_put():
    """Gamma is identical for calls and puts at same strike+expiry."""
    g_c = bs.gamma("c", S=100, K=100, T=0.25, r=0.05, sigma=0.20)
    g_p = bs.gamma("p", S=100, K=100, T=0.25, r=0.05, sigma=0.20)
    assert g_c == pytest.approx(g_p, abs=1e-9)


def test_vega_positive_for_both():
    v_c = bs.vega("c", S=100, K=100, T=0.25, r=0.05, sigma=0.20)
    v_p = bs.vega("p", S=100, K=100, T=0.25, r=0.05, sigma=0.20)
    assert v_c > 0
    assert v_p > 0
    assert v_c == pytest.approx(v_p, abs=1e-9)


def test_theta_negative_for_long_options():
    t_c = bs.theta("c", S=100, K=100, T=0.25, r=0.05, sigma=0.20)
    t_p = bs.theta("p", S=100, K=100, T=0.25, r=0.05, sigma=0.20)
    assert t_c < 0
    assert t_p < 0


def test_implied_vol_round_trip():
    """Compute price at sigma=0.25, then back-solve IV — should match."""
    p = bs.call_price(S=100, K=100, T=0.5, r=0.05, sigma=0.25)
    iv = bs.implied_volatility("c", p, S=100, K=100, T=0.5, r=0.05)
    assert iv == pytest.approx(0.25, abs=0.001)


def test_implied_vol_below_intrinsic_raises():
    with pytest.raises(ValueError):
        bs.implied_volatility("c", 0.01, S=100, K=80, T=0.5, r=0.05)


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        bs.call_price(S=0, K=100, T=0.5, r=0.05, sigma=0.20)
    with pytest.raises(ValueError):
        bs.call_price(S=100, K=100, T=0, r=0.05, sigma=0.20)
    with pytest.raises(ValueError):
        bs.call_price(S=100, K=100, T=0.5, r=0.05, sigma=0)


def test_dispatch_wrapper():
    p1 = bs.price("call", 100, 100, 0.5, 0.05, 0.20)
    p2 = bs.call_price(100, 100, 0.5, 0.05, 0.20)
    assert p1 == p2


def test_all_greeks_returns_six_keys():
    g = bs.all_greeks("c", 100, 100, 0.25, 0.05, 0.20)
    assert set(g.keys()) == {"price", "delta", "gamma", "vega", "theta", "rho"}


# Cross-validate against py_vollib if installed
try:
    from py_vollib.black_scholes import black_scholes as _vollib_bs
    from py_vollib.black_scholes.greeks.analytical import (
        delta as _vd, gamma as _vg, vega as _vv, theta as _vt, rho as _vr,
    )
    PYVOLLIB_AVAILABLE = True
except ImportError:
    PYVOLLIB_AVAILABLE = False


@pytest.mark.skipif(not PYVOLLIB_AVAILABLE, reason="py_vollib not installed")
def test_cross_check_price_against_pyvollib():
    """Our price must match py_vollib within 0.1% for the same inputs."""
    inputs = (100, 100, 0.5, 0.05, 0.25)
    our = bs.call_price(*inputs)
    theirs = _vollib_bs("c", *inputs)
    assert our == pytest.approx(theirs, rel=0.001), \
        f"BS drift: ours={our}, theirs={theirs}"


@pytest.mark.skipif(not PYVOLLIB_AVAILABLE, reason="py_vollib not installed")
def test_cross_check_delta_against_pyvollib():
    inputs = (100, 100, 0.5, 0.05, 0.25)
    our = bs.delta("c", *inputs)
    theirs = _vd("c", *inputs)
    assert our == pytest.approx(theirs, rel=0.001)
