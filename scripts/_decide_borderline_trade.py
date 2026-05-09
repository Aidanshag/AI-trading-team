"""Autonomous borderline-trade decision-maker.

When a proposal was approved but the order can't be placed cleanly
(broker rejection during daily break, price retracement past
invalidation, gap at reopen, etc), this script wakes the Risk Manager
with full context and asks for a real verdict — no human in the loop.

Outputs one of:
  - PLACE_AS_PROPOSED    (original order — proceed)
  - PLACE_MODIFIED       (RM approved with different size/price/type)
  - PASS                 (thesis genuinely invalidated; no order)

Then acts on the verdict via direct broker API.
"""
from __future__ import annotations
import asyncio, os, sys, re, json
from datetime import datetime, timezone, timedelta
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

import httpx
import sqlite3
from runtime.orchestrator import Orchestrator


# Tonight's specific case — ZN ORB breakout post-reopen
PROPOSAL_ID = 140  # the order_proposal decision in the DB
THESIS_ID   = 132  # the original QR thesis
ORIGINAL_ENTRY = 110.921875
ORIGINAL_STOP  = 110.859375
ORIGINAL_TARGET= 111.046875
TICK_SIZE = 0.015625
CONTRACT_ID = "CON.F.US.TYA.M26"


def _ts(): return datetime.now(tz=timezone.utc).strftime("%H:%M:%S")


def _get_token():
    r = httpx.post("https://api.topstepx.com/api/Auth/loginKey",
                   json={"userName": os.environ["PROJECTX_USERNAME"],
                         "apiKey":   os.environ["PROJECTX_API_KEY"]}, timeout=15.0)
    return r.json().get("token")


def _get_recent_bars(token, contract_id, n_bars=10):
    H = {"Authorization": f"Bearer {token}"}
    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(minutes=n_bars * 1)
    r = httpx.post("https://api.topstepx.com/api/History/retrieveBars",
                   headers=H,
                   json={"contractId": contract_id, "live": False,
                         "startTime": start.isoformat(),
                         "endTime": end.isoformat(),
                         "unit": 2, "unitNumber": 1, "limit": n_bars,
                         "includePartialBar": True},
                   timeout=20.0)
    return r.json().get("bars", []) if r.status_code == 200 else []


def _place_buy_stop(token, contract_id, stop_entry, stop_loss, target):
    """Place a stop-limit buy with permissive limit, like the M6B trade."""
    H = {"Authorization": f"Bearer {token}"}
    order = {
        "accountId": int(os.environ["PROJECTX_ACCOUNT_ID"]),
        "contractId": contract_id,
        "type": 4,                              # stop-limit
        "side": 0,                              # buy
        "size": 1,
        "stopPrice": stop_entry,
        "limitPrice": target + 5 * TICK_SIZE,   # permissive — let it fill at market-ish on touch
        "customTag": "ZN_ORB_20260428_AUTONOMOUS",
    }
    r = httpx.post("https://api.topstepx.com/api/Order/place",
                   headers=H, json=order, timeout=30.0)
    return r.status_code, r.json()


def _build_rm_prompt(bars, current_price, gap_ticks):
    """Build the Risk Manager re-evaluation prompt."""
    bar_lines = "\n".join(
        f"  {b.get('t','?')[11:19]} O={b.get('o')} H={b.get('h')} L={b.get('l')} C={b.get('c')} V={b.get('v')}"
        for b in bars[-5:]
    )
    return f"""BORDERLINE TRADE RE-EVALUATION — autonomous decision required.

You previously APPROVED a proposal earlier today (decision {PROPOSAL_ID}, original thesis from Quant Researcher decision {THESIS_ID}). The Execution Trader could not place the order because Topstep rejected it during the CME daily maintenance break (21:00–22:00 UTC). Now the market has reopened and the situation has changed.

ORIGINAL THESIS (your prior approval):
- Symbol: ZN
- Side: BUY (Long, ORB breakout)
- Entry: LIMIT @ {ORIGINAL_ENTRY}  (the 30-min ORB high)
- Stop: {ORIGINAL_STOP}  (4 ticks below = 1.0× ATR = $62.50 risk)
- Target: {ORIGINAL_TARGET}  (8 ticks above = $125 reward, R:R 2.0)
- Strategy: opening_range_breakout + vol_regime_trend
- Confirmation: 3× volume spike on the 20:00 UTC bar; Hawkes intensity

ORIGINAL INVALIDATION (per the analyst):
"If ZN closes back below 110.875 on TWO consecutive bars without a bounce — thesis broken before stop is hit."

CURRENT STATE (post-reopen, last 5 bars 1-min):
{bar_lines}

Last price: {current_price}
Gap from original entry {ORIGINAL_ENTRY}: {gap_ticks:+.1f} ticks ({"BELOW" if current_price < ORIGINAL_ENTRY else "ABOVE"} entry)

DECISION REQUESTED. Choose ONE:

1. **PLACE_AS_PROPOSED** — place the order using current parameters (e.g., a buy-stop at {ORIGINAL_ENTRY}, target {ORIGINAL_TARGET}, stop {ORIGINAL_STOP}). Use this if the breakout setup is still valid; the entry only fires if price rallies back through the ORB high.

2. **PLACE_MODIFIED** — place the order with adjusted parameters. Specify the new entry/stop/target. Use this if the structure is intact but levels have shifted enough that the original numbers are stale.

3. **PASS** — thesis is invalidated. Do not place. Use this if price action has decisively negated the breakout (close on 2+ consecutive bars below 110.875, or material gap, or any other reason the trade should not happen).

Reason your decision in 4-6 sentences citing specific bar data + the invalidation rule.

End with EXACTLY one of:
- DECISION: PLACE_AS_PROPOSED
- DECISION: PLACE_MODIFIED  entry=<X>  stop=<Y>  target=<Z>  size=<N>
- DECISION: PASS
"""


