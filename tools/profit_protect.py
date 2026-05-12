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
from datetime import datetime, timezone
from typing import Callable

# ── Configuration ──────────────────────────────────────────────

TRAILING_PROFIT_TIERS: tuple[tuple[float, float], ...] = (
    # (peak_threshold_usd, floor_usd) — order doesn't matter, decide()
    # picks the highest-active floor. Trades stack: as peak grows, tighter
    # higher-floor tiers progressively replace looser low-floor tiers.
    #
    # 2026-05-12: added MICRO tiers below $30 after exec_mirror analysis
    # showed cells with target=$30-50 were getting clipped at $0 (break-
    # even minus friction) instead of locking a small positive. The
    # (15, 5) and (25, 12) tiers force closes to lock a small positive
    # on retrace from low peaks. (30, 0) is retained for clarity but is
    # dominated by (25, 12) above $25 peak. The user's "let runners run"
    # is preserved — once peak >= $80 the original tier ladder takes
    # over and the micro tiers become irrelevant.
    # --- micro tiers (NEW 2026-05-12) — lock small wins, don't clip runners
    ( 15.0,     5.0),    # peak $15 → lock $5 (small-quick-win protection)
    ( 25.0,    12.0),    # peak $25 → lock $12 (closes the $30-$79 gap zone)
    # --- 2026-05-11 expansion: runner-zone tiers (>$400 peak) after the
    # +$2,616 GC trade revealed the prior cap was clipping runners.
    # --- tight tiers (small/medium winners — never give back too much)
    ( 30.0,     0.0),    # original "never let +$30 become a loss"
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

# Per-position agent-veto state (process-local).
# `_position_consecutive_holds`: how many times the agent has held this position
# in a row. Resets on close or on a CLOSE decision.
# `_position_entry_ts_seen`: first time we saw this position in this process.
# Used as a proxy for entry_ts (we don't have the real fill time without an
# extra DB lookup). Resets on close.
_position_consecutive_holds: dict[str, int] = {}
_position_entry_ts_seen: dict[str, datetime] = {}


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


# ── Agent-veto helpers ────────────────────────────────────────

_EXIT_REASONER_CONFIG_PATH = "config/exit_reasoner.yaml"


def _load_exit_reasoner_config() -> dict:
    """Return the feature-flag config. Disabled-everything on any error."""
    try:
        import yaml
        from pathlib import Path
        path = Path(__file__).resolve().parent.parent / _EXIT_REASONER_CONFIG_PATH
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {"enabled": False}


def _is_agent_enabled_for_cell(symbol: str, side: str,
                                 strategy: str | None) -> bool:
    """True iff this (strategy, symbol, side) is routed through the agent."""
    cfg = _load_exit_reasoner_config()
    if not cfg.get("enabled"):
        return False
    cell_key = f"{strategy or '*'}/{symbol}/{side}"
    denied = cfg.get("denied_cells") or []
    for d in denied:
        if d == cell_key or d == "*":
            return False
    enabled_cells = cfg.get("enabled_cells") or []
    if "*" in enabled_cells:
        return True
    for c in enabled_cells:
        if c == cell_key:
            return True
        # Allow "*/SYMBOL/side" wildcard
        if "*" in c and _wildcard_match(c, cell_key):
            return True
    return False


def _wildcard_match(pattern: str, key: str) -> bool:
    """Simple wildcard match — '*' matches a whole segment."""
    p_parts = pattern.split("/")
    k_parts = key.split("/")
    if len(p_parts) != len(k_parts):
        return False
    return all(p == "*" or p == k for p, k in zip(p_parts, k_parts))


def _parse_trailing_lock_floor(reason: str) -> float | None:
    """Extract the `floor $X` value from decide()'s reason string. Returns
    None if not a trailing_lock reason or parse fails."""
    if "trailing_lock" not in reason:
        return None
    import re
    m = re.search(r"floor \$(-?\d+(?:\.\d+)?)", reason)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _bars_df_to_dicts(bars_df) -> list[dict]:
    """Convert the pandas DataFrame returned by fetch_bars to a list of
    dicts suitable for the agent prompt. Last 20 bars, oldest first."""
    if bars_df is None or len(bars_df) == 0:
        return []
    out = []
    tail = bars_df.tail(20)
    for ts, row in tail.iterrows():
        try:
            ts_iso = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
            out.append({
                "t": ts_iso,
                "o": float(row.get("Open") or row.get("open") or 0),
                "h": float(row.get("High") or row.get("high") or 0),
                "l": float(row.get("Low") or row.get("low") or 0),
                "c": float(row.get("Close") or row.get("close") or 0),
            })
        except Exception:
            continue
    return out


def _open_db_connection():
    """Open a connection to fund.db for agent_exit_vetoes logging."""
    try:
        import sqlite3
        from pathlib import Path
        path = Path(__file__).resolve().parent.parent / "state" / "fund.db"
        return sqlite3.connect(str(path), timeout=5.0)
    except Exception:
        return None


# ── Main entrypoint ───────────────────────────────────────────

def check_and_close(client, account_id, log_fn: Callable[[str], None] | None = None,
                     fetch_bars_fn: Callable | None = None,
                     strategy_lookup_fn: Callable | None = None) -> list[dict]:
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
                # Reset consecutive_holds when the rule no longer wants to close
                _position_consecutive_holds.pop(key, None)
                continue

            # ── Agent veto layer (Phase 1b 2026-05-12) ──
            # ONLY trailing_lock reasons route through the agent. Loss caps,
            # gain caps, and any unknown reason remain mechanical.
            tier_floor = _parse_trailing_lock_floor(reason)
            strategy = None
            if strategy_lookup_fn is not None:
                try:
                    strategy = strategy_lookup_fn(symbol, side, contract_id)
                except Exception:
                    strategy = None

            if tier_floor is not None and _is_agent_enabled_for_cell(
                    symbol, side, strategy):
                # Mark / refresh entry-ts proxy
                if key not in _position_entry_ts_seen:
                    _position_entry_ts_seen[key] = datetime.now(tz=timezone.utc)

                cfg = _load_exit_reasoner_config()
                report_only = bool(cfg.get("report_only", True))

                try:
                    from tools.exit_reasoner import (
                        decide_exit_with_agent, TradeContext,
                    )
                    bar_dicts = _bars_df_to_dicts(bars)
                    ctx = TradeContext(
                        symbol=symbol, side=side, strategy=strategy,
                        contract_id=contract_id,
                        entry_price=avg_price,
                        entry_ts=_position_entry_ts_seen[key],
                        avg_fill_price=avg_price,
                        current_price=last_close,
                        peak_unrealized_usd=prev_peak,
                        current_unrealized_usd=unrealized,
                        tier_floor_usd=tier_floor,
                        risk_usd=0.0,        # not used in prompt-only flow
                        recent_bars=bar_dicts,
                        regime={},           # filled by caller if available
                        consecutive_holds=_position_consecutive_holds.get(key, 0),
                    )
                    db = _open_db_connection()
                    try:
                        decision = decide_exit_with_agent(
                            ctx, db_conn=db, log_fn=log, enabled=True,
                        )
                    finally:
                        if db is not None:
                            try: db.close()
                            except Exception: pass

                    if decision.action == "HOLD" and not report_only:
                        _position_consecutive_holds[key] = (
                            _position_consecutive_holds.get(key, 0) + 1
                        )
                        log(f"  AGENT_HOLD: {symbol} {side} peak=${prev_peak:.0f} "
                             f"cur=${unrealized:+.0f} -- {decision.reason} "
                             f"(holds={_position_consecutive_holds[key]})")
                        continue   # skip close this iteration
                    elif decision.action == "HOLD" and report_only:
                        log(f"  AGENT_HOLD (report-only, closing anyway): {symbol} "
                             f"{side} peak=${prev_peak:.0f} -- {decision.reason}")
                    # else: CLOSE or FALLBACK_CLOSE → proceed to market close
                    _position_consecutive_holds.pop(key, None)
                except Exception as e:
                    log(f"  exit_reasoner threw — falling back to rigid close: "
                         f"{type(e).__name__}: {e}")
                    # Fall through to mechanical close below

            # ── Mechanical market-close ──
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
                _position_consecutive_holds.pop(key, None)
                _position_entry_ts_seen.pop(key, None)
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
