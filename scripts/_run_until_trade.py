"""Rotate through CME-tradeable analysts until a trade executes or we hit caps.

User directive: "let them trade." Two prior chains correctly stood down.
This driver tries the analyst rotation that hasn't been tested yet, with
explicit framing that the user wants validation-grade test data.

Stops when ANY of:
  - A trade actually executes (Risk Manager allow + order shipped)
  - 5 analyst attempts made
  - Cumulative spend exceeds $3.00
  - Risk Manager blocks 3 times in a row (saturation signal)
"""
from __future__ import annotations
import asyncio, os, sys
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

env = Path(".env")
for line in env.read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); os.environ.setdefault(k.strip(), v.strip())

from runtime.orchestrator import Orchestrator
import sqlite3

# CME-tradeable rotation. Already tried Softs (ICE) and Metals (down-tape).
# Picking analysts whose sectors have actionable extremes or clean trends.
ROTATION = [
    "Index/Macro Analyst",   # ES/NQ/RTY/YM — broad CME, goldilocks regime
    "Rates Analyst",          # ZN/ZF/ZB/UB — 90th+ pct positioning crowded long
    "Energies Analyst",       # CL/NG/RB/HO — Iran tensions context per news
    "Grains Analyst",         # ZC/ZS/ZW/ZL/ZM — ZL/ZM crowded long
    "FX Futures Analyst",     # 6E/6B/6J/6A — 6A at 81st pct
]

ANALYST_PROMPT = """VALIDATION CHAIN RUN. User has authorized a lower
conviction floor (down to "low") for this chain in exchange for real
end-to-end test data. Your standard discipline applies otherwise:
- Setup must be REAL (rule-based, not vibes), not forced
- Must match an entry from your strategy library
- Must be CME-tradeable (no ICE softs, no Brent)
- Defined-risk only — no naked shorts on outright futures

If you find ANY rule-based setup with even low conviction, write a thesis
and emit "THESIS: <SYMBOL> conviction=low" (or med/high if warranted).

If after honest research you cannot find ANY rule-based setup, emit
"NO_TRADE: <reason>".

Available data: FRED macro, CFTC positioning (vault/flow/cot_2026-04-26.md),
EIA energies, live Topstep quotes, news RSS.
"""


def _spent_today_usd(db) -> float:
    today_utc = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    row = db.connect().execute(
        "SELECT COALESCE(SUM(usd_est), 0) FROM costs WHERE day = ?",
        (today_utc,),
    ).fetchone()
    return float(row[0] or 0.0)


def _ts(): return datetime.now(tz=timezone.utc).strftime("%H:%M:%S")


async def main():
    orch = Orchestrator()
    print(f"[{_ts()}] orchestrator loaded. Starting analyst rotation.")
    print(f"[{_ts()}] caps: 5 attempts, $3.00 budget, 3 consecutive risk blocks")
    print(f"[{_ts()}] starting spend: ${_spent_today_usd(orch.db):.2f}")
    print()

    consecutive_risk_blocks = 0
    for i, analyst in enumerate(ROTATION, 1):
        spent = _spent_today_usd(orch.db)
        print("=" * 72)
        print(f"[{_ts()}] ATTEMPT {i}/5  analyst={analyst}  spent_today=${spent:.2f}")
        print("=" * 72)
        if spent >= 3.00:
            print(f"[{_ts()}] BUDGET CAP HIT (${spent:.2f} >= $3.00). Stopping.")
            break
        if consecutive_risk_blocks >= 3:
            print(f"[{_ts()}] 3 CONSECUTIVE RISK BLOCKS. Saturation. Stopping.")
            break

        # Patch the prompt the orchestrator's run_analyst_chain uses by
        # using wake_agent directly with our own prompt then submit_proposal.
        a_result = await orch.wake_agent(analyst, ANALYST_PROMPT)
        text = (a_result.get("final_text") or "")
        print(text[:1500])
        print()

        # Did the analyst record a thesis?
        thesis = orch._latest_thesis_for(analyst)
        if not thesis or "THESIS:" not in text.upper():
            print(f"[{_ts()}] {analyst} -> NO_TRADE. Rotating.")
            print()
            consecutive_risk_blocks = 0
            continue

        # Got a thesis. Run the back half of the chain.
        print(f"[{_ts()}] {analyst} produced thesis. Running PM -> Risk -> Exec.")
        conviction = (thesis.get("conviction") or "low").lower()
        challenge = None
        if conviction in ("med", "high"):
            challenge = await orch.wake_agent(
                "Red Team",
                f"Challenge this thesis: {thesis}. Verdict strong|gaps|weak. <500 words.",
            )

        pm_result = await orch.wake_agent(
            "Portfolio Manager",
            f"Thesis: {thesis}\nRed Team: "
            f"{challenge.get('final_text','n/a') if challenge else 'skipped (low)'}\n\n"
            "Decide pursue|pass. If pursue, produce order proposal "
            "(symbol, side, qty, order_type, stop, target, rationale). "
            "Record via state_record_decision kind=order_proposal. "
            "End with PROPOSE or PASS.",
        )
        if "PROPOSE" not in pm_result.get("final_text", "").upper():
            print(f"[{_ts()}] PM passed. Rotating.")
            consecutive_risk_blocks = 0
            continue

        proposal = orch._latest_proposal()
        if not proposal:
            print(f"[{_ts()}] PM said PROPOSE but no proposal recorded. Rotating.")
            consecutive_risk_blocks = 0
            continue

        # Risk Manager + Execution
        result = await orch.submit_proposal(proposal)
        print(f"[{_ts()}] Chain final status: {result.get('status')}")

        if result.get("status") == "executed":
            print()
            print("=" * 72)
            print(f"[{_ts()}] *** TRADE EXECUTED *** by {analyst} chain")
            print("=" * 72)
            print(f"Final spend: ${_spent_today_usd(orch.db):.2f}")
            return
        elif result.get("status") == "blocked_by_risk":
            consecutive_risk_blocks += 1
            print(f"[{_ts()}] Risk Manager veto #{consecutive_risk_blocks}.")
        else:
            consecutive_risk_blocks = 0

    print()
    print("=" * 72)
    print(f"[{_ts()}] ROTATION COMPLETE — no trade executed.")
    print(f"Final spend: ${_spent_today_usd(orch.db):.2f}")
    print("=" * 72)


asyncio.run(main())
