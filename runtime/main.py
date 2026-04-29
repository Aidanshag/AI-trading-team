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
    # Belt-and-braces: load .env here too in case _preflight gets called
    # before main()'s load_dotenv (e.g. test imports).
    load_dotenv()
    missing = [k for k in ("ANTHROPIC_API_KEY",) if not os.environ.get(k)]
    if missing:
        console.print(f"[red]Missing env vars:[/] {missing}. Fill .env first.")
        sys.exit(2)

    db = get_db()
    if not db.path.exists():
        console.print("[yellow]State DB missing — initializing schema.[/]")
    db.init_schema()

    # Strip whitespace + inline comments from .env value (e.g.
    # "live       # paper | live" → "live"). Common .env-parser quirk
    # that previously caused FUND_MODE comparisons to silently fail.
    raw_mode = os.environ.get("FUND_MODE", "paper")
    mode = raw_mode.split("#", 1)[0].strip().lower()
    console.print(f"[bold]Fund starting in [cyan]{mode}[/] mode.[/]")
    if mode == "live":
        console.print("[red bold]LIVE MODE — real orders will be placed via Topstep/ProjectX.[/]")
        console.print(
            "[yellow]Risk hook is the final gate. Verify "
            "config/risk_limits.yaml before letting the runtime run unattended.[/]"
        )
        # The stale 2026-04-23 halt-on-live guard was removed 2026-04-29.
        # ProjectX client is implemented (tools/projectx_client.py) and
        # has placed real fills (ZN order #2897285454 was the validation).
    elif mode != "paper":
        console.print(f"[red]Unknown FUND_MODE={raw_mode!r}. Set to 'paper' or 'live'.[/]")
        sys.exit(3)


async def _amain() -> None:
    orch = Orchestrator()
    await orch.run()


def main() -> None:
    # CRITICAL: load .env BEFORE _preflight runs its env-var checks. The
    # original ordering was correct in this function but _preflight was
    # being called before this in some background-launch paths because the
    # imports at module scope can resolve env-dependent objects. Belt and
    # braces: explicitly call load_dotenv() inside _preflight too if needed.
    load_dotenv()
    _preflight()
    try:
        asyncio.run(_amain())
    except KeyboardInterrupt:
        console.print("[yellow]Shutdown requested.[/]")


if __name__ == "__main__":
    main()
