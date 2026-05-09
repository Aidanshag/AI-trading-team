"""First live CIO wake against the user's Combine.

Read-only: the CIO reads account state and writes a brief greeting to
the journal. No orders. No analyst wakes. Just a round-trip confirmation
that the full pipeline works end-to-end.
"""

import asyncio
from runtime.orchestrator import Orchestrator


async def main() -> None:
    orch = Orchestrator()
    print(f"Agents loaded: {len(orch.specs)}")
    print(f"MCP servers:   {list(orch.mcp_servers)}")
    print()
    print("Waking CIO...")
    print()

    task = (
        "Session introduction. Do the following in order:\n"
        "1. Call `topstep_get_account` to read the live account state from Topstep.\n"
        "2. Call `vault_append_journal` to write a brief (3-4 sentence) greeting "
        "to today's journal under heading 'CIO — first live wake'. Include the "
        "account name and balance you observed. Note the Combine rules: $1000 "
        "DLL, $2000 TDD. State the fund's posture: paper/observation mode until "
        "user authorizes live trading.\n"
        "3. Call `state_record_decision` with kind='session_init' and a short "
        "rationale noting the first live wake completed.\n"
        "Do NOT call any trading tools. Do NOT wake other agents. Keep total "
        "output under 400 tokens."
    )

    result = await orch.wake_agent("CIO", task)

    print("=" * 70)
    print(f"Model used:      {result.get('model')}")
    print(f"Messages:        {result.get('messages_count')}")
    print(f"Usage:           {result.get('usage')}")
    print()
    print("Final text from CIO:")
    print("-" * 70)
    print(result.get("final_text") or "(no text)")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
