"""Deterministic auto-trader — bypasses the Claude SDK for trigger evaluation.

WHY THIS EXISTS:
The orchestrator's wake_agent flow depends on the Claude Agent SDK
spawning the claude.exe CLI as a subprocess. On this machine, that
subprocess fork has been failing intermittently (FileNotFoundError on
the CLI binary, despite the file existing). Detection of trigger
conditions (Bollinger squeeze, ORB, RSI2, Donchian, vol spike, etc.)
is pure math on OHLCV bars — it doesn't need an LLM.

This script runs the full strategy library directly in Python, applies
the SAME risk hook checks the SDK chain would, and places real orders
through the existing topstep/ProjectX integration. It produces real
trades and real data, today.

LLM use is reserved for what LLMs are uniquely good at: regime reads,
post-mortems, the weekly review. None of that is needed for the
trigger phase.

USAGE:
    python -m scripts.auto_trader            # live, focus universe
    python -m scripts.auto_trader --once     # one scan and exit (debug)
    python -m scripts.auto_trader --dry-run  # find triggers, don't place

Environment:
    FUND_MODE=live      # if 'paper', no orders are placed
    PROJECTX_*          # required for live broker calls
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from dotenv import load_dotenv
load_dotenv()

# Ensure cwd resolves project paths regardless of where the script was launched
_HERE = Path(__file__).resolve().parent.parent
os.chdir(_HERE)

from state.db import get_db, utcnow_iso
from tools.projectx_client import ProjectXError, get_account_id, get_client
from tools.backtest import strategies as strats
from hooks.risk_gate import (
    _check_kill_switch, _check_focus_universe, _check_strategy_blacklist,
    _check_active_lessons, _check_post_stop_cooldown, _check_high_impact_blackout,
    _check_combine_defensive_ladder, _check_daily_target_lock,
    _check_daily_trade_count, _check_session_window,
    _check_no_naked_shorts, _check_stop_required, _check_per_symbol_limits,
    _check_sector_and_basket_limits, _load_yaml,
)


# ── Strategy roster (ordered by what we trust) ───────────────
# Each tuple: (callable, default kwargs, conviction floor, label)
# We try strategies in this order; first trigger wins per symbol per scan.
STRATEGY_ROSTER: list[tuple[Any, dict, str, str]] = [
    # Highest priority: classic mean-reversion + breakout combos with
    # strong literature priors (Connors RSI2, Donchian, NR7, Bollinger squeeze)
    (strats.rsi2_extreme_reversion, {}, "med", "rsi2_extreme_reversion"),
    (strats.bollinger_squeeze_break, {}, "med", "bollinger_squeeze_break"),
    (strats.narrow_range_break, {}, "med", "narrow_range_break"),
    (strats.donchian_breakout, {}, "low", "donchian_breakout"),
    (strats.vol_regime_trend, {}, "med", "vol_regime_trend"),
    (strats.keltner_breakout, {}, "low", "keltner_breakout"),
    (strats.bollinger_mean_reversion, {}, "low", "bollinger_mean_reversion"),
    (strats.range_mean_reversion, {}, "low", "range_mean_reversion"),
    (strats.inside_bar_break, {}, "low", "inside_bar_break"),
    (strats.vol_spike_fade, {}, "low", "vol_spike_fade"),
    (strats.pullback_in_trend, {}, "low", "pullback_in_trend"),
    (strats.volatility_breakout, {}, "low", "volatility_breakout"),
    (strats.support_resistance_bounce, {}, "low", "support_resistance_bounce"),
    (strats.vwap_reversion, {}, "low", "vwap_reversion"),
    (strats.volume_spike_reversal, {}, "low", "volume_spike_reversal"),
    (strats.gap_fill, {}, "low", "gap_fill"),
    (strats.pivot_reversal, {}, "low", "pivot_reversal"),
    # ORB excluded — strategy_blacklist already vetoes ZN+ORB and NG+ORB
    # but we keep it last so it can fire on MES/GC/6E if no other does
    (strats.opening_range_breakout, {}, "low", "opening_range_breakout"),
]


CONVICTION_RR_FLOOR = {"high": 1.5, "med": 2.0, "low": 2.5, "validation": 1.5}


# ── Bar fetching ─────────────────────────────────────────────

def fetch_bars(client, symbol: str, *, minutes: int = 5, lookback: int = 200) -> pd.DataFrame | None:
    """Fetch the last `lookback` bars at `minutes`-minute resolution.

    Returns a pd.DataFrame with the same columns the strategies expect:
    Open, High, Low, Close, Volume, indexed by timestamp.
    """
    try:
        contracts = client.search_contracts(symbol, live=False)
        if not contracts:
            return None
        front = sorted(contracts,
                       key=lambda c: c.get("expiryDate") or c.get("lastTradeDate") or "")[0]
        cid = front.get("id") or front.get("contractId")
        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(minutes=minutes * lookback * 2)
        bars = client.get_bars(
            contract_id=cid,
            start_time=start.isoformat(),
            end_time=end.isoformat(),
            unit=2, unit_number=minutes, limit=lookback,
            live=False,
        )
        if not bars:
            return None
        df = pd.DataFrame(bars)
        # ProjectX field names: t, o, h, l, c, v
        rename = {"t": "Date", "o": "Open", "h": "High",
                  "l": "Low", "c": "Close", "v": "Volume"}
        df = df.rename(columns=rename)
        if "Date" not in df.columns:
            return None
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()
        for col in ("Open", "High", "Low", "Close", "Volume"):
            if col not in df.columns:
                return None
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df.dropna()
    except Exception as e:
        print(f"  [fetch_bars] {symbol}: {type(e).__name__}: {e}")
        return None


def find_latest_signal(bars: pd.DataFrame, strategy_fn, **kwargs) -> dict | None:
    """Run a strategy on the bars; return the LAST entry signal if any
    fired in the most recent 3 bars (i.e., still actionable)."""
    if len(bars) < 30:
        return None
    last_idx = bars.index[-1]
    cutoff = bars.index[-3] if len(bars) >= 3 else bars.index[0]
    latest = None
    try:
        for sig in strategy_fn(bars, **kwargs):
            if sig.kind != "entry":
                continue
            if sig.date >= cutoff:
                latest = sig
    except Exception as e:
        return None
    if latest is None:
        return None
    return {
        "date": latest.date, "side": latest.side, "price": float(latest.price),
        "stop": float(latest.stop) if latest.stop is not None else None,
        "target": float(latest.target) if latest.target is not None else None,
        "reason": latest.reason,
    }


# ── Risk gate (manual application) ───────────────────────────

ACTIVE_RISK_CHECKS = [
    ("kill_switch", _check_kill_switch),
    ("focus_universe", _check_focus_universe),
    ("strategy_blacklist", _check_strategy_blacklist),
    ("active_lessons", _check_active_lessons),
    ("post_stop_cooldown", _check_post_stop_cooldown),
    ("high_impact_blackout", _check_high_impact_blackout),
    ("combine_defensive_ladder", _check_combine_defensive_ladder),
    ("daily_target_lock", _check_daily_target_lock),
    ("daily_trade_count", _check_daily_trade_count),
    ("session_window", _check_session_window),
    ("no_naked_shorts", _check_no_naked_shorts),
    ("stop_required", _check_stop_required),
    ("per_symbol_limits", _check_per_symbol_limits),
    ("sector_basket_limits", _check_sector_and_basket_limits),
]


def apply_risk_gate(order: dict) -> dict | None:
    """Run the same checks the SDK PreToolUse hook would. Returns a verdict
    dict on block, None on pass."""
    db = get_db()
    limits = _load_yaml("risk_limits.yaml")
    topstep = _load_yaml("topstep.yaml")
    symbols = _load_yaml("symbols.yaml").get("symbols", {})
    snap = db.latest_account_snapshot() or {"realized_pl_day_usd": 0.0}
    positions = db.current_positions()

    for label, fn in ACTIVE_RISK_CHECKS:
        try:
            v = fn(tool_name="topstep_place_order", order=order,
                   agent="auto_trader", limits=limits, topstep=topstep,
                   symbols=symbols, snap=snap, positions=positions)
        except Exception as e:
            return {"rule": f"{label}_exception",
                    "reason": f"{type(e).__name__}: {e}"}
        if v is not None:
            return v
    return None


# ── Order placement ──────────────────────────────────────────

def _tick_size_for(symbol: str) -> float:
    """Get tick size for a symbol from config/symbols.yaml. Used to build the
    limit price for marketable-limit entries (Topstep rejects pure market orders)."""
    syms = _load_yaml("symbols.yaml").get("symbols", {})
    s = syms.get(symbol, {}) or {}
    return float(s.get("tick_size", 0.01))


# Quality thresholds — prevent the noise-trading that caused 35 circular
# round-trips today. Tightened 2026-04-29 per user directive.
MIN_STOP_TICKS = 5      # default — stops closer than 5 ticks get eaten by noise
MIN_REWARD_USD = 30.0   # don't trade for less than $30 even if RR looks good

# Sector-aware MIN_STOP_TICKS: index futures have larger tick values × tighter
# normal noise → need more ticks for the stop to survive intraday chop.
# Energies/metals tolerate the default 5. Rates need slightly more due to
# their finer tick increments. 2026-04-30: derived from incident review
# (5-tick MES stop = $6.25 loss, eaten by 1-2 sec of noise).
MIN_STOP_TICKS_BY_SECTOR = {
    "index_macro": 8,
    "rates":       10,
    "ag":          5,
    "fx_futures":  5,
    "energies":    5,
    "metals":      5,
    "crypto":      6,
}


def _min_stop_ticks_for(symbol: str) -> int:
    """Sector-aware stop-distance floor (in ticks)."""
    syms = _load_yaml("symbols.yaml").get("symbols", {})
    sector = (syms.get(symbol) or {}).get("sector")
    return MIN_STOP_TICKS_BY_SECTOR.get(sector, MIN_STOP_TICKS)


def _round_trip_fee_usd(symbol: str) -> float:
    """Fee per round-trip per contract for `symbol` from risk_limits.yaml.

    Critical for trade economics: if expected reward < 3x fees, the trade
    is unprofitable in expectation regardless of strategy hit rate.
    """
    limits = _load_yaml("risk_limits.yaml")
    fees = limits.get("fees_round_trip_usd") or {}
    return float(fees.get(symbol, fees.get("default", 5.00)))


def _expected_reward_usd(signal: dict, tick_value: float, tick_size: float) -> float:
    """Expected gross profit at target hit, in USD per contract."""
    entry = float(signal.get("price") or 0)
    target = float(signal.get("target") or 0)
    if target == 0 or entry == 0 or tick_size == 0:
        return 0.0
    move_ticks = abs(target - entry) / tick_size
    return move_ticks * tick_value


def _fee_decision_pass(symbol: str, signal: dict, tick_size: float) -> tuple[bool, str]:
    """Returns (pass, reason). Skip trade if reward at target is too small
    to justify the round-trip fee."""
    limits = _load_yaml("risk_limits.yaml")
    fee_rules = limits.get("fee_decision") or {}
    min_ratio = float(fee_rules.get("min_reward_to_fee_ratio", 3.0))
    if min_ratio <= 0:
        return True, ""
    syms = limits.get("per_symbol", {})
    # Get tick_value from symbols.yaml
    s = _load_yaml("symbols.yaml").get("symbols", {}).get(symbol, {})
    tick_value = float(s.get("tick_value", 1.0))
    fee = _round_trip_fee_usd(symbol)
    reward = _expected_reward_usd(signal, tick_value, tick_size)
    if reward == 0:
        return False, "no target → cannot evaluate fee economics"
    ratio = reward / fee
    if ratio < min_ratio:
        return False, (f"reward ${reward:.2f} / fee ${fee:.2f} = {ratio:.1f}x "
                       f"< required {min_ratio}x")
    return True, f"reward {ratio:.1f}x fee — economical"


def _round_to_tick(price: float, tick: float) -> float:
    """Round a price to the nearest valid tick boundary.

    CRITICAL FIX 2026-04-29: Topstep REJECTS any order whose limit/stop
    price is not exactly on a tick boundary. Strategies generate prices
    via statistical math (e.g. target = 1.173843140941422) which are
    almost never aligned. Without this rounding, ~55% of entry orders
    were rejected by Topstep, costing fees on every rejection. Round
    DOWN for buy limits / sell stops (more conservative entry / wider
    stop) to maintain favorable fill behavior; not strictly required
    but safer than nearest.
    """
    if tick <= 0:
        return price
    n = round(price / tick)
    return round(n * tick, 10)


def place_bracket(client, symbol: str, signal: dict, qty: int = 1) -> dict:
    """Place entry + stop via ProjectX directly (bypasses the SDK @tool wrapper).

    IMPORTANT: Topstep REJECTS pure market orders (status=5, instant rejection).
    Confirmed empirically 2026-04-29: NG/6E market orders rejected in 3ms with
    fill_volume=0. Solution: use marketable-limit orders (limit price set
    deliberately worse than the current quote so it fills like a market order
    but goes through Topstep's limit-order pipeline). Buy limit > expected
    fill, sell limit < expected fill, both with a 5-tick slippage buffer.
    """
    import sqlite3
    side = "buy" if signal["side"] == "long" else "sell"
    cid = f"auto_{uuid.uuid4().hex[:12]}"
    db = get_db()
    account_id = get_account_id()

    tick = _tick_size_for(symbol)
    slippage_ticks = 5
    entry_price = float(signal["price"])
    if side == "buy":
        limit_price = entry_price + slippage_ticks * tick
    else:
        limit_price = entry_price - slippage_ticks * tick

    # Pre-flight INSERT — UNIQUE(client_order_id) is our idempotency guard
    try:
        with db.tx() as c:
            c.execute(
                """INSERT INTO orders
                    (client_order_id, agent, ts_proposed, symbol, contract_month,
                     side, order_type, qty, limit_price, stop_price,
                     status, risk_verdict)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (cid, "auto_trader", utcnow_iso(), symbol, None,
                 side, "limit", int(qty), limit_price, signal["stop"],
                 "proposed", "allow"),
            )
    except sqlite3.IntegrityError:
        return {"status": "duplicate", "client_order_id": cid,
                "error": "client_order_id collision"}

    # 1. Resolve front-month contract id
    try:
        contract_id = client.front_month_contract_id(symbol)
    except ProjectXError as e:
        with db.tx() as c:
            c.execute("UPDATE orders SET status=?, risk_reason=? WHERE client_order_id=?",
                      ("rejected", f"contract_lookup_failed: {e}"[:500], cid))
        return {"status": "failed", "error": f"contract lookup: {e}",
                "client_order_id": cid}

    # Round all prices to valid tick boundaries (Topstep rejects fractional)
    limit_price = _round_to_tick(limit_price, tick)

    # 2. Submit MARKETABLE-LIMIT entry (Topstep rejects pure market)
    try:
        result = client.place_order(
            account_id=account_id,
            contract_id=contract_id,
            side=side,
            qty=int(qty),
            order_type="limit",
            limit_price=limit_price,
            stop_price=None,
            time_in_force="day",
            client_order_id=cid,
        )
    except ProjectXError as e:
        with db.tx() as c:
            c.execute("UPDATE orders SET status=?, risk_reason=? WHERE client_order_id=?",
                      ("rejected", f"broker_error: {e}"[:500], cid))
        return {"status": "failed", "error": str(e), "client_order_id": cid}

    # Detect broker-side rejection (success=False even when no exception raised).
    # Margin shortfall, tick-mis-rounding, etc. surface as success=False.
    # We log it but do NOT cooldown the symbol (per user directive 2026-04-29:
    # rely on lower scan frequency + thesis cooldown instead of per-symbol bans).
    if isinstance(result, dict) and result.get("success") is False:
        err = (result.get("errorMessage") or
               f"errorCode {result.get('errorCode', '?')}")
        with db.tx() as c:
            c.execute("UPDATE orders SET status=?, risk_reason=? WHERE client_order_id=?",
                      ("rejected", f"broker_rejected: {err}"[:500], cid))
        db.record_risk_event(
            severity="warn", rule="broker_rejected_entry",
            agent="auto_trader",
            detail={"symbol": symbol, "reason": str(err)[:200]},
        )
        return {"status": "rejected", "error": err, "client_order_id": cid}

    # 3. Mark submitted in DB with broker order id
    broker_oid = None
    if isinstance(result, dict):
        broker_oid = (result.get("orderId") or result.get("id")
                      or result.get("brokerOrderId"))
    with db.tx() as c:
        c.execute(
            """UPDATE orders SET ts_submitted=?, status=?, broker_order_id=?
                WHERE client_order_id=?""",
            (utcnow_iso(), "submitted",
             str(broker_oid) if broker_oid else None, cid),
        )

    # 4. Place the protective stop as a stop-LIMIT order (type=4).
    # IMPORTANT: Topstep rejects stop-limits when the limit is too far from
    # the stop. Empirically verified 2026-04-29: 5-tick gap → rejected;
    # 1-tick gap → accepted. The limit must be EXACTLY 1 tick past the
    # stop in the protective direction so the stop fires almost-marketable
    # while still satisfying Topstep's tight-limit rule.
    stop_cid = cid + "_stop"
    opposite = "sell" if side == "buy" else "buy"
    stop_trigger = _round_to_tick(float(signal["stop"]), tick)
    stop_limit_offset_ticks = 1   # confirmed working on Topstep
    if opposite == "sell":
        stop_limit_px = stop_trigger - stop_limit_offset_ticks * tick
    else:
        stop_limit_px = stop_trigger + stop_limit_offset_ticks * tick
    stop_limit_px = _round_to_tick(stop_limit_px, tick)
    try:
        stop_result = client.place_order(
            account_id=account_id,
            contract_id=contract_id,
            side=opposite,
            qty=int(qty),
            order_type="stop_limit",
            limit_price=stop_limit_px,
            stop_price=stop_trigger,
            time_in_force="gtc",
            client_order_id=stop_cid,
        )
        stop_broker_oid = None
        if isinstance(stop_result, dict):
            stop_broker_oid = (stop_result.get("orderId") or stop_result.get("id")
                               or stop_result.get("brokerOrderId"))
        # Record the stop in orders table too (separate row)
        try:
            with db.tx() as c:
                c.execute(
                    """INSERT INTO orders
                        (client_order_id, agent, ts_proposed, ts_submitted, symbol,
                         side, order_type, qty, stop_price, status, risk_verdict,
                         broker_order_id)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (stop_cid, "auto_trader", utcnow_iso(), utcnow_iso(), symbol,
                     opposite, "stop", int(qty), float(signal["stop"]),
                     "submitted", "allow",
                     str(stop_broker_oid) if stop_broker_oid else None),
                )
        except sqlite3.IntegrityError:
            pass  # stop already recorded
    except ProjectXError as e:
        # Entry filled but stop placement failed — this is bad; log breach
        db.record_risk_event(
            severity="breach", rule="bracket_stop_failed",
            agent="auto_trader",
            detail={"symbol": symbol, "client_order_id": cid,
                    "error": str(e)[:300],
                    "context": "Entry order placed but protective stop could "
                               "not be created. verify_position_stops sweep "
                               "should recover within 1 tick."},
        )

    # 5. Place the TARGET (take-profit) limit order on the OPPOSITE side.
    # MISSING-TARGET-BUG fix 2026-04-29: previously the auto-trader placed
    # entry + stop but never a target, so winning trades had no automatic
    # profit-take. Result: positions ran to either the stop or were held
    # indefinitely. Now: a passive limit order at the strategy's target
    # is placed immediately. Orphan-cancel sweep on next scan handles the
    # case where the stop fills first (target becomes orphaned).
    target_cid = cid + "_target"
    target_price = signal.get("target")
    target_broker_oid = None
    if target_price is not None and target_price > 0:
        target_price = _round_to_tick(float(target_price), tick)
        try:
            target_result = client.place_order(
                account_id=account_id,
                contract_id=contract_id,
                side=opposite,
                qty=int(qty),
                order_type="limit",
                limit_price=float(target_price),
                stop_price=None,
                time_in_force="gtc",
                client_order_id=target_cid,
            )
            if isinstance(target_result, dict):
                target_broker_oid = (target_result.get("orderId")
                                     or target_result.get("id")
                                     or target_result.get("brokerOrderId"))
            try:
                with db.tx() as c:
                    c.execute(
                        """INSERT INTO orders
                            (client_order_id, agent, ts_proposed, ts_submitted, symbol,
                             side, order_type, qty, limit_price, status, risk_verdict,
                             broker_order_id)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (target_cid, "auto_trader", utcnow_iso(), utcnow_iso(),
                         symbol, opposite, "limit", int(qty), float(target_price),
                         "submitted", "allow",
                         str(target_broker_oid) if target_broker_oid else None),
                    )
            except sqlite3.IntegrityError:
                pass
        except ProjectXError as e:
            db.record_risk_event(
                severity="warn", rule="bracket_target_failed",
                agent="auto_trader",
                detail={"symbol": symbol, "client_order_id": cid,
                        "error": str(e)[:300]},
            )

    return {
        "status": "submitted",
        "client_order_id": cid,
        "broker_order_id": broker_oid,
        "stop_client_order_id": stop_cid,
        "target_client_order_id": target_cid if target_price else None,
    }


