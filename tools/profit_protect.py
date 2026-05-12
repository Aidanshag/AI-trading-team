"""Trailing-profit-lock + gain/loss hard-cap protection for open positions.

Extracted as a tool module (2026-05-11 evening) per the "trim the knife"
directive — the trader (`scripts/live_trader.py`) keeps only the call site;
all tier logic / high-water tracking / P&L math lives here.

WHY IT EXISTS:
Live execution today operates with `SKIP_TARGET_LEG=True` (workaround for
broker target-fill anomaly — see
vault/research/analysis/2026-05-11_broker_target_fill_anomaly.md). Without
target legs at the broker, profits can run unbounded UNTIL stop fires OR
something software-side closes the position. This module is that
something. The rule "never let a gain become a loss" is user-stated.

TIER SEMANTICS:
Each tier is `(peak_threshold_usd, floor_usd)`. Once a position's PEAK
unrealized P&L crosses `peak_threshold`, the floor is engaged: if current
unrealized DROPS to or below `floor`, market-close the position
immediately. Tiers are checked highest-first so the tightest active tier
wins.

  Default tiers (mirrored from `scripts/auto_trader.py` 2026-05-08):
    (400, 200)   # at +$400 peak, lock in +$200 minimum
    (250, 100)   # at +$250 peak, lock in +$100 minimum
    (150,  50)
    ( 80,  20)
    ( 30,   0)   # at +$30 peak, never let it become a loss

GAIN-SIDE HARD CAP (`GAIN_TIER_HARD_CAP_USD`):
Unconditional market-close when unrealized exceeds this. Stops a runaway
winner from reversing on overnight news/gaps. Default $400 (matches the
top trailing tier's threshold — at +$400 we'd rather take it now).

USAGE (from live_trader.py):
    from tools.profit_protect import check_and_close
    closed = check_and_close(client, account_id, log_fn=_log)
"""
from __future__ import annotations

import time
import uuid
from typing import Callable

# ── Configuration ──────────────────────────────────────────────

TRAILING_PROFIT_TIERS: tuple[tuple[float, float], ...] = (
    # (peak_threshold_usd, floor_usd) — order doesn't matter, decide()
    # picks the highest-active tier. 2026-05-11 evening expansion: added
    # runner-zone tiers (>$400 peak) after the +$2,616 GC trade revealed
    # the prior cap was clipping runners. Floors at 50-65% of peak in
    # the runner zone.
    # --- tight tiers (small/medium winners — never give back too much)
    ( 30.0,     0.0),    # never let a +$30 gain become a loss
    ( 80.0,    20.0),
    (150.0,    50.0),
    (250.0,   100.0),
    (400.0,   200.0),
    # --- runner zone (allow big winners to breathe)
    (750.0,   400.0),
    (1500.0,  900.0),
    (2500.0, 1500.0),
    (5000.0, 3000.0),
    (10000.0, 6500.0),
)

# 2026-05-11: hard cap REMOVED (set to None) per user direction. The old
# $400 cap would have force-closed today's GC trade at $400 instead of
# letting it run to +$2,616. With expanded runner-zone tiers above,
# trailing-lock is sufficient protection without a fixed ceiling.
GAIN_TIER_HARD_CAP_USD: float | None = None
LOSS_TIER_HARD_CAP_USD: float = 150.0   # belt-and-suspenders for broker stop

# Per-position high-water mark (process-local; resets on trader restart).
# Key: "SYMBOL_SIDE". Value: peak unrealized $ seen this session.
_position_high_water: dict[str, float] = {}


# ── Symbol parsing helpers ────────────────────────────────────

def _contract_to_symbol(contract_id: str) -> str | None:
    """Pick the symbol token out of a ProjectX contract id like
    'CON.F.US.GCE.M26'. Skip prefixes and month codes."""
    for tok in contract_id.split("."):
        if tok in ("CON", "F", "US", ""):
            continue
        if len(tok) <= 3 and tok and tok[0].isalpha() and tok[1:].isdigit():
            continue  # month code like 'M26'
        return tok
    return None


def _strip_exchange_suffix(sym: str) -> str:
    """Normalize 'GCE' → 'GC', 'NGE' → 'NG', etc. ProjectX uses 'E' suffix
    for some products."""
    if len(sym) > 2 and sym.endswith("E") and sym[:-1] in ("GC", "NG", "CL", "SI"):
        return sym[:-1]
    return sym


# ── Tick economics (kept lightweight; mirrors live_trader fallback) ─

_TICK_ECONOMICS: dict[str, tuple[float, float]] = {
    "ZN": (0.015625, 15.625), "ZB": (0.03125, 31.25),
    "ZT": (0.0078125, 15.625), "ZF": (0.0078125, 7.8125),
    "NG": (0.001, 10.0),
    "GC": (0.10, 10.0), "SI": (0.005, 25.0), "HG": (0.0005, 12.5),
    "MES": (0.25, 1.25), "MNQ": (0.25, 0.50),
    "ES": (0.25, 12.50), "NQ": (0.25, 5.00),
    "MCL": (0.01, 1.00), "CL": (0.01, 10.00),
    "6E": (0.00005, 6.25), "6B": (0.0001, 6.25),
    "6J": (0.0000005, 6.25), "6A": (0.0001, 10.00), "6C": (0.0001, 10.00),
}


# ── Decision logic (pure) ─────────────────────────────────────

