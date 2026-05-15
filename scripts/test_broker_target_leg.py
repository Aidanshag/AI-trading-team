"""Phase 4 — re-test broker target-leg behavior.

The 2026-05-11 anomaly: target LIMIT orders auto-filled at next-available
market instead of sitting as working orders. As a workaround,
`scripts/live_trader.py:SKIP_TARGET_LEG = True` was set — we manage
take-profit in software via tools/profit_protect.py instead.

This script tests whether the broker behavior has lifted by placing
a non-marketable SELL LIMIT on MGC well above the current ask. If
the order STAYS as 'open' for 60s, the bug is lifted. If it FILLS
at market, the bug persists.

Safety:
  - 1 contract MGC (smallest position, $1/tick)
  - Limit placed 30 ticks ($3) above current ask — definitively non-marketable
  - Auto-cancel after 60s regardless
  - If filled (bug confirmed), immediately flatten via close_position

Worst-case cost: ~$5 (bid/ask spread + close slippage).

Usage:
    .venv/Scripts/python.exe -m scripts.test_broker_target_leg
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load .env
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for raw in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip(); v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v

sys.path.insert(0, str(PROJECT_ROOT))

from tools.projectx_client import ProjectXClient, get_account_id  # noqa: E402

TEST_SYMBOL = "MGC"
TEST_OFFSET_TICKS = 30   # 30 ticks above ask = $3 above market
TICK_SIZE = 0.10
OBSERVATION_SECONDS = 60


def main() -> int:
    client = ProjectXClient()
    client.authenticate()
    acct = get_account_id()
    contract_id = client.front_month_contract_id(TEST_SYMBOL)
    print(f"=== broker target-leg test ===")
    print(f"contract: {contract_id}")
    print()

    # Get current price (use last from latest 1-min bars)
    try:
        bars = client.get_bars(contract_id,
            "2026-05-15T00:00:00Z",
            "2026-05-15T23:59:59Z",
            unit=2, unit_number=1, limit=5, live=False) or []
        if not bars:
            print("ERROR: no recent bars; market may be closed")
            return 1
        # Bars come newest-first
        last_close = float(bars[0].get("c") or bars[0].get("close") or 0)
        print(f"current MGC ~{last_close:.2f}")
    except Exception as e:
        print(f"ERROR fetching bars: {e}")
        return 1

    # Compute non-marketable SELL LIMIT — 30 ticks ABOVE current
    test_limit_price = round(last_close + TEST_OFFSET_TICKS * TICK_SIZE, 2)
    print(f"placing SELL LIMIT {test_limit_price} (= last_close + {TEST_OFFSET_TICKS}t = +${TEST_OFFSET_TICKS * TICK_SIZE:.2f} above current)")
    print(f"if it stays 'open' for {OBSERVATION_SECONDS}s, the broker bug lifted.")
    print(f"if it 'fills' at market, the bug persists. Will flatten immediately.")
    print()

    import uuid
    test_cid = f"phase4test_{uuid.uuid4().hex[:8]}"

    # Place the test order
    try:
        result = client.place_order(
            account_id=acct,
            contract_id=contract_id,
            side="sell",
            qty=1,
            order_type="limit",
            limit_price=test_limit_price,
            client_order_id=test_cid,
        )
    except Exception as e:
        print(f"ERROR placing order: {e}")
        return 1

    if isinstance(result, dict) and result.get("success") is False:
        print(f"ORDER REJECTED: {result.get('errorMessage')}")
        return 1

    order_id = result.get("orderId") or result.get("id")
    print(f"order placed: id={order_id} tag={test_cid}")
    print(f"observing for {OBSERVATION_SECONDS}s ...")
    print()

    # Poll order status every 5 seconds
    final_status = None
    final_status_code = None
    for i in range(OBSERVATION_SECONDS // 5):
        time.sleep(5)
        try:
            history = client.get_order_history(acct,
                start_timestamp="2026-05-15T00:00:00Z")
            match = None
            for o in history:
                if (o.get("customTag") == test_cid
                    or str(o.get("id")) == str(order_id)):
                    match = o
                    break
            if match:
                status_code = match.get("status")
                status_map = {1: "Open", 2: "Filled", 3: "Cancelled",
                                4: "Expired", 5: "Rejected", 6: "Pending"}
                final_status = status_map.get(status_code, f"unknown({status_code})")
                final_status_code = status_code
                fill_px = match.get("filledPrice")
                elapsed = (i + 1) * 5
                print(f"  +{elapsed:>3}s  status={final_status}  fill={fill_px}")
                if status_code != 1:  # not 'Open' = something happened
                    break
        except Exception as e:
            print(f"  poll error: {e}")

    print()
    # Decide outcome
    if final_status_code == 1:
        # Still open — bug lifted!
        print(f"RESULT: bug LIFTED — order stayed 'Open' for {OBSERVATION_SECONDS}s")
        print(f"  RECOMMENDATION: flip SKIP_TARGET_LEG=False in scripts/live_trader.py")
    elif final_status_code == 2:
        # Filled — bug present
        print(f"RESULT: bug PRESENT — order auto-filled at {match.get('filledPrice')}")
        print(f"  RECOMMENDATION: keep SKIP_TARGET_LEG=True")
        # Need to flatten the position
        print(f"  flattening accidental short position ...")
        try:
            close_result = client.close_position(acct, contract_id)
            print(f"  close result: {close_result}")
        except Exception as e:
            print(f"  CLOSE FAILED: {e}")
    else:
        print(f"RESULT: order ended in unexpected status: {final_status} ({final_status_code})")

    # Cancel the order regardless (in case it's still open)
    if final_status_code == 1:  # still open
        print(f"  cancelling test order ...")
        try:
            client.cancel_order(acct, order_id)
            print(f"  cancelled")
        except Exception as e:
            print(f"  CANCEL FAILED: {e}")

    return 0 if final_status_code in (1, 2) else 1


if __name__ == "__main__":
    sys.exit(main())