def _parse_rm_decision(text: str) -> dict:
    t = text.upper()
    if re.search(r"DECISION\s*[:\-]\s*PLACE_AS_PROPOSED\b", t):
        return {"action": "PLACE_AS_PROPOSED"}
    m = re.search(r"DECISION\s*[:\-]\s*PLACE_MODIFIED\s+ENTRY=(\S+)\s+STOP=(\S+)\s+TARGET=(\S+)\s+SIZE=(\S+)", t)
    if m:
        try:
            return {
                "action": "PLACE_MODIFIED",
                "entry":  float(m.group(1)),
                "stop":   float(m.group(2)),
                "target": float(m.group(3)),
                "size":   int(m.group(4)),
            }
        except ValueError:
            pass
    if re.search(r"DECISION\s*[:\-]\s*PASS\b", t):
        return {"action": "PASS"}
    # Fallback: conservative pass
    return {"action": "PASS", "fallback": True}


async def main():
    orch = Orchestrator()
    print(f"[{_ts()}] orchestrator loaded")

    token = _get_token()
    if not token:
        print(f"[{_ts()}] auth failed"); return 1

    # 1. Pull current state
    bars = _get_recent_bars(token, CONTRACT_ID, n_bars=10)
    if not bars:
        print(f"[{_ts()}] no bars — aborting"); return 2
    last_close = float(bars[-1].get("c"))
    gap_ticks = (last_close - ORIGINAL_ENTRY) / TICK_SIZE
    print(f"[{_ts()}] ZN last close: {last_close}  gap from entry: {gap_ticks:+.1f} ticks")

    # 2. Wake Risk Manager
    print(f"[{_ts()}] Waking Risk Manager for autonomous re-evaluation...")
    rm_result = await orch.wake_agent("Risk Manager", _build_rm_prompt(bars, last_close, gap_ticks))
    rm_text = (rm_result.get("final_text") or "").strip()
    print()
    print("=" * 72)
    print(f"[{_ts()}] RISK MANAGER VERDICT")
    print("=" * 72)
    print(rm_text[:2500])
    print()

    decision = _parse_rm_decision(rm_text)
    print(f"[{_ts()}] Parsed decision: {decision}")

    # 3. Act on decision
    if decision["action"] == "PASS":
        print(f"[{_ts()}] PASS — no order placed. Done.")
        orch.db.record_decision(
            agent="Risk Manager",
            kind="autonomous_borderline_pass",
            summary="ZN ORB borderline re-eval: PASS",
            rationale=rm_text[:2000],
            model="autonomous",
            symbol="ZN",
        )
        return 0

    if decision["action"] == "PLACE_AS_PROPOSED":
        entry, stop, target = ORIGINAL_ENTRY, ORIGINAL_STOP, ORIGINAL_TARGET
    else:  # PLACE_MODIFIED
        entry  = decision.get("entry",  ORIGINAL_ENTRY)
        stop   = decision.get("stop",   ORIGINAL_STOP)
        target = decision.get("target", ORIGINAL_TARGET)

    print(f"[{_ts()}] Placing buy-stop at {entry} (stop {stop}, target {target})")
    status, body = _place_buy_stop(token, CONTRACT_ID, entry, stop, target)
    print(f"[{_ts()}] Broker response: {status} {body}")

    if status == 200 and body.get("success"):
        order_id = body.get("orderId")
        orch.db.record_decision(
            agent="Risk Manager",
            kind="autonomous_borderline_place",
            summary=f"ZN ORB borderline re-eval: PLACED order {order_id}",
            rationale=f"RM verdict: {decision['action']}\n\n" + rm_text[:1500],
            model="autonomous",
            symbol="ZN",
        )
        print(f"[{_ts()}] *** ORDER PLACED *** broker order ID: {order_id}")
    else:
        print(f"[{_ts()}] Order placement FAILED.")


asyncio.run(main())
