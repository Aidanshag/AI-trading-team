"""Topstep / ProjectX broker MCP server — LIVE.

Wraps `tools.projectx_client.ProjectXClient` into the MCP tool interface
the agents consume. All write operations (place/cancel/flatten) are still
gated by the PreToolUse risk hook in `hooks/risk_gate.py`.

Environment required:
    PROJECTX_API_KEY, PROJECTX_USERNAME, PROJECTX_ACCOUNT_ID
"""

from __future__ import annotations

import os
import uuid
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from tools.projectx_client import ProjectXError, get_account_id, get_client


def _json_text(obj: Any) -> dict[str, Any]:
    import json
    return {"content": [{"type": "text", "text": json.dumps(obj, default=str)}]}


# ── Read-only tools ────────────────────────────────────────────
@tool(
    "topstep_get_account",
    "Return account state (balance, day P&L, trailing DD, margin, open contracts).",
    {},
)
async def get_account(args: dict[str, Any]) -> dict[str, Any]:
    try:
        client = get_client()
        account_id = get_account_id()
        accounts = client.get_accounts()
        mine = next(
            (a for a in accounts if str(a.get("id")) == str(account_id)), None
        )
        if mine is None:
            return _json_text({"error": f"account {account_id} not visible"})
        return _json_text(mine)
    except ProjectXError as e:
        return _json_text({"error": str(e)})


@tool(
    "topstep_get_positions",
    "List all open positions for the configured account.",
    {},
)
async def get_positions(args: dict[str, Any]) -> dict[str, Any]:
    try:
        positions = get_client().get_positions(get_account_id())
        return _json_text({"positions": positions, "count": len(positions)})
    except ProjectXError as e:
        return _json_text({"error": str(e)})


@tool(
    "topstep_get_working_orders",
    "List all working (unfilled) orders.",
    {},
)
async def get_working_orders(args: dict[str, Any]) -> dict[str, Any]:
    try:
        orders = get_client().get_working_orders(get_account_id())
        return _json_text({"orders": orders, "count": len(orders)})
    except ProjectXError as e:
        return _json_text({"error": str(e)})


@tool(
    "topstep_find_contract",
    "Find the front-month contract ID for a symbol root (e.g. 'CL', 'ES', 'GC'). "
    "Use before placing an order since orders require a contract ID, not a symbol.",
    {"symbol": str},
)
async def find_contract(args: dict[str, Any]) -> dict[str, Any]:
    try:
        client = get_client()
        contracts = client.search_contracts(args["symbol"], live=True)
        front = None
        if contracts:
            front = sorted(
                contracts,
                key=lambda c: c.get("expiryDate") or c.get("lastTradeDate") or "",
            )[0]
        return _json_text({
            "symbol": args["symbol"],
            "front_month": front,
            "all_contracts": contracts,
        })
    except ProjectXError as e:
        return _json_text({"error": str(e)})


# ── Write tools (risk-gated) ──────────────────────────────────
@tool(
    "topstep_place_order",
    (
        "Place a futures or futures-options order on Topstep via ProjectX. "
        "Required: symbol (root, e.g. 'CL'), side ('buy'|'sell'), qty, "
        "order_type ('market'|'limit'|'stop'|'stop_limit'). "
        "Optional: limit_price, stop_price, time_in_force ('day'|'gtc'), "
        "client_order_id, rationale. "
        "IMPORTANT: every order MUST include a stop_price or be part of a "
        "defined-risk structure; otherwise the risk hook will block it."
    ),
    {
        "symbol": str,
        "side": str,
        "qty": int,
        "order_type": str,
        "limit_price": float,
        "stop_price": float,
        "time_in_force": str,
        "client_order_id": str,
        "rationale": str,
    },
)
async def place_order(args: dict[str, Any]) -> dict[str, Any]:
    try:
        client = get_client()
        account_id = get_account_id()
        contract_id = client.front_month_contract_id(args["symbol"])
        client_order_id = args.get("client_order_id") or f"fund_{uuid.uuid4().hex[:12]}"

        result = client.place_order(
            account_id=account_id,
            contract_id=contract_id,
            side=args["side"],
            qty=int(args["qty"]),
            order_type=args["order_type"],
            limit_price=args.get("limit_price"),
            stop_price=args.get("stop_price"),
            time_in_force=args.get("time_in_force", "day"),
            client_order_id=client_order_id,
        )
        return _json_text({
            "status": "submitted",
            "client_order_id": client_order_id,
            "contract_id": contract_id,
            "result": result,
        })
    except ProjectXError as e:
        return _json_text({"error": str(e), "status": "failed"})


@tool(
    "topstep_cancel_order",
    "Cancel a working order by broker order ID.",
    {"broker_order_id": str},
)
async def cancel_order(args: dict[str, Any]) -> dict[str, Any]:
    try:
        result = get_client().cancel_order(
            account_id=get_account_id(),
            order_id=args["broker_order_id"],
        )
        return _json_text({"status": "cancelled", "result": result})
    except ProjectXError as e:
        return _json_text({"error": str(e)})


@tool(
    "topstep_flatten_all",
    (
        "Emergency flatten — cancel all working orders and close all "
        "positions at market. Use only on risk breach or explicit user "
        "command. The risk hook must specifically allow this — ordinarily "
        "blocked."
    ),
    {"reason": str},
)
async def flatten_all(args: dict[str, Any]) -> dict[str, Any]:
    try:
        client = get_client()
        account_id = get_account_id()

        # 1. Cancel all working orders
        open_orders = client.get_working_orders(account_id)
        cancelled = []
        for o in open_orders:
            try:
                oid = o.get("id") or o.get("orderId")
                client.cancel_order(account_id, oid)
                cancelled.append(oid)
            except ProjectXError:
                pass

        # 2. Close each open position via the native close endpoint
        # (cleaner than reversing with opposite-side market orders)
        open_positions = client.get_positions(account_id)
        closed = []
        for p in open_positions:
            contract_id = p.get("contractId")
            if not contract_id:
                continue
            try:
                r = client.close_position(account_id, contract_id)
                closed.append({"contract": contract_id, "result": r})
            except ProjectXError as e:
                closed.append({"contract": contract_id, "error": str(e)})

        return _json_text({
            "status": "flattened",
            "reason": args.get("reason", "unspecified"),
            "cancelled_orders": cancelled,
            "closed_positions": closed,
        })
    except ProjectXError as e:
        return _json_text({"error": str(e), "status": "failed"})


TOOLS = [
    get_account,
    get_positions,
    get_working_orders,
    find_contract,
    place_order,
    cancel_order,
    flatten_all,
]

server = create_sdk_mcp_server(name="topstep", version="0.1.0", tools=TOOLS)
