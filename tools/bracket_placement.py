"""Bracket placement — entry-limit + fill-confirm + stop placement.

Extracted from scripts/live_trader.py 2026-05-13 as part of the
continuous-trim directive. PURE PLACEMENT code — no decision logic.
The trader imports place_bracket and helpers from here.

WHY THIS LIVES HERE (not in the brain): even though it's mechanical,
it's the broker IO sequence. Brain bugs can't bypass it (brain emits
signals, trader places via this module).

Key safety properties preserved from the original:
  - Orphan-leg-safe: stop/target legs only place AFTER entry-fill is
    confirmed (2026-05-10 incident).
  - Stop recalculated relative to actual fill price (2026-05-11 MNQ
    favorable-fill incident).
  - Stop placement verified at broker; emergency-flatten if absent
    (2026-05-11 belt-and-suspenders).
  - SKIP_TARGET_LEG honored (2026-05-11 broker target-fill anomaly).
"""
from __future__ import annotations

import time
import uuid
from typing import Callable

from state.db import get_db
from tools.projectx_client import ProjectXError
from tools.trader_utils import _tick_size, _round_to_tick, _utcnow_iso


FILL_WAIT_TIMEOUT_S = 30          # how long to wait for entry to fill before cancelling
FILL_WAIT_POLL_S = 2              # polling cadence while waiting


def _position_signature(client, account_id, contract_id: str) -> tuple[int, int]:
    """(type, size) for the contract, or (0, 0) if flat. Used to detect
    entry fills without trusting any single API field."""
    try:
        for p in client.get_positions(account_id):
            if p.get("contractId") == contract_id:
                size = int(p.get("size", 0))
                if size != 0:
                    return (int(p.get("type", 0)), size)
    except Exception:
        pass
    return (0, 0)


def _position_avg_price(client, account_id, contract_id: str) -> float | None:
    """Return averagePrice for the open position on this contract, or
    None if flat. 2026-05-11: needed to recalculate the stop AFTER fill —
    see place_bracket comment on MNQ 39-point favorable-fill bug."""
    try:
        for p in client.get_positions(account_id):
            if p.get("contractId") == contract_id and int(p.get("size", 0)) != 0:
                px = p.get("averagePrice")
                if px is not None:
                    return float(px)
    except Exception:
        pass
    return None


def _verify_stop_landed(client, account_id, contract_id: str,
                        stop_cid: str, poll_attempts: int = 3,
                        poll_s: float = 1.0) -> bool:
    """Confirm the stop order shows up in working orders after placement.
    Brokers can lag in surfacing newly-placed orders. 2026-05-11."""
    for _ in range(poll_attempts):
        try:
            for o in client.get_working_orders(account_id) or []:
                if str(o.get("customTag") or "") == stop_cid:
                    return True
        except Exception:
            pass
        time.sleep(poll_s)
    return False


def _emergency_flatten_position(client, account_id, contract_id: str,
                                  side_to_close: str, qty: int,
                                  reason: str,
                                  log_fn: Callable[[str], None]) -> bool:
    """Market-close a position that has no working protective stop.
    2026-05-11: belt-and-suspenders for stop-placement failures."""
    cid = f"emergency_flat_{uuid.uuid4().hex[:8]}"
    try:
        client.place_order(
            account_id=account_id, contract_id=contract_id,
            side=side_to_close, qty=int(qty), order_type="market",
            time_in_force="ioc", client_order_id=cid,
        )
        log_fn(f"  EMERGENCY FLATTEN: {contract_id} {side_to_close} x{qty} -- {reason}")
        return True
    except Exception as e:
        log_fn(f"  EMERGENCY FLATTEN FAILED for {contract_id}: {e}")
        return False


