---
name: Formal trading-firm workflow
description: The fund operates like a traditional hedge-fund front office — CIO directs, Research proposes, PM decides pursue/pass, Risk Manager has final say, Execution fills
type: feedback
originSessionId: 0fb1ece1-0ed0-47f7-9c25-6b7ec073a6ec
---
The user formalized the fund's workflow to mirror a traditional hedge-fund front office. Document of record: `vault/_meta/trading_process.md`.

**Why:** The user wants agents to operate with the same separation of duties a human trading firm uses — because that separation is what prevents blow-ups. A runaway analyst can't trade; a reckless PM can't execute without risk approval; a careless risk officer is caught by the PreToolUse hook; a buggy execution agent is capped by position limits.

**How to apply:**
- **CIO directs all agents** — wakes them, sets priorities, arbitrates disagreements, gatekeeps escalations. CIO never trades.
- **Research agents pull data and research ideas**, then present to PM/traders. Research proposes; it does not decide.
- **PM (and analysts) decide pursue or pass** on Research-originated or analyst-originated ideas. Pass is a valid, expected outcome — most ideas should pass.
- **If pursued**, PM submits order proposal to Risk Manager.
- **Risk Manager has FINAL SAY.** Approve | approve_with_modifications | block. No override. No appeal. PM may resubmit a revised proposal.
- **Options Risk shares veto authority for options trades.**
- **Execution Trader fills cleanly**, does not reason about trade quality.
- **Compliance watches beside the decision path**, surfaces patterns.

This workflow is now the definitive reference in `vault/_meta/trading_process.md`. Updates to agent prompts should be consistent with it. If a future instruction would violate this structure (e.g., "let analysts place orders directly"), flag the conflict to the user before implementing.
