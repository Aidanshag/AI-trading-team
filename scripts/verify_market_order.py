"""Live verification of order_type='market' (new mapping → type=2).

Places 1 MGC buy at market, immediately closes via close_position.
Total expected cost: bid/ask spread + commission (~$3-5 on MGC).

We need to confirm:
1. order_type='market' is accepted by broker (no rejection)
2. It actually fills at market (not as a working order)
3. The fill price is reasonable (within spread of current quote)
4. close_position cleanly flattens after
"""
import sys, time, uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv()
from tools.projectx_client import get_client, get_account_id
from tools.bar_fetcher import fetch_bars

client = get_client()
aid = get_account_id()

# Pre-flight: must be flat
positions = client.get_positions(aid) or []
if positions:
    print("ABORT: account not flat")
    for p in positions: print(f"  {p}")
    sys.exit(1)
print("Account flat. Proceeding with live market-order test.")

contract = client.front_month_contract_id("MGC")
print(f"Contract: {contract}")
bars = fetch_bars(client, "MGC", 1, 5)
last_close = float(bars["Close"].iloc[-1]) if bars is not None and len(bars) > 0 else None
print(f"Current MGC last_close: {last_close}")
print()

test_cid = f"MKTVERIFY_{uuid.uuid4().hex[:8]}"
print(f"=== TEST: BUY MARKET 1ct MGC ===")
print(f"order_type='market' (new mapping → type=2)")
try:
    resp = client.place_order(
        account_id=aid, contract_id=contract,
        side="buy", qty=1, order_type="market",
        limit_price=None, stop_price=None,
        time_in_force="day", client_order_id=test_cid,
    )
    print(f"place_order response: {resp}")
    if isinstance(resp, dict) and resp.get("success") is False:
        print(f"❌ REJECTED: {resp.get('errorMessage')}")
        sys.exit(1)
except Exception as e:
    print(f"❌ Raised: {type(e).__name__}: {e}")
    sys.exit(1)

time.sleep(3)
# Check position fill
positions = client.get_positions(aid) or []
print()
print(f"Open positions after market submit: {len(positions)}")
if positions:
    for p in positions:
        avg = p.get("averagePrice") or p.get("avgPrice")
        print(f"  FILLED @ {avg}  size={p.get('size')}  type={p.get('type')}")
        if last_close and avg:
            slip = abs(float(avg) - last_close)
            print(f"  slippage vs last_close ({last_close}): {slip:.2f} pts = {slip/0.10:.1f} ticks")

# Close immediately
print()
print("Closing position via close_position...")
close_result = client.close_position(aid, contract)
print(f"close_position response: {close_result}")
time.sleep(2)

positions_final = client.get_positions(aid) or []
print(f"Open after close: {len(positions_final)}")

# Also cancel any leftover working orders from this test
working_final = client.get_working_orders(aid) or []
for o in working_final:
    if o.get("customTag", "").startswith("MKTVERIFY_"):
        try:
            client.cancel_order(aid, o.get("id"))
            print(f"  cancelled leftover {o.get('customTag')}")
        except Exception: pass

print()
print("=== SUMMARY ===")
if positions and not positions_final:
    print("✅ MARKET ORDER TEST PASSED")
    print("  - Broker accepted order_type='market' (type=2)")
    print("  - Filled at market immediately (not working order)")
    print("  - close_position successfully flattened")
else:
    print("⚠️ TEST INCONCLUSIVE")
    print(f"  positions: {positions}")
    print(f"  positions_final: {positions_final}")