def decide(unrealized: float, prev_peak: float,
            tiers: tuple[tuple[float, float], ...] = TRAILING_PROFIT_TIERS,
            gain_cap: float | None = GAIN_TIER_HARD_CAP_USD,
            loss_cap: float = LOSS_TIER_HARD_CAP_USD,
            ) -> tuple[bool, str]:
    """Pure decision function — returns (should_close, reason).
    No broker IO; easy to unit-test.

    Closure rules (checked in order):
      1. Loss hard cap: unrealized <= -loss_cap → close (backstop)
      2. Gain hard cap: unrealized >= gain_cap → close (if cap is not None)
      3. Trailing tiers: among tiers whose peak_threshold the position
         has crossed, the TIGHTEST floor (highest floor) wins. Close iff
         current unrealized < that floor.
    """
    if gain_cap is not None and unrealized >= gain_cap:
        return True, f"hard_cap: unrealized ${unrealized:.2f} >= ${gain_cap:.0f}"
    if unrealized <= -loss_cap:
        return True, (f"loss_hard_cap: unrealized ${unrealized:.2f} "
                       f"<= -${loss_cap:.0f} (broker stop backstop)")
    # Among crossed tiers, pick the one with the highest floor (tightest
    # protection wins).
    active_floor: float | None = None
    active_peak: float | None = None
    for peak_threshold, floor in tiers:
        if prev_peak >= peak_threshold:
            if active_floor is None or floor > active_floor:
                active_floor = floor
                active_peak = peak_threshold
    if active_floor is not None and unrealized < active_floor:
        return True, (f"trailing_lock: peak ${prev_peak:.2f} crossed "
                       f"${active_peak:.0f}, current ${unrealized:.2f} "
                       f"fell below floor ${active_floor:.0f}")
    return False, ""


def _unrealized_usd(side: str, size: int, avg_price: float,
                     last_price: float, tick_size: float,
                     tick_value: float) -> float:
    move = (last_price - avg_price) if side == "long" else (avg_price - last_price)
    ticks = move / tick_size
    return ticks * tick_value * abs(size)


# ── Main entrypoint ───────────────────────────────────────────

def check_and_close(client, account_id, log_fn: Callable[[str], None] | None = None,
                     fetch_bars_fn: Callable | None = None) -> list[dict]:
    """For each open position, check trailing-profit-lock + hard caps. If a
    rule triggers, market-close the position at the broker.

    `client` must implement: get_positions, place_order.
    `fetch_bars_fn` optional: callable(client, symbol, minutes, lookback)
    returning a DataFrame with 'Close' column. If omitted, uses
    tools/bar_fetcher.fetch_bars.

    Returns list of closure records: [{symbol, side, size, unrealized, reason}].
    """
    log = log_fn if log_fn is not None else (lambda _msg: None)
    closed: list[dict] = []
    try:
        positions = client.get_positions(account_id) or []
    except Exception as e:
        log(f"  profit_protect: get_positions failed: {type(e).__name__}: {e}")
        return closed

    for p in positions:
        try:
            size = int(p.get("size") or 0)
            if size == 0:
                continue
            contract_id = str(p.get("contractId") or "")
            if not contract_id:
                continue
            avg_price = float(p.get("averagePrice") or 0)
            if avg_price <= 0:
                continue
            type_code = int(p.get("type") or 0)
            side = "long" if type_code == 1 else "short" if type_code == 2 else (
                "long" if size > 0 else "short")
            size = abs(size)
            raw_sym = _contract_to_symbol(contract_id) or ""
            symbol = _strip_exchange_suffix(raw_sym)
            if not symbol:
                continue
            tick_size, tick_value = _TICK_ECONOMICS.get(symbol, (0.0, 0.0))
            if tick_size <= 0 or tick_value <= 0:
                continue

            # Latest mark via 1-min bars (cheap; usually cached)
            if fetch_bars_fn is None:
                from tools.bar_fetcher import fetch_bars as _fb
                bars = _fb(client, symbol, 1, 5)
            else:
                bars = fetch_bars_fn(client, symbol, 1, 5)
            if bars is None or len(bars) == 0:
                continue
            last_close = float(bars["Close"].iloc[-1])

            unrealized = _unrealized_usd(side, size, avg_price, last_close,
                                          tick_size, tick_value)
            key = f"{symbol}_{side}"
            prev_peak = _position_high_water.get(key, 0.0)
            if unrealized > prev_peak:
                _position_high_water[key] = unrealized
                prev_peak = unrealized

            should_close, reason = decide(unrealized, prev_peak)
            if not should_close:
                continue

            # Market-close
            opposite = "sell" if side == "long" else "buy"
            cid = f"profitlock_{int(time.time())}_{uuid.uuid4().hex[:6]}"
            try:
                client.place_order(
                    account_id=account_id, contract_id=contract_id,
                    side=opposite, qty=int(size), order_type="market",
                    time_in_force="ioc", client_order_id=cid,
                )
                log(f"  PROFIT_LOCK_CLOSE: {symbol} {side} {size}ct "
                     f"unrealized=${unrealized:+.2f} peak=${prev_peak:+.2f} "
                     f"-- {reason}")
                _position_high_water.pop(key, None)
                closed.append({"symbol": symbol, "side": side, "size": size,
                                "unrealized": unrealized, "peak": prev_peak,
                                "reason": reason})
            except Exception as e:
                log(f"  profit_lock_close FAILED {symbol}: "
                     f"{type(e).__name__}: {e}")
        except Exception as e:
            log(f"  profit_protect inner error on {p.get('contractId','?')}: "
                 f"{type(e).__name__}: {e}")
            continue
    return closed