# ── Main scan loop ───────────────────────────────────────────

def load_focus_universe() -> list[str]:
    cfg = _load_yaml("focus_universe.yaml") or {}
    if not cfg.get("focus_period_active"):
        # Default to a sane focus list anyway
        return ["MES", "NG", "GC", "ZN", "6E"]
    out: list[str] = []
    for syms in (cfg.get("allowed_symbols") or {}).values():
        out.extend(syms or [])
    return out or ["MES", "NG", "GC", "ZN", "6E"]


def _broker_position_for(client, account_id, symbol: str) -> dict | None:
    """Return broker position for a symbol if any, normalized."""
    try:
        positions = client.get_positions(account_id)
    except Exception:
        return None
    from hooks.risk_gate import _normalize_root
    for p in positions:
        contract = p.get("contractId", "")
        for tok in str(contract).split("."):
            if tok in ("CON", "F", "US", ""):
                continue
            if _normalize_root(tok) == symbol.upper():
                size = int(p.get("size") or 0)
                if size == 0:
                    continue
                t = int(p.get("type") or 0)
                side = "long" if t == 1 else "short" if t == 2 else (
                    "long" if size > 0 else "short")
                return {"symbol": symbol, "side": side, "size": abs(size),
                        "avg_price": float(p.get("averagePrice") or p.get("avgPrice") or 0)}
    return None


