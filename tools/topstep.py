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
    """Place a Topstep order with DB-side idempotency + audit-log persistence.

    The schema's UNIQUE(client_order_id) on the orders table is our
    duplicate-submission guard. We INSERT first (status='proposed') so
    a retry of the same client_order_id raises IntegrityError before
    a second broker call ever happens.

    Stop-entry orders default to time_in_force='day' to prevent the
    overnight-fill failure mode (2026-04-29 ZN lesson). To override,
    explicitly pass time_in_force='gtc'.
    """
    from state.db import get_db, utcnow_iso
    import sqlite3

    client_order_id = args.get("client_order_id") or f"fund_{uuid.uuid4().hex[:12]}"
    db = get_db()

    # Stop-entry safety: force 'day' TIF unless caller explicitly opts into GTC.
    # Stop-entry orders that persist overnight have filled in thin liquidity
    # and produced unprofitable fills — the ZN ORB loss was exactly this.
    order_type = (args.get("order_type") or "").lower()
    if order_type in ("stop", "stop_limit") and not args.get("time_in_force"):
        args["time_in_force"] = "day"

    # 1. Pre-flight INSERT — fails if the client_order_id was used before.
    try:
        with db.tx() as c:
            c.execute(
                """INSERT INTO orders
                    (client_order_id, agent, ts_proposed, symbol, contract_month,
                     side, order_type, qty, limit_price, stop_price,
                     status, risk_verdict)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (client_order_id, args.get("agent") or "execution_trader",
                 utcnow_iso(), args["symbol"], args.get("contract_month"),
                 args["side"], args["order_type"], int(args["qty"]),
                 args.get("limit_price"), args.get("stop_price"),
                 "proposed", "allow"),  # if we got here, risk hook said allow
            )
    except sqlite3.IntegrityError:
        return _json_text({
            "status": "duplicate",
            "error": f"client_order_id {client_order_id!r} already used — "
                     "idempotent rejection. Generate a new id and retry if intentional.",
            "client_order_id": client_order_id,
        })

    # 2. Submit to broker
    try:
        client = get_client()
        account_id = get_account_id()
        contract_id = client.front_month_contract_id(args["symbol"])

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

        # 3. Mark as submitted with broker order id (best-effort lookup)
        broker_oid = None
        if isinstance(result, dict):
            broker_oid = (result.get("orderId") or result.get("id")
                          or result.get("brokerOrderId"))
        try:
            with db.tx() as c:
                c.execute(
                    """UPDATE orders SET ts_submitted=?, status=?, broker_order_id=?
                        WHERE client_order_id=?""",
                    (utcnow_iso(), "submitted",
                     str(broker_oid) if broker_oid else None,
                     client_order_id),
                )
        except Exception:
            pass  # broker submitted; DB update failed but trade is real

        return _json_text({
            "status": "submitted",
            "client_order_id": client_order_id,
            "contract_id": contract_id,
            "result": result,
        })
    except ProjectXError as e:
        # Broker rejected — mark the row so a retry with same id stays blocked
        try:
            with db.tx() as c:
                c.execute(
                    """UPDATE orders SET status=?, risk_reason=?
                        WHERE client_order_id=?""",
                    ("rejected", f"broker_error: {e}"[:500], client_order_id),
                )
        except Exception:
            pass
        return _json_text({"error": str(e), "status": "failed",
                           "client_order_id": client_order_id})


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

        # 1. Cancel all working orders. Track failures explicitly — a
        # surviving stop combined with a market close = double exit.
        from state.db import get_db
        db = get_db()
        open_orders = client.get_working_orders(account_id)
        cancelled: list[str] = []
        cancel_failed: list[dict[str, Any]] = []
        for o in open_orders:
            oid = o.get("id") or o.get("orderId")
            try:
                client.cancel_order(account_id, oid)
                cancelled.append(str(oid))
            except ProjectXError as e:
                cancel_failed.append({"order_id": oid, "error": str(e)})
                db.record_risk_event(
                    severity="warn", rule="flatten_cancel_failed",
                    detail={"order_id": oid, "error": str(e)[:300],
                            "context": "flatten_all step 1 — surviving stop "
                                       "may double-exit when position closes"},
                )

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
            "status": "flattened" if not cancel_failed else "flattened_with_warnings",
            "reason": args.get("reason", "unspecified"),
            "cancelled_orders": cancelled,
            "cancel_failures": cancel_failed,
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
