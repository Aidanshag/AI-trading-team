"""Periodic check that every open position has a working broker stop.

Built 2026-05-12 evening as a Combine-helpful safety: tonight's MNQ
incident showed that a stop CAN fail to land at the broker (rejection).
The verify-after-place check at `place_bracket` catches initial failures,
but the broker can ALSO cancel a stop later (session-end cleanup, server
error, ProjectX OCO interactions). Without this sweep, a position could
sit unprotected mid-session.

Algorithm (runs every scan, after `enforce_loss_cap`):
  1. List open positions
  2. For each: look for a working stop order with a matching customTag
     (we use the `live_<cid>_stop` convention)
  3. If no matching stop is found AND the position has been open long
     enough that the trader's place_bracket should have completed
     (`PROTECTION_GRACE_SEC` buffer), emergency-flatten the position
"""
from __future__ import annotations

import time as _time
import uuid as _uuid
from datetime import datetime, timezone
from typing import Callable


PROTECTION_GRACE_SEC = 90   # buffer after position open before sweep enforces
                            # (gives place_bracket time to confirm + place stop)


def _has_working_stop_for(working_orders: list[dict], contract_id: str) -> bool:
    """Is there at least one stop/stop-limit working on `contract_id`
    with the `live_` customTag prefix?"""
    for o in working_orders:
        if o.get("contractId") != contract_id:
            continue
        otype = o.get("type")  # ProjectX: 3=stop, 4=stop_limit
        if otype not in (3, 4):
            continue
        tag = str(o.get("customTag") or "")
        if tag.startswith("live_") and tag.endswith("_stop"):
            return True
    return False


def _age_seconds(position: dict) -> float:
    """Approximate age of an open position from `creationTimestamp`.
    Falls back to a large age if timestamp parsing fails (treats as
    long-enough to be subject to the sweep)."""
    ts = position.get("creationTimestamp") or ""
    if not ts:
        return PROTECTION_GRACE_SEC * 10  # assume old
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds()
    except Exception:
        return PROTECTION_GRACE_SEC * 10


def sweep(client, account_id,
           log_fn: Callable[[str], None] | None = None,
           grace_sec: int = PROTECTION_GRACE_SEC) -> dict:
    """Run the protection sweep. Returns:
        {checked: int, flattened: list[contract_id], skipped_grace: int}

    `client` must implement: get_positions, get_working_orders, place_order.
    On any broker fetch error, returns triggered=False (fail-open — don't
    flatten on bad data).
    """
    log = log_fn if log_fn is not None else (lambda _msg: None)
    out = {"checked": 0, "flattened": [], "skipped_grace": 0}
    try:
        positions = client.get_positions(account_id) or []
        working = client.get_working_orders(account_id) or []
    except Exception as e:
        log(f"  position_protection: fetch failed: {type(e).__name__}: {e}")
        return out

    for p in positions:
        size = int(p.get("size") or 0)
        if size == 0:
            continue
        contract_id = p.get("contractId")
        if not contract_id:
            continue
        out["checked"] += 1

        # Grace period: don't flatten a freshly-opened position whose stop
        # hasn't propagated through the API yet.
        if _age_seconds(p) < grace_sec:
            out["skipped_grace"] += 1
            continue

        if _has_working_stop_for(working, contract_id):
            continue   # protected — all good

        # CRITICAL — no working stop found. Emergency-flatten.
        type_code = int(p.get("type") or 0)
        opp = "sell" if type_code == 1 else "buy"
        cid = f"protsweep_{_uuid.uuid4().hex[:8]}"
        try:
            client.place_order(
                account_id=account_id, contract_id=contract_id,
                side=opp, qty=abs(size), order_type="market",
                time_in_force="ioc", client_order_id=cid,
            )
            out["flattened"].append(contract_id)
            log(f"  POSITION_PROTECTION FLATTEN: {contract_id} {opp} x{abs(size)} "
                 f"— no working stop found after grace period")
        except Exception as e:
            log(f"  position_protection flatten failed {contract_id}: {e}")
    return out
