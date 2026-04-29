"""State store MCP server — REAL (not a stub).

Agents use these tools to read and append to the SQLite state. Only this
server should write to the DB; other code may read directly.
"""

from __future__ import annotations

from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from state.db import get_db, utcnow_iso


@tool(
    "state_account_snapshot",
    "Return the most recent account snapshot (balance, day P&L, trailing DD, open contracts).",
    {},
)
async def state_account_snapshot(args: dict[str, Any]) -> dict[str, Any]:
    snap = get_db().latest_account_snapshot()
    text = "No account snapshot yet." if snap is None else str(snap)
    return {"content": [{"type": "text", "text": text}]}


@tool(
    "state_positions",
    "List all open positions.",
    {},
)
async def state_positions(args: dict[str, Any]) -> dict[str, Any]:
    rows = get_db().current_positions()
    return {"content": [{"type": "text", "text": str(rows)}]}


@tool(
    "state_record_decision",
    (
        "Append a decision record (thesis, order proposal, risk vote, PM allocation, "
        "post-trade review, regime call). Use this liberally — this is the audit log."
    ),
    {
        "agent": str,
        "kind": str,
        "summary": str,
        "rationale": str,
        "symbol": str,
        "vault_path": str,
    },
)
async def state_record_decision(args: dict[str, Any]) -> dict[str, Any]:
    did = get_db().record_decision(
        agent=args["agent"],
        kind=args["kind"],
        summary=args["summary"],
        rationale=args["rationale"],
        symbol=args.get("symbol"),
        vault_path=args.get("vault_path"),
    )
    return {"content": [{"type": "text", "text": f"decision_id={did}"}]}


@tool(
    "state_recent_decisions",
    "Return the most recent N decisions (optionally filtered by agent or symbol).",
    {"limit": int, "agent": str, "symbol": str},
)
async def state_recent_decisions(args: dict[str, Any]) -> dict[str, Any]:
    limit = int(args.get("limit") or 20)
    agent = args.get("agent")
    symbol = args.get("symbol")
    q = "SELECT ts, agent, kind, symbol, summary FROM decisions"
    conds, params = [], []
    if agent:
        conds.append("agent = ?")
        params.append(agent)
    if symbol:
        conds.append("symbol = ?")
        params.append(symbol)
    if conds:
        q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY ts DESC LIMIT ?"
    params.append(limit)
    rows = [dict(r) for r in get_db().connect().execute(q, params).fetchall()]
    return {"content": [{"type": "text", "text": str(rows)}]}


@tool(
    "state_risk_events_today",
    "All risk events recorded today, newest first.",
    {},
)
async def state_risk_events_today(args: dict[str, Any]) -> dict[str, Any]:
    today = utcnow_iso()[:10]
    rows = [
        dict(r) for r in get_db().connect().execute(
            "SELECT ts, severity, rule, agent, detail FROM risk_events "
            "WHERE ts LIKE ? ORDER BY ts DESC",
            (f"{today}%",),
        ).fetchall()
    ]
    return {"content": [{"type": "text", "text": str(rows)}]}


@tool(
    "state_record_shadow_trade",
    (
        "Record a hypothetical TRIGGER for after-the-fact performance review. "
        "Use this when you spot a clean rule-based setup on a ticker that is "
        "outside the focus universe, blocked by risk, or otherwise not "
        "actionable right now. The shadow recap evaluates these for promotion "
        "to the active universe. shadow_reason ∈ focus_universe_blocked | "
        "risk_block | sector_disabled | scout_only | budget_exhausted | duplicate_position. "
        "side ∈ long | short. conviction ∈ low | med | high | validation. "
        "horizon ∈ intraday | swing | position."
    ),
    {
        "agent": str,
        "symbol": str,
        "strategy": str,
        "side": str,
        "entry_price": float,
        "stop_price": float,
        "target_price": float,
        "shadow_reason": str,
        "risk_usd": float,
        "rr_planned": float,
        "conviction": str,
        "horizon": str,
        "notes": str,
    },
)
async def state_record_shadow_trade(args: dict[str, Any]) -> dict[str, Any]:
    sid = get_db().record_shadow_trade(
        agent=args["agent"],
        symbol=args["symbol"],
        strategy=args["strategy"],
        side=args["side"],
        entry_price=float(args["entry_price"]),
        stop_price=float(args["stop_price"]),
        target_price=float(args["target_price"]),
        shadow_reason=args["shadow_reason"],
        risk_usd=float(args["risk_usd"]) if args.get("risk_usd") is not None else None,
        rr_planned=float(args["rr_planned"]) if args.get("rr_planned") is not None else None,
        conviction=args.get("conviction"),
        horizon=args.get("horizon"),
        notes=args.get("notes"),
    )
    return {"content": [{"type": "text", "text": f"shadow_trade_id={sid}"}]}


@tool(
    "state_shadow_trade_stats",
    (
        "Per-(symbol, strategy) hit-rate + avg R-multiple over the last N days "
        "(default 14). Reads only resolved shadow trades. Used by CIO + "
        "Quant Researcher to identify symbols/strategies worth promoting."
    ),
    {"days": int},
)
async def state_shadow_trade_stats(args: dict[str, Any]) -> dict[str, Any]:
    days = int(args.get("days") or 14)
    rows = get_db().shadow_trade_stats(days=days)
    return {"content": [{"type": "text", "text": str(rows)}]}


TOOLS = [
    state_account_snapshot,
    state_positions,
    state_record_decision,
    state_recent_decisions,
    state_risk_events_today,
    state_record_shadow_trade,
    state_shadow_trade_stats,
]

server = create_sdk_mcp_server(name="state_store", version="0.1.0", tools=TOOLS)
