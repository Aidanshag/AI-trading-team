"""Inject FX Analyst's GBP Donchian-breakout thesis as a manual record,
then run PM -> Risk Manager -> (Exec) on it.

Why this exists: FX Futures Analyst found a real low-conviction setup
during the validation rotation but failed to call state_record_decision,
so the chain stopped at thesis_not_recorded. This driver manually
records what the analyst would have written, then drives PM forward.

Setup specifics (from FX Analyst's actual research output):
  Symbol:  6B (British Pound futures, CME)
  Side:    LONG
  Trigger: Donchian breakout above 1.3600
  Stop:    1.3520 (80 pips below)
  Target:  1.3700 (100 pips above)
  Catalyst: BoE Thursday vs Fed/ECB divergence
  Conviction: LOW
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


THESIS_RATIONALE = """\
SETUP: GBP/USD (6B) Donchian breakout above 1.3600.

Recent context: GBP has been the strongest G10 currency this month,
+417 pips from 3/30 low to 4/17 high. Current price 1.3549 is consolidating
just below the 1.3598 prior high. A break above 1.3600 signals continuation.

CATALYST: Bank of England meets Thursday. BoE expected to signal "patient"
(no rate move), but tone matters relative to Fed/ECB. If BoE is less
dovish than Fed (markets currently expect Fed lower-for-longer), GBP
outperforms in the post-decision window.

ENTRY: Break above 1.3600 (Donchian-style breakout from the 4/17 high).
STOP: 1.3520 (below the 4/20 support; 80 pips of risk per contract).
TARGET: 1.3700 (100 pips upside; 1.25:1 R:R).
INVALIDATION: BoE dovish surprise OR break of 1.3520.

CONVICTION: low — defined-risk, technical-only setup with macro
catalyst pending. Suitable for small size or skipping under tight
risk-manager rules. Validation-grade trade for chain test.

NOTE TO PM: per-trade risk cap is 0.5% of equity = $250. At 80 pips
stop, 1 contract = 80 × $6.25 = $500 risk = 100% of full DLL on a
single trade. Sizing options: (a) right-size to 0 contracts (skip),
(b) widen target / use option overlay, or (c) propose 1 contract and
let Risk Manager veto if outside cap. PM has discretion.
"""

THESIS_SUMMARY = (
    "GBP 6B Donchian breakout long. Entry above 1.3600, stop 1.3520, "
    "target 1.3700. BoE Thursday catalyst. Conviction: low."
)


def _ts(): return datetime.now(tz=timezone.utc).strftime("%H:%M:%S")


async def main():
    orch = Orchestrator()
    print(f"[{_ts()}] orchestrator loaded.")

    # === STEP 1: inject the thesis ===
    orch.db.record_decision(
        agent="FX Futures Analyst",
        kind="thesis",
        summary=THESIS_SUMMARY,
        rationale=THESIS_RATIONALE,
        model="manual_injection",
        symbol="6B",
    )
    print(f"[{_ts()}] thesis injected for FX Futures Analyst (symbol=6B).")
    thesis = orch._latest_thesis_for("FX Futures Analyst")
    print(f"[{_ts()}] verified: {thesis['symbol']} conviction={thesis['conviction']}")
    print()

    # === STEP 2: skip Red Team (conviction = low per chain rule) ===
    print(f"[{_ts()}] Red Team SKIPPED (conviction=low per chain rule).")
    print()

    # === STEP 3: PM evaluates ===
    print("=" * 72)
    print(f"[{_ts()}] STEP: Portfolio Manager evaluation")
    print("=" * 72)
    pm_task = (
        f"Thesis from FX Futures Analyst:\n{THESIS_RATIONALE}\n\n"
        "PM job: evaluate pursue|pass. Sizing must respect per-trade "
        "risk cap (0.5% of $50K = $250). Note that 1 contract of 6B "
        "with an 80-pip stop = $500 risk, EXCEEDING the per-trade cap. "
        "If you choose to pursue, you must propose a size that respects "
        "the cap (likely 0 contracts - i.e. PASS - or a tighter stop). "
        "Record via state_record_decision kind=order_proposal. "
        "End with PROPOSE or PASS."
    )
    pm_result = await orch.wake_agent("Portfolio Manager", pm_task)
    text = pm_result.get("final_text", "") or ""
    print(text[:2000])
    print()
    if "PROPOSE" not in text.upper():
        print(f"[{_ts()}] PM PASSED. Trade dies here. Chain validated up to PM.")
        return

    proposal = orch._latest_proposal()
    if not proposal:
        print(f"[{_ts()}] PM said PROPOSE but no order_proposal recorded.")
        return

    # === STEP 4: Risk Manager + (Exec if approved) ===
    print("=" * 72)
    print(f"[{_ts()}] STEP: Risk Manager review + Execution if approved")
    print("=" * 72)
    print(f"[{_ts()}] proposal: {proposal}")
    result = await orch.submit_proposal(proposal)
    print()
    print("=" * 72)
    print(f"[{_ts()}] CHAIN FINAL STATUS: {result.get('status')}")
    print("=" * 72)
    if result.get("result"):
        rt = (result["result"].get("final_text") or "")[:2000]
        print(rt)


asyncio.run(main())
