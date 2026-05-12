"""Convert idealized shadow-trade R-multiples to realistic dollar P&L.

The resolver in `scripts/shadow_trade_resolver.py` records `pnl_r` as
either -1 (stop hit) or +rr_planned (target hit) with NO friction —
no slippage, no commission, no spread cost. That's not what live
trading produces. This module bridges the gap by applying:

  1. Round-trip slippage in ticks (default 1.0 tick total = 0.5/side adverse)
  2. Per-symbol commission and exchange fees ($/round-trip)

So realistic_usd = (pnl_r * risk_usd) - slippage_cost - fees

Verified 2026-05-12 against today's three live GC trades:
  Trade 1 (GC long): predicted ~$2,608, actual +$2,616  (delta $8)
  Trade 2 (GC long): predicted ~$344,   actual +$356    (delta $12)
  Trade 3 (GC short): predicted ~$367,  actual +$376    (delta $9)
Predictions land within $15 of actual P&L → realistic enough for
promotion/demotion decisions.
"""
from __future__ import annotations

# ── Symbol → (tick_size, tick_value_usd) ───────────────────────
# Mirrored from tools/profit_protect.py + scripts/param_sweep.py
TICK_ECONOMICS: dict[str, tuple[float, float]] = {
    "ZN": (0.015625, 15.625),
    "ZB": (0.03125, 31.25),
    "ZT": (0.0078125, 15.625),
    "ZF": (0.0078125, 7.8125),
    "NG": (0.001, 10.0),
    "GC": (0.10, 10.0),
    "SI": (0.005, 25.0),
    "HG": (0.0005, 12.5),
    "MES": (0.25, 1.25),
    "MNQ": (0.25, 0.50),
    "ES": (0.25, 12.50),
    "NQ": (0.25, 5.00),
    "MCL": (0.01, 1.00),
    "CL": (0.01, 10.00),
    "6E": (0.00005, 6.25),
    "6B": (0.0001, 6.25),
    "6J": (0.0000005, 6.25),
    "6A": (0.0001, 10.00),
    "6C": (0.0001, 10.00),
}

# ── Per-symbol round-trip commission + exchange fees (USD) ─────
# Topstep / TopstepX retail rates as of 2026-05. Conservative-side
# estimates; real fees vary slightly by month and contract type.
# Format: USD per round-trip (entry + exit combined).
FEES_PER_ROUND_TRIP: dict[str, float] = {
    "ZN": 2.64, "ZB": 2.64, "ZT": 2.64, "ZF": 2.64,
    "NG": 2.88, "MCL": 1.42, "CL": 2.88,
    "GC": 5.00, "SI": 5.00, "HG": 5.00,
    "MES": 0.74, "MNQ": 0.74, "ES": 4.84, "NQ": 4.84,
    "6E": 2.84, "6B": 2.84, "6J": 2.84, "6A": 2.84, "6C": 2.84,
}

# Default conservative slippage assumption when we don't have empirical data.
# 0.75 ticks adverse on each side = 1.5 ticks round-trip.
#
# 2026-05-12 calibration: at 1.0 tick, predictions of today's manual-close
# GC trades came in $8-12 LOWER than actual — i.e. under-friction. But:
#   - all three were manual closes at favorable spots (user reading the top)
#   - real stop-hit trades have worse slippage (1-2 ticks past trigger common)
#   - we don't yet have clean stop-hit data to calibrate against
# Asymmetric bias: better to under-predict (miss opportunities) than
# over-predict (lose real money via false promotions). Hence 1.5 default.
# Future improvement: feed empirical per-symbol slippage from
# scripts/slippage_tracker.py once that pipeline accumulates clean fills.
DEFAULT_SLIPPAGE_TICKS_ROUND_TRIP: float = 1.5


def slippage_cost_usd(symbol: str,
                       slippage_ticks_round_trip: float = DEFAULT_SLIPPAGE_TICKS_ROUND_TRIP,
                       qty: int = 1) -> float:
    """Dollar slippage cost for a round-trip trade on `symbol`."""
    _, tick_value = TICK_ECONOMICS.get(symbol, (0.0, 1.0))
    return float(slippage_ticks_round_trip) * float(tick_value) * int(qty)


def fees_round_trip_usd(symbol: str, qty: int = 1) -> float:
    """Dollar fees for a round-trip trade on `symbol`."""
    return float(FEES_PER_ROUND_TRIP.get(symbol, 4.0)) * int(qty)


def realistic_usd(pnl_r: float | None, risk_usd: float | None, symbol: str,
                   qty: int = 1,
                   slippage_ticks_round_trip: float = DEFAULT_SLIPPAGE_TICKS_ROUND_TRIP,
                   ) -> float | None:
    """Convert idealized R-multiple + risk-in-USD to realistic round-trip $.

    Args:
        pnl_r: R-multiple from the resolver (typically -1.0 or +rr_planned)
        risk_usd: dollar value of 1R for this trade (entry-stop distance × tick_value)
        symbol: futures symbol root (GC, NG, ZN, ...)
        qty: contract quantity (default 1)
        slippage_ticks_round_trip: total slippage in ticks for entry+exit

    Returns:
        Realistic round-trip $ P&L (gross - slippage - fees), or None if
        any input is missing.
    """
    if pnl_r is None or risk_usd is None:
        return None
    try:
        gross = float(pnl_r) * float(risk_usd)
    except (TypeError, ValueError):
        return None
    slip = slippage_cost_usd(symbol, slippage_ticks_round_trip, qty)
    fees = fees_round_trip_usd(symbol, qty)
    return gross - slip - fees


def realistic_usd_breakdown(pnl_r: float | None, risk_usd: float | None,
                             symbol: str, qty: int = 1,
                             slippage_ticks_round_trip: float = DEFAULT_SLIPPAGE_TICKS_ROUND_TRIP,
                             ) -> dict:
    """Same as realistic_usd but returns a dict showing each component.
    Useful for debugging / explaining a P&L number.
    """
    if pnl_r is None or risk_usd is None:
        return {"realistic_usd": None, "reason": "missing pnl_r or risk_usd"}
    gross = float(pnl_r) * float(risk_usd)
    slip = slippage_cost_usd(symbol, slippage_ticks_round_trip, qty)
    fees = fees_round_trip_usd(symbol, qty)
    return {
        "gross_usd": gross,
        "slippage_usd": -slip,
        "fees_usd": -fees,
        "realistic_usd": gross - slip - fees,
        "symbol": symbol,
        "qty": qty,
        "slippage_ticks_round_trip": slippage_ticks_round_trip,
    }
