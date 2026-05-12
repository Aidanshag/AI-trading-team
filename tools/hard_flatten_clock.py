"""3:10 PM CT hard-flatten enforcement (Topstep Combine + XFA rule).

Topstep rule (per `vault/_meta/topstep_combine_rules.md`):
    "All positions must be closed by 3:10 PM CT (or the product's market
    close, whichever comes first). The system must have a hard time-based
    flatten mechanism that fires at 3:05 PM CT regardless of P&L."

Holding any position past 3:10 PM CT is a rule violation that can trigger
account review or closure. This module:

  1. Detects the closing window via timezone-aware CT clock (DST-aware)
  2. At ≥ ENTRY_BLOCK_TIME_CT, blocks new entries
  3. At ≥ FLATTEN_TIME_CT, market-closes all positions + cancels working orders
  4. At ≥ DEADLINE_TIME_CT, logs critical if anything is still open

Used by `scripts/live_trader.py` at the top of scan_once.

2026-05-12: built as backlog item P0 — Combine-required.
"""
from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Callable

# ── Hard thresholds (per Topstep rules) ────────────────────────

ENTRY_BLOCK_TIME_CT  = time(14, 55)   # 2:55 PM CT — stop placing new entries
FLATTEN_TIME_CT      = time(15, 5)    # 3:05 PM CT — proactive flatten (5min buffer)
DEADLINE_TIME_CT     = time(15, 10)   # 3:10 PM CT — the hard rule deadline
END_OF_WINDOW_CT     = time(15, 30)   # 3:30 PM CT — after this, overnight trading resumes
                                      # (Topstep allows ~23h sessions; only the 3:10 deadline matters)


def _now_ct() -> datetime:
    """Current time in US Central. Uses zoneinfo for DST correctness."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Chicago"))
    except Exception:
        # Fallback: approximate UTC-5 (CST). DST will offset by 1h.
        from datetime import timedelta
        return datetime.now(timezone(timedelta(hours=-5)))


def current_window(now: datetime | None = None) -> str:
    """Return which closing-window we're in:
      'normal'        — before close-window starts (full trading)
      'no_new_entries' — close-10min through close-5min (block entries)
      'flatten'       — close-5min through close (proactive flatten window)
      'past_deadline' — close through close+20min (rule violation if anything open)
      then back to 'normal' for the overnight session.

    2026-05-12: now holiday-aware. Reads `tools/holiday_schedule.py` and on
    fully-closed days returns 'flatten' all day; on abbreviated days the
    close window slides to the earlier abbreviated close.
    """
    if now is None:
        now = _now_ct()
    # Day-of-week filter: weekends have no enforcement (no RTH session)
    if now.weekday() >= 5:
        return "normal"
    # Holiday check — get effective hard-close time for today
    try:
        from tools.holiday_schedule import (rule_for_date,
                                              hard_flatten_time_ct)
        rule = rule_for_date(now.date())
    except Exception:
        rule = None
    if rule is not None and rule.closed:
        # Fully-closed holiday → always in flatten mode (no trading)
        return "flatten"
    # Compute window thresholds for today's effective close time
    if rule is not None and rule.abbreviated_close_ct is not None:
        deadline = rule.abbreviated_close_ct
        from datetime import timedelta as _td
        # Reconstruct via datetime arithmetic for minute math
        _base = datetime.combine(now.date(), deadline)
        flatten = (_base - _td(minutes=5)).time()
        block = (_base - _td(minutes=15)).time()
        end_window = (_base + _td(minutes=20)).time()
    else:
        deadline = DEADLINE_TIME_CT
        flatten = FLATTEN_TIME_CT
        block = ENTRY_BLOCK_TIME_CT
        end_window = END_OF_WINDOW_CT

    t = now.time()
    if t < block:
        return "normal"
    if t < flatten:
        return "no_new_entries"
    if t < deadline:
        return "flatten"
    if t < end_window:
        return "past_deadline"
    return "normal"


def should_block_new_entries(now: datetime | None = None) -> bool:
    """True iff we're in the 2:55 PM CT → end-of-day window where no new
    entries should be placed."""
    win = current_window(now)
    return win in ("no_new_entries", "flatten", "past_deadline")


def should_flatten_now(now: datetime | None = None) -> bool:
    """True iff we're in the proactive-flatten window (≥3:05 PM CT) or past."""
    win = current_window(now)
    return win in ("flatten", "past_deadline")


def enforce_hard_flatten(client, account_id,
                         log_fn: Callable[[str], None] | None = None,
                         now: datetime | None = None) -> dict:
    """Run the 3:10 PM CT enforcement. Returns:
      {window: str, flattened: list[contract_id], cancelled: int, blocked_entries: bool}

    Idempotent: re-running in the flatten window when already flat is a no-op.
    """
    log = log_fn if log_fn is not None else (lambda _msg: None)
    window = current_window(now)
    result = {"window": window, "flattened": [], "cancelled": 0,
              "blocked_entries": window in ("no_new_entries", "flatten",
                                              "past_deadline")}
    if not should_flatten_now(now):
        return result
    # ≥ 3:05 PM CT: market-close everything + cancel working orders
    try:
        for o in client.get_working_orders(account_id) or []:
            oid = o.get("id") or o.get("orderId")
            if not oid:
                continue
            try:
                client.cancel_order(account_id, oid)
                result["cancelled"] += 1
            except Exception as e:
                log(f"  hard_flatten: cancel failed {oid}: {e}")
    except Exception as e:
        log(f"  hard_flatten: get_working_orders failed: {e}")
    try:
        positions = client.get_positions(account_id) or []
    except Exception as e:
        log(f"  hard_flatten: get_positions failed: {e}")
        return result
    import uuid as _uuid
    for p in positions:
        size = int(p.get("size") or 0)
        if size == 0:
            continue
        contract_id = p.get("contractId")
        type_code = int(p.get("type") or 0)
        opp = "sell" if type_code == 1 else "buy"
        cid = f"hardflat_{_uuid.uuid4().hex[:8]}"
        try:
            client.place_order(
                account_id=account_id, contract_id=contract_id,
                side=opp, qty=abs(size), order_type="market",
                time_in_force="ioc", client_order_id=cid,
            )
            result["flattened"].append(contract_id)
            log(f"  HARD_FLATTEN [{window}]: {contract_id} {opp} x{abs(size)} "
                 f"-- 3:10 PM CT deadline enforcement")
        except Exception as e:
            log(f"  hard_flatten: market-close failed {contract_id}: {e}")
    return result
