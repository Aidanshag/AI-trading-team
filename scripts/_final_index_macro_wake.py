"""Last-shot Index/Macro Analyst wake before session close.

Goal: ES/MES/NQ/MNQ are the most liquid CME contracts — best chance of
producing a fillable order in the remaining 20 minutes. Defined-risk
LONG only. Risk Manager has full veto. Run full chain.
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


PROMPT = """LAST-SHOT INDEX SCAN — ~25 min until 16:00 ET cutoff.

Mission: find a defined-risk LONG setup on ES, MES, NQ, MNQ, RTY,
M2K, YM, or MYM that could fill in the next 25 minutes.

Constraints:
- LONG only (defined-risk; no naked shorts)
- R:R ≥ 2.0:1
- Risk per trade ≤ $200 (slightly tighter than the 50bp cap to give
  Risk Manager headroom)
- Stop placement realistic (≥ 1.0 × ATR; not inside the noise)
- Strategy from `tools/backtest/strategies.py` — name it
- Full 12-question pre-trade checklist
- Explicit invalidation that fires before stop

Goldilocks regime per FRED today: VIX 19.31, curve +53bp uninverted,
Fed funds 3.75%. Favors trend / breakout strategies on indices.

If you find a clean setup:
1. Call `state_record_decision` with agent_name='Index/Macro Analyst'
   (exact spelling), kind='thesis', and a complete rationale.
2. End your response with EXACTLY:
   THESIS: <SYMBOL> conviction=<low|med|high>

If nothing triggers cleanly, end with:
   NO_TRADE: <one-line reason>

Be honest — disciplined no-trade is acceptable. But MES has $1.25/tick
which makes tight-risk setups very feasible. Look hard.
"""


def _ts(): return datetime.now(tz=timezone.utc).strftime("%H:%M:%S")


def _detect_pm_decision(text: str) -> str:
    t = text.upper()
    m = re.search(r"DECISION\s*[:\-]\s*(PROPOSE|PASS)\b", t)
    if m: return m.group(1)
    return "PROPOSE" if t.rstrip().endswith("PROPOSE") else "PASS"


async def main():
    orch = Orchestrator()
    print(f"[{_ts()}] orchestrator loaded")

    # Step 1: Index/Macro Analyst
    print()
    print("=" * 72)
    print(f"[{_ts()}] STEP 1: Index/Macro Analyst")
    print("=" * 72)
    a_result = await orch.wake_agent("Index/Macro Analyst", PROMPT)
    text = a_result.get("final_text", "") or ""
    print(text[:2500])
    print()

    if "THESIS:" not in text.upper() or "NO_TRADE:" in text.upper():
        print(f"[{_ts()}] No actionable thesis. End.")
        return

    # Step 2: lookup with fuzzy match
    thesis = orch._latest_thesis_for("Index/Macro Analyst")
    if not thesis:
        print(f"[{_ts()}] Thesis not found in DB. End.")
        return
    print(f"[{_ts()}] thesis: {thesis['symbol']} conviction={thesis['conviction']}")

    # Step 3: PM (skip Red Team if low conviction for time)
    print()
    print("=" * 72)
    print(f"[{_ts()}] STEP 2: PM evaluation")
    print("=" * 72)
    pm_result = await orch.wake_agent(
        "Portfolio Manager",
        f"Thesis: {thesis}\n"
        "Time-sensitive: ~20 min to session close. Decide pursue|pass quickly. "
        "If pursue, produce order_proposal (symbol, side, qty, order_type, "
        "stop_loss_price, target_price, rationale). Record via "
        "state_record_decision kind=order_proposal. End with EXACTLY: "
        "'DECISION: PROPOSE' or 'DECISION: PASS'."
    )
    pm_text = pm_result.get("final_text", "") or ""
    print(pm_text[:2000])
    decision = _detect_pm_decision(pm_text)
    print()
    print(f"[{_ts()}] PM: {decision}")

    if decision != "PROPOSE":
        print(f"[{_ts()}] PM passed. End.")
        return

    proposal = orch._latest_proposal()
    if not proposal:
        print(f"[{_ts()}] No proposal recorded. End.")
        return

    # Step 4: Risk Manager + Execution
    print()
    print("=" * 72)
    print(f"[{_ts()}] STEP 3: Risk Manager + Execution")
    print("=" * 72)
    result = await orch.submit_proposal(proposal)
    print(f"[{_ts()}] CHAIN STATUS: {result.get('status')}")
    if result.get("result"):
        rt = (result["result"].get("final_text") or "")[:2000]
        print(rt)


asyncio.run(main())
