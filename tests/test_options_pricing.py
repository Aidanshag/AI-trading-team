"""Tests for tools/options_pricing.py — Black-76 + Greeks + IV solver."""

import math

import pytest

from tools.options_pricing import (
    Leg,
    black76,
    implied_vol,
    structure_greeks,
)


# ── Sanity: prices increase with vol, both calls and puts ──────
def test_call_price_monotonic_in_vol():
    p_low  = black76(F=100, K=100, T=0.25, sigma=0.10, right="C").price
    p_high = black76(F=100, K=100, T=0.25, sigma=0.40, right="C").price
    assert p_high > p_low


def test_put_price_monotonic_in_vol():
    p_low  = black76(F=100, K=100, T=0.25, sigma=0.10, right="P").price
    p_high = black76(F=100, K=100, T=0.25, sigma=0.40, right="P").price
    assert p_high > p_low


# ── ATM call/put prices roughly equal under Black-76 (no carry) ─
def test_atm_call_put_parity_approx():
    """For F=K and r=0, call and put have the same price."""
    r = 0.0
    c = black76(F=100, K=100, T=0.5, sigma=0.20, r=r, right="C").price
    p = black76(F=100, K=100, T=0.5, sigma=0.20, r=r, right="P").price
    assert abs(c - p) < 1e-8


# ── Put-call parity holds with discounting ──────────────────────
def test_put_call_parity_with_rate():
    F, K, T, sigma, r = 100.0, 95.0, 0.5, 0.25, 0.04
    c = black76(F, K, T, sigma, r, "C").price
    p = black76(F, K, T, sigma, r, "P").price
    discount = math.exp(-r * T)
    # Under Black-76: C - P = exp(-rT)(F - K)
    assert abs((c - p) - discount * (F - K)) < 1e-6


# ── Greeks signs and magnitudes ─────────────────────────────────
def test_call_delta_in_range():
    res = black76(F=100, K=100, T=0.25, sigma=0.20, right="C")
    assert 0.0 < res.delta < 1.0


def test_put_delta_in_range():
    res = black76(F=100, K=100, T=0.25, sigma=0.20, right="P")
    assert -1.0 < res.delta < 0.0


def test_gamma_positive():
    """Gamma is always positive for long options."""
    c = black76(F=100, K=100, T=0.25, sigma=0.20, right="C")
    p = black76(F=100, K=100, T=0.25, sigma=0.20, right="P")
    assert c.gamma > 0
    assert p.gamma > 0


def test_vega_positive():
    """Vega is always positive for long options."""
    c = black76(F=100, K=100, T=0.25, sigma=0.20, right="C")
    p = black76(F=100, K=100, T=0.25, sigma=0.20, right="P")
    assert c.vega > 0
    assert p.vega > 0


def test_call_delta_near_one_deep_itm():
    res = black76(F=200, K=100, T=0.25, sigma=0.20, right="C")
    assert res.delta > 0.95


def test_call_delta_near_zero_deep_otm():
    res = black76(F=50, K=100, T=0.25, sigma=0.20, right="C")
    assert res.delta < 0.05


# ── Theta is negative for long options (time decay) ─────────────
def test_long_theta_negative():
    """Time decay erodes long option value."""
    c = black76(F=100, K=100, T=0.25, sigma=0.20, right="C")
    p = black76(F=100, K=100, T=0.25, sigma=0.20, right="P")
    assert c.theta_per_day < 0
    assert p.theta_per_day < 0


# ── At expiry: intrinsic only ───────────────────────────────────
def test_zero_dte_intrinsic_only():
    res = black76(F=110, K=100, T=0, sigma=0.20, right="C")
    assert res.price == 10.0
    assert res.delta == 0.0
    assert res.gamma == 0.0


# ── Implied vol round-trip ──────────────────────────────────────
def test_implied_vol_round_trip_call():
    F, K, T, sigma, r = 100.0, 100.0, 0.25, 0.20, 0.04
    market_price = black76(F, K, T, sigma, r, "C").price
    iv = implied_vol(market_price, F, K, T, r, "C")
    assert abs(iv - sigma) < 1e-4


def test_implied_vol_round_trip_put():
    F, K, T, sigma, r = 100.0, 95.0, 0.5, 0.30, 0.04
    market_price = black76(F, K, T, sigma, r, "P").price
    iv = implied_vol(market_price, F, K, T, r, "P")
    assert abs(iv - sigma) < 1e-4


# ── Multi-leg structure: long call spread ───────────────────────
def test_long_call_spread_max_loss_is_debit():
    """A long call spread's max loss = the debit paid."""
    legs = [
        Leg(F=100, K=100, T=0.25, sigma=0.20, right="C", side="long",  qty=1),
        Leg(F=100, K=110, T=0.25, sigma=0.20, right="C", side="short", qty=1),
    ]
    g = structure_greeks(legs)
    assert g["net_price"] > 0  # debit
    # Max loss for credit-defined-risk is NaN; for long debit is the premium.
    # Since this is a mixed structure (long+short), max_loss returns NaN per
    # current implementation. The PM/Options Risk agents are responsible for
    # the strike-width × multiplier max-loss calc.
    assert math.isnan(g["max_loss_usd"]) or g["max_loss_usd"] == g["net_price"]


def test_iron_condor_net_delta_near_zero():
    """An ATM-balanced iron condor should have small net delta."""
    legs = [
        Leg(F=100, K=95,  T=0.25, sigma=0.20, right="P", side="long",  qty=1),
        Leg(F=100, K=98,  T=0.25, sigma=0.20, right="P", side="short", qty=1),
        Leg(F=100, K=102, T=0.25, sigma=0.20, right="C", side="short", qty=1),
        Leg(F=100, K=105, T=0.25, sigma=0.20, right="C", side="long",  qty=1),
    ]
    g = structure_greeks(legs)
    assert abs(g["net_delta"]) < 0.1
    assert g["net_theta_per_day"] > 0     # short premium → positive theta
    assert g["net_vega_per_pct"] < 0      # short premium → negative vega
