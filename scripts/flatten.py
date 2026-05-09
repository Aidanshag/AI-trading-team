"""Emergency flatten: cancel all working orders + close all positions.

Used by `fund flatten` (scripts/fund.ps1) and any other panic-button scenario.
Safe to run anytime; idempotent if already flat.
"""
from __future__ import annotations
import os
import sys
import time
from pathlib import Path

# Pin cwd so config + state paths resolve regardless of how invoked
HERE = Path(__file__).resolve().parent.parent
os.chdir(HERE)
from dotenv import load_dotenv
load_dotenv()

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from tools.projectx_client import get_client, get_account_id


def main() -> int:
    client = get_client()
    aid = get_account_id()

    # 1. Cancel working orders
    print("Cancelling all working orders...")
    cancelled = 0
    for o in client.get_working_orders(aid):
        try:
            client.cancel_order(aid, o.get("id"))
            cancelled += 1
        except Exception as e:
            print(f"  failed to cancel {o.get('id')}: {e}")
    print(f"  cancelled {cancelled} order(s)")
    time.sleep(1)

    # 2. Close positions
    print("Closing all positions...")
    closed = 0
    for p in client.get_positions(aid):
        if int(p.get("size", 0)) == 0:
            continue
        try:
            client.close_position(aid, p.get("contractId"))
            print(f"  closed {p.get('contractId')} (size={p.get('size')})")
            closed += 1
        except Exception as e:
            print(f"  failed to close {p.get('contractId')}: {e}")
    time.sleep(2)

    # 3. Verify
    positions = client.get_positions(aid)
    orders = client.get_working_orders(aid)
    open_pos = [p for p in positions if int(p.get("size", 0)) != 0]
    print()
    print("=== Final state ===")
    print(f"  Open positions: {len(open_pos)}")
    print(f"  Working orders: {len(orders)}")
    for a in client.get_accounts():
        if str(a.get("id")) == str(aid):
            print(f"  Balance: ${a.get('balance', 0):,.2f}")
            break
    return 0 if not open_pos and not orders else 1


if __name__ == "__main__":
    sys.exit(main())
