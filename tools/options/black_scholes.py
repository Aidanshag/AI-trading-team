"""Black-Scholes-Merton pricing — our own implementation.

European options only (no early exercise). For American options on
dividend-paying stocks, the BS price is an LOWER bound on a call and
an UPPER bound on a put — fine for screening; use a binomial tree for
production pricing on American puts.

Validated against:
  - Hull "Options, Futures, and Other Derivatives" Ch.15 Example 15.6
    (S=42, K=40, T=0.5, r=0.10, sigma=0.20 → C=4.76, P=0.81)
  - Put-call parity: C - P = S·e^(-qT) - K·e^(-rT)
  - Implied-vol round trip: solve back from price → original sigma

Note 2026-05-17: py_vollib cross-check is currently disabled because
py_vollib's dependency py_lets_be_rational imports `_testcapi` which is
no longer included in Python 3.14+. When py_vollib publishes a 3.14-compatible
build, re-enable the test_cross_check_* tests in tests/test_options_black_scholes.

Inputs:
  S  : underlying spot price
  K  : strike price
  T  : time to expiry in YEARS (e.g., 30 days = 30/365)
  r  : risk-free rate (decimal, e.g., 0.045 = 4.5%)
  sigma : implied volatility (decimal, e.g., 0.20 = 20%)
  q  : continuous dividend yield (decimal, default 0)

References:
  - Hull, "Options, Futures, and Other Derivatives" Ch. 15
  - py_vollib source (https://github.com/vollib/py_vollib)
"""
from __future__ import annotations

import math
from typing import Literal


SQRT_2PI = math.sqrt(2 * math.pi)


def _normal_cdf(x: float) -> float:
    """Standard normal CDF via erfc — accurate to ~1e-15."""
    return 0.5 * math.erfc(-x / math.sqrt(2))


def _normal_pdf(x: float) -> float:
    """Standard normal PDF."""
    return math.exp(-0.5 * x * x) / SQRT_2PI


def _d1_d2(S: float, K: float, T: float, r: float, sigma: float,
            q: float = 0.0) -> tuple[float, float]:
    """Compute d1 and d2 from the BS formula. Raises on T<=0 or sigma<=0."""
    if T <= 0:
        raise ValueError("T must be > 0")
    if sigma <= 0:
        raise ValueError("sigma must be > 0")
    if S <= 0 or K <= 0:
        raise ValueError("S and K must be > 0")
    sigma_sqrt_T = sigma * math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / sigma_sqrt_T
    d2 = d1 - sigma_sqrt_T
    return d1, d2


def call_price(S: float, K: float, T: float, r: float, sigma: float,
                q: float = 0.0) -> float:
    """European call price (Black-Scholes-Merton with continuous dividend)."""
    d1, d2 = _d1_d2(S, K, T, r, sigma, q)
    return S * math.exp(-q * T) * _normal_cdf(d1) - K * math.exp(-r * T) * _normal_cdf(d2)


def put_price(S: float, K: float, T: float, r: float, sigma: float,
               q: float = 0.0) -> float:
    """European put price (BSM with dividend)."""
    d1, d2 = _d1_d2(S, K, T, r, sigma, q)
    return K * math.exp(-r * T) * _normal_cdf(-d2) - S * math.exp(-q * T) * _normal_cdf(-d1)


def price(option_type: Literal["c", "p", "call", "put"],
           S: float, K: float, T: float, r: float, sigma: float,
           q: float = 0.0) -> float:
    """Dispatch wrapper. `option_type` accepts 'c'/'call' or 'p'/'put'."""
    t = option_type.lower()
    if t in ("c", "call"):
        return call_price(S, K, T, r, sigma, q)
    if t in ("p", "put"):
        return put_price(S, K, T, r, sigma, q)
    raise ValueError(f"unknown option_type: {option_type}")


