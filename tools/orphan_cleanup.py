"""Orphan-bracket cleanup.

Cancels working bracket legs whose underlying position is flat. Extracted
from scripts/live_trader.py 2026-05-13.

WHY: ProjectX `place_order` has no native bracket OCO linkage. The
trader places entry/stop/target as 3 independent orders. If one leg
fills and the broker's implicit OCO doesn't fire (or doesn't exist),
the other legs stay working and can trigger unintended fills later.
This sweep cancels orders that no longer protect a position.

Safe-by-default:
  - 2-min grace per order: never cancels a freshly-placed bracket
    whose position hasn't propagated through the API yet.
  - Only acts on orders tagged 'live_' (our customTag prefix). Won't
    touch user-placed manual orders.
  - Only cancels when position is verifiably flat (not inferred).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable


ORPHAN_GRACE_SEC = 120  # 2-min grace before any cancel


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def cleanup_orphan_brackets(client, account_id,
                              log_fn: Callable[[str], None] | None = None) -> int:
    """Cancel working bracket legs whose underlying position is flat.
    Returns # orders cancelled."""
    log = log_fn if log_fn is not None else (lambda _msg: None)
    cancelled = 0
    try:
        positions = client.get_positions(account_id) or []
        working = client.get_working_orders(account_id) or []
    except Exception as e:
        log(f"  cleanup skipped (broker fetch failed): {type(e).__name__}: {e}")
        return 0

    has_position: dict[str, bool] = {}
    for p in positions:
        cid = p.get("contractId")
        if not cid:
            continue
        size = int(p.get("size") or 0)
        if size != 0:
            has_position[cid] = True

    now = _now_utc()
    for o in working:
        tag = str(o.get("customTag") or "")
        if not tag.startswith("live_"):
            continue  # not ours
        cid = o.get("contractId")
        if not cid:
            continue
        if has_position.get(cid):
            continue  # position is open; bracket is legitimate

        try:
            ts_str = o.get("creationTimestamp") or ""
            if ts_str:
                order_ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                age_sec = (now - order_ts).total_seconds()
            else:
                age_sec = ORPHAN_GRACE_SEC + 1
        except Exception:
            age_sec = ORPHAN_GRACE_SEC + 1

        if age_sec < ORPHAN_GRACE_SEC:
            continue  # too fresh; broker may still be propagating fill state

        oid = o.get("id") or o.get("orderId")
        if not oid:
            continue
        try:
            client.cancel_order(account_id, oid)
            log(f"  cleaned orphan {tag} (id={oid}, age={age_sec:.0f}s, contract={cid})")
            cancelled += 1
        except Exception as e:
            log(f"  cleanup cancel failed for {oid}: {type(e).__name__}: {e}")

    return cancelled
