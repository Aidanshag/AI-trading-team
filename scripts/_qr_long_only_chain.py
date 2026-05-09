"""Wake QR with defined-risk LONG-only framing, then drive full chain.

Prior QR run produced a 6E SHORT setup which is naked-short-blocked by
the risk hook. This run constrains QR to long-only or defined-risk
options structures. PM has specialist-wake authority. Risk Manager has
final say. Goal: get a second working order on Topstep before close.
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

from runtime.orchestrator import Orchestrator


QR_PROMPT = """LONG-ONLY INTRADAY SCAN. Constraints:
- Defined-risk LONG futures only, OR defined-risk options structures
  (vertical spreads, butterflies). NO naked shorts.
- R:R ≥ 2.0:1 required.
- Conviction floor: low acceptable if 12-checklist complete and R:R clean.
- CME-tradeable only (no ICE softs/Brent).

Your prior scan correctly identified a 6E vol_regime_trend SHORT, but
naked short futures are categorically blocked here. Either:
(a) Find a different LONG setup that triggers right now, OR
(b) Convert a bearish view to a defined-risk options structure
    (e.g., long puts or short call spread on the underlying).

Use your full advanced-math toolkit. Apply physics overlays (Hawkes
intensity, Marchenko-Pastur, power-law tails) where they sharpen the
edge. Document which mathematical/physical method you used.

CRITICAL: When you find a setup, you MUST call
`state_record_decision` with:
  agent_name = "Quant Researcher"  (exact, with space and capitals)
  kind = "thesis"
  symbol = <SYMBOL>
  summary = <one-line>
  rationale = <full pre-trade checklist + math methods used>

Then end your response with EXACTLY:
  THESIS: <SYMBOL> conviction=<low|med|high>
or:
  NO_TRADE: <one-line reason>

If nothing triggers cleanly, NO_TRADE is acceptable. Don't manufacture.
"""


def _ts(): return datetime.now(tz=timezone.utc).strftime("%H:%M:%S")


def _detect_pm_decision(text: str) -> str:
    t = text.upper()
    m = re.search(r"DECISION\s*[:\-]\s*(PROPOSE|PASS)\b", t)
    if m: return m.group(1)
    return "PROPOSE" if t.rstrip().endswith("PROPOSE") else "PASS"


async def main():
    orch = Orchestrator()
    print(f"[{_ts()}] orchestrator loaded.")

    # Step 1: QR with long-only framing
    print()
    print("=" * 72)
    print(f"[{_ts()}] STEP 1: Quant Researcher — long-only scan")
    print("=" * 72)
    q_result = await orch.wake_agent("Quant Researcher", QR_PROMPT)
    text = q_result.get("final_text", "") or ""
    print(text[:2500])
    print()

    if "THESIS:" not in text.upper():
        print(f"[{_ts()}] No thesis. End.")
        return

    # Step 2: pull thesis (now with fuzzy agent-name matching)
    thesis = orch._latest_thesis_for("Quant Researcher")
    if not thesis:
        print(f"[{_ts()}] Thesis not in DB even with fuzzy match. End.")
        return
    print(f"[{_ts()}] thesis found: {thesis['symbol']} "
          f"conviction={thesis['conviction']} agent={thesis['agent']}")

    # Step 3: Red Team if med/high
    conviction = (thesis.get("conviction") or "low").lower()
    challenge = None
    if conviction in ("med", "high"):
        print()
        print("=" * 72)
        print(f"[{_ts()}] STEP 2: Red Team challenge")
        print("=" * 72)
        challenge = await orch.wake_agent(
            "Red Team",
            f"Challenge this Quant thesis: {thesis}. "
            "Verdict strong|gaps|weak. <500 words.",
        )

    # Step 4: PM (with specialist-wake authority via run_analyst_chain logic)
    print()
    print("=" * 72)
    print(f"[{_ts()}] STEP 3: Portfolio Manager (with specialist-wake)")
    print("=" * 72)
    autonomous = True  # explicit for this run
    pm_first = (
        f"Thesis from Quant Researcher: {thesis}\n"
        f"Red Team: {challenge.get('final_text','n/a') if challenge else 'skipped (low conv)'}\n\n"
        "Step 1 — Optionally consult specialists by emitting:\n"
        "  WAKE_SPECIALIST: <agent> | <focused question>\n"
        "Allowed: Macro Strategist, Flow Analyst, Volatility Strategist, Execution Specialist.\n"
        "Up to 3 in parallel.\n\n"
        "Step 2 — Decide pursue|pass. If pursue, produce order_proposal "
        "(symbol, side, qty, order_type, stop_loss_price, target_price, rationale). "
        "Record via state_record_decision kind=order_proposal. "
        "End with EXACTLY: 'DECISION: PROPOSE' or 'DECISION: PASS'."
    )
    pm_result = await orch.wake_agent("Portfolio Manager", pm_first)
    pm_text = pm_result.get("final_text", "") or ""

    # Step 4b: if specialists requested, wake them and re-prompt PM
    if "WAKE_SPECIALIST:" in pm_text.upper():
        print(f"[{_ts()}] PM requested specialist consults — waking in parallel")
        consults = await orch.pm_wake_specialists(pm_text, thesis, max_wakes=3)
        print(f"[{_ts()}] {len(consults)} specialists responded")
        if consults:
            consult_summary = "\n\n".join(
                f"--- {r['specialist']} on '{r['question']}' ---\n{r['response']}"
                for r in consults
            )
            pm_second = (
                f"Thesis: {thesis}\n"
                f"Red Team: {challenge.get('final_text','n/a') if challenge else 'skipped'}\n\n"
                f"Specialist consults you requested:\n{consult_summary}\n\n"
                "Now make your final decision. Produce order_proposal if pursuing. "
                "Record via state_record_decision kind=order_proposal. "
                "End with EXACTLY: 'DECISION: PROPOSE' or 'DECISION: PASS'."
            )
            pm_result = await orch.wake_agent("Portfolio Manager", pm_second)
            pm_text = pm_result.get("final_text", "") or ""

    print(pm_text[:2500])
    decision = _detect_pm_decision(pm_text)
    print()
    print(f"[{_ts()}] PM: {decision}")

    if decision != "PROPOSE":
        print(f"[{_ts()}] PM passed. End.")
        return

    proposal = orch._latest_proposal()
    if not proposal:
        print(f"[{_ts()}] PM said PROPOSE but no proposal recorded. End.")
        return

    # Step 5: Risk Manager + Execution
    print()
    print("=" * 72)
    print(f"[{_ts()}] STEP 4: Risk Manager + Execution")
    print("=" * 72)
    result = await orch.submit_proposal(proposal)
    print(f"[{_ts()}] CHAIN STATUS: {result.get('status')}")
    if result.get("result"):
        rt = (result["result"].get("final_text") or "")[:2500]
        print(rt)


asyncio.run(main())
