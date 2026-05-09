"""MCP server exposing options pricing + Greeks to agents.

Used primarily by Options Risk agent to compute Greeks on every options
proposal. Net delta/gamma/vega/theta of multi-leg structures available
via `compute_structure_greeks`.
"""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from tools.options_pricing import Leg, black76, implied_vol, structure_greeks


def _json(obj: Any) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(obj, default=str)}]}


@tool(
    "compute_greeks",
    (
        "Compute Black-76 price + Greeks for a single futures option. "
        "Args: F (futures price), K (strike), T (years to expiry; e.g. 30/365), "
        "sigma (annualized vol as decimal, 0.25 = 25%), r (risk-free rate, "
        "default 0.04), right ('C' or 'P')."
    ),
    {"F": float, "K": float, "T": float, "sigma": float, "r": float, "right": str},
)
async def compute_greeks(args: dict[str, Any]) -> dict[str, Any]:
    res = black76(
        F=float(args["F"]),
        K=float(args["K"]),
        T=float(args["T"]),
        sigma=float(args["sigma"]),
        r=float(args.get("r", 0.04)),
        right=args.get("right", "C"),
    )
    return _json({
        "price": res.price,
        "delta": res.delta,
        "gamma": res.gamma,
        "vega_per_pct": res.vega_per_pct,
        "theta_per_day": res.theta_per_day,
        "rho": res.rho,
    })


@tool(
    "compute_implied_vol",
    (
        "Solve for implied volatility from a market option price. "
        "Args: market_price, F, K, T, r, right. Returns sigma (decimal)."
    ),
    {"market_price": float, "F": float, "K": float, "T": float, "r": float, "right": str},
)
async def compute_implied_vol(args: dict[str, Any]) -> dict[str, Any]:
    iv = implied_vol(
        market_price=float(args["market_price"]),
        F=float(args["F"]),
        K=float(args["K"]),
        T=float(args["T"]),
        r=float(args.get("r", 0.04)),
        right=args.get("right", "C"),
    )
    return _json({"implied_vol": iv})


@tool(
    "compute_structure_greeks",
    (
        "Net Greeks of a multi-leg option structure. Each leg: F, K, T, sigma, "
        "right ('C'|'P'), side ('long'|'short'), qty. "
        "Returns net_delta, net_gamma, net_vega_per_pct, net_theta_per_day, "
        "net_price (positive=debit, negative=credit), max_loss_usd."
    ),
    {"legs": list},
)
async def compute_structure_greeks(args: dict[str, Any]) -> dict[str, Any]:
    legs = [
        Leg(
            F=float(L["F"]), K=float(L["K"]), T=float(L["T"]),
            sigma=float(L["sigma"]), right=L["right"], side=L["side"],
            qty=int(L.get("qty", 1)), r=float(L.get("r", 0.04)),
        )
        for L in args["legs"]
    ]
    return _json(structure_greeks(legs))


TOOLS = [compute_greeks, compute_implied_vol, compute_structure_greeks]

server = create_sdk_mcp_server(name="options", version="0.1.0", tools=TOOLS)
