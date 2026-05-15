"""Pinpoint which subscribe method is the right one.

The first probe showed events DO flow but 5 candidate methods were
fired in one batch. This narrows down by trying ONE method at a time
with a 5s wait between to see which one actually triggers events.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
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
from tools.projectx_client import ProjectXClient  # noqa: E402
from signalrcore.hub_connection_builder import HubConnectionBuilder  # noqa: E402


def main() -> int:
    client = ProjectXClient(); client.authenticate()
    jwt = client._jwt
    cid_mgc = client.front_month_contract_id("MGC")
    print(f"Probing with {cid_mgc}")

    methods = [
        "SubscribeContractQuotes",
        "SubscribeContract",
        "SubscribeQuote",
        "Subscribe",
        "SubscribeContractMarketData",
    ]

    for method in methods:
        hub = (
            HubConnectionBuilder()
            .with_url("https://rtc.topstepx.com/hubs/market",
                       options={"access_token_factory": lambda: jwt,
                                  "skip_negotiation": False})
            .configure_logging(50)  # CRITICAL only
            .build()
        )
        events = []
        hub.on("GatewayQuote", lambda args, evs=events: evs.append(args))
        hub.start()
        time.sleep(1)
        try:
            hub.send(method, [cid_mgc])
        except Exception as e:
            print(f"  {method:35} send raised: {e}")
            try: hub.stop()
            except Exception: pass
            continue
        time.sleep(4)  # 4s window to receive ticks
        try: hub.stop()
        except Exception: pass
        time.sleep(0.5)
        print(f"  {method:35} -> {len(events)} GatewayQuote events")
    return 0


if __name__ == "__main__":
    sys.exit(main())