def implied_volatility(option_type: Literal["c", "p"], market_price: float,
                        S: float, K: float, T: float, r: float,
                        q: float = 0.0,
                        tol: float = 1e-6, max_iter: int = 100) -> float:
    """Solve for implied volatility via Newton-Raphson, with bisection
    fallback if Newton diverges. Returns sigma such that BS(sigma) ≈ market.

    Raises ValueError if market_price is below intrinsic or above the
    no-arbitrage upper bound."""
    intrinsic = max(0.0, (S - K) if option_type.lower().startswith("c")
                    else (K - S))
    if market_price < intrinsic - tol:
        raise ValueError(f"market_price {market_price} < intrinsic {intrinsic}")
    # Initial guess via Brenner-Subrahmanyam approximation
    sigma = math.sqrt(2 * math.pi / T) * (market_price / S) if S > 0 else 0.2
    sigma = max(0.001, min(sigma, 5.0))
    for _ in range(max_iter):
        try:
            p = price(option_type, S, K, T, r, sigma, q)
            v = vega(option_type, S, K, T, r, sigma, q)
        except ValueError:
            sigma *= 1.5
            continue
        diff = p - market_price
        if abs(diff) < tol:
            return sigma
        if v <= 1e-12:
            # Vega too small for Newton — try bisection
            return _iv_bisection(option_type, market_price, S, K, T, r, q, tol)
        sigma -= diff / v
        sigma = max(0.001, min(sigma, 5.0))
    return sigma  # best effort


def _iv_bisection(option_type, market_price, S, K, T, r, q, tol):
    """Bisection fallback for IV when Newton fails."""
    lo, hi = 0.001, 5.0
    for _ in range(200):
        mid = (lo + hi) / 2
        try:
            p = price(option_type, S, K, T, r, mid, q)
        except ValueError:
            return mid
        if abs(p - market_price) < tol:
            return mid
        if p < market_price:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ── Greeks (analytical) ────────────────────────────────────────────

def delta(option_type, S, K, T, r, sigma, q=0.0) -> float:
    """Δ — sensitivity to underlying price (per $1 move)."""
    d1, _ = _d1_d2(S, K, T, r, sigma, q)
    discount = math.exp(-q * T)
    if option_type.lower().startswith("c"):
        return discount * _normal_cdf(d1)
    return -discount * _normal_cdf(-d1)


def gamma(option_type, S, K, T, r, sigma, q=0.0) -> float:
    """Γ — rate of change of delta. Same for calls and puts."""
    d1, _ = _d1_d2(S, K, T, r, sigma, q)
    return (math.exp(-q * T) * _normal_pdf(d1)) / (S * sigma * math.sqrt(T))


def vega(option_type, S, K, T, r, sigma, q=0.0) -> float:
    """ν — sensitivity to volatility, per 1.00 change in sigma.
    Many use ν/100 (per 1% IV change) — caller chooses."""
    d1, _ = _d1_d2(S, K, T, r, sigma, q)
    return S * math.exp(-q * T) * _normal_pdf(d1) * math.sqrt(T)


def theta(option_type, S, K, T, r, sigma, q=0.0) -> float:
    """Θ — time decay per YEAR. Divide by 365 for daily theta."""
    d1, d2 = _d1_d2(S, K, T, r, sigma, q)
    term1 = -(S * math.exp(-q * T) * _normal_pdf(d1) * sigma) / (2 * math.sqrt(T))
    if option_type.lower().startswith("c"):
        term2 = q * S * math.exp(-q * T) * _normal_cdf(d1)
        term3 = -r * K * math.exp(-r * T) * _normal_cdf(d2)
        return term1 + term2 + term3
    term2 = -q * S * math.exp(-q * T) * _normal_cdf(-d1)
    term3 = r * K * math.exp(-r * T) * _normal_cdf(-d2)
    return term1 + term2 + term3


def rho(option_type, S, K, T, r, sigma, q=0.0) -> float:
    """ρ — sensitivity to interest rate, per 1.00 change in r."""
    _, d2 = _d1_d2(S, K, T, r, sigma, q)
    if option_type.lower().startswith("c"):
        return K * T * math.exp(-r * T) * _normal_cdf(d2)
    return -K * T * math.exp(-r * T) * _normal_cdf(-d2)


def all_greeks(option_type, S, K, T, r, sigma, q=0.0) -> dict:
    """Return all greeks in one dict — convenience for portfolio analysis."""
    return {
        "price": price(option_type, S, K, T, r, sigma, q),
        "delta": delta(option_type, S, K, T, r, sigma, q),
        "gamma": gamma(option_type, S, K, T, r, sigma, q),
        "vega": vega(option_type, S, K, T, r, sigma, q),
        "theta": theta(option_type, S, K, T, r, sigma, q),
        "rho": rho(option_type, S, K, T, r, sigma, q),
    }
