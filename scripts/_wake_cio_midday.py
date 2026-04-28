"""Wake CIO with midday-start context. Single-shot."""
from __future__ import annotations
import asyncio, os
from pathlib import Path

# Load .env
env = Path(".env")
for line in env.read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); os.environ.setdefault(k.strip(), v.strip())

from runtime.orchestrator import Orchestrator


TASK = """MIDDAY SESSION START — 2026-04-27 ~12:21 ET (Monday).

Today is Monday, the user is starting the trading session midday after a delayed start.
Auto-halt expired at 09:30 ET as planned. Account: $50,000, no open positions.
Session-end cutoff: 16:00 ET (15:00 CT). User has authorized: no trade cap, no risk
manager overrides, halt re-engages at session close.

Your job RIGHT NOW:

1. Read account state via topstep_get_account to confirm balance + tradeable status.

2. Read TODAY's regime context (fresh data layer is now wired):
   - FRED: VIX ~19.3 (low-mid vol), 10Y yield 4.34%, 2Y 3.83%, curve uninverted +53bp,
     Fed funds upper 3.75%, unemployment 4.3%
   - CFTC positioning extremes (per vault/flow/cot_2026-04-26.md):
       Crowded LONG: CT, ZL, ZM (>=95th pct); ZF, ZB rates (90-94th pct)
       Crowded SHORT: CC (1st), GC/MGC (2nd), SI/SIL (10th), UB (1st)
   - EIA: crude stocks 465.7Mbbl, nat gas storage 616 Bcf

3. Acknowledge the constraints of a midday entry:
   - Opening drive / ORB strategies are out (already happened)
   - Limited time horizon (~3.5h RTH remaining)
   - Setups should favor: pullback continuation, late-day mean-reversion,
     positioning-extreme fades

4. Decide and emit: either ONE clean WAKE: <Analyst Name> directive on its own
   line if you see a setup worth pursuing, or a stand-down message if the
   risk/reward of starting cold doesn't justify a trade today.

Be concise (under 250 words). Output the brief, then your single WAKE: line
(or "WAKE: none" if standing down).
"""


async def main():
    orch = Orchestrator()
    print(f"Loaded {len(orch.specs)} agent specs, {len(orch.mcp_servers)} MCP servers.")
    print()
    result = await orch.wake_agent("CIO", TASK)
    print("=" * 72)
    print("CIO RESPONSE")
    print("=" * 72)
    text = result.get("final_text") or "(no final text)"
    print(text)
    print()
    print("=" * 72)
    usage = result.get("usage") or {}
    if usage:
        print(f"Tokens: input={usage.get('input_tokens', '?')} "
              f"output={usage.get('output_tokens', '?')} "
              f"cache_read={usage.get('cache_read_input_tokens', '?')}")
    if result.get("stub"):
        print("[!!! ] STUB RESPONSE — SDK not loaded in this Python")


asyncio.run(main())
