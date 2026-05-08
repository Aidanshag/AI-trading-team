"""Run a full CIO -> Analyst -> Red Team -> PM -> Risk -> Exec chain.

Validation-mode framing: user wants real test data of the chain end-to-end.
CIO is told to find the best available setup at acceptable conviction; not
forced to trade if nothing exists, but the conviction bar is lowered so
the chain can validate against a real order rather than waiting for an
ideal setup that may not occur today.
"""
from __future__ import annotations
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 on Windows console so agent output with arrows / em-dashes prints
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

env = Path(".env")
for line in env.read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); os.environ.setdefault(k.strip(), v.strip())

from runtime.orchestrator import Orchestrator, _parse_wake_line


CIO_PROMPT = """MIDDAY CHAIN VALIDATION RUN #2 — 2026-04-27 ~12:32 ET.

PRIOR ATTEMPT: You picked Softs Analyst. They returned NO_TRADE because ICE
softs (KC/CT/SB/CC/OJ) AREN'T TRADEABLE ON TOPSTEP — Topstep is CME-only.
Brent (BZ) is also ICE. So softs were dead-on-arrival.

User wants chain end-to-end validation TODAY. Lowered conviction bar from
'high' to 'medium' is in effect. Constraints unchanged: Risk Manager final
veto, no overrides; internal $500 DLL; defensive ladder; 16:00 ET cutoff.

CME-TRADEABLE positioning extremes (from vault/flow/cot_2026-04-26.md):
- Metals: GC SHORT @ 2nd pct, SI/SIL SHORT @ 10th pct (Managed Money low
  in gold/silver — fade-decline candidate)
- Rates: ZF LONG @ 94th pct, ZB LONG @ 90th pct (Lev Funds long in 5Y/30Y
  — fade-rally candidate)
- Grains: ZL LONG @ 100th, ZM LONG @ 95th, ZS LONG @ 89th (oilseed crush
  long crowded)
- Bonds: UB SHORT @ 1st pct (Lev Funds extreme short Ultra Bond)

Goldilocks regime (VIX 19.3, curve +53bp) favors mean-reversion fades.

Your job:
1. topstep_get_account → confirm balance.
2. Pick CME-only sector with cleanest data path. Best picks: Metals,
   Rates, Grains, Index/Macro. AVOID Softs (ICE).
3. Emit EXACTLY ONE wake directive on its own line:
   WAKE: <Analyst Name>

Be concise (<150 words). End with the WAKE line.
"""


def _ts():
    return datetime.now(tz=timezone.utc).strftime("%H:%M:%S")


def _print_step(step_num, name, result):
    print()
    print("=" * 72)
    print(f"[{_ts()}] STEP {step_num}: {name}")
    print("=" * 72)
    text = (result.get("final_text") or "(no final text)").strip()
    print(text[:3000])  # cap to keep readable
    if len(text) > 3000:
        print(f"... [{len(text) - 3000} more chars truncated]")
    usage = result.get("usage") or {}
    if usage:
        print()
        print(f"  tokens: in={usage.get('input_tokens', '?')} "
              f"out={usage.get('output_tokens', '?')} "
              f"cache_read={usage.get('cache_read_input_tokens', '?')}")
    sys.stdout.flush()


async def main():
    orch = Orchestrator()
    print(f"[{_ts()}] orchestrator loaded: "
          f"{len(orch.specs)} agents, {len(orch.mcp_servers)} MCP servers")

    # === STEP 1: CIO chooses analyst ===
    cio = await orch.wake_agent("CIO", CIO_PROMPT)
    _print_step(1, "CIO midday brief + analyst pick", cio)
    analyst = _parse_wake_line(cio.get("final_text", ""))
    if not analyst or analyst.lower() == "none":
        print()
        print(f"[{_ts()}] CIO stood down again. Stopping chain. "
              "Re-run later or wake a specific analyst directly.")
        return
    print(f"[{_ts()}] CIO picked: {analyst}")

    # === STEPS 2-5: full analyst chain ===
    chain = await orch.run_analyst_chain(analyst)
    print()
    print("=" * 72)
    print(f"[{_ts()}] CHAIN COMPLETE")
    print("=" * 72)
    print(f"Final status: {chain.get('status')}")
    for k, v in chain.items():
        if k != "status":
            print(f"  {k}: {str(v)[:200]}")


asyncio.run(main())
