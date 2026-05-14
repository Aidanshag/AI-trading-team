"""Diagnostic — show current open positions + profit-lock decision state."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv()

from tools.projectx_client import get_client, get_account_id
from tools.profit_protect import (
    decide, _unrealized_usd, _TICK_ECONOMICS, _contract_to_symbol,
    _strip_exchange_suffix, _position_high_water,
)
from tools.bar_fetcher import fetch_bars


def main():
    client = get_client()
    aid = get_account_id()
    print(f"account_id={aid}")
    print()

    positions = client.get_positions(aid) or []
    print(f"=== open positions: {len(positions)} ===")
    for p in positions:
        print(f"  raw: {p}")
    print()

    if not positions:
        print("(no positions)")
        return 0

    for p in positions:
        size = int(p.get("size") or 0)
        if size == 0:
            continue
        cid = p.get("contractId", "")
        avg = float(p.get("averagePrice") or p.get("avgPrice") or 0)
        if avg <= 0:
            print(f"  {cid}: avgPrice missing/zero")
            continue
        type_code = int(p.get("type") or 0)
        side = ("long" if type_code == 1
                  else "short" if type_code == 2
                  else ("long" if size > 0 else "short"))
        raw_sym = _contract_to_symbol(cid) or ""
        sym = _strip_exchange_suffix(raw_sym)
        tick_size, tick_value = _TICK_ECONOMICS.get(sym, (0, 0))
        try:
            bars = fetch_bars(client, sym, 1, 5)
        except Exception as e:
            print(f"  {sym}: fetch_bars failed: {e}")
            continue
        last = float(bars["Close"].iloc[-1]) if bars is not None and len(bars) > 0 else None
        if last is None:
            print(f"  {sym}: no recent bars")
            continue
        unrealized = _unrealized_usd(side, abs(size), avg, last, tick_size, tick_value)
        key = f"{sym}_{side}"
        peak = _position_high_water.get(key, unrealized)
        peak = max(peak, unrealized)
        print(f"=== {sym} {side} {size}ct ===")
        print(f"  avg_price:  {avg}")
        print(f"  last bar:   {last}")
        print(f"  unrealized: ${unrealized:+.2f}")
        print(f"  peak (process-local): ${peak:+.2f}")
        print(f"  tick_size={tick_size}  tick_value=${tick_value}")
        should, reason = decide(unrealized, peak)
        print(f"  profit-lock should_close: {should}")
        print(f"  reason: {reason!r}")
        print()

    # Also show working orders
    try:
        working = client.get_working_orders(aid) or []
    except Exception as e:
        print(f"get_working_orders failed: {e}")
        return 0
    print(f"=== working orders: {len(working)} ===")
    for o in working:
        print(f"  {o}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
