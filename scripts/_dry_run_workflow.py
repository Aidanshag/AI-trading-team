"""End-to-end dry-run of the trading workflow.

Walks: SESSION_OPEN -> CIO brief + analyst pick -> Analyst chain
       (thesis -> Red Team -> PM -> Risk Manager).

Stops BEFORE Execution Trader. The Execution Trader's allowedTools list
is monkey-patched to remove the place_order tool for this dry run, so
even if the chain reached it, no broker order could be placed.

Use this to confirm the full pipeline holds together end-to-end. Run
on weekend or any time markets are closed — won't affect P&L either way.
"""

import asyncio

from runtime.orchestrator import Orchestrator, EXECUTION_ONLY_TOOLS


async def main() -> None:
    orch = Orchestrator()

    # SAFETY: strip any execution tools from any agent's allowed list for
    # this dry run, defense-in-depth against accidentally placing orders.
    blocked = set(EXECUTION_ONLY_TOOLS)
    for spec in orch.specs.values():
        spec.allowed_tools = [t for t in spec.allowed_tools if t not in blocked]
    print("[DRY-RUN] All place_order/cancel_order tools stripped from agents.")
    print()

    print("Step 1/2: SESSION_OPEN workflow (CIO brief + analyst pick)")
    print("-" * 70)
    result = await orch.session_open_workflow()
    print(f"Result: {result}")
    print()

    print("=" * 70)
    print("DRY RUN COMPLETE")
    print("=" * 70)
    print(f"Final status: {result.get('status')}")
    print()
    print("Inspect output:")
    print("  - vault/journal/<today>.md  - CIO brief + chain entries")
    print("  - state/fund.db decisions table - chain handoff records")


if __name__ == "__main__":
    asyncio.run(main())
