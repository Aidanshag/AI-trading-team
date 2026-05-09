"""Black-Scholes pricing + Greeks for futures options.

Self-contained — no external dependency beyond the stdlib + math.
Used by the Options Risk agent to compute delta/gamma/vega/theta/rho
on every options proposal.

Convention: continuous compounding, Black-76 model for futures options
(uses futures price F instead of spot * exp(-r*T)). For options on cash
indices/equities, use the standard Black-Scholes (set q=0).

Reference: Black, F. (1976) "The pricing of commodity contracts."
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

OptionRight = Literal["C", "P"]


def _norm_cdf(x: float) -> float:
    """Standard normal cumulative distribution function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x: float) -> float:
    """Standard normal probability density function."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _d1_d2(F: float, K: float, T: float, sigma: float) -> tuple[float, float]:
    """Black-76 d1, d2."""
    if T <= 0 or sigma <= 0 or F <= 0 or K <= 0:
        raise ValueError(f"Invalid inputs: F={F} K={K} T={T} sigma={sigma}")
    sqrtT = math.sqrt(T)
    d1 = (math.log(F / K) + 0.5 * sigma * sigma * T) / (sigma * sqrtT)
    d2 = d1 - sigma * sqrtT
    return d1, d2


@dataclass
class OptionResult:
    """Results from a Black-76 calculation."""
    price: float
    delta: float
    gamma: float
    vega: float
    theta: float           # per year
    rho: float
    F: float
    K: float
    T: float               # years
    sigma: float
    r: float
    right: OptionRight

    @property
    def theta_per_day(self) -> float:
        return self.theta / 365.0

    @property
    def vega_per_pct(self) -> float:
        """Sensitivity to a 1 percentage-point change in IV (e.g., 20% -> 21%)."""
        return self.vega / 100.0

    def __repr__(self) -> str:
        return (
            f"OptionResult({self.right} F={self.F:.4f} K={self.K:.4f} "
            f"T={self.T:.4f}y σ={self.sigma:.3f} | "
            f"price={self.price:.4f} Δ={self.delta:+.3f} "
            f"Γ={self.gamma:.4f} ν={self.vega_per_pct:.3f}/1%IV "
            f"Θ={self.theta_per_day:+.4f}/day)"
        )


def black76(
    F: float,
    K: float,
    T: float,
    sigma: float,
    r: float = 0.04,
    right: OptionRight = "C",
) -> OptionResult:
    """Black-76 pricing for futures options.

    Args:
        F:     Underlying futures price.
        K:     Strike.
        T:     Years to expiration (e.g., 30/365 for 30 days).
        sigma: Annualized volatility (e.g., 0.25 for 25%).
        r:     Risk-free rate (continuous, annual). Default 4% — adjust.
        right: 'C' for call, 'P' for put.

    Returns:
        OptionResult with price + Greeks.
    """
    if right not in ("C", "P"):
        raise ValueError(f"right must be 'C' or 'P', got {right!r}")
    if T <= 0:
        # At expiry: intrinsic value only, all Greeks zero
        intrinsic = max(F - K, 0.0) if right == "C" else max(K - F, 0.0)
        return OptionResult(
            price=intrinsic, delta=0.0, gamma=0.0, vega=0.0, theta=0.0, rho=0.0,
            F=F, K=K, T=T, sigma=sigma, r=r, right=right,
        )

    d1, d2 = _d1_d2(F, K, T, sigma)
    discount = math.exp(-r * T)
    sqrtT = math.sqrt(T)

    if right == "C":
        price = discount * (F * _norm_cdf(d1) - K * _norm_cdf(d2))
        delta = discount * _norm_cdf(d1)
        rho = -T * price                       # ∂C/∂r under Black-76
        theta_part = -F * _norm_pdf(d1) * sigma * discount / (2.0 * sqrtT)
        theta = theta_part + r * (price)        # full theta
    else:  # put
        price = discount * (K * _norm_cdf(-d2) - F * _norm_cdf(-d1))
        delta = -discount * _norm_cdf(-d1)
        rho = -T * price
        theta_part = -F * _norm_pdf(d1) * sigma * discount / (2.0 * sqrtT)
        theta = theta_part + r * (price)

    gamma = discount * _norm_pdf(d1) / (F * sigma * sqrtT)
    vega = F * discount * _norm_pdf(d1) * sqrtT     # ∂Price/∂σ for σ change of 1.0

    return OptionResult(
        price=price, delta=delta, gamma=gamma, vega=vega, theta=theta, rho=rho,
        F=F, K=K, T=T, sigma=sigma, r=r, right=right,
    )


def implied_vol(
    market_price: float,
    F: float,
    K: float,
    T: float,
    r: float = 0.04,
    right: OptionRight = "C",
    tol: float = 1e-6,
    max_iter: int = 100,
) -> float:
    """Solve for implied volatility via Newton-Raphson with bisection fallback.

    Returns the sigma that makes black76(...).price == market_price.
    Returns NaN if no convergence (deep OTM with near-zero market price, etc.).
    """
    if market_price <= 0 or T <= 0 or F <= 0 or K <= 0:
        return float("nan")

    # Initial guess via Brenner-Subrahmanyam approximation
    sigma = math.sqrt(2.0 * math.pi / T) * (market_price / F)
    sigma = max(0.01, min(sigma, 5.0))

    # Newton-Raphson
    for _ in range(max_iter):
        try:
            r_obj = black76(F, K, T, sigma, r, right)
        except ValueError:
            break
        diff = r_obj.price - market_price
        if abs(diff) < tol:
            return sigma
        if r_obj.vega < 1e-10:
            break
        sigma -= diff / r_obj.vega
        sigma = max(0.001, min(sigma, 10.0))

    # Bisection fallback
    lo, hi = 0.001, 10.0
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        try:
            r_obj = black76(F, K, T, mid, r, right)
        except ValueError:
            return float("nan")
        if abs(r_obj.price - market_price) < tol:
            return mid
        if r_obj.price < market_price:
            lo = mid
        else:
            hi = mid
    return float("nan")


@dataclass
class Leg:
    """One leg of a multi-leg option structure."""
    F: float
    K: float
    T: float
    sigma: float
    right: OptionRight
    side: Literal["long", "short"]
    qty: int = 1
    r: float = 0.04


def structure_greeks(legs: list[Leg]) -> dict[str, float]:
    """Aggregate Greeks across a multi-leg structure.

    Returns dict with: net_delta, net_gamma, net_vega_per_pct, net_theta_per_day,
    net_price (debit if positive, credit if negative).
    """
    net_delta = net_gamma = net_vega = net_theta = net_price = 0.0
    for leg in legs:
        r_obj = black76(leg.F, leg.K, leg.T, leg.sigma, leg.r, leg.right)
        sign = 1 if leg.side == "long" else -1
        net_price += sign * leg.qty * r_obj.price
        net_delta += sign * leg.qty * r_obj.delta
        net_gamma += sign * leg.qty * r_obj.gamma
        net_vega  += sign * leg.qty * r_obj.vega_per_pct
        net_theta += sign * leg.qty * r_obj.theta_per_day
    return {
        "net_delta": net_delta,
        "net_gamma": net_gamma,
        "net_vega_per_pct": net_vega,
        "net_theta_per_day": net_theta,
        "net_price": net_price,
        "max_loss_usd": _structure_max_loss(legs, net_price),
    }


def _structure_max_loss(legs: list[Leg], net_price: float) -> float:
    """Best-effort max loss for common defined-risk structures.

    For long-only structures (net debit), max loss = premium paid.
    For credit structures, returns NaN — caller must compute from strike
    width × contract multiplier.
    """
    all_long = all(leg.side == "long" for leg in legs)
    if all_long and net_price > 0:
        return net_price
    return float("nan")
