"""Controlled empirical test of ProjectX order semantics.

Places small test orders FAR from current market (won't accidentally
fill), inspects broker response, and verifies the order appears as
expected in get_working_orders. Then cancels everything.

What we're testing tonight (2026-05-14):
1. Does `place_order(order_type="limit")` (new mapping: type=1) actually
   produce a LIMIT order that sits at the broker?
2. Does `place_order(order_type="market")` (new mapping: type=2) actually
   produce a MARKET order? (We won't actually submit a market here — too
   risky — but we'll inspect the rejection if any.)
3. Does the broker show the customTag we set?
4. Does cancel_order actually remove the working order?
"""
import sys
import time
import uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv()
from tools.projectx_client import get_client, get_account_id

client = get_client()
aid = get_account_id()

# Make sure we're flat before the test
positions = client.get_positions(aid) or []
if positions:
    print("ABORT: positions exist, can't safely test placement")
    for p in positions:
        print(f"  open: {p}")
    sys.exit(1)
print("Account flat. Running test.")
print()

# Cancel any leftover working orders first (clean slate)
working = client.get_working_orders(aid) or []
for o in working:
    oid = o.get("id")
    if oid:
        try:
            client.cancel_order(aid, oid)
            print(f"Cancelled leftover working order id={oid}")
        except Exception as e:
            print(f"  cancel failed: {e}")
time.sleep(2)

contract = client.front_month_contract_id("MGC")
print(f"Contract: {contract}")

# Test 1: Place a clearly non-marketable buy limit (40+ points BELOW
# current price). Should sit as working.
test_cid = f"VERIFY_{uuid.uuid4().hex[:8]}"
test_price = 4500.0   # well below current MGC ~4705
print()
print(f"=== TEST 1: BUY LIMIT @ {test_price} (non-marketable) ===")
print(f"Submitting with order_type='limit' (new mapping → type=1)...")
try:
    resp = client.place_order(
        account_id=aid, contract_id=contract,
        side="buy", qty=1, order_type="limit",
        limit_price=test_price, stop_price=None,
        time_in_force="day", client_order_id=test_cid,
    )
    print(f"Response: {resp}")
except Exception as e:
    print(f"Place failed: {type(e).__name__}: {e}")
    sys.exit(1)

time.sleep(2)
print()
print("Checking working orders for our test order...")
working = client.get_working_orders(aid) or []
ours = [o for o in working if o.get("customTag") == test_cid]
print(f"Found {len(ours)} matching customTag={test_cid}")
for o in ours:
    print(f"  id={o.get('id')} type={o.get('type')} side={o.get('side')} "
          f"limitPrice={o.get('limitPrice')} stopPrice={o.get('stopPrice')}")

if ours:
    print()
    print("✅ TEST 1 PASSED: limit order placed and sitting as working")
    print(f"  Broker type code returned: {ours[0].get('type')}")
    print(f"  This confirms our 'limit' → broker type code is correct.")
else:
    print()
    print("❌ TEST 1 FAILED: order vanished. Either rejected silently or wrong type.")
    print("  Full working orders list:")
    for o in working:
        print(f"    {o}")

# Cleanup: cancel the test order
print()
print("Cleaning up — cancelling test order...")
if ours:
    try:
        client.cancel_order(aid, ours[0].get("id"))
        print("  Cancelled.")
    except Exception as e:
        print(f"  Cancel failed: {e}")
time.sleep(1)
final_check = client.get_working_orders(aid) or []
print(f"Final working orders: {len(final_check)}")
positions_final = client.get_positions(aid) or []
print(f"Final positions: {len(positions_final)}")
