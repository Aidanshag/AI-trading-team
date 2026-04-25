"""Fund entry point.

    fund                     # run the orchestrator against current config
    python -m runtime.main   # same

Reads `.env`, initializes the DB if missing, and starts the event loop.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console

from state.db import get_db
from runtime.orchestrator import Orchestrator

console = Console()


def _preflight() -> None:
    missing = [k for k in ("ANTHROPIC_API_KEY",) if not os.environ.get(k)]
    if missing:
        console.print(f"[red]Missing env vars:[/] {missing}. Fill .env first.")
        sys.exit(2)

    db = get_db()
    if not db.path.exists():
        console.print("[yellow]State DB missing — initializing schema.[/]")
    db.init_schema()

    mode = os.environ.get("FUND_MODE", "paper").lower()
    console.print(f"[bold]Fund starting in [cyan]{mode}[/] mode.[/]")
    if mode == "live":
        console.print("[red bold]LIVE MODE — real orders will be placed.[/]")
        console.print(
            "[red]Halting: set FUND_MODE=paper until ProjectX client is "
            "implemented and fully reviewed.[/]"
        )
        sys.exit(3)


async def _amain() -> None:
    orch = Orchestrator()
    await orch.run()


def main() -> None:
    load_dotenv()
    _preflight()
    try:
        asyncio.run(_amain())
    except KeyboardInterrupt:
        console.print("[yellow]Shutdown requested.[/]")


if __name__ == "__main__":
    main()