def _wait_for_entry_fill(client, account_id, contract_id: str,
                          baseline_sig: tuple[int, int],
                          timeout_s: int = FILL_WAIT_TIMEOUT_S,
                          poll_s: int = FILL_WAIT_POLL_S) -> bool:
    """Poll until the position signature changes (= entry filled) or
    timeout. Default-deny: timeout → not filled → caller cancels entry."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if _position_signature(client, account_id, contract_id) != baseline_sig:
            return True
        time.sleep(poll_s)
    return False


def place_bracket(client, account_id, symbol: str, signal: dict,
                  qty: int = 1, dry_run: bool = False,
                  log_fn: Callable[[str], None] | None = None,
                  skip_target_leg: bool = True) -> dict:
    """Place entry-limit; on confirmed fill, place stop (and optional
    target). See module docstring for safety properties.

    `skip_target_leg=True` is the production default — broker has a
    target-fill anomaly so targets are software-managed via profit_protect.
    """
    log = log_fn if log_fn is not None else (lambda _msg: None)
    side = "buy" if signal["side"] == "long" else "sell"
    cid = f"live_{uuid.uuid4().hex[:12]}"
    db = get_db()
    tick = _tick_size(symbol)
    entry_price = float(signal["price"])
    # Marketable-limit: 5-tick slippage buffer
    if side == "buy":
        limit_px = _round_to_tick(entry_price + 5 * tick, tick)
    else:
        limit_px = _round_to_tick(entry_price - 5 * tick, tick)
    stop_px = _round_to_tick(float(signal["stop"]), tick)
    target_px = _round_to_tick(float(signal["target"]), tick) if signal.get("target") else None

    if dry_run:
        log(f"  DRY: would place {symbol} {side} qty={qty} entry={limit_px} "
              f"stop={stop_px} target={target_px} cid={cid}")
        return {"status": "dry_run", "client_order_id": cid}

    # Front-month contract id
    try:
        contract_id = client.front_month_contract_id(symbol)
    except ProjectXError as e:
        log(f"  contract lookup failed for {symbol}: {e}")
        return {"status": "failed", "error": str(e)}

    db.connect().execute(
        """INSERT INTO orders (client_order_id, agent, ts_proposed, symbol, side,
                                 order_type, qty, limit_price, stop_price,
                                 status, risk_verdict)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (cid, "live_trader", _utcnow_iso(), symbol, side, "limit", int(qty),
         limit_px, stop_px, "proposed", "allow"),
    )
    db.connect().commit()

    # 1. Snapshot baseline position for fill detection
    baseline_sig = _position_signature(client, account_id, contract_id)

    # 2. Entry as marketable-limit
    try:
        result = client.place_order(
            account_id=account_id, contract_id=contract_id,
            side=side, qty=int(qty), order_type="limit",
            limit_price=limit_px, stop_price=None,
            time_in_force="day", client_order_id=cid,
        )
    except ProjectXError as e:
        log(f"  entry place failed: {e}")
        return {"status": "failed", "error": str(e)}

    if isinstance(result, dict) and result.get("success") is False:
        err = result.get("errorMessage") or "broker rejected"
        log(f"  entry rejected: {err}")
        return {"status": "rejected", "error": err}

    broker_oid = (result.get("orderId") or result.get("id") if isinstance(result, dict) else None)
    db.connect().execute(
        "UPDATE orders SET ts_submitted=?, status=?, broker_order_id=? WHERE client_order_id=?",
        (_utcnow_iso(), "submitted", str(broker_oid) if broker_oid else None, cid),
    )
    db.connect().commit()

    # 3. Wait for fill confirmation
    log(f"  {symbol} entry placed, polling fill (timeout {FILL_WAIT_TIMEOUT_S}s)")
    filled = _wait_for_entry_fill(client, account_id, contract_id, baseline_sig)
    if not filled:
        log(f"  {symbol} entry {cid} UNFILLED after {FILL_WAIT_TIMEOUT_S}s -- "
              f"cancelling; no protective legs placed")
        try:
            if broker_oid is not None:
                client.cancel_order(account_id, broker_oid)
        except Exception as e:
            log(f"  entry cancel failed (will remain working): {e}")
        db.connect().execute(
            "UPDATE orders SET status=?, ts_cancelled=? WHERE client_order_id=?",
            ("cancelled_unfilled", _utcnow_iso(), cid),
        )
        db.connect().commit()
        return {"status": "cancelled_unfilled", "client_order_id": cid}

    # 3a. Recalculate stop relative to ACTUAL fill price.
    # 2026-05-11: signal entry was 29448.5, fill was 29409.25 (39pt favorable),
    # stop ended up on wrong side of fill → broker rejected → unprotected.
    actual_fill = _position_avg_price(client, account_id, contract_id) or entry_price
    signal_risk = abs(entry_price - float(signal["stop"]))
    if side == "buy":
        stop_px = _round_to_tick(actual_fill - signal_risk, tick)
    else:
        stop_px = _round_to_tick(actual_fill + signal_risk, tick)
    log(f"  {symbol} entry FILLED @ {actual_fill}; "
          f"stop recalculated to {stop_px} (risk={signal_risk:.4f} from fill)")

    # 4. Stop-limit (1-tick offset for Topstep's tight-limit rule)
    opp = "sell" if side == "buy" else "buy"
    stop_limit_px = (stop_px - tick) if opp == "sell" else (stop_px + tick)
    stop_limit_px = _round_to_tick(stop_limit_px, tick)
    stop_cid = cid + "_stop"
    stop_placed_ok = False
    try:
        sr = client.place_order(
            account_id=account_id, contract_id=contract_id,
            side=opp, qty=int(qty), order_type="stop_limit",
            limit_price=stop_limit_px, stop_price=stop_px,
            time_in_force="gtc", client_order_id=stop_cid,
        )
        sboid = (sr.get("orderId") or sr.get("id")) if isinstance(sr, dict) else None
        sr_ok = (not isinstance(sr, dict)) or sr.get("success") is not False
        if not sr_ok:
            err = sr.get("errorMessage") or "rejected"
            log(f"  stop placement REJECTED by broker: {err}")
        else:
            db.connect().execute(
                """INSERT INTO orders (client_order_id, agent, ts_proposed, ts_submitted,
                                         symbol, side, order_type, qty, stop_price,
                                         status, risk_verdict, broker_order_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (stop_cid, "live_trader", _utcnow_iso(), _utcnow_iso(),
                 symbol, opp, "stop", int(qty), stop_px,
                 "submitted", "allow", str(sboid) if sboid else None),
            )
            db.connect().commit()
            stop_placed_ok = _verify_stop_landed(client, account_id, contract_id, stop_cid)
            if not stop_placed_ok:
                log(f"  CRITICAL: stop {stop_cid} not visible in working orders "
                      f"after placement; emergency-flattening position")
                _emergency_flatten_position(
                    client, account_id, contract_id,
                    side_to_close=opp, qty=int(qty),
                    reason=f"stop {stop_cid} did not land at broker",
                    log_fn=log,
                )
                return {"status": "stop_placement_failed_flattened",
                        "client_order_id": cid}
    except ProjectXError as e:
        log(f"  stop placement failed: {e}")
        _emergency_flatten_position(
            client, account_id, contract_id,
            side_to_close=opp, qty=int(qty),
            reason=f"stop place_order raised: {e}",
            log_fn=log,
        )
        return {"status": "stop_placement_failed_flattened",
                "client_order_id": cid}

    # 5. Target as limit (only when not skipping target legs)
    if target_px is not None and not skip_target_leg:
        target_cid = cid + "_target"
        try:
            tr = client.place_order(
                account_id=account_id, contract_id=contract_id,
                side=opp, qty=int(qty), order_type="limit",
                limit_price=target_px, stop_price=None,
                time_in_force="gtc", client_order_id=target_cid,
            )
            tboid = (tr.get("orderId") or tr.get("id")) if isinstance(tr, dict) else None
            db.connect().execute(
                """INSERT INTO orders (client_order_id, agent, ts_proposed, ts_submitted,
                                         symbol, side, order_type, qty, limit_price,
                                         status, risk_verdict, broker_order_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (target_cid, "live_trader", _utcnow_iso(), _utcnow_iso(),
                 symbol, opp, "limit", int(qty), target_px,
                 "submitted", "allow", str(tboid) if tboid else None),
            )
            db.connect().commit()
        except ProjectXError as e:
            log(f"  target placement failed: {e}")

    log(f"  PLACED {symbol} {side} qty={qty} entry≈{limit_px} stop={stop_px} "
          f"target={target_px or '—'} cid={cid}")
    # Discord alert on trade open — user wants visibility on every fill
    try:
        from tools.alert import send_alert as _alert
        risk_pts = abs(actual_fill - stop_px)
        _alert(
            f"📈 OPEN {symbol} {side} {qty}ct @ {actual_fill} "
            f"stop={stop_px} (risk={risk_pts:.2f}pts)",
            level="info",
        )
    except Exception:
        pass
    return {"status": "submitted", "client_order_id": cid,
            "broker_order_id": broker_oid}
