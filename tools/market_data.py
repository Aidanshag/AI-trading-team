"""Market data MCP server — LIVE via ProjectX.

Uses the ProjectX client already instantiated for Topstep broker tools.
Real-time quotes come through the order endpoints (bid/ask via contract
metadata); historical bars via /api/History/retrieveBars.

For MARKET HOURS non-Topstep-covered data (economic calendar, options
chains), stubs remain.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from tools.projectx_client import ProjectXError, get_client


def _json_text(obj: Any) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(obj, default=str)}]}


_UNIT_MAP = {
    "1s": (1, 1), "1m": (2, 1), "5m": (2, 5), "15m": (2, 15), "30m": (2, 30),
    "1h": (3, 1), "4h": (3, 4), "1d": (4, 1), "1w": (5, 1),
}


@tool(
    "get_quote",
    "Latest quote for a symbol via ProjectX (front-month contract). Returns "
    "last trade, bid/ask if available, and contract metadata.",
    {"symbol": str},
)
async def get_quote(args: dict[str, Any]) -> dict[str, Any]:
    try:
        client = get_client()
        contracts = client.search_contracts(args["symbol"], live=False)
        if not contracts:
            return _json_text({"error": f"no contracts for {args['symbol']}"})
        front = sorted(
            contracts,
            key=lambda c: c.get("expiryDate") or c.get("lastTradeDate") or "",
        )[0]

        # Latest 1-minute bar as a reliable quote proxy
        now = datetime.now(tz=timezone.utc)
        bars = client.get_bars(
            contract_id=front.get("id") or front.get("contractId"),
            start_time=(now - timedelta(minutes=10)).isoformat(),
            end_time=now.isoformat(),
            unit=2, unit_number=1, limit=10,
            live=False,
        )
        latest = bars[-1] if bars else None

        return _json_text({
            "symbol": args["symbol"],
            "contract": front,
            "latest_bar": latest,
        })
    except ProjectXError as e:
        return _json_text({"error": str(e)})


@tool(
    "get_bars",
    (
        "Historical OHLCV bars via ProjectX. "
        "Args: symbol (root, e.g. 'CL'), timeframe ('1m'|'5m'|'15m'|'30m'|"
        "'1h'|'4h'|'1d'|'1w'), lookback (int bars, default 100)."
    ),
    {"symbol": str, "timeframe": str, "lookback": int},
)
async def get_bars(args: dict[str, Any]) -> dict[str, Any]:
    try:
        tf = args.get("timeframe", "1d")
        if tf not in _UNIT_MAP:
            return _json_text({"error": f"bad timeframe {tf!r}, use {list(_UNIT_MAP)}"})
        unit, unit_n = _UNIT_MAP[tf]
        lookback = int(args.get("lookback", 100))

        # Approximate time range for the requested lookback
        per_bar = {
            "1s": 1/60, "1m": 1, "5m": 5, "15m": 15, "30m": 30,
            "1h": 60, "4h": 240, "1d": 60*24, "1w": 60*24*7,
        }[tf]
        total_minutes = int(lookback * per_bar * 1.5)  # buffer for gaps
        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(minutes=total_minutes)

        client = get_client()
        contract_id = client.front_month_contract_id(args["symbol"])
        bars = client.get_bars(
            contract_id=contract_id,
            start_time=start.isoformat(),
            end_time=end.isoformat(),
            unit=unit, unit_number=unit_n, limit=lookback,
            live=False,
        )
        return _json_text({
            "symbol": args["symbol"],
            "timeframe": tf,
            "contract_id": contract_id,
            "bars_count": len(bars),
            "bars": bars[-lookback:],
        })
    except ProjectXError as e:
        return _json_text({"error": str(e)})


@tool(
    "get_option_chain",
    "Full option chain for a futures underlying. STUB — ProjectX options "
    "chain endpoint depends on the account's data entitlement. Wire once "
    "you confirm the endpoint with TopstepX support.",
    {"underlying": str, "expiries": int},
)
async def get_option_chain(args: dict[str, Any]) -> dict[str, Any]:
    return _json_text({
        "error": "Option chain endpoint not yet wired. Contact TopstepX "
                 "support to confirm /api/Options path for your entitlement."
    })


@tool(
    "get_economic_calendar",
    "Upcoming high-impact economic events in the next N hours. STUB — "
    "wire to TradingEconomics / FRED calendar when ready.",
    {"hours_ahead": int},
)
async def get_economic_calendar(args: dict[str, Any]) -> dict[str, Any]:
    return _json_text({
        "error": "Economic calendar not wired. Free sources: FRED release "
                 "calendar, EIA/USDA RSS feeds."
    })


TOOLS = [get_quote, get_bars, get_option_chain, get_economic_calendar]

server = create_sdk_mcp_server(name="market_data", version="0.1.0", tools=TOOLS)