def _count_open_positions(client, account_id) -> int:
    """How many distinct contracts have an open position right now."""
    try:
        positions = client.get_positions(account_id)
    except Exception:
        return 0
    return sum(1 for p in positions if int(p.get("size") or 0) != 0)


def _in_thin_tape_window() -> tuple[bool, str]:
    """True if current ET time falls inside the thin_tape regime window.

    Returns (in_window, reason). Reads `risk_limits.yaml:regime_gates.thin_tape`
    so the source of truth lives in config. Window is interpreted as a
    half-open interval [start, end) in America/New_York time.

    The window may cross midnight (e.g., 21:00 → 04:00 next day); that's
    handled by checking start <= now OR now < end when start > end.
    """
    cfg = (_load_yaml("risk_limits.yaml").get("regime_gates") or {})
    thin = cfg.get("thin_tape") or {}
    if not thin.get("enabled"):
        return False, "regime gate disabled"
    from zoneinfo import ZoneInfo
    et = datetime.now(tz=ZoneInfo("America/New_York"))
    try:
        sh, sm = (int(x) for x in str(thin.get("start_et", "21:00")).split(":"))
        eh, em = (int(x) for x in str(thin.get("end_et",   "04:00")).split(":"))
    except Exception:
        return False, "thin_tape config malformed"
    now_minutes = et.hour * 60 + et.minute
    start_minutes = sh * 60 + sm
    end_minutes = eh * 60 + em
    if start_minutes < end_minutes:
        in_window = start_minutes <= now_minutes < end_minutes
    else:
        # Window wraps midnight (start > end)
        in_window = now_minutes >= start_minutes or now_minutes < end_minutes
    relation = "INSIDE" if in_window else "outside"
    return in_window, (
        f"{et.strftime('%H:%M ET')} {relation} thin-tape window "
        f"{thin.get('start_et')}–{thin.get('end_et')} ET"
    )


def _today_fees_usd() -> float:
    """Sum of estimated round-trip fees on filled orders today.

    Reads `orders` table (status='submitted' and 'filled' both count once
    per round-trip — entry pays the fee). Uses
    `risk_limits.yaml:fees_round_trip_usd` per-symbol schedule.
    """
    db = get_db()
    today_utc = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    fees_cfg = _load_yaml("risk_limits.yaml").get("fees_round_trip_usd") or {}
    default_fee = float(fees_cfg.get("default", 5.00))
    # Each entry order incurs one round-trip fee. Stops/targets are exits
    # (already counted via the entry). Filter by parent client_order_id
    # pattern: `auto_*` (no _stop/_target suffix) is the entry leg.
    rows = db.connect().execute(
        "SELECT symbol, qty FROM orders "
        "WHERE ts_proposed LIKE ? "
        "  AND agent='auto_trader' "
        "  AND client_order_id NOT LIKE '%_stop' "
        "  AND client_order_id NOT LIKE '%_target' "
        "  AND status IN ('submitted', 'filled') ",
        (f"{today_utc}%",),
    ).fetchall()
    total = 0.0
    for r in rows:
        sym = r["symbol"]
        qty = int(r["qty"] or 0)
        per_contract = float(fees_cfg.get(sym, default_fee))
        total += per_contract * qty
    return total


