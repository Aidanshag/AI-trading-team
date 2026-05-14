"""One-shot: close the open MGC position via the native close_position
endpoint (the place_order market-IOC path appears broken)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv()
from tools.projectx_client import get_client, get_account_id

client = get_client()
aid = get_account_id()
positions = client.get_positions(aid) or []
print(f"Open positions before close: {len(positions)}")
for p in positions:
    cid = p.get("contractId")
    print(f"  closing {cid}...")
    try:
        result = client.close_position(aid, cid)
        print(f"    response: {result}")
    except Exception as e:
        print(f"    FAILED: {type(e).__name__}: {e}")

import time; time.sleep(2)
positions_after = client.get_positions(aid) or []
print(f"Open positions after close: {len(positions_after)}")
for p in positions_after:
    print(f"  still open: {p}")
