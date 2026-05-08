"""Wake the Quant Researcher with HFT-flavored framing.

True HFT isn't possible on Topstep (no co-location, no tick data, REST
API latency ~100ms+). What we DO have: intraday-cadence strategies
(ORB, NR7, inside-bar, vol-spike-fade, bollinger-squeeze) on whatever
bar timeframe the data layer supplies. The Quant Researcher owns these.

This driver asks them to scan for the fastest-cadence rule-based setup
that triggers right now, then drives the chain to execution.
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


HFT_PROMPT = """HIGH-CADENCE TRADE SCAN. User wants to see what your
intraday-cadence strategies could fire right now.

Reality check: true HFT (sub-second) is impossible on Topstep — no
co-location, no tick data, REST API latency. What you DO have is the
13-strategy library at `tools/backtest/strategies.py`, including these
intraday-cadence patterns I built specifically for this:

INTRADAY-CADENCE STRATEGIES (yours to use):
1. opening_range_breakout — first N bars define range, break = entry
2. narrow_range_break (NR7) — narrowest range bar of last 7, break either way
3. inside_bar_break — inside bar coil, break in either direction
4. vol_spike_fade — TR > 2.5×ATR fade-the-exhaustion
5. bollinger_squeeze_break — BB-width in bottom 20% over 120 bars → break
6. keltner_breakout — ATR-channel break + trend filter
7. vol_regime_trend — Donchian breakout filtered to low realized-vol regime
8. rsi2_extreme_reversion — RSI(2) <10 + above 200-EMA mean-reversion

YOUR JOB:

1. Pull current quotes for the most liquid CME futures (ES, NQ, CL, GC,
   6E, 6B, ZN — anything you can get bars on). Note: Topstep data is
   delayed, so treat the latest bar as "approximate now."

2. For each instrument, check which of the 8 strategies above has a
   triggering condition RIGHT NOW (or imminent). Be specific about which
   pattern signals on which instrument.

3. Pick the SINGLE highest-quality setup with:
   - Defined risk (stop placement clear)
   - R:R ≥ 2.0:1
   - Strategy backtested to positive expectancy

4. If found, write a thesis (12-question pre-trade checklist) and emit:
   THESIS: <SYMBOL> conviction=<low|med|high>

   If nothing triggers right now (which is fine — disciplined no-trade
   is acceptable), emit:
   NO_TRADE: <one-line reason>

Be honest about whether anything actually triggers. The user wants
real intraday signals, not forced trades.

Constraints in force:
- Risk Manager has full veto authority (no overrides)
- Per-trade risk cap $250 (50 bps)
- Internal $500 DLL ceiling
- Session ends 16:00 ET (~2 hours from now)
- Defined-risk only, no naked shorts
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
    print()

    # Step 1: Quant Researcher — find a fast-cadence setup
    print("=" * 72)
    print(f"[{_ts()}] STEP 1: Quant Researcher — high-cadence scan")
    print("=" * 72)
    q_result = await orch.wake_agent("Quant Researcher", HFT_PROMPT)
    text = q_result.get("final_text", "") or ""
    print(text[:3000])
    print()

    # Step 2: Did they find something?
    if "THESIS:" not in text.upper():
        print(f"[{_ts()}] No THESIS marker found — Quant Researcher stood down.")
        return

    thesis = orch._latest_thesis_for("Quant Researcher")
    if not thesis:
        print(f"[{_ts()}] THESIS marker but not recorded in DB. Stopping.")
        return

    # Step 3: Red Team if med/high
    conviction = (thesis.get("conviction") or "low").lower()
    challenge = None
    if conviction in ("med", "high"):
        print("=" * 72)
        print(f"[{_ts()}] STEP 2: Red Team challenge")
        print("=" * 72)
        challenge = await orch.wake_agent(
            "Red Team",
            f"Challenge this Quant Researcher thesis: {thesis}. "
            "Verdict strong|gaps|weak. <500 words.",
        )
        print((challenge.get("final_text") or "")[:1500])
        print()

    # Step 4: PM
    print("=" * 72)
    print(f"[{_ts()}] STEP {3 if challenge else 2}: Portfolio Manager")
    print("=" * 72)
    pm_result = await orch.wake_agent(
        "Portfolio Manager",
        f"High-cadence thesis from Quant Researcher: {thesis}\n"
        f"Red Team: {challenge.get('final_text','n/a') if challenge else 'skipped (low conviction)'}\n\n"
        "Decide pursue|pass. If pursue, propose order with explicit "
        "symbol/side/qty/order_type/stop_loss_price/target_price. "
        "Record via state_record_decision kind=order_proposal. "
        "End with EXACTLY: 'DECISION: PROPOSE' or 'DECISION: PASS'."
    )
    pm_text = pm_result.get("final_text", "") or ""
    print(pm_text[:2000])
    print()
    decision = _detect_pm_decision(pm_text)
    print(f"[{_ts()}] PM: {decision}")

    if decision != "PROPOSE":
        print(f"[{_ts()}] PM passed. End of chain.")
        return

    # Step 5: Risk Manager + Execution
    proposal = orch._latest_proposal()
    if not proposal:
        print(f"[{_ts()}] PM said PROPOSE but no proposal recorded. End.")
        return

    print()
    print("=" * 72)
    print(f"[{_ts()}] FINAL STEP: Risk Manager + Execution")
    print("=" * 72)
    result = await orch.submit_proposal(proposal)
    print(f"[{_ts()}] CHAIN STATUS: {result.get('status')}")
    if result.get("result"):
        rt = (result["result"].get("final_text") or "")[:2500]
        print(rt)


asyncio.run(main())
