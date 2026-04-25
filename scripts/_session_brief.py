"""Step 1 of the first live session: CIO session brief + analyst selection.

The CIO reads live account state, scans the regime file, picks ONE analyst
to wake today, and explains the choice. Must end the brief with an explicit
line:  WAKE: <analyst name>  or  WAKE: none
so the next script can parse the decision.
"""

import asyncio
from runtime.orchestrator import Orchestrator


async def main() -> None:
    orch = Orchestrator()

    task = (
        "FIRST LIVE SESSION — SESSION BRIEF\n\n"
        "Context: this is the fund's first live session on the Topstep $50K "
        "Combine. We are in observation/evaluation mode. The goal today is a "
        "single well-calibrated trade idea — or no trade if conditions don't "
        "support one.\n\n"
        "Do this in order:\n\n"
        "1. Call `topstep_get_account` to confirm live balance.\n"
        "2. Call `vault_read` on `regime/current.md` to read the current regime.\n"
        "3. Call `state_recent_decisions` with limit=5 to see what the fund "
        "   has been doing recently.\n"
        "4. Check the CME session state: is the market currently open for "
        "   major contracts (/ES, /CL, /GC, /ZN)? If it's thin overnight or "
        "   closed, note that — overnight thin markets are not where we make "
        "   our first real trade.\n"
        "5. Publish a concise daily brief (<200 words) to today's journal "
        "   via `vault_append_journal`. Include:\n"
        "   - regime read (one line)\n"
        "   - session-open conditions (open / thin / closed)\n"
        "   - analyst wake plan with explicit reasoning\n\n"
        "6. Record a decision with kind='session_brief'.\n\n"
        "Critically: end your output with a SINGLE LINE in one of these "
        "exact formats:\n"
        "   WAKE: Energies Analyst\n"
        "   WAKE: Metals Analyst\n"
        "   WAKE: Grains Analyst\n"
        "   WAKE: Softs Analyst\n"
        "   WAKE: Livestock Analyst\n"
        "   WAKE: Rates Analyst\n"
        "   WAKE: FX Futures Analyst\n"
        "   WAKE: Index/Macro Analyst\n"
        "   WAKE: none\n\n"
        "The 'WAKE:' line is parsed programmatically so the format must be "
        "exact. 'none' is a valid and respected outcome — if the session is "
        "thin or no analyst has meaningful edge, pick none. Conservation > "
        "activity.\n\n"
        "Keep total output under 500 tokens."
    )

    print("Waking CIO for first live session brief...")
    print()
    result = await orch.wake_agent("CIO", task)

    print("=" * 70)
    print(f"Model:        {result.get('model')}")
    print(f"Messages:     {result.get('messages_count')}")
    usage = result.get("usage") or {}
    print(f"Tokens in:    {usage.get('input_tokens', 0)} "
          f"(+{usage.get('cache_read_input_tokens', 0)} cached)")
    print(f"Tokens out:   {usage.get('output_tokens', 0)}")
    print()
    print("CIO brief:")
    print("-" * 70)
    text = result.get("final_text") or "(no text)"
    print(text)
    print("=" * 70)

    # Parse the WAKE line
    wake_line = next(
        (line.strip() for line in text.splitlines()
         if line.strip().upper().startswith("WAKE:")),
        None,
    )
    if wake_line:
        choice = wake_line.split(":", 1)[1].strip()
        print(f"\n>> CIO picked: {choice}")
    else:
        print("\n>> CIO did not emit a parseable WAKE: line.")


if __name__ == "__main__":
    asyncio.run(main())
