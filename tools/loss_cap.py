"""Per-trade loss cap enforcement.

Force-closes any open position whose unrealized loss exceeds the cap.
Extracted from scripts/live_trader.py 2026-05-13.

Called from the position-polling thread (sub-minute) AND inside the
trader's scan loop (5-min) — both are idempotent (market-IOC on a
flat position is a no-op).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable

from tools.trader_utils import _load_yaml


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def enforce_loss_cap(client, account_id,
                      per_trade_cap_usd: float = 150.0,
                      log_fn: Callable[[str], None] | None = None) -> int:
    """Force-close positions whose unrealized loss < -per_trade_cap_usd.
    Returns # positions closed."""
    log = log_fn if log_fn is not None else (lambda _msg: None)
    closed = 0
    try:
        positions = client.get_positions(account_id) or []
    except Exception:
        return 0
    syms = _load_yaml("config/symbols.yaml").get("symbols", {})
    for p in positions:
        size = int(p.get("size") or 0)
        if size == 0:
            continue
        contract = p.get("contractId") or ""
        avg = float(p.get("avgPrice") or 0)
        if avg <= 0 or not contract:
            continue
        type_code = int(p.get("type") or 0)
        sign = 1 if type_code == 1 else -1 if type_code == 2 else (1 if size > 0 else -1)
        size = abs(size)
        root = None
        for tok in contract.split("."):
            if tok in ("CON", "F", "US", ""): continue
            if len(tok) <= 3 and tok and tok[0].isalpha() and tok[1:].isdigit(): continue
            root = tok; break
        meta = syms.get(root or "", {})
        tick_size = float(meta.get("tick_size") or 0)
        tick_value = float(meta.get("tick_value") or 0)
        if tick_size <= 0 or tick_value <= 0:
            continue
        try:
            bars = client.get_bars(contract_id=contract,
                                     start_time=(_now_utc() - timedelta(minutes=10)).isoformat(),
                                     end_time=_now_utc().isoformat(),
                                     unit=2, unit_number=1, limit=5, live=False)
            mark = float(bars[-1].get("c") or 0) if bars else 0
        except Exception:
            continue
        if mark <= 0:
            continue
        unrealized = sign * size * ((mark - avg) / tick_size) * tick_value
        if unrealized < -per_trade_cap_usd:
            opp = "sell" if type_code == 1 else "buy"
            cid = f"livecap_{uuid.uuid4().hex[:8]}"
            try:
                client.place_order(account_id=account_id, contract_id=contract,
                                     side=opp, qty=size, order_type="market",
                                     time_in_force="ioc", client_order_id=cid)
                log(f"  LOSS-CAP CLOSE: {root} unrealized=${unrealized:+.2f} "
                     f"< -${per_trade_cap_usd:.0f}")
                try:
                    from tools.alert import send_alert as _alert
                    _alert(
                        f"🛑 LOSS-CAP CLOSE {root} @ ${unrealized:+.0f} "
                        f"(cap -${per_trade_cap_usd:.0f})",
                        level="warn",
                    )
                except Exception:
                    pass
                closed += 1
            except Exception as e:
                log(f"  loss-cap close failed for {root}: {e}")
                try:
                    from tools.alert import send_alert as _alert
                    _alert(
                        f"CRITICAL: loss-cap close FAILED for {root} at "
                        f"unrealized ${unrealized:+.0f}: {type(e).__name__}: {e}",
                        level="crit",
                    )
                except Exception:
                    pass
    return closed
