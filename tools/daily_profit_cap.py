"""Daily profit cap enforcement — Combine consistency-rule discipline.

Tracks today's P&L vs a configured cap (default $600 in Combine stage,
disabled outside Combine). On breach: flattens all positions and halts
trading until next day boundary (5 PM CT, matches DLL reset).

Day boundary semantics: a "day" is defined as the period between
successive 5 PM CT resets. Balance reference is captured at the first
scan after a new boundary crosses; subsequent scans compute
day_pnl = current_balance - day_start_balance.

State persists across trader restarts via `state/day_start_balance.json`.

2026-05-12: built per user direction to dilute today's +$2,948 GC day
across many smaller days, satisfying the 50% consistency requirement.
"""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DAY_STATE_FILE = PROJECT_ROOT / "state" / "day_start_balance.json"


def _now_ct() -> datetime:
    """Current time in US Central (CT). Approximated as UTC-5 (CST) /
    UTC-4 (CDT). Uses zoneinfo when available, else best-effort offset."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Chicago"))
    except Exception:
        # Fallback: approximate as UTC-5 (CST). DST will offset by 1h.
        return datetime.now(timezone(timedelta(hours=-5)))


def _current_day_key(reset_hour_ct: int = 17) -> str:
    """Compute a 'day key' that increments at reset_hour_ct each day.
    Example: 4 PM CT on 2026-05-12 → key '2026-05-12'.
              6 PM CT on 2026-05-12 → key '2026-05-12_after5pm' (new window).
    Using simple naming: pre-5pm uses date, post-5pm uses date+suffix."""
    now = _now_ct()
    if now.hour >= reset_hour_ct:
        # We're in the "post-reset" window; the day key is for the
        # window that starts at today's reset_hour_ct and runs until
        # tomorrow's reset_hour_ct.
        return f"{now.strftime('%Y-%m-%d')}_after{reset_hour_ct}ct"
    # Pre-reset: this window started yesterday at reset_hour_ct
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    return f"{yesterday}_after{reset_hour_ct}ct"


def _load_day_state() -> dict:
    if not DAY_STATE_FILE.exists():
        return {}
    try:
        return json.loads(DAY_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_day_state(state: dict) -> None:
    DAY_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    DAY_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def get_day_start_balance(current_balance: float,
                          reset_hour_ct: int = 17) -> float:
    """Return the balance at the start of the current day-window. If
    there's no record for today, records the current balance as the
    new day-start.

    Idempotent — repeated calls in same day return the same value."""
    state = _load_day_state()
    key = _current_day_key(reset_hour_ct)
    if state.get("day_key") != key:
        state = {"day_key": key, "start_balance": float(current_balance),
                 "recorded_at": datetime.now(timezone.utc).isoformat()}
        _save_day_state(state)
    return float(state.get("start_balance", current_balance))


def compute_day_pnl(current_balance: float,
                    reset_hour_ct: int = 17) -> float:
    """Day P&L = current_balance - day_start_balance."""
    return current_balance - get_day_start_balance(current_balance,
                                                    reset_hour_ct)


def check_and_enforce(client, account_id,
                      cap_usd: float | None,
                      reset_hour_ct: int = 17,
                      log_fn: Callable[[str], None] | None = None,
                      halt_setter: Callable[[datetime], None] | None = None,
                      ) -> dict:
    """Check today's P&L vs cap. If at/over cap: flatten all positions
    and (if halt_setter given) set the halt timestamp to next day boundary.

    Returns: {triggered: bool, day_pnl: float, balance: float, cap: float, ...}
    On any error, returns triggered=False so trading isn't halted by a bug.
    """
    log = log_fn if log_fn is not None else (lambda _msg: None)
    if cap_usd is None or cap_usd <= 0:
        return {"triggered": False, "reason": "cap_not_configured"}

    # Read current balance
    try:
        accts = client.get_accounts() if hasattr(client, "get_accounts") else []
        bal = None
        for a in accts:
            if str(a.get("id")) == str(account_id):
                bal = float(a.get("balance", 0))
                break
        if bal is None:
            return {"triggered": False, "reason": "balance_unavailable"}
    except Exception as e:
        log(f"  daily_profit_cap: balance fetch failed: {e}")
        return {"triggered": False, "reason": "balance_error", "error": str(e)}

    start = get_day_start_balance(bal, reset_hour_ct)
    day_pnl = bal - start

    if day_pnl < cap_usd:
        return {"triggered": False, "day_pnl": day_pnl, "balance": bal,
                "cap": cap_usd, "start": start}

    # CAP BREACHED. Flatten + halt.
    log(f"  DAILY_PROFIT_CAP HIT: day_pnl=${day_pnl:+.2f} >= cap ${cap_usd:.0f} "
         f"-- flattening + halting until next reset")

    # Flatten all open positions
    flattened = []
    try:
        for p in client.get_positions(account_id) or []:
            size = int(p.get("size") or 0)
            if size == 0:
                continue
            contract_id = p.get("contractId")
            type_code = int(p.get("type") or 0)
            opp = "sell" if type_code == 1 else "buy"
            cid = f"profitcap_close_{uuid.uuid4().hex[:8]}"
            try:
                client.place_order(
                    account_id=account_id, contract_id=contract_id,
                    side=opp, qty=abs(size), order_type="market",
                    time_in_force="ioc", client_order_id=cid,
                )
                flattened.append(contract_id)
                log(f"  daily_profit_cap: flattened {contract_id} {opp} x{abs(size)}")
            except Exception as e:
                log(f"  daily_profit_cap: flatten failed for {contract_id}: {e}")
    except Exception as e:
        log(f"  daily_profit_cap: position fetch failed: {e}")

    # Set halt until next reset (next 5 PM CT)
    if halt_setter is not None:
        now_ct = _now_ct()
        if now_ct.hour < reset_hour_ct:
            # Reset is later today
            next_reset = now_ct.replace(hour=reset_hour_ct, minute=0, second=0,
                                         microsecond=0)
        else:
            # Reset is tomorrow at reset_hour_ct
            next_reset = (now_ct + timedelta(days=1)).replace(
                hour=reset_hour_ct, minute=0, second=0, microsecond=0)
        try:
            halt_setter(next_reset.astimezone(timezone.utc))
        except Exception as e:
            log(f"  daily_profit_cap: halt-set failed: {e}")

    return {"triggered": True, "day_pnl": day_pnl, "balance": bal,
            "cap": cap_usd, "start": start, "flattened": flattened}
