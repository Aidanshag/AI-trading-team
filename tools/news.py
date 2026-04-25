"""News and web-search MCP server — STUB.

Recommended wiring: Tavily for web search, NewsAPI/Benzinga/Reuters for
headlines. Cache headlines into state_store.news_items so agents can be
audited on what they saw.
"""

from __future__ import annotations

from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool


@tool(
    "search_news",
    "Search recent news headlines relevant to one or more symbols or topics.",
    {"query": str, "hours": int, "limit": int},
)
async def search_news(args: dict[str, Any]) -> dict[str, Any]:
    raise NotImplementedError("Wire to your news vendor and cache into state_store.news_items.")


@tool(
    "web_search",
    "General web search (for macro context, background reading, filings).",
    {"query": str, "limit": int},
)
async def web_search(args: dict[str, Any]) -> dict[str, Any]:
    raise NotImplementedError("Wire to Tavily or similar.")


@tool(
    "fetch_url",
    "Fetch and return cleaned text content of a URL.",
    {"url": str},
)
async def fetch_url(args: dict[str, Any]) -> dict[str, Any]:
    raise NotImplementedError("Wire to httpx + readability.")


TOOLS = [search_news, web_search, fetch_url]

server = create_sdk_mcp_server(name="news", version="0.1.0", tools=TOOLS)
