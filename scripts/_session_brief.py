"""Step 1 of the first live session: CIO session brief + analyst selection.

The CIO reads live account state, scans the regime file, picks ONE analyst
to wake today, and explains the choice. Must end the brief with an explicit
line:  WAKE: <analyst name>  or  WAKE: none
so the next script can parse the decision.

2026-05-08 (per cowork_coordination.md priority #9): the brief now opens
with a cost-ledger one-liner so the CIO sees today's NET P&L (gross
trading − fees − slippage − fixed cost) before deciding what to do.
The line forces every session to confront 'a flat day is a -$26 day'
per vault/_meta/economics.md.
"""

import asyncio
import re
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from runtime.orchestrator import Orchestrator


def _cost_ledger_oneliner() -> str:
    """Build the MTD cost-ledger one-liner for the CIO brief.

    Format:
      MTD: gross +$X, fees -$Y, slip -$Z, fixed -$W, NET +$V (Δ vs break-even)

    Returns a string ready to embed in the brief. On failure (e.g. DB
    unavailable, no snapshots yet), returns a placeholder line so the
    brief still composes.
    """
    try:
        from scripts.cost_ledger import build_ledger, FIXED_COST_PER_DAY_USD
        from calendar import monthrange
        now = datetime.now(tz=timezone.utc).date()
        since = f"{now.year:04d}-{now.month:02d}-01"
        last_day = monthrange(now.year, now.month)[1]
        until = f"{now.year:04d}-{now.month:02d}-{last_day:02d}"
        ledger = build_ledger(since, until)
        s = ledger["summary"]
        gross = s.get("gross_usd", 0.0) or 0.0
        fees = s.get("fees_usd", 0.0) or 0.0
        slip = s.get("slippage_usd", 0.0) or 0.0
        fixed = s.get("fixed_cost_usd", 0.0) or 0.0
        net = s.get("net_usd", 0.0) or 0.0
        avg_per_day = s.get("avg_net_per_day_usd", 0.0) or 0.0
        n_trade = s.get("n_trading_days", 0) or 0
        n_cal = s.get("n_calendar_days", 0) or 0
        delta_vs_be = "ahead" if avg_per_day >= 0 else "behind"
        return (
            f"COST LEDGER MTD ({n_trade}/{n_cal} trade-days, "
            f"{s.get('n_entries_total', 0)} entries):  "
            f"gross ${gross:+,.2f}  fees ${-fees:+,.2f}  "
            f"slip ${-slip:+,.2f}  fixed ${-fixed:+,.2f}  "
            f"NET ${net:+,.2f}  ({delta_vs_be} break-even, "
            f"avg ${avg_per_day:+,.2f}/day)."
        )
    except Exception as e:
        return (f"COST LEDGER: unavailable ({type(e).__name__}). "
                f"Run `python -m scripts.cost_ledger --print` to inspect. "
                f"Treat this as a fail-loud signal that telemetry is broken.")


async def main() -> None:
    orch = Orchestrator()

    now_utc = datetime.now(tz=timezone.utc)
    cost_line = _cost_ledger_oneliner()
    date_block = (
        f"CURRENT TIME: {now_utc.strftime('%Y-%m-%d %A %H:%M UTC')} "
        f"(US/Eastern: {now_utc.astimezone().strftime('%a %H:%M %Z')}).\n"
        "Use this to judge session state — do NOT guess the day.\n\n"
        f"{cost_line}\n"
        "The fund's only KPI per vault/_meta/economics.md is NET monthly "
        "P&L. A flat (no-trade) day still costs ~$26 in subscriptions. "
        "If we're behind break-even, that should bias your wake decision.\n\n"
    )

    task = (
        "FIRST LIVE SESSION — SESSION BRIEF\n\n"
        + date_block +
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
        "Critically: end your output with a blank line followed by a "
        "SINGLE LINE in one of these exact formats. The line must start at "
        "column 0 with no markdown formatting (no bold, no bullets, no "
        "leading characters). It must be the FINAL line of your output:\n"
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

    # Parse the WAKE directive — tolerate markdown wrapping and mid-line emit.
    # Strip common decoration (**, *, ##, leading -/>/* etc.) then regex.
    cleaned = re.sub(r"[*_`#>]+", "", text)
    m = re.search(r"WAKE:\s*([A-Za-z/\- ]+?)\s*$", cleaned, re.MULTILINE)
    if not m:
        # Fallback: search anywhere, take last hit, stop at sentence/punct.
        hits = re.findall(r"WAKE:\s*([A-Za-z/\- ]+?)(?:[.\n]|$)", cleaned)
        m_text = hits[-1].strip() if hits else None
    else:
        m_text = m.group(1).strip()

    if m_text:
        print(f"\n>> CIO picked: {m_text}")
    else:
        print("\n>> CIO did not emit a parseable WAKE: line.")


if __name__ == "__main__":
    asyncio.run(main())
