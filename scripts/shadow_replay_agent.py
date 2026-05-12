"""Phase 2 validation: replay the exit_reasoner agent against historical
exec_mirror profit_lock events.

For each sampled shadow trade where the mechanical tier would have
closed via profit_lock:
  1. Re-fetch bars (ProjectX)
  2. Run evaluate_exec_mirror TWICE on the same bars:
       a. Control: pure mechanical tier (current behavior)
       b. Agent: tier triggers route through decide_exit_with_agent
  3. Compare R outcomes per trade
  4. Aggregate: does the agent improve, hurt, or match the control?

Cost: ~$0.002 per agent call × ~50-100 trades × 2 tier-triggers each
= $0.20-0.40 per replay run. Cheap.

USAGE:
  python -m scripts.shadow_replay_agent --sample 50
  python -m scripts.shadow_replay_agent --sample 200 --since 2026-05-01

Built 2026-05-12 per Phase 2 of the exit_reasoner build plan.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from state.db import get_db
from tools.exec_mirror import evaluate_exec_mirror
from tools.exit_reasoner import (
    decide_exit_with_agent, TradeContext, AGENT_MODEL,
)
from tools.projectx_client import ProjectXError, get_client


def _bar_ts_to_iso(b: dict) -> str:
    ts = b.get("t") or b.get("ts") or b.get("time")
    if isinstance(ts, datetime):
        return ts.isoformat()
    return str(ts) if ts is not None else ""


def _bar_ts_obj(b: dict) -> datetime | None:
    ts = b.get("t") or b.get("ts") or b.get("time")
    if isinstance(ts, str):
        try: return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError: return None
    return ts if isinstance(ts, datetime) else None


def _front_contract_id(client, symbol: str) -> str | None:
    contracts = client.search_contracts(symbol, live=False)
    if not contracts: return None
    front = sorted(contracts,
                    key=lambda c: c.get("expiryDate") or c.get("lastTradeDate") or "")[0]
    return front.get("id") or front.get("contractId")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--sample", type=int, default=50,
                   help="how many profit_lock shadows to replay")
    p.add_argument("--since", type=str, default="2026-05-01",
                   help="only sample shadows after this date")
    p.add_argument("--max-window-hours", type=int, default=8)
    args = p.parse_args()

    db = get_db()
    rows = db.connect().execute(
        """SELECT id, ts_signal, symbol, strategy, side,
                  entry_price, stop_price, target_price, risk_usd,
                  exec_mirror_pnl_r, exec_mirror_outcome
             FROM shadow_trades
            WHERE exec_mirror_outcome = 'profit_lock'
              AND risk_usd IS NOT NULL AND risk_usd > 0
              AND ts_signal >= ?
            ORDER BY RANDOM()
            LIMIT ?""",
        (args.since, args.sample),
    ).fetchall()
    if not rows:
        print("No profit_lock shadows in sample window.")
        return 0

    sample = [dict(r) for r in rows]
    print(f"Sampled {len(sample)} profit_lock shadow trades from {args.since} onward\n")

    try:
        client = get_client()
    except Exception as e:
        print(f"ERROR: ProjectX client unavailable: {e}", file=sys.stderr)
        return 2

    # ── Replay each ──
    results = []
    n_agent_holds = 0
    n_agent_closes = 0
    n_agent_fallback = 0
    total_control_r = 0.0
    total_agent_r = 0.0

    for i, s in enumerate(sample):
        sig_ts = datetime.fromisoformat(s["ts_signal"].replace("Z", "+00:00"))
        end_ts = sig_ts + timedelta(hours=args.max_window_hours)
        if end_ts > datetime.now(tz=timezone.utc):
            end_ts = datetime.now(tz=timezone.utc)
        sym = s["symbol"]

        try:
            cid = _front_contract_id(client, sym)
            if not cid:
                print(f"  [{i+1}/{len(sample)}] skip {sym} #{s['id']}: no contract")
                continue
            bars = client.get_bars(
                contract_id=cid,
                start_time=sig_ts.isoformat(),
                end_time=end_ts.isoformat(),
                unit=2, unit_number=1, limit=2000, live=False,
            )
        except ProjectXError as e:
            print(f"  [{i+1}/{len(sample)}] skip {sym} #{s['id']}: bars failed ({e})")
            continue
        if not bars:
            continue

        # Build an agent-callback closure that calls the LLM
        def make_agent_cb(shadow: dict, all_bars: list):
            def cb(peak_usd, current_usd, floor_usd, holds, bar_idx, bar_ts):
                # Build the bar window the agent should see (last 20 bars up to bar_idx)
                recent = all_bars[max(0, bar_idx - 20):bar_idx + 1]
                entry_ts_proxy = sig_ts
                # Use a fake entry_ts so the time-cap doesn't immediately trip
                # for trades that were 10h+ ago in shadow data
                fake_entry_ts = datetime.now(tz=timezone.utc) - timedelta(
                    minutes=10 + holds * 5,
                )
                ctx = TradeContext(
                    symbol=shadow["symbol"], side=shadow["side"],
                    strategy=shadow["strategy"],
                    contract_id=cid,
                    entry_price=float(shadow["entry_price"]),
                    avg_fill_price=float(shadow["entry_price"]),
                    entry_ts=fake_entry_ts,
                    current_price=float(recent[-1].get("c") if recent else
                                         shadow["entry_price"]),
                    peak_unrealized_usd=peak_usd,
                    current_unrealized_usd=current_usd,
                    tier_floor_usd=floor_usd,
                    risk_usd=float(shadow["risk_usd"] or 0),
                    recent_bars=recent,
                    regime={"vol_regime": "med",   # we don't compute on replay
                            "trend_regime": "?",
                            "news_proximity": "?"},
                    consecutive_holds=holds,
                )
                d = decide_exit_with_agent(ctx, enabled=True)
                nonlocal_state["last_decision"] = d
                return d.action
            return cb

        nonlocal_state = {"last_decision": None}
        cb = make_agent_cb(s, bars)

        # Control run (no agent)
        out_ctrl, r_ctrl, _ = evaluate_exec_mirror(
            bars,
            symbol=sym, side=s["side"],
            entry=float(s["entry_price"]),
            stop=float(s["stop_price"]),
            risk_usd=float(s["risk_usd"]),
        )
        # Agent run
        out_agent, r_agent, note_agent = evaluate_exec_mirror(
            bars,
            symbol=sym, side=s["side"],
            entry=float(s["entry_price"]),
            stop=float(s["stop_price"]),
            risk_usd=float(s["risk_usd"]),
            exit_decision_fn=cb,
        )
        delta = r_agent - r_ctrl
        # Tally last decision
        if nonlocal_state["last_decision"] is not None:
            la = nonlocal_state["last_decision"].action
            if la == "HOLD": n_agent_holds += 1
            elif la == "CLOSE": n_agent_closes += 1
            elif la == "FALLBACK_CLOSE": n_agent_fallback += 1

        total_control_r += r_ctrl
        total_agent_r += r_agent

        results.append({
            "id": s["id"], "symbol": sym, "strategy": s["strategy"],
            "control_outcome": out_ctrl, "control_R": r_ctrl,
            "agent_outcome": out_agent, "agent_R": r_agent,
            "delta_R": delta,
        })
        print(f"  [{i+1}/{len(sample)}] {sym:4s} #{s['id']} "
              f"{s['strategy']:22s} "
              f"ctrl={out_ctrl:11s} {r_ctrl:+.2f}R  "
              f"agent={out_agent:11s} {r_agent:+.2f}R  "
              f"Δ={delta:+.2f}R")

    # ── Aggregate ──
    print()
    print(f"=== Phase 2 replay summary (n={len(results)}) ===")
    if results:
        avg_ctrl = total_control_r / len(results)
        avg_agent = total_agent_r / len(results)
        print(f"  Control avg R:  {avg_ctrl:+.3f}")
        print(f"  Agent avg R:    {avg_agent:+.3f}")
        print(f"  Delta per trade: {avg_agent - avg_ctrl:+.3f}R")
        print()
        improvements = sum(1 for r in results if r["delta_R"] > 0.01)
        worsens = sum(1 for r in results if r["delta_R"] < -0.01)
        unchanged = len(results) - improvements - worsens
        print(f"  Agent improved {improvements}/{len(results)} trades, "
              f"worsened {worsens}, unchanged {unchanged}")
        print()
        print(f"  Last-decision tally: HOLD={n_agent_holds}  "
              f"CLOSE={n_agent_closes}  FALLBACK={n_agent_fallback}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
