"""MCP server exposing the fundamentals loaders to agents.

Agents call these tools when they wake to gather context beyond price —
real yields, EIA inventories, CFTC positioning, USDA crop progress, etc.
Responses are JSON-serialized for the agent to parse.
"""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from tools.fundamentals import cftc as cftc_mod
from tools.fundamentals import eia as eia_mod
from tools.fundamentals import fred as fred_mod
from tools.fundamentals import usda as usda_mod


def _df_to_json(df, tail: int = 20) -> str:
    """Serialize a DataFrame's last N rows to JSON for agent consumption."""
    if df is None or df.empty:
        return json.dumps({"rows": [], "note": "no data"})
    tail_df = df.tail(tail).reset_index()
    # Coerce timestamps to ISO strings
    for col in tail_df.columns:
        if "date" in col.lower() or "period" in col.lower() or col == "index":
            tail_df[col] = tail_df[col].astype(str)
    return json.dumps({
        "rows": tail_df.to_dict(orient="records"),
        "total_rows": len(df),
        "showing_tail": min(tail, len(df)),
    }, default=str)


# ── FRED ─────────────────────────────────────────────────────────
@tool(
    "fred_series",
    "Load a FRED macro series (rates, inflation, DXY, breakevens, etc.). "
    "Known series in FRED_SERIES_COMMON — use codes like DGS10, DFII10, "
    "CPIAUCSL, DTWEXBGS, BAMLH0A0HYM2.",
    {"series_id": str, "start": str, "end": str},
)
async def fred_series(args: dict[str, Any]) -> dict[str, Any]:
    df = fred_mod.load_series(args["series_id"], args["start"], args["end"])
    return {"content": [{"type": "text", "text": _df_to_json(df)}]}


# ── EIA ──────────────────────────────────────────────────────────
@tool(
    "eia_crude_stocks",
    "Weekly US crude oil ending stocks (thousand barrels) with surprise z-score. "
    "Returns last 20 weeks with week-over-week change and z-score vs trailing 52 weeks.",
    {"start": str, "end": str},
)
async def eia_crude_stocks(args: dict[str, Any]) -> dict[str, Any]:
    df = eia_mod.weekly_surprise(eia_mod.crude_stocks, args["start"], args["end"])
    return {"content": [{"type": "text", "text": _df_to_json(df)}]}


@tool(
    "eia_distillate_stocks",
    "Weekly US distillate (diesel/ULSD) ending stocks + surprise z-score.",
    {"start": str, "end": str},
)
async def eia_distillate_stocks(args: dict[str, Any]) -> dict[str, Any]:
    df = eia_mod.weekly_surprise(eia_mod.distillate_stocks, args["start"], args["end"])
    return {"content": [{"type": "text", "text": _df_to_json(df)}]}


@tool(
    "eia_natgas_storage",
    "Weekly US working gas in underground storage (BCF) + surprise z-score.",
    {"start": str, "end": str},
)
async def eia_natgas_storage(args: dict[str, Any]) -> dict[str, Any]:
    df = eia_mod.weekly_surprise(eia_mod.natgas_storage, args["start"], args["end"])
    return {"content": [{"type": "text", "text": _df_to_json(df)}]}


# ── CFTC ─────────────────────────────────────────────────────────
@tool(
    "cftc_commitments",
    "Weekly Commitments of Traders data (positioning) for a named market. "
    "Markets: crude_wti, natgas, gold, silver, copper, corn, soybeans, wheat, "
    "10y_note, 30y_bond, eur, gbp, jpy, sp500, nasdaq.",
    {"market": str, "start": str, "end": str},
)
async def cftc_commitments(args: dict[str, Any]) -> dict[str, Any]:
    df = cftc_mod.commitments(args["market"], args["start"], args["end"])
    return {"content": [{"type": "text", "text": _df_to_json(df)}]}


# ── USDA NASS ────────────────────────────────────────────────────
@tool(
    "usda_crop_progress",
    "Weekly USDA NASS crop progress for a commodity (CORN, SOYBEANS, WHEAT). "
    "Shows planting / silking / harvest percentages vs trend.",
    {"commodity": str, "year_start": int, "year_end": int},
)
async def usda_crop_progress(args: dict[str, Any]) -> dict[str, Any]:
    df = usda_mod.crop_progress(args["commodity"], args["year_start"], args["year_end"])
    return {"content": [{"type": "text", "text": _df_to_json(df)}]}


@tool(
    "usda_cattle_on_feed",
    "Monthly Cattle on Feed — on-feed, placements, marketings.",
    {"year_start": int, "year_end": int},
)
async def usda_cattle_on_feed(args: dict[str, Any]) -> dict[str, Any]:
    df = usda_mod.cattle_on_feed(args["year_start"], args["year_end"])
    return {"content": [{"type": "text", "text": _df_to_json(df)}]}


TOOLS = [
    fred_series,
    eia_crude_stocks,
    eia_distillate_stocks,
    eia_natgas_storage,
    cftc_commitments,
    usda_crop_progress,
    usda_cattle_on_feed,
]

server = create_sdk_mcp_server(name="fundamentals", version="0.1.0", tools=TOOLS)