def _engage_auto_halt(halt_until_iso: str, *, reason: str) -> None:
    """Write trading_halt_until into risk_limits.yaml so the risk hook
    auto-blocks orders until that timestamp.

    Targeted text-only edit (no yaml.safe_dump) so YAML comments are preserved.
    Idempotent: if an existing halt is later than ours, leave it alone.
    """
    import re as _re
    import yaml as _yaml
    from pathlib import Path
    path = Path("config/risk_limits.yaml")
    text = path.read_text()
    # Read existing halt only (no rewrite)
    cfg = _yaml.safe_load(text)
    existing = (cfg.get("hard_rules") or {}).get("trading_halt_until", "")
    new_halt = halt_until_iso
    if existing and str(existing) > halt_until_iso:
        new_halt = str(existing)
    if new_halt == str(existing):
        # No change needed
        return
    new_text, n = _re.subn(
        r"(^[ \t]*trading_halt_until:[ \t]*)(?:\"[^\"]*\"|'[^']*'|\S+)([ \t]*(?:#.*)?)$",
        rf'\g<1>"{new_halt}"\g<2>',
        text, count=1, flags=_re.MULTILINE,
    )
    if n != 1:
        # Refuse to corrupt the file; surface the issue.
        get_db().record_risk_event(
            severity="warn", rule="auto_halt_yaml_edit_failed",
            agent="auto_trader",
            detail={"new_halt": new_halt, "reason": reason},
        )
        return
    path.write_text(new_text)
    get_db().record_decision(
        agent="auto_trader", kind="auto_halt_engaged",
        summary=f"Auto-halt engaged until {new_halt}",
        rationale=f"Reason: {reason}", model="system",
    )


def _strategy_hit_rate(label: str) -> tuple[float, int, str]:
    """Bayesian-blended hit rate for a strategy from strategy_performance.

    Returns (hit_rate, n_observed, confidence). When no data exists, falls
    back to a conservative 35% prior so unproven strategies need bigger
    rewards to justify firing.
    """
    try:
        from tools.strategy_performance import get_strategy_stats
        stats = get_strategy_stats()
    except Exception:
        return 0.35, 0, "ADVISORY"
    s = stats.get(label)
    if s is None:
        return 0.35, 0, "ADVISORY"
    hr = float(s.blended_hit) if 0 < s.blended_hit < 1 else 0.35
    return hr, int(s.n_observed), str(s.confidence)


def _consecutive_recent_losers() -> int:
    """Count consecutive recent stop-out events (newest first) before a
    non-stop-out outcome appears. Used by autonomous consecutive-loser halt.

    Reads `risk_events.rule = 'stop_hit_observed'` chronologically. We
    consider 'consecutive losers' the run of stop_hit_observed events at the
    tail with no winning event between them. Since we don't yet have a
    'target_hit_observed' counterpart, we approximate: if the most recent
    closed trade was a stop_hit, and the one before that was also a stop_hit
    (within the last 4 hours), the streak counts.
    """
    db = get_db()
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(hours=4)
              ).isoformat(timespec="seconds")
    rows = db.connect().execute(
        "SELECT ts, rule FROM risk_events "
        "WHERE rule IN ('stop_hit_observed', 'target_hit_observed', "
        "               'manual_close_observed') "
        "  AND ts >= ? "
        "ORDER BY id DESC",
        (cutoff,),
    ).fetchall()
    streak = 0
    for r in rows:
        if r["rule"] == "stop_hit_observed":
            streak += 1
        else:
            break
    return streak


def _recent_agent_wake_errors(window_minutes: int) -> int:
    """How many wake_error decisions in the recent window across all agents.

    Used to detect cascade conditions where the agent chain is broken — the
    pattern from 2026-04-29 where CIO + Edge Hunter wake_errored for hours
    while auto_trader kept trading.
    """
    db = get_db()
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(minutes=window_minutes)
              ).isoformat(timespec="seconds")
    row = db.connect().execute(
        "SELECT COUNT(*) FROM decisions WHERE kind = 'wake_error' AND ts >= ?",
        (cutoff,),
    ).fetchone()
    return int(row[0] or 0) if row else 0


def _today_trade_count_for_symbol(symbol: str) -> int:
    """Count of auto_trader entry orders for `symbol` today (UTC)."""
    db = get_db()
    today_utc = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    row = db.connect().execute(
        "SELECT COUNT(*) FROM orders "
        "WHERE ts_proposed LIKE ? AND agent='auto_trader' AND symbol=? "
        "  AND client_order_id NOT LIKE '%_stop' "
        "  AND client_order_id NOT LIKE '%_target' "
        "  AND status IN ('submitted', 'filled') ",
        (f"{today_utc}%", symbol),
    ).fetchone()
    return int(row[0] or 0) if row else 0


def _today_total_trade_count() -> int:
    """Count of auto_trader entry orders today across all symbols."""
    db = get_db()
    today_utc = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    row = db.connect().execute(
        "SELECT COUNT(*) FROM orders "
        "WHERE ts_proposed LIKE ? AND agent='auto_trader' "
        "  AND client_order_id NOT LIKE '%_stop' "
        "  AND client_order_id NOT LIKE '%_target' "
        "  AND status IN ('submitted', 'filled') ",
        (f"{today_utc}%",),
    ).fetchone()
    return int(row[0] or 0) if row else 0


def _recent_thesis_in_db(symbol: str, minutes: int = 30) -> bool:
    """True if auto_trader recorded a thesis for this symbol in the last N min.
    Prevents re-firing the same setup on every consecutive 5-min scan."""
    from datetime import datetime, timedelta, timezone
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(minutes=minutes)
              ).isoformat(timespec="seconds")
    db = get_db()
    row = db.connect().execute(
        "SELECT 1 FROM decisions WHERE agent='auto_trader' AND kind='thesis' "
        "AND symbol=? AND ts >= ? LIMIT 1",
        (symbol, cutoff),
    ).fetchone()
    return row is not None


def _capture_account_snapshot(client, account_id) -> dict | None:
    """Pull live broker state and write an account_snapshots row before the
    scan runs. Mirrors `Orchestrator.capture_account_snapshot` but lives here
    because auto_trader runs as a separate process and the orchestrator may
    not be alive.

    Without this, every P&L-aware risk check (DLL, TDD, defensive ladder,
    daily target lock) reads `snap=None` and short-circuits to allow.
    The 2026-04-29 DLL-breach incident occurred precisely because
    no process was writing snapshots while auto_trader was trading.
    """
    db = get_db()
    try:
        accounts = client.get_accounts()
        mine = next(
            (a for a in accounts if str(a.get("id")) == str(account_id)), None
        )
        if mine is None:
            db.record_risk_event(
                severity="warn", rule="snapshot_capture_failed",
                agent="auto_trader",
                detail={"error": f"account {account_id} not visible"},
            )
            return None
        balance = float(mine.get("balance", 0) or 0)
        can_trade = bool(mine.get("canTrade", True))
        positions = client.get_positions(account_id)
        open_contracts = sum(
            int(p.get("size") or p.get("netQuantity") or 0) for p in positions
        )

        # Realized day P&L = balance - first snapshot of UTC day
        first_today = db.first_snapshot_today_utc()
        realized_day = (balance - float(first_today["balance_usd"])
                        if first_today else 0.0)

        # Trailing DD = peak balance ever seen (or starting balance) − current
        risk_cfg = _load_yaml("risk_limits.yaml")
        starting = float(risk_cfg.get("account", {}).get("starting_balance", 0))
        peak = db.peak_eod_balance(fallback=starting)
        trailing_dd = max(0.0, peak - balance)
        env = str(risk_cfg.get("account", {}).get("environment", "combine"))

        # Note: unrealized P&L computation skipped here (orchestrator does it
        # via per-position bar fetches). auto_trader runs more frequently and
        # extra bar fetches per scan would be wasteful. realized + canTrade
        # + trailing_dd give DLL/TDD/ladder enough to enforce.
        db.record_account_snapshot(
            balance_usd=balance, environment=env,
            unrealized_pl_usd=0.0,
            realized_pl_day_usd=realized_day,
            trailing_dd_usd=trailing_dd,
            open_contracts_total=open_contracts,
            can_trade=can_trade,
        )
        if not can_trade:
            db.record_risk_event(
                severity="warn", rule="broker_can_trade_false",
                agent="auto_trader",
                detail={"balance_usd": balance,
                        "note": "Broker reports canTrade=false."},
            )
        return {"balance_usd": balance, "realized_pl_day_usd": realized_day,
                "trailing_dd_usd": trailing_dd, "can_trade": can_trade}
    except Exception as e:
        db.record_risk_event(
            severity="warn", rule="snapshot_capture_failed",
            agent="auto_trader", detail={"error": str(e)[:300]},
        )
        return None


