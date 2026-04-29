"""Standalone safety check — verify every open position has a working
stop and target on the broker. Place missing brackets if found.

Run anytime to confirm portfolio safety:
  .\.venv\Scripts\python.exe scripts/verify_brackets.py
"""
from __future__ import annotations
import asyncio, os, sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

env = Path(".env")
for line in env.read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); os.environ.setdefault(k.strip(), v.strip())

from runtime.orchestrator import Orchestrator


async def main():
    orch = Orchestrator()
    print("Verifying all positions have working stops...")
    result = await orch.verify_position_stops()
    print(f"Result: {result}")
    if result.get("fixed", 0) > 0:
        print(f"⚠ Auto-recovered {result['fixed']} missing stop(s)")
    if result.get("flattened", 0) > 0:
        print(f"⚠⚠ Auto-flattened {result['flattened']} unprotected position(s) — no stop level recoverable")
    if result.get("checked", 0) == 0:
        print("No open positions.")
    elif result.get("fixed", 0) == 0 and result.get("flattened", 0) == 0:
        print("✓ All positions protected.")


asyncio.run(main())
