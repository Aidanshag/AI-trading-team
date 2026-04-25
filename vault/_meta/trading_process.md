---
type: meta
status: active
updated: 2026-04-23
applies_to: [all]
---

# The fund's trading process

This is the definitive workflow the fund operates under. It is the same shape a hedge fund's front office uses — direction from the CIO, research from analysts and the Research agent, decisions from PMs/traders, veto power with the Risk Manager. Every agent is expected to operate within this process. It is not optional; it is how the firm works.

Agents are welcome — encouraged — to suggest refinements via journal entries under `## Refinement ask — {agent} — {one-line}`. The user reads those and decides what to change.

## The core workflow

```
┌─────────────────────────────────────────────────────────────┐
│ CIO                                                          │
│   • Sets daily posture (regime read, themes, events)         │
│   • Decides which analysts to wake and with what focus       │
│   • Gatekeeps escalations (Research, frontier model wakes)   │
│   • Arbitrates disagreements between analysts                │
│   • Never places orders                                      │
└──────────────────────┬──────────────────────────────────────┘
                       │ wakes
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Sector Analyst / Research Agent                              │
│   • Pulls data, news, tape, calendar                         │
│   • Identifies clean setups (or "no trade today")            │
│   • Research agent produces deep-dive briefs when called     │
│   • Writes theses to vault/theses/ or vault/research/        │
│   • Presents idea to the Portfolio Manager                   │
└──────────────────────┬──────────────────────────────────────┘
                       │ publishes med/high conviction thesis
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Red Team (adversarial review — every med/high thesis)        │
│   • Produces 3 counter-narratives + null-hypothesis test     │
│   • Cites historical analog failures                         │
│   • Base-rate check against strategy's documented hit rate   │
│   • Verdict: strong | gaps | weak (advisory, not blocking)   │
│   • Output to vault/research/challenges/                     │
└──────────────────────┬──────────────────────────────────────┘
                       │ challenge report + thesis forward to
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Portfolio Manager (+ Trader if applicable)                   │
│   • Reads thesis; checks current positions, regime fit,      │
│     correlation with existing book                           │
│   • DECIDES: pursue this idea or pass. "Pass" is a valid     │
│     outcome — most ideas should pass.                        │
│   • If pursuing, sizes the position per risk_limits.yaml     │
│   • Writes the order proposal (symbol, side, qty, stop,      │
│     target, structure)                                       │
└──────────────────────┬──────────────────────────────────────┘
                       │ submits
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Risk Manager (+ Options Risk if options)                     │
│   • Runs the 12-point check on the proposal                  │
│   • Has FINAL SAY. Approve | approve_with_modifications |    │
│     block. No appeal. PM may resubmit with changes.          │
│   • For novel structures or ambiguous regime: may escalate   │
│     to Research (frontier) for a second-opinion deep-dive.   │
│   • On drawdown, tightens buffers per book_state_playbook.   │
└──────────────────────┬──────────────────────────────────────┘
                       │ if approved
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Execution Trader                                             │
│   • Translates approved proposal into broker order payload   │
│   • Calls topstep_place_order (or equity_broker when live)   │
│   • PreToolUse risk hook is the final hard gate              │
│   • Logs fill, slippage, stop placement                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Compliance                                                   │
│   • Audits: every order has a matching proposal + risk vote  │
│   • Flags patterns (repeat rule-trips, correlation drift)    │
│   • End-of-day summary + weekly review prep                  │
└─────────────────────────────────────────────────────────────┘
```

## Rules the workflow enforces

1. **CIO directs; does not trade.** CIO's power is orchestration, not execution. They set the board; they don't move the pieces themselves.
2. **Research proposes; doesn't decide.** Research agent answers questions and produces briefs. The *decision* to trade on a Research view lives with the PM/analyst, then Risk.
3. **Red Team challenges; doesn't block.** Every med/high-conviction thesis gets adversarially reviewed before the PM considers it. Red Team verdict is advisory — the PM still decides — but a `weak` verdict is a strong signal to pass.
4. **PM decides yes/no.** The PM is the portfolio captain. Not every Research idea or analyst thesis becomes a proposal. Pass is cheap; bad trade is expensive. PM reads both thesis AND red-team challenge before deciding.
5. **Risk has final say.** Risk Manager approves or blocks. No override. No appeal. PM may resubmit a revised proposal. Options Risk shares this authority for options.
6. **Execution executes.** Execution Trader does not think about whether a trade is good. They fill cleanly. If the hook blocks, they stop; they do not retry.
7. **Book Monitor watches the live book.** Between analyst wakes, the Book Monitor sweeps every 5 minutes for stop approaches, adverse moves, correlated drift. It flags; it does not act.
8. **Compliance watches.** Compliance is not in the decision path but sits beside it, auditing. They surface patterns the front office is too close to see.

## Why this works

This is how real firms survive. The separation of duties means no single agent can accidentally put the fund at existential risk:

- A runaway analyst can't trade — they only propose.
- A reckless PM can't execute — they propose, risk vetoes.
- A careless Risk Manager can't silently ignore — the hook is the floor below their judgment.
- A buggy Execution Trader can't lose big — tool access is capped to one function, and position limits bound size.

Each layer catches what the layer above misses. Over a year, this prevents blow-ups and lets small-edge decisions compound.

## Parallel tracks

The same workflow applies to the **equities desk** once it's live. Until then, the equity team is in learning mode (shadow trades only). The **futures desk** on Topstep is the primary track during the setup window.

## How the workflow evolves

This process is the current best-known structure. It is NOT set in stone. When the weekly review surfaces patterns where the workflow broke down — a thesis that should have been rejected but wasn't, a risk block that should have been allowed, a proposal that took too long to process — the user can refine the workflow and Claude will update this document and the agent prompts accordingly.

## Related notes

- [[team]] — who we are and how we collaborate.
- [[topstep_setup_window]] — the current learning sprint.
- [[idle_protocol]] — what agents do when they have nothing live to do (only when activated).
- [[idle_backlog]] — the queue of expansion tasks.
- Playbooks: [[market_wizards]], [[risk_officer_principles]], [[position_sizing]], [[psychology_and_discipline]], [[macro_framework]], [[trend_following]], [[quant_principles]].
- Routines: [[daily_routine]], [[weekly_review]].
