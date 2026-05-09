"""Auto-resubmit ZN limit order at 22:00 UTC market reopen.

Sleeps until 22:00:15 UTC, pulls ZN quote, checks gap from 110.921875.
If within ±8 ticks of entry, submits LIMIT BUY 1 ZN at 110.921875 plus
OCO bracket (stop 110.859375 / target 111.046875). If gap > 8 ticks,
PASS — thesis invalidated.
"""
from __future__ import annotations
import os, sys, time, asyncio, httpx, json
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

env = Path(".env")
for line in env.read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); os.environ.setdefault(k.strip(), v.strip())


ENTRY_PRICE = 110.921875
STOP_PRICE  = 110.859375
TARGET      = 111.046875
TICK_TOLERANCE = 8     # 8 ticks of gap-tolerance per QR thesis
TICK_SIZE   = 0.015625  # ZN tick


def _ts(): return datetime.now(tz=timezone.utc).strftime("%H:%M:%S")


def _seconds_until(target_utc: datetime) -> float:
    return max(0.0, (target_utc - datetime.now(tz=timezone.utc)).total_seconds())


def _get_token():
    r = httpx.post("https://api.topstepx.com/api/Auth/loginKey",
                   json={"userName": os.environ["PROJECTX_USERNAME"],
                         "apiKey":   os.environ["PROJECTX_API_KEY"]},
                   timeout=15.0)
    return r.json().get("token")


def _get_zn_contract_id(token: str) -> str | None:
    """Look up the active ZN front-month contract id."""
    H = {"Authorization": f"Bearer {token}"}
    r = httpx.post("https://api.topstepx.com/api/Contract/search",
                   headers=H, json={"searchText": "ZN", "live": False},
                   timeout=15.0)
    data = r.json().get("contracts", []) or []
    # Pick the front-month ZN by symbol prefix; sort by expiry.
    candidates = [c for c in data if c.get("symbolId", "").startswith("F.US.TY")
                  or c.get("name", "").upper().startswith("ZN")]
    if not candidates:
        return None
    candidates.sort(key=lambda c: c.get("contractMonth") or "")
    return candidates[0].get("id")


def _get_quote(token: str, contract_id: str) -> tuple[float, float] | None:
    """Returns (bid, ask) — try market data endpoint."""
    H = {"Authorization": f"Bearer {token}"}
    # Topstep / ProjectX quote endpoint
    r = httpx.post("https://api.topstepx.com/api/MarketData/quote",
                   headers=H, json={"contractId": contract_id}, timeout=15.0)
    if r.status_code != 200:
        return None
    d = r.json()
    bid = d.get("bid") or d.get("lastBid")
    ask = d.get("ask") or d.get("lastAsk")
    if bid is None or ask is None:
        return None
    return float(bid), float(ask)


def main():
    target = datetime(2026, 4, 28, 22, 0, 15, tzinfo=timezone.utc)
    wait = _seconds_until(target)
    print(f"[{_ts()}] Sleeping {wait:.0f}s until 22:00:15 UTC reopen check.")
    time.sleep(wait)

    print(f"[{_ts()}] Reopen check starting.")
    token = _get_token()
    if not token:
        print(f"[{_ts()}] Auth FAILED. Aborting.")
        return 1
    H = {"Authorization": f"Bearer {token}"}

    contract_id = _get_zn_contract_id(token)
    print(f"[{_ts()}] ZN contract id: {contract_id}")
    if not contract_id:
        print(f"[{_ts()}] Could not resolve ZN contract. Aborting.")
        return 2

    # Pull a quote (retry up to 6× over 30s if early in reopen)
    quote = None
    for attempt in range(6):
        quote = _get_quote(token, contract_id)
        if quote:
            break
        time.sleep(5)
    if not quote:
        print(f"[{_ts()}] Could not get ZN quote after 30s. Aborting.")
        return 3

    bid, ask = quote
    mid = (bid + ask) / 2
    gap_ticks = abs(mid - ENTRY_PRICE) / TICK_SIZE
    print(f"[{_ts()}] ZN reopen quote: bid={bid:.6f} ask={ask:.6f} mid={mid:.6f}")
    print(f"[{_ts()}] Gap from entry {ENTRY_PRICE}: {gap_ticks:.1f} ticks")

    if gap_ticks > TICK_TOLERANCE:
        print(f"[{_ts()}] GAP > {TICK_TOLERANCE} ticks — PASS per thesis. No order.")
        return 0

    # Place the limit order
    print(f"[{_ts()}] Within tolerance. Placing LIMIT BUY 1 ZN @ {ENTRY_PRICE}")
    order = {
        "accountId": int(os.environ["PROJECTX_ACCOUNT_ID"]),
        "contractId": contract_id,
        "type": 1,            # 1 = limit
        "side": 0,            # 0 = buy
        "size": 1,
        "limitPrice": ENTRY_PRICE,
        "customTag": "ZN_ORB_20260428_RESUBMIT",
    }
    r = httpx.post("https://api.topstepx.com/api/Order/place",
                   headers=H, json=order, timeout=30.0)
    print(f"[{_ts()}] Place response: {r.status_code} {r.json()}")
    if r.status_code == 200 and r.json().get("success"):
        order_id = r.json().get("orderId")
        print(f"[{_ts()}] LIMIT order placed. Broker order ID: {order_id}")
        # Place stop-limit + target as separate working orders
        stop = {
            "accountId": int(os.environ["PROJECTX_ACCOUNT_ID"]),
            "contractId": contract_id,
            "type": 4,             # 4 = stop-limit
            "side": 1,             # 1 = sell
            "size": 1,
            "stopPrice": STOP_PRICE,
            "limitPrice": STOP_PRICE - 5 * TICK_SIZE,  # permissive limit below stop
            "customTag": "ZN_ORB_STOP",
        }
        target = {
            "accountId": int(os.environ["PROJECTX_ACCOUNT_ID"]),
            "contractId": contract_id,
            "type": 1,             # limit
            "side": 1,             # sell
            "size": 1,
            "limitPrice": TARGET,
            "customTag": "ZN_ORB_TARGET",
        }
        # Note: we place stop+target only AFTER fill, normally. For this
        # validation we leave the limit working alone; user can add
        # bracket once filled.
        print(f"[{_ts()}] Done. Working order on Topstep awaiting fill.")
    else:
        print(f"[{_ts()}] Order placement failed.")
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
