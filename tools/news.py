"""News and web-search MCP server.

`search_news` works against the RSS feed list in `config/news_sources.yaml`
(no API key needed). Agents query by keyword + recency window, results are
de-duplicated and ranked by recency. Cached to state.news_items for audit.

`web_search` and `fetch_url` remain stubs until paid tier is wired.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import yaml
from claude_agent_sdk import create_sdk_mcp_server, tool

from state.db import get_db, utcnow_iso

NEWS_SOURCES = Path("config/news_sources.yaml")


def _load_rss_feeds() -> dict[str, str]:
    if not NEWS_SOURCES.exists():
        return {}
    cfg = yaml.safe_load(NEWS_SOURCES.read_text()) or {}
    return cfg.get("rss_feeds", {})


def _parse_feed(url: str, timeout: float = 10.0) -> list[dict[str, Any]]:
    """Fetch and parse one RSS feed. Returns list of {title, link, published, summary, source}."""
    try:
        import feedparser
        # feedparser can fetch directly but using httpx for timeout control
        resp = httpx.get(url, timeout=timeout, follow_redirects=True,
                         headers={"User-Agent": "AI-Trading-Fund/0.1"})
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
        items = []
        for entry in parsed.entries[:50]:
            items.append({
                "title": getattr(entry, "title", ""),
                "link": getattr(entry, "link", ""),
                "published": getattr(entry, "published", "") or getattr(entry, "updated", ""),
                "summary": (getattr(entry, "summary", "") or "")[:500],
                "source_url": url,
            })
        return items
    except Exception:
        return []


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "")


def _matches_query(item: dict, query: str) -> bool:
    q = query.lower()
    blob = f"{item.get('title','')} {item.get('summary','')}".lower()
    # OR-of-tokens: any whitespace-separated word matches
    tokens = [t for t in q.split() if len(t) >= 2]
    return any(t in blob for t in tokens) if tokens else True


@tool(
    "search_news",
    (
        "Search recent news headlines from RSS feeds (CNBC, Reuters, MarketWatch, "
        "WSJ, Fed, BLS, Treasury, EIA, USDA). Args: query (keywords), "
        "hours (lookback window, default 24), limit (max results, default 20). "
        "Returns headlines with title, link, source, published timestamp, summary."
    ),
    {"query": str, "hours": int, "limit": int},
)
async def search_news(args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("query", "")).strip()
    hours = int(args.get("hours", 24))
    limit = int(args.get("limit", 20))

    feeds = _load_rss_feeds()
    if not feeds:
        return {"content": [{"type": "text", "text": json.dumps({
            "error": "No RSS feeds configured in config/news_sources.yaml",
            "items": [],
        })}]}

    all_items: list[dict] = []
    for name, url in feeds.items():
        for item in _parse_feed(url):
            item["source_name"] = name
            item["summary"] = _strip_html(item.get("summary", ""))
            all_items.append(item)

    # Filter by query (if provided)
    if query:
        all_items = [i for i in all_items if _matches_query(i, query)]

    # Filter by recency: only keep items with parseable published <= hours
    now = datetime.now(tz=timezone.utc)
    cutoff = now - timedelta(hours=hours)

    def _parse_published(s: str) -> datetime | None:
        try:
            from email.utils import parsedate_to_datetime
            d = parsedate_to_datetime(s)
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return d
        except Exception:
            return None

    fresh: list[tuple[datetime, dict]] = []
    for item in all_items:
        d = _parse_published(item.get("published", ""))
        if d is None:
            continue
        if d >= cutoff:
            fresh.append((d, item))

    # Sort recent first; deduplicate by title (case-insensitive)
    seen_titles: set[str] = set()
    deduped: list[dict] = []
    for d, item in sorted(fresh, key=lambda x: x[0], reverse=True):
        t = item.get("title", "").strip().lower()
        if t in seen_titles or not t:
            continue
        seen_titles.add(t)
        item["published_iso"] = d.isoformat()
        deduped.append(item)
        if len(deduped) >= limit:
            break

    # Persist to state.news_items for audit
    if deduped:
        try:
            db = get_db()
            with db.tx() as c:
                for item in deduped:
                    c.execute(
                        """INSERT INTO news_items (ts, source, url, headline, body, symbols, impact)
                           VALUES (?,?,?,?,?,?,?)""",
                        (
                            item.get("published_iso", utcnow_iso()),
                            item.get("source_name", "rss"),
                            item.get("link", ""),
                            item.get("title", ""),
                            item.get("summary", ""),
                            "",
                            "low",
                        ),
                    )
        except Exception:
            pass  # never fail the read on cache write

    return {"content": [{"type": "text", "text": json.dumps({
        "query": query,
        "hours_window": hours,
        "n_results": len(deduped),
        "items": deduped,
    }, default=str)}]}


@tool(
    "web_search",
    "General web search via Tavily/Perplexity. Configure key in .env.",
    {"query": str, "limit": int},
)
async def web_search(args: dict[str, Any]) -> dict[str, Any]:
    import os
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        return {"content": [{"type": "text", "text": json.dumps({
            "error": "Web search not configured. Set TAVILY_API_KEY in .env.",
        })}]}
    raise NotImplementedError("Tavily client not yet wired.")


@tool(
    "fetch_url",
    "Fetch and return cleaned text content of a URL.",
    {"url": str},
)
async def fetch_url(args: dict[str, Any]) -> dict[str, Any]:
    url = args.get("url", "")
    if not url:
        return {"content": [{"type": "text", "text": '{"error":"missing url"}'}]}
    # Check ToS guardrails
    try:
        cfg = yaml.safe_load(NEWS_SOURCES.read_text()) or {}
        blocked = (cfg.get("tos_guardrails", {}) or {}).get("never_fetch_hosts", [])
        for host in blocked:
            if host in url:
                return {"content": [{"type": "text", "text": json.dumps({
                    "error": f"Host {host} on never_fetch list (ToS)",
                })}]}
    except Exception:
        pass
    try:
        r = httpx.get(url, timeout=15.0, follow_redirects=True,
                      headers={"User-Agent": "AI-Trading-Fund/0.1"})
        r.raise_for_status()
        text = _strip_html(r.text)[:8000]
        return {"content": [{"type": "text", "text": json.dumps({
            "url": url,
            "status": r.status_code,
            "text": text,
        })}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": json.dumps({
            "error": str(e),
        })}]}


TOOLS = [search_news, web_search, fetch_url]
server = create_sdk_mcp_server(name="news", version="0.1.0", tools=TOOLS)
