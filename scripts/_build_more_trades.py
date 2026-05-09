"""Active trade-builder — rotate analysts, ship anything Risk Manager approves.

User has explicitly authorized full team trading authority for rest of
session. The team's discipline is preserved (Risk Manager veto is law),
but we drive analyst rotation aggressively to find setups.

Stops on:
  - 3 successful executions, OR
  - $4 cumulative spend today, OR
  - 5 attempts with no thesis through PM
"""
from __future__ import annotations
import asyncio, os, sys, re
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

from runtime.orchestrator import Orchestrator, _parse_wake_line


# Energies first — CIO already flagged Hormuz/CL theme this session.
# Then Index/Macro (live equity tape), then Rates (curve crowded long).
# Skip Softs (ICE), Metals (already tried + tape down), Grains (off-season),
# FX (already produced M6B trade — diminishing returns on second FX wake).
ROTATION = [
    "Energies Analyst",
    "Index/Macro Analyst",
    "Rates Analyst",
]

ANALYST_PROMPT = """ACTIVE TRADE WINDOW. User has authorized full team
trading authority for rest of session. M6B trade already placed via
FX desk. Looking for one more clean defined-risk setup in your sector.

Conviction bar: medium acceptable; low acceptable IF defined-risk
with R:R ≥ 2:1 and complete checklist.

Sector context for you specifically:
- Energies: CIO flagged Hormuz/CL risk this session as the dominant
  macro theme. Live news suggests US-Iran tensions. Crude has been
  rallying. EIA Wed inventory data not in cache yet (next release).
- Index/Macro: VIX 19.31 low-mid, curve uninverted +53bp, Fed funds
  3.75%. Goldilocks regime. ES around 4750. Earnings week ongoing.
- Rates: ZF/ZB at 90-94th pct LONG specs. Crowded long bonds.
  Fade-rally setup possible if 5Y/30Y at resistance.

Required output if you find a setup (else NO_TRADE):

THESIS: <SYMBOL> conviction=<low|med|high>

Then a complete pre-trade checklist (12 questions). Cite a specific
strategy from your library by name. R:R ≥ 2.0:1. Complete invalidation
(must fire before stop). State stop in ticks (so PM can math the risk).
"""


def _ts(): return datetime.now(tz=timezone.utc).strftime("%H:%M:%S")


def _spent_today(orch) -> float:
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    return float(orch.db.connect().execute(
        "SELECT COALESCE(SUM(usd_est), 0) FROM costs WHERE day = ?", (today,)
    ).fetchone()[0] or 0.0)


def _detect_pm_decision(text: str) -> str:
    t = text.upper()
    m = re.search(r"DECISION\s*[:\-]\s*(PROPOSE|PASS)\b", t)
    if m: return m.group(1)
    return "PROPOSE" if t.rstrip().endswith("PROPOSE") else "PASS"


async def main():
    orch = Orchestrator()
    print(f"[{_ts()}] orchestrator loaded.")
    print(f"[{_ts()}] starting spend: ${_spent_today(orch):.2f}")
    print()

    executed = 0
    no_thesis_count = 0

    for i, analyst in enumerate(ROTATION, 1):
        spent = _spent_today(orch)
        print("=" * 72)
        print(f"[{_ts()}] ATTEMPT {i}: {analyst}  spent_today=${spent:.2f}")
        print("=" * 72)
        if spent >= 4.00:
            print(f"[{_ts()}] BUDGET CAP HIT (${spent:.2f}). Stopping.")
            break
        if executed >= 3:
            print(f"[{_ts()}] 3 EXECUTIONS HIT. Stopping.")
            break
        if no_thesis_count >= 5:
            print(f"[{_ts()}] 5 NO-THESIS RESULTS. Stopping.")
            break

        # Step 1: Analyst
        a_result = await orch.wake_agent(analyst, ANALYST_PROMPT)
        text = a_result.get("final_text", "") or ""
        print(text[:1500])
        print()

        thesis = orch._latest_thesis_for(analyst)
        if not thesis or "THESIS:" not in text.upper():
            print(f"[{_ts()}] {analyst} -> NO_TRADE")
            no_thesis_count += 1
            continue

        # Step 2: Red Team if med/high
        conviction = (thesis.get("conviction") or "low").lower()
        challenge = None
        if conviction in ("med", "high"):
            print(f"[{_ts()}] Red Team challenge (conviction={conviction})")
            challenge = await orch.wake_agent(
                "Red Team",
                f"Challenge this thesis: {thesis}. Verdict strong|gaps|weak. <500 words.",
            )

        # Step 3: PM
        print(f"[{_ts()}] PM evaluation")
        pm_result = await orch.wake_agent(
            "Portfolio Manager",
            f"Thesis: {thesis}\nRed Team: "
            f"{challenge.get('final_text','n/a') if challenge else 'skipped (low)'}\n\n"
            "Decide pursue|pass. If pursue, produce order proposal "
            "(symbol, side, qty, order_type, stop_loss_price, target_price). "
            "Record via state_record_decision kind=order_proposal. "
            "End with EXACTLY: 'DECISION: PROPOSE' or 'DECISION: PASS'."
        )
        decision = _detect_pm_decision(pm_result.get("final_text", "") or "")
        print(f"[{_ts()}] PM: {decision}")

        if decision != "PROPOSE":
            print(f"[{_ts()}] PM passed. Rotating.")
            continue

        proposal = orch._latest_proposal()
        if not proposal:
            print(f"[{_ts()}] No proposal recorded. Skipping.")
            continue

        # Step 4: Risk Manager + Exec via submit_proposal (now with fixed parser)
        print(f"[{_ts()}] submit_proposal: Risk Manager + Execution")
        result = await orch.submit_proposal(proposal)
        print(f"[{_ts()}] FINAL: {result.get('status')}")
        if result.get("status") == "executed":
            executed += 1
            print(f"*** TRADE {executed} EXECUTED via {analyst} ***")
        print()

    print()
    print("=" * 72)
    print(f"[{_ts()}] ROTATION COMPLETE")
    print(f"  Trades executed: {executed}")
    print(f"  Final spend: ${_spent_today(orch):.2f}")
    print("=" * 72)


asyncio.run(main())
