"""Obsidian vault MCP server — REAL.

Exposes read/append operations on the `vault/` folder so agents can read
playbooks and theses, and append journal/thesis/review notes.

Safety:
- Writes are append-only or atomic-replace; no in-place edits.
- Confined to the vault root; path traversal (`..`) is blocked.
- Wikilinks and frontmatter are plain markdown, no plugin dependencies.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

VAULT_ROOT = Path(os.environ.get("VAULT_PATH", "./vault")).resolve()


def _safe_path(rel: str) -> Path:
    p = (VAULT_ROOT / rel).resolve()
    if VAULT_ROOT not in p.parents and p != VAULT_ROOT:
        raise ValueError(f"Path escapes vault root: {rel}")
    return p


def _today_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")


@tool(
    "vault_read",
    "Read a markdown note from the vault. Path is relative to vault root.",
    {"path": str},
)
async def vault_read(args: dict[str, Any]) -> dict[str, Any]:
    p = _safe_path(args["path"])
    if not p.exists():
        return {"content": [{"type": "text", "text": f"(not found: {args['path']})"}]}
    return {"content": [{"type": "text", "text": p.read_text(encoding="utf-8")}]}


@tool(
    "vault_list",
    "List markdown files under a folder (default: vault root). Non-recursive unless 'recursive'=true.",
    {"folder": str, "recursive": bool},
)
async def vault_list(args: dict[str, Any]) -> dict[str, Any]:
    folder = _safe_path(args.get("folder") or "")
    pattern = "**/*.md" if args.get("recursive") else "*.md"
    files = sorted(str(f.relative_to(VAULT_ROOT)) for f in folder.glob(pattern))
    return {"content": [{"type": "text", "text": "\n".join(files) or "(empty)"}]}


@tool(
    "vault_append_journal",
    (
        "Append a timestamped block to today's journal note "
        "(vault/journal/YYYY-MM-DD.md). Creates the note if missing. "
        "Use this for any agent observation, decision, or hand-off."
    ),
    {"agent": str, "heading": str, "body": str},
)
async def vault_append_journal(args: dict[str, Any]) -> dict[str, Any]:
    path = _safe_path(f"journal/{_today_iso()}.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(
            f"---\ndate: {_today_iso()}\ntype: journal\n---\n\n# Journal — {_today_iso()}\n\n",
            encoding="utf-8",
        )
    block = (
        f"\n## {datetime.now(tz=timezone.utc).strftime('%H:%M UTC')} — "
        f"{args['agent']} — {args['heading']}\n\n{args['body']}\n"
    )
    with path.open("a", encoding="utf-8") as f:
        f.write(block)
    return {"content": [{"type": "text", "text": str(path.relative_to(VAULT_ROOT))}]}


@tool(
    "vault_upsert_thesis",
    (
        "Create or replace a thesis note under vault/theses/{symbol}.md. "
        "Body should be the full markdown (include frontmatter). Atomic replace."
    ),
    {"symbol": str, "body": str},
)
async def vault_upsert_thesis(args: dict[str, Any]) -> dict[str, Any]:
    path = _safe_path(f"theses/{args['symbol']}.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".md.tmp")
    tmp.write_text(args["body"], encoding="utf-8")
    os.replace(tmp, path)
    return {"content": [{"type": "text", "text": str(path.relative_to(VAULT_ROOT))}]}


@tool(
    "vault_append_review",
    "Append a post-trade review entry under vault/reviews/YYYY-MM-DD.md.",
    {"symbol": str, "outcome": str, "lessons": str},
)
async def vault_append_review(args: dict[str, Any]) -> dict[str, Any]:
    path = _safe_path(f"reviews/{_today_iso()}.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(
            f"---\ndate: {_today_iso()}\ntype: review\n---\n\n# Post-trade reviews — {_today_iso()}\n\n",
            encoding="utf-8",
        )
    block = (
        f"\n## [[{args['symbol']}]] — {args['outcome']}\n\n{args['lessons']}\n"
    )
    with path.open("a", encoding="utf-8") as f:
        f.write(block)
    return {"content": [{"type": "text", "text": str(path.relative_to(VAULT_ROOT))}]}


TOOLS = [
    vault_read,
    vault_list,
    vault_append_journal,
    vault_upsert_thesis,
    vault_append_review,
]

server = create_sdk_mcp_server(name="vault", version="0.1.0", tools=TOOLS)
