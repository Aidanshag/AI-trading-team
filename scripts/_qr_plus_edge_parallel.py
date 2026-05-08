"""Wake Quant Researcher + Edge Hunter in parallel for HFT/intraday scan.

True HFT impossible on Topstep (no co-location, no tick data, REST
latency). What we DO have: 8 intraday-cadence strategies in the
backtest library, plus QR's physics overlays. Both agents scan in
parallel; whichever finds the cleaner setup gets PM → Risk → Exec.
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


QR_HFT_PROMPT = """HIGH-CADENCE / "HFT-FLAVORED" INTRADAY SCAN.

Reality check: true sub-second HFT impossible on our infra (no co-loc,
no tick data, REST API latency). What you DO have is the intraday-
cadence library at tools/backtest/strategies.py:

  Cadence:  opening_range_breakout, narrow_range_break (NR7), inside_bar_break
  Vol:      vol_spike_fade, bollinger_squeeze_break, keltner_breakout, vol_regime_trend
  Mean-rev: rsi2_extreme_reversion

Plus your full physics-quant toolkit (Marchenko-Pastur regime breaks,
Hawkes intensity, power-law tail fits, Sornette LPPL). Apply them.

YOUR JOB:
1. Pull live quotes + recent bars (5m or 15m) for liquid CME futures:
   ES, NQ, CL, GC, 6E, 6B, ZN.
2. For EACH instrument, check which of the 8 strategies has a
   triggering condition right now (or in the last 1-2 bars).
3. Cross-check with at least 1 physics overlay (Hawkes, RMT, tail
   fit) where applicable.
4. Pick the SINGLE highest-quality setup with:
   - Defined risk (long futures or defined-risk options structure;
     NO naked shorts — convert to bear put spread if bearish)
   - Risk per trade <= $200 (better: $100 for validation-grade)
   - R:R >= 2.0 for med conviction, >= 1.5 for high or validation
   - Stop >= 1.0x ATR (real, not noise)

5. **CRITICAL:** Call state_record_decision(
     agent_name="Quant Researcher",  # exact spelling
     kind="thesis",
     symbol="<SYMBOL>",
     summary="<one-line>",
     rationale="<full pre-trade checklist + math methods used>"
   ) — REQUIRED for the chain to pick up your thesis.

6. End with EXACTLY:
   THESIS: <SYMBOL> conviction=<low|med|high>
   or
   NO_TRADE: <one-line reason>

Be honest. Disciplined no-trade is acceptable.
"""

EDGE_PROMPT = """INTRADAY SCAN. Find the highest-quality rule-based
trigger active in the CME-tradeable universe right now. Follow your
output protocol (TRIGGER / WATCHLIST / NO_TRIGGER) and call
state_record_decision if you find a TRIGGER.
"""


def _ts(): return datetime.now(tz=timezone.utc).strftime("%H:%M:%S")


async def main():
    orch = Orchestrator()
    print(f"[{_ts()}] orchestrator loaded ({len(orch.specs)} agents)")
    print()

    # Parallel wake
    print(f"[{_ts()}] Waking Quant Researcher + Edge Hunter in parallel...")
    qr_task = asyncio.create_task(orch.wake_agent("Quant Researcher", QR_HFT_PROMPT))
    eh_task = asyncio.create_task(orch.wake_agent("Edge Hunter", EDGE_PROMPT))
    qr_result, eh_result = await asyncio.gather(qr_task, eh_task)

    qr_text = (qr_result.get("final_text") or "").strip()
    eh_text = (eh_result.get("final_text") or "").strip()

    print()
    print("=" * 72)
    print(f"[{_ts()}] QUANT RESEARCHER")
    print("=" * 72)
    print(qr_text[:2000])
    print()
    print("=" * 72)
    print(f"[{_ts()}] EDGE HUNTER")
    print("=" * 72)
    print(eh_text[:1500])
    print()

    # Did either record a thesis?
    qr_thesis = orch._latest_thesis_for("Quant Researcher")
    eh_thesis = orch._latest_thesis_for("Edge Hunter")

    # Pick the more recent thesis (both might have fired). _latest_thesis_for
    # returns the most recent for each agent; we compare the IDs implicitly
    # by checking which has higher ID.
    import sqlite3
    c = sqlite3.connect("state/fund.db")
    c.row_factory = sqlite3.Row
    latest_thesis = c.execute(
        "SELECT agent FROM decisions WHERE kind='thesis' "
        "AND ts > datetime('now', '-5 minutes') "
        "AND agent IN ('Quant Researcher', 'Edge Hunter') "
        "ORDER BY id DESC LIMIT 1"
    ).fetchone()

    if not latest_thesis:
        print(f"[{_ts()}] Neither agent recorded a thesis in DB. End.")
        return

    picked = latest_thesis["agent"]
    print(f"[{_ts()}] Latest thesis from: {picked}")
    print()

    # Run the chain on whichever produced the thesis
    print("=" * 72)
    print(f"[{_ts()}] Running chain: {picked} -> PM -> Risk -> Exec")
    print("=" * 72)
    chain_result = await orch.run_analyst_chain(picked)
    print(f"[{_ts()}] Chain status: {chain_result.get('status')}")

    if chain_result.get("status") == "executed":
        print()
        print(f"[{_ts()}] *** TRADE EXECUTED ***")
    elif chain_result.get("status") == "blocked_by_risk":
        print(f"[{_ts()}] Risk Manager blocked. See details:")
        if chain_result.get("result"):
            print((chain_result["result"].get("final_text") or "")[:1500])
    else:
        print(f"[{_ts()}] Status detail: {chain_result}")


asyncio.run(main())
