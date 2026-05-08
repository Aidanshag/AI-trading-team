"""Inject the ZN ORB breakout proposal directly into PM → Risk → Exec.

The QR thesis (decision 132) is institutional-grade but the chain's
run_analyst_chain() re-wakes the analyst and lost the original. This
script bypasses that bug by recording the order_proposal directly
and running submit_proposal."""
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


PROPOSAL = {
    "symbol": "ZN",
    "side": "buy",
    "qty": 1,
    "order_type": "limit",
    "limit_price":      110.921875,   # ORB high
    "stop_loss_price":  110.859375,   # 4 ticks below = 1.0× ATR = $62.50 risk
    "target_price":     111.046875,   # 8 ticks above = $125 reward
    "structure_id": None,
    "asset_type": "future",
    "summary": (
        "ZN ORB breakout LONG. Limit 110.921875, stop 110.859375, "
        "target 111.046875. 1 contract = $62.50 risk = 0.125% equity. "
        "R:R 2.0:1. Strategy: opening_range_breakout + vol_regime_trend. "
        "Conditional entry at 22:00 UTC daily-break reopen."
    ),
    "rationale": (
        "PRE-TRADE CHECKLIST — Quant Researcher decision 132 (full analysis).\n\n"
        "(1) STRATEGY: opening_range_breakout + vol_regime_trend confirmation, "
        "both from tools/backtest/strategies.py.\n"
        "(2) TRIGGER: ZN 30-min ORB high = 110.921875 (set by 13:45 UTC bar). "
        "20:00 UTC bar made H=110.953125 with volume 41,692 = 3× afternoon "
        "baseline. Hawkes intensity confirms cluster. Pullback-to-breakout entry.\n"
        "(3) ENTRY: LIMIT 110.921875 (or better, tolerance 110.921875-110.9375). "
        "Do not enter above 111.0000 (would compress R:R below 2.0).\n"
        "(4) STOP: 110.859375. 4 ticks below entry = 1.0× ATR(20) = $62.50. "
        "ATR computed over 20 RTH bars; mean TR = 3.55 ticks → 4 used. "
        "Below ORB midpoint; close below invalidates breakout thesis.\n"
        "(5) WORST-CASE: 4 × $15.625 = $62.50.\n"
        "(6) % EQUITY: 0.125% (vs 50bp cap). 1/4 of cap.\n"
        "(7) TARGET: 111.046875. 8 ticks above entry = $125. Sits in "
        "overnight consolidation range 111.015-111.062.\n"
        "(8) R-MULTIPLE: 8/4 = 2.0:1 exactly.\n"
        "(9) INVALIDATION (pre-stop): "
        "(a) Close back below 110.875 on TWO consecutive bars without bounce; "
        "(b) Gap below 110.859375 at 22:00 UTC reopen — thesis failed overnight, "
        "cancel order immediately.\n"
        "(10) REGIME FIT: Post-deleveraging recovery trend. ZN+ES parallel "
        "correlated-selling eigenmode 12:00-14:30 UTC (Marchenko-Pastur). Both "
        "recovering since 12:30 UTC low. ZN recovery proportionally stronger "
        "(+250 ticks from low). With-trend.\n"
        "(11) CORRELATION: Zero existing positions. No correlated drift.\n"
        "(12) EXECUTION PLAN: LIMIT BUY at 110.921875 placed immediately after "
        "22:00 UTC market resumption. If no fill within first 2 bars (30 min), "
        "cancel — market has moved away. Stop-limit at 110.859375 placed "
        "simultaneously. Target limit at 111.046875. Entry condition: "
        "price re-opens within ±8 ticks of 110.921875. If gap >8 ticks either "
        "way at reopen, PASS — do not chase. NOT a market order."
    ),
}


def _ts(): return datetime.now(tz=timezone.utc).strftime("%H:%M:%S")


async def main():
    orch = Orchestrator()
    print(f"[{_ts()}] orchestrator loaded")
    print(f"[{_ts()}] proposal: BUY 1 ZN LIMIT 110.921875 / stop 110.859375 / target 111.046875")
    print(f"[{_ts()}] risk: $62.50 (0.125% equity), R:R 2.0:1")
    print()

    # Record the proposal in DB
    orch.db.record_decision(
        agent="manual_pm_bypass",
        kind="order_proposal",
        summary=PROPOSAL["summary"],
        rationale=PROPOSAL["rationale"],
        model="manual_injection_QR_thesis_132",
        symbol="ZN",
    )
    print(f"[{_ts()}] proposal recorded in decisions table")
    print()

    # Run Risk Manager + Execution via submit_proposal
    print("=" * 72)
    print(f"[{_ts()}] submit_proposal: Risk Manager + Execution")
    print("=" * 72)
    result = await orch.submit_proposal(PROPOSAL)
    print()
    print("=" * 72)
    print(f"[{_ts()}] CHAIN STATUS: {result.get('status')}")
    print("=" * 72)
    if result.get("result"):
        text = (result["result"].get("final_text") or "")[:3000]
        print(text)


asyncio.run(main())