def scan_once(*, dry_run: bool = False, cooldown_minutes: int = 45) -> dict:
    """One scan pass over the focus universe. Returns a summary dict."""
    db = get_db()
    try:
        client = get_client()
        account_id = get_account_id()
    except Exception as e:
        return {"status": "broker_unavailable", "error": str(e)}

    # Step −1: SNAPSHOT — pull broker state into account_snapshots so the
    # P&L-aware risk checks have data. Critical: auto_trader runs separately
    # from the orchestrator and the table goes empty otherwise. Failures
    # log + continue (better partial enforcement than zero enforcement).
    snap_result = _capture_account_snapshot(client, account_id)

    # Step −0.95: LOSS ALERTS — fire push notifications on threshold crosses.
    # No-op when DISCORD_WEBHOOK_URL / TELEGRAM_* aren't set in .env.
    # Logs locally regardless. Once-per-session dedup is in the alerter.
    if snap_result:
        try:
            from scripts.loss_alerter import check_and_alert
            check_and_alert(
                balance=snap_result["balance_usd"],
                day_pl=(snap_result.get("realized_pl_day_usd", 0)
                        + snap_result.get("unrealized_pl_usd", 0)),
                can_trade=snap_result.get("can_trade", True),
            )
        except Exception as e:
            db.record_risk_event(
                severity="warn", rule="loss_alerter_failed",
                agent="auto_trader", detail={"error": str(e)[:200]},
            )

    if snap_result and not snap_result.get("can_trade", True):
        # Topstep flipped canTrade=false. Stop the scan immediately.
        print(f"  HALTED — broker reports canTrade=false (balance "
              f"${snap_result['balance_usd']:.2f}). Skipping all symbols.")
        return {"status": "broker_halted",
                "balance_usd": snap_result["balance_usd"]}

    # Step −0.9: HARD INTERNAL-DLL KILL — independent of the hook layer.
    # The risk_gate's _check_daily_loss_limit relies on snapshots and a
    # complex projection. This is the raw "if we lost too much today,
    # stop" check that runs every scan regardless of hook plumbing.
    # 2026-04-29 incident: $1,013 drawdown despite $500 internal target.
    # Snap may be missing on first scan — fall through to broker balance.
    if snap_result:
        balance = snap_result["balance_usd"]
        risk_cfg = _load_yaml("risk_limits.yaml")
        starting = float(risk_cfg.get("account", {}).get("starting_balance", 50000))
        internal_dll = float(
            risk_cfg.get("account", {}).get("internal_dll_target_usd", 500)
        )
        topstep_dll = float(
            risk_cfg.get("account", {}).get("daily_loss_limit_usd", 1000)
        )
        # Compare today's realized P&L to the internal DLL.
        # NOTE: this is "today's realized day P&L" not "drawdown from start".
        # If account is already in drawdown when the day opens, that drawdown
        # doesn't reset — we still want to allow trading up to the daily
        # tolerance.
        today_realized = snap_result.get("realized_pl_day_usd", 0.0)
        if today_realized <= -internal_dll:
            print(f"  HALTED — today's realized P&L ${today_realized:+.2f} "
                  f"<= -${internal_dll:.0f} internal DLL. Stop trading until "
                  f"session close.")
            db.record_risk_event(
                severity="block", rule="internal_dll_hard_kill",
                agent="auto_trader",
                detail={"realized_pl_day": today_realized,
                        "internal_dll": internal_dll,
                        "balance_usd": balance},
            )
            return {"status": "internal_dll_hit",
                    "realized_pl_day_usd": today_realized}
        # TDD-ANCHOR-LEADING SAFETY HALT: replaces the old cumulative-DD
        # check that was redundantly tighter than Topstep's actual TDD.
        # Topstep's TDD floor = max(starting, peak_eod) - trailing_drawdown_usd.
        # We halt when balance is within $200 of that floor, leading Topstep
        # by a small buffer so we never reach their wall.
        tdd_usd = float(risk_cfg.get("account", {}).get("trailing_drawdown_usd", 2000))
        peak_eod = db.peak_eod_balance(fallback=starting)
        tdd_anchor = max(starting, peak_eod)
        tdd_floor = tdd_anchor - tdd_usd
        soft_halt = tdd_floor + 200
        if balance <= soft_halt:
            print(f"  HALTED — balance ${balance:.2f} within $200 of TDD floor "
                  f"${tdd_floor:.2f} (anchor ${tdd_anchor:.2f}). Halt to "
                  f"preserve headroom; need a green session before resuming.")
            db.record_risk_event(
                severity="block", rule="tdd_anchor_leading_halt",
                agent="auto_trader",
                detail={"balance": balance, "tdd_floor": tdd_floor,
                        "tdd_anchor": tdd_anchor, "soft_halt": soft_halt},
            )
            return {"status": "tdd_anchor_halt", "balance": balance}

    # Step −0.85: GLOBEX-REOPEN BUFFER — give the snapshot pipeline time
    # to write rows before any trade fires. Catches "system started fresh,
    # snapshot table empty, P&L checks no-op" pattern from 2026-04-29.
    sessions_cfg = (_load_yaml("risk_limits.yaml").get("sessions") or {})
    reopen_buffer = int(sessions_cfg.get("block_first_n_minutes_after_globex_reopen", 0))
    if reopen_buffer > 0:
        from zoneinfo import ZoneInfo as _ZI
        ct_now = datetime.now(tz=_ZI("America/Chicago"))
        # Globex re-opens at 17:00 CT Sunday and again each weekday after the
        # daily 16:00-17:00 CT maintenance break. We treat 17:00-17:30 CT every
        # day as the buffer window.
        if ct_now.hour == 17 and ct_now.minute < reopen_buffer:
            print(f"  REOPEN-BUFFER — within {reopen_buffer} min of 17:00 CT "
                  f"Globex reopen ({ct_now.strftime('%H:%M CT')}). "
                  f"Letting snapshot pipeline catch up.")
            db.record_risk_event(
                severity="info", rule="globex_reopen_buffer_block",
                agent="auto_trader",
                detail={"now_ct": ct_now.strftime("%H:%M"),
                        "buffer_minutes": reopen_buffer},
            )
            return {"status": "globex_reopen_buffer"}

    # Step −0.8: REGIME GATE — block all entries during thin-tape window.
    # 2026-04-29 incident: $1,013 lost during 03:30-07:00 UTC (Asian thin
    # tape). Strategies generated noise as signal. The blanket block is
    # the simplest and safest response.
    in_thin_tape, thin_reason = _in_thin_tape_window()
    if in_thin_tape:
        print(f"  REGIME-BLOCKED — {thin_reason}. No new entries.")
        db.record_risk_event(
            severity="info", rule="thin_tape_regime_block",
            agent="auto_trader", detail={"reason": thin_reason},
        )
        # Still run the snapshot capture (already done above) but skip the
        # symbol loop. Keeps monitoring + fee tracking alive.
        return {"status": "thin_tape_blocked", "reason": thin_reason}

    # Step −0.7: AUTONOMOUS-MODE WINDOW — when running unattended, additionally
    # restrict to RTH only (07:30-14:30 ET). Today's loss happened entirely
    # outside RTH. Read the autonomous flag from fund.yaml, not risk_limits.
    fund_cfg = _load_yaml("fund.yaml")
    autonomous = bool(fund_cfg.get("autonomous_mode", False))
    autonomous_rules = fund_cfg.get("autonomous_restrictions") or {}
    if autonomous and autonomous_rules.get("rth_only"):
        from zoneinfo import ZoneInfo as _ZI
        et_now = datetime.now(tz=_ZI("America/New_York"))
        try:
            sh, sm = (int(x) for x in str(autonomous_rules.get("rth_start_et", "07:30")).split(":"))
            eh, em = (int(x) for x in str(autonomous_rules.get("rth_end_et", "14:30")).split(":"))
        except Exception:
            sh, sm, eh, em = 7, 30, 14, 30
        now_min = et_now.hour * 60 + et_now.minute
        in_rth = (sh*60+sm) <= now_min < (eh*60+em)
        if not in_rth:
            print(f"  AUTONOMOUS-RTH-ONLY — {et_now.strftime('%H:%M ET')} "
                  f"outside {sh:02d}:{sm:02d}–{eh:02d}:{em:02d} ET window. "
                  f"Autonomous mode forbids overnight/extended-hours entries.")
            db.record_risk_event(
                severity="info", rule="autonomous_rth_only_block",
                agent="auto_trader",
                detail={"now_et": et_now.strftime("%H:%M"),
                        "rth_window": f"{sh:02d}:{sm:02d}-{eh:02d}:{em:02d}"},
            )
            return {"status": "autonomous_outside_rth"}

    # Step −0.65: HEALTH CHECKS (autonomous-mode only) — auto-halt cascade.
    # 2026-04-29 lesson: agents crashed for 4+ hours but auto_trader kept
    # trading because the two paths don't talk to each other. These checks
    # close that loop.
    if autonomous and autonomous_rules:
        # Consecutive-loser halt: 3 stop-outs in a row → 60-min pause.
        # Bellafiore "Playbook" rule, encoded.
        cl_threshold = int(autonomous_rules.get("consecutive_losers_halt", 0) or 0)
        if cl_threshold > 0:
            streak = _consecutive_recent_losers()
            if streak >= cl_threshold:
                pause = int(autonomous_rules.get("consecutive_loser_pause_minutes", 60))
                from datetime import datetime as _dt, timedelta as _td, timezone as _tz
                halt_until = (_dt.now(tz=_tz.utc) + _td(minutes=pause)
                              ).isoformat(timespec="seconds") + "Z"
                print(f"  CONSECUTIVE-LOSER HALT — {streak} stop-outs in a row "
                      f"(threshold {cl_threshold}). Pausing for {pause} min.")
                db.record_risk_event(
                    severity="block", rule="consecutive_loser_pause",
                    agent="auto_trader",
                    detail={"streak": streak, "pause_minutes": pause,
                            "halt_until": halt_until},
                )
                # Engage the standard auto-halt mechanism so the agent chain
                # also respects this. Edits risk_limits.yaml in place.
                _engage_auto_halt(halt_until,
                                  reason=f"consecutive {streak} losers")
                return {"status": "consecutive_loser_pause",
                        "streak": streak, "halt_until": halt_until}

        # Agent-wake-error cascade halt: agents are crashing → don't trade.
        ae_threshold = int(autonomous_rules.get("agent_wake_error_threshold", 0) or 0)
        ae_window = int(autonomous_rules.get("agent_wake_error_window_minutes", 30))
        if ae_threshold > 0:
            errs = _recent_agent_wake_errors(ae_window)
            if errs >= ae_threshold:
                print(f"  AGENT-CASCADE HALT — {errs} wake_errors in last "
                      f"{ae_window} min (threshold {ae_threshold}). "
                      f"Agents are broken; pausing trading.")
                from datetime import datetime as _dt, timedelta as _td, timezone as _tz
                halt_until = (_dt.now(tz=_tz.utc) + _td(hours=1)
                              ).isoformat(timespec="seconds") + "Z"
                db.record_risk_event(
                    severity="block", rule="agent_cascade_halt",
                    agent="auto_trader",
                    detail={"wake_errors": errs, "window_minutes": ae_window,
                            "halt_until": halt_until},
                )
                _engage_auto_halt(halt_until,
                                  reason=f"agent cascade — {errs} wake_errors")
                return {"status": "agent_cascade_halt",
                        "wake_errors": errs, "halt_until": halt_until}

    # Step −0.6: DAILY FEE BUDGET — halt if today's fees exceed the budget.
    # Catches the cost-frequency loop pattern (today: ~$150 in fees alone
    # over 4 hours despite per-trade gates being green).
    risk_cfg = _load_yaml("risk_limits.yaml")
    cost_cfg = risk_cfg.get("cost_discipline") or {}
    fee_budget = float(cost_cfg.get("daily_fee_budget_usd", 30.0))
    # Tighten budget under autonomous mode if configured
    if autonomous and autonomous_rules.get("daily_fee_budget_usd"):
        fee_budget = float(autonomous_rules["daily_fee_budget_usd"])
    fees_so_far = _today_fees_usd()
    if fees_so_far >= fee_budget:
        print(f"  FEE-BUDGET-HIT — today's fees ${fees_so_far:.2f} ≥ "
              f"budget ${fee_budget:.2f}. Halt new entries; manage book only.")
        db.record_risk_event(
            severity="block", rule="daily_fee_budget_exhausted",
            agent="auto_trader",
            detail={"fees_so_far": fees_so_far, "budget": fee_budget,
                    "autonomous": autonomous},
        )
        return {"status": "fee_budget_exhausted",
                "fees_so_far": fees_so_far, "budget": fee_budget}

    # Step −0.5: TOTAL TRADE-COUNT CAP (cost-aware). Independent of the hook's
    # max_trades_per_day which gates on risk_events; this gates on actual
    # broker-side filled/submitted entries.
    daily_count_cap = int(cost_cfg.get("max_trades_per_day_cost_aware", 12))
    if autonomous and autonomous_rules.get("max_trades_per_day"):
        daily_count_cap = int(autonomous_rules["max_trades_per_day"])
    today_trades = _today_total_trade_count()
    if today_trades >= daily_count_cap:
        print(f"  TRADE-COUNT-HIT — {today_trades} entries today ≥ cap "
              f"{daily_count_cap}. Halt; manage book only.")
        db.record_risk_event(
            severity="block", rule="daily_trade_count_cost_aware",
            agent="auto_trader",
            detail={"trades_today": today_trades, "cap": daily_count_cap,
                    "autonomous": autonomous},
        )
        return {"status": "trade_count_exhausted",
                "trades_today": today_trades, "cap": daily_count_cap}

    universe = load_focus_universe()
    # Show ET (Eastern Time) for human readability — DB still stores UTC
    from zoneinfo import ZoneInfo
    _et = datetime.now(tz=ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S ET")
    print(f"[{_et}] scanning {len(universe)} symbols: {universe}")

    summary = {"scanned": 0, "triggers": 0, "blocked": 0, "placed": 0,
               "skipped_already_in_trade": 0, "skipped_recent_thesis": 0,
               "errors": 0}

    # Refresh DB ↔ broker so per_symbol_limits check operates on truth
    if not dry_run:
        try:
            from scripts.reconcile_positions import reconcile
            reconcile(verbose=False)
        except Exception as e:
            print(f"  [reconcile failed: {e}]")

    # ORPHAN CLEANUP: cancel two classes of stale orders:
    #   (a) Orphans — working orders on contracts where the position is gone
    #       (entry filled, stop hit, leaving target on the books — or vice
    #       versa). Without this, an orphan would re-open a fresh position
    #       on the wrong side if filled later.
    #   (b) Stale entry limits — entry limit orders older than 10 minutes
    #       that haven't filled. The signal that placed them is no longer
    #       valid; price moved on. User directive 2026-04-29: "some aren't
    #       even being filled" — these eat exchange-side resources and
    #       sometimes incur cancel/modify fees if they auto-expire.
    if not dry_run:
        try:
            broker_positions = client.get_positions(account_id)
            broker_orders = client.get_working_orders(account_id)
            with_position = set()
            for p in broker_positions:
                if int(p.get("size") or 0) != 0:
                    with_position.add(p.get("contractId"))
            cancelled = 0
            stale_cancelled = 0
            from datetime import datetime as _dt, timedelta as _td, timezone as _tz
            stale_cutoff = _dt.now(tz=_tz.utc) - _td(minutes=10)
            for o in broker_orders:
                contract = o.get("contractId")
                tag = str(o.get("customTag") or "")
                # Only cancel auto_trader / recovery orders (never user-placed)
                if not (tag.startswith("auto_") or tag.startswith("recovery_")):
                    continue
                oid = o.get("id") or o.get("orderId")
                # (a) orphan: no position on this contract
                is_orphan = contract not in with_position
                # (b) stale entry: type=2 (limit), no _stop / _target suffix
                is_stale_entry = False
                if (int(o.get("type") or 0) == 2
                        and not tag.endswith("_stop")
                        and not tag.endswith("_target")):
                    ts_str = o.get("creationTimestamp") or ""
                    try:
                        ts = _dt.fromisoformat(ts_str.replace("Z", "+00:00"))
                        if ts < stale_cutoff:
                            is_stale_entry = True
                    except Exception:
                        pass
                if not (is_orphan or is_stale_entry):
                    continue
                try:
                    client.cancel_order(account_id, oid)
                    if is_stale_entry:
                        stale_cancelled += 1
                    else:
                        cancelled += 1
                except Exception:
                    pass
            if cancelled or stale_cancelled:
                msg = []
                if cancelled:
                    msg.append(f"{cancelled} orphan(s)")
                if stale_cancelled:
                    msg.append(f"{stale_cancelled} stale entry/entries")
                print(f"  [cleanup: cancelled {' + '.join(msg)}]")
        except Exception as e:
            print(f"  [cleanup failed: {e}]")

    # GUARD 0 (account-wide): max concurrent open positions.
    # Default 5 (Topstep $50K Combine cap). Autonomous mode tightens to 2
    # because today's incident showed 5 simultaneous bleed positions cost
    # $35-50 per stop-out cycle.
    MAX_CONCURRENT_POSITIONS = 5
    if autonomous and autonomous_rules.get("max_concurrent_positions"):
        MAX_CONCURRENT_POSITIONS = int(autonomous_rules["max_concurrent_positions"])
    open_positions = _count_open_positions(client, account_id)
    if open_positions >= MAX_CONCURRENT_POSITIONS:
        print(f"  GLOBAL SKIP — {open_positions} positions already open "
              f"(cap is {MAX_CONCURRENT_POSITIONS}"
              f"{', autonomous' if autonomous else ''}).")
        summary["skipped_concurrent_cap"] = summary.get("skipped_concurrent_cap", 0) + 1
        return summary

    # Pre-loop: per-strategy session shot count under autonomous mode
    autonomous_per_strategy_used: dict[str, int] = {}
    autonomous_per_strategy_cap = 1
    if autonomous and autonomous_rules.get("per_strategy_per_session_cap"):
        autonomous_per_strategy_cap = int(autonomous_rules["per_strategy_per_session_cap"])
    # Pre-load today's per-symbol trade counts once (avoid N+1 query)
    per_symbol_warn = int(cost_cfg.get("per_symbol_trade_count_warn", 3))
    per_symbol_block = int(cost_cfg.get("per_symbol_trade_count_block", 5))

    for symbol in universe:
        # GUARD 0.5: per-symbol burn rate. After N filled trades on this
        # symbol today, block. Catches the 30+ MES round-trips pattern.
        sym_count = _today_trade_count_for_symbol(symbol)
        if sym_count >= per_symbol_block:
            print(f"  {symbol:5s}  SKIP — {sym_count} trades on this symbol "
                  f"today ≥ block threshold {per_symbol_block}. Fee-sink protection.")
            db.record_risk_event(
                severity="block", rule="per_symbol_burn_block",
                agent="auto_trader",
                detail={"symbol": symbol, "count": sym_count,
                        "block_threshold": per_symbol_block},
            )
            summary["skipped_per_symbol_burn"] = summary.get("skipped_per_symbol_burn", 0) + 1
            continue
        elif sym_count >= per_symbol_warn:
            db.record_risk_event(
                severity="warn", rule="per_symbol_burn_warn",
                agent="auto_trader",
                detail={"symbol": symbol, "count": sym_count,
                        "warn_threshold": per_symbol_warn},
            )

        # GUARD 1: already have a position on this symbol → skip
        existing = _broker_position_for(client, account_id, symbol)
        if existing is not None:
            print(f"  {symbol:5s}  SKIP — already {existing['side']} "
                  f"{existing['size']} @ {existing['avg_price']}")
            summary["skipped_already_in_trade"] += 1
            continue

        # GUARD 2: same-symbol thesis fired in the last `cooldown_minutes` min.
        # Configurable via --cooldown-minutes (default 45 = option 2).
        # Hard floor of 15 in live mode (set in main(), not here).
        if cooldown_minutes > 0 and _recent_thesis_in_db(symbol, minutes=cooldown_minutes):
            print(f"  {symbol:5s}  SKIP — recent thesis ({cooldown_minutes}-min cooldown)")
            summary["skipped_recent_thesis"] += 1
            continue

        # PRE-SCAN: detect direction conflicts between 5m and 15m. If the
        # two timeframes disagree on direction, BOTH are skipped — this is
        # a noisy market and our triggers are not reliable here. This
        # eliminates the circular-trade pattern where 5m said long, 15m
        # said short, both placed, both stopped.
        try:
            bars_5 = fetch_bars(client, symbol, minutes=5, lookback=120)
            bars_15 = fetch_bars(client, symbol, minutes=15, lookback=120)
            sig_5 = sig_15 = None
            if bars_5 is not None and len(bars_5) >= 30:
                for sf, p, _, _ in STRATEGY_ROSTER:
                    s = find_latest_signal(bars_5, sf, **p)
                    if s and s.get("stop") is not None:
                        sig_5 = s; break
            if bars_15 is not None and len(bars_15) >= 30:
                for sf, p, _, _ in STRATEGY_ROSTER:
                    s = find_latest_signal(bars_15, sf, **p)
                    if s and s.get("stop") is not None:
                        sig_15 = s; break
            if (sig_5 and sig_15
                    and sig_5["side"] != sig_15["side"]):
                print(f"  {symbol:5s}  SKIP - direction conflict (5m={sig_5['side']}, 15m={sig_15['side']})")
                summary["skipped_direction_conflict"] = (
                    summary.get("skipped_direction_conflict", 0) + 1)
                continue
        except Exception:
            pass  # if pre-scan fails, fall through to normal flow

        # Try multiple timeframes (5m primary, 15m secondary).
        # IMPORTANT: only ONE entry per symbol per scan (any timeframe).
        symbol_placed_this_scan = False
        for tf_minutes in (5, 15):
            if symbol_placed_this_scan:
                break
            bars = fetch_bars(client, symbol, minutes=tf_minutes, lookback=120)
            if bars is None or len(bars) < 30:
                continue
            summary["scanned"] += 1

            # Try every strategy, first trigger wins
            for strat_fn, params, conviction, label in STRATEGY_ROSTER:
                # AUTONOMOUS conviction floor: skip "low" conviction strategies
                # under autonomous mode. Today's bleed was almost entirely
                # low-conviction setups (vwap_reversion, support_resistance_bounce).
                if autonomous and autonomous_rules.get("min_conviction"):
                    floor = str(autonomous_rules["min_conviction"]).lower()
                    rank = {"low": 0, "med": 1, "high": 2, "validation": 1}
                    if rank.get(conviction, 0) < rank.get(floor, 1):
                        continue

                # AUTONOMOUS per-strategy session shot cap: each strategy
                # gets N entries per session. Default 1. Stops the
                # "narrow_range_break fired 30 times" pattern from today.
                if autonomous and autonomous_per_strategy_used.get(label, 0) >= autonomous_per_strategy_cap:
                    continue

                signal = find_latest_signal(bars, strat_fn, **params)
                if signal is None:
                    continue
                if signal["stop"] is None:
                    continue  # need a stop to trade

                # R:R floor check — autonomous mode lifts the floor higher
                rr_floor = CONVICTION_RR_FLOOR.get(conviction, 2.0)
                if autonomous and autonomous_rules.get("rr_floor_override"):
                    rr_floor = max(rr_floor, float(autonomous_rules["rr_floor_override"]))
                if signal["target"]:
                    risk = abs(signal["price"] - signal["stop"])
                    reward = abs(signal["target"] - signal["price"])
                    rr = reward / risk if risk > 0 else 0
                    if rr < rr_floor:
                        continue

                tick = _tick_size_for(symbol)

                # MIN STOP DISTANCE: sector-aware. Index futures need 8+
                # ticks because 5-tick MES = $6.25 loss eaten by 1-2 sec
                # of intraday noise. Rates need 10+ for similar reasons.
                # Energies/metals tolerate 5.
                min_stop_ticks = _min_stop_ticks_for(symbol)
                stop_dist_ticks = abs(signal["price"] - signal["stop"]) / tick
                if stop_dist_ticks < min_stop_ticks:
                    print(f"  {symbol} [{tf_minutes}m] {label} | "
                          f"SKIP - stop too tight ({stop_dist_ticks:.1f} ticks "
                          f"< sector min {min_stop_ticks})")
                    summary["skipped_stop_too_tight"] = (
                        summary.get("skipped_stop_too_tight", 0) + 1)
                    continue

                # MIN ABSOLUTE REWARD: target reward must be ≥ $30 in USD,
                # regardless of R:R. Tiny-reward trades are noise.
                syms = _load_yaml("symbols.yaml").get("symbols", {})
                tick_value = float(syms.get(symbol, {}).get("tick_value", 1.0))
                if signal.get("target") and signal.get("price"):
                    reward_usd = (abs(signal["target"] - signal["price"])
                                  / tick * tick_value)
                    if reward_usd < MIN_REWARD_USD:
                        print(f"  {symbol} [{tf_minutes}m] {label} | "
                              f"SKIP - reward ${reward_usd:.2f} "
                              f"< min ${MIN_REWARD_USD}")
                        summary["skipped_reward_too_small"] = (
                            summary.get("skipped_reward_too_small", 0) + 1)
                        continue

                # FEE-AWARE FILTER: skip if reward < 3× round-trip fee
                fee_ok, fee_reason = _fee_decision_pass(symbol, signal, tick)
                if not fee_ok:
                    print(f"  {symbol} [{tf_minutes}m] {label} | "
                          f"FEE-SKIP: {fee_reason}")
                    summary["skipped_fee_unfavorable"] = summary.get("skipped_fee_unfavorable", 0) + 1
                    continue

                # HIT-RATE-AWARE EV GATE: compute expected NET dollar profit
                # using observed hit rate (Bayesian-blended). If expected_net
                # < threshold, skip — no strategy fires unless its math is
                # positive in expectation. The 2026-04-29 incident bled
                # because individually-negative-EV trades fired at high
                # frequency. This catches that at the trigger level.
                if signal.get("target") and signal.get("price") and signal.get("stop"):
                    hit_rate, n_obs, hr_conf = _strategy_hit_rate(label)
                    risk_usd = (abs(signal["price"] - signal["stop"]) / tick) * tick_value
                    reward_usd = (abs(signal["target"] - signal["price"]) / tick) * tick_value
                    fee = _round_trip_fee_usd(symbol)
                    expected_net = (hit_rate * reward_usd
                                    - (1 - hit_rate) * risk_usd
                                    - fee)
                    min_expected_net = 5.0   # $5 NET per trade minimum
                    # Tighter under autonomous mode: $10 floor
                    if autonomous:
                        min_expected_net = 10.0
                    if expected_net < min_expected_net:
                        print(f"  {symbol} [{tf_minutes}m] {label} | "
                              f"EV-SKIP: expected_net ${expected_net:.2f} < "
                              f"${min_expected_net:.2f} (hit={hit_rate:.0%} "
                              f"n={n_obs} {hr_conf} reward=${reward_usd:.0f} "
                              f"risk=${risk_usd:.0f} fee=${fee:.2f})")
                        summary["skipped_negative_ev"] = (
                            summary.get("skipped_negative_ev", 0) + 1)
                        continue

                # Build order proposal
                order = {
                    "symbol": symbol, "side": "buy" if signal["side"] == "long" else "sell",
                    "qty": 1, "order_type": "market",
                    "stop_price": signal["stop"],
                    "strategy": label,
                    "conviction": conviction,
                    "horizon": "intraday",
                    "tf": f"{tf_minutes}m",
                }

                # Apply risk gate
                verdict = apply_risk_gate(order)
                summary["triggers"] += 1

                if verdict:
                    summary["blocked"] += 1
                    db.record_risk_event(
                        severity="block", rule=verdict["rule"],
                        agent="auto_trader",
                        detail={"symbol": symbol, "strategy": label,
                                "reason": verdict["reason"][:200]},
                    )
                    print(f"  {symbol} [{tf_minutes}m] {label} | "
                          f"BLOCKED by {verdict['rule']}: {verdict['reason'][:80]}")
                    break  # next symbol; don't try more strategies on this one

                # Cleared the gate — record the thesis and place
                db.record_decision(
                    agent="auto_trader", kind="thesis", symbol=symbol,
                    summary=f"{label} {signal['side']} @ {signal['price']:.4f} "
                            f"stop={signal['stop']:.4f} target={signal['target']}",
                    rationale=(f"strategy={label} side={signal['side']} "
                               f"entry={signal['price']} stop={signal['stop']} "
                               f"target={signal['target']} conviction={conviction} "
                               f"tf={tf_minutes}m rr_planned="
                               f"{abs((signal['target'] or signal['price']) - signal['price'])/max(abs(signal['price']-signal['stop']),0.0001):.2f} "
                               f"horizon=intraday reason={signal['reason']}"),
                    model="auto_trader",
                )

                if dry_run:
                    print(f"  {symbol} [{tf_minutes}m] {label} | "
                          f"DRY RUN: would place {order['side']} qty=1 "
                          f"stop={signal['stop']}")
                    symbol_placed_this_scan = True
                    autonomous_per_strategy_used[label] = autonomous_per_strategy_used.get(label, 0) + 1
                else:
                    try:
                        result = place_bracket(client, symbol, signal, qty=1)
                        if result.get("status") == "submitted":
                            summary["placed"] += 1
                            symbol_placed_this_scan = True
                            autonomous_per_strategy_used[label] = autonomous_per_strategy_used.get(label, 0) + 1
                            print(f"  {symbol} [{tf_minutes}m] {label} | "
                                  f"PLACED {order['side']} qty=1 "
                                  f"broker_oid={result.get('broker_order_id')} "
                                  f"cid={result.get('client_order_id')}")
                        else:
                            summary["errors"] += 1
                            print(f"  {symbol} [{tf_minutes}m] {label} | "
                                  f"PLACE FAILED: {result.get('error')}")
                    except Exception as e:
                        summary["errors"] += 1
                        print(f"  {symbol} [{tf_minutes}m] {label} | "
                              f"PLACE EXCEPTION: {type(e).__name__}: {e}")
                        traceback.print_exc()
                break  # exit strategy loop after one trigger

    return summary


def _acquire_instance_lock(dry_run: bool) -> Path | None:
    """File-based lock to prevent concurrent auto_trader instances.

    Two parallel scans on the same broker account compound damage: each one
    independently passes its own cooldown check (different in-memory state)
    but together they fire 2x the orders. 2026-04-29 incident analysis
    couldn't rule this out.

    Lock file is left in place if the process crashes; we check whether the
    PID inside it is still alive and steal the lock if not.
    Dry runs are exempt — multiple dry runs in parallel are fine.
    """
    if dry_run:
        return None
    lock_path = Path("logs/auto_trader.pid")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.exists():
        try:
            existing = int(lock_path.read_text().strip())
        except Exception:
            existing = 0
        if existing > 0:
            try:
                # Cheap is-alive check: os.kill(pid, 0) raises if dead.
                # On Windows this works for processes we own.
                os.kill(existing, 0)
                print(f"REFUSING to start: another auto_trader is already "
                      f"running (PID {existing}). Either stop it first or "
                      f"delete {lock_path} if you're sure it's dead.",
                      file=sys.stderr)
                return None
            except (OSError, ProcessLookupError):
                # PID dead — steal the lock
                print(f"  [lock] previous instance PID {existing} is gone; "
                      f"taking over the lock.", file=sys.stderr)
    lock_path.write_text(str(os.getpid()))
    return lock_path


def _release_instance_lock(lock_path: Path | None) -> None:
    if lock_path is None:
        return
    try:
        # Only delete if we still own it
        if lock_path.exists() and int(lock_path.read_text().strip()) == os.getpid():
            lock_path.unlink()
    except Exception:
        pass


def main_loop(*, interval_minutes: int = 15, dry_run: bool = False,
              cooldown_minutes: int = 45) -> None:
    """Run scans on a loop until interrupted."""
    print(f"=== auto_trader: {interval_minutes}-minute cadence, "
          f"{cooldown_minutes}-min same-symbol cooldown, "
          f"{'DRY RUN' if dry_run else 'LIVE'} ===")
    while True:
        try:
            result = scan_once(dry_run=dry_run, cooldown_minutes=cooldown_minutes)
            print(f"  summary: {result}\n")
        except KeyboardInterrupt:
            print("\n=== interrupted, exiting ===")
            return
        except Exception as e:
            print(f"  scan_once raised: {type(e).__name__}: {e}")
            traceback.print_exc()
        time.sleep(interval_minutes * 60)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--once", action="store_true",
                   help="single scan and exit (debug)")
    p.add_argument("--dry-run", action="store_true",
                   help="find + log triggers but don't place orders")
    p.add_argument("--interval-minutes", type=int, default=15,
                   help="minutes between scans. Default 15 (slow + fee-aware). "
                        "Use 5 for aggressive, 30 for very conservative.")
    p.add_argument("--cooldown-minutes", type=int, default=45,
                   help="same-symbol thesis cooldown. Default 45 min. "
                        "Hard floor of 15 in live mode; 0 only allowed in "
                        "dry-run. Setting 0 in live mode caused the "
                        "2026-04-29 DLL breach (24 theses in one minute "
                        "during overnight thin tape).")
    args = p.parse_args()

    mode = os.environ.get("FUND_MODE", "paper").split("#", 1)[0].strip().lower()
    if mode != "live" and not args.dry_run:
        print(f"FUND_MODE={mode!r} — refusing to place real orders. "
              f"Either set FUND_MODE=live in .env or use --dry-run.",
              file=sys.stderr)
        return 2

    # Hard floor on cooldown in live mode. Past incident: --cooldown-minutes 0
    # in fund.ps1:start-debug allowed dozens of theses per minute, compounding
    # the 2026-04-29 loss. Dry-run can still go to 0 for debugging.
    MIN_LIVE_COOLDOWN = 15
    if not args.dry_run and args.cooldown_minutes < MIN_LIVE_COOLDOWN:
        print(f"--cooldown-minutes {args.cooldown_minutes} clamped to "
              f"{MIN_LIVE_COOLDOWN} (live-mode floor). Use --dry-run if "
              f"you need a tighter loop for testing.", file=sys.stderr)
        args.cooldown_minutes = MIN_LIVE_COOLDOWN

    lock = _acquire_instance_lock(args.dry_run)
    if lock is None and not args.dry_run:
        return 3   # another instance is running
    try:
        if args.once:
            result = scan_once(dry_run=args.dry_run,
                               cooldown_minutes=args.cooldown_minutes)
            print(f"\nfinal summary: {result}")
            return 0

        main_loop(interval_minutes=args.interval_minutes,
                  dry_run=args.dry_run,
                  cooldown_minutes=args.cooldown_minutes)
        return 0
    finally:
        _release_instance_lock(lock)


if __name__ == "__main__":
    raise SystemExit(main())
