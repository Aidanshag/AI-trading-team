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
CIO → Sector Analyst → [Red Team if med/high] → PM → Risk Manager → Execution → Compliance
```

- **CIO** sets daily posture, picks which analyst to wake, gatekeeps escalations. Never places orders.
- **Sector Analyst / Research** pulls data, identifies setups (or NO_TRADE), writes thesis to `vault/theses/`, calls `state_record_decision` (mandatory).
- **Red Team** challenges every med/high thesis (3 counter-narratives, null-hypothesis test, historical analog, verdict strong|gaps|weak — advisory).
- **PM** reads thesis + Red Team, decides pursue|pass, sizes per `risk_limits.yaml`. May wake specialists for ensemble validation in autonomous mode.
- **Risk Manager** runs 13-gate check, has FINAL SAY (allow | allow_with_modifications | block). No appeal. PM may resubmit with changes. Options Risk shares this authority for options.
- **Execution Trader** translates approved proposal into broker order, calls `topstep_place_order`. Does not think about trade quality.
- **Compliance** audits every order has a matching proposal + risk vote; flags patterns; daily/weekly review.
- **Book Monitor** runs between analyst wakes, sweeps for stop approaches, adverse moves, correlated drift.

## Rules the workflow enforces

1. **CIO directs; does not trade.** CIO's power is orchestration, not execution. They set the board; they don't move the pieces themselves.
2. **Research proposes; doesn't decide.** Research agent answers questions and produces briefs. The *decision* to trade on a Research view lives with the PM/analyst, then Risk.
3. **Red Team challenges; doesn't block.** Every med/high-conviction thesis gets adversarially reviewed before the PM considers it. Red Team verdict is advisory — the PM still decides — but a `weak` verdict is a strong signal to pass.
4. **PM decides yes/no.** The PM is the portfolio captain. Not every Research idea or analyst thesis becomes a proposal. Pass is cheap; bad trade is expensive. PM reads both thesis AND red-team challenge before deciding.
5. **Risk has final say.** Risk Manager approves or blocks. No override. No appeal. PM may resubmit a revised proposal. Options Risk shares this authority for options.
6. **Execution executes.** Execution Trader does not think about whether a trade is good. They fill cleanly. If the hook blocks, they stop; they do not retry.
7. **Book Monitor watches the live book.** Between analyst wakes, the Book Monitor sweeps every 5 minutes for stop approaches, adverse moves, correlated drift. It flags; it does not act.
8. **Compliance watches.** Compliance is not in the decision path but sits beside it, auditing. They surface patterns the front office is too close to see.

### v2 institutional roles (background, inform every decision)

The five v2 specialist roles run in the background on their own cadence and feed every other agent. See [[agent_v2_protocol]] for full details.

| Role | Cadence | Output consumed by |
|---|---|---|
| **Quant Researcher** | Daily + Sunday weekly | PM (sizing), CIO (analyst tier), Compliance (calibration) |
| **Macro Strategist** | Sunday weekly | CIO (regime bias), all analysts (with-regime check) |
| **Flow Analyst** | Tue + Fri | All analysts (positioning context), PM (crowded-trade veto) |
| **Volatility Strategist** | Mon + Wed + Fri | Options Risk (vol regime), Diamond Hunter (mispricing setups) |
| **Execution Specialist** | Per-trade | Execution Trader (plan), Compliance (slippage) |

These roles do NOT block trades. They inform. The Risk Manager remains the final gate.

## Why this works

This is how real firms survive. The separation of duties means no single agent can accidentally put the fund at existential risk:

- A runaway analyst can't trade — they only propose.
- A reckless PM can't execute — they propose, risk vetoes.
- A careless Risk Manager can't silently ignore — the hook is the floor below their judgment.
- A buggy Execution Trader can't lose big — tool access is capped to one function, and position limits bound size.

Each layer catches what the layer above misses. Over a year, this prevents blow-ups and lets small-edge decisions compound.

## ⚠ MANDATORY PROTOCOL — calling `state_record_decision`

**Every analyst, every wake, MUST call `state_record_decision` if you produce a thesis OR a no-trade verdict.** This is non-negotiable. The chain has no way to forward your output to PM/Risk/Exec unless it's recorded in the decisions table.

**If you find a setup:**
```
state_record_decision(
  agent_name="<your canonical name, e.g. 'Quant Researcher' or 'Energies Analyst'>",
  kind="thesis",
  symbol="<SYMBOL>",
  summary="<one-line setup description>",
  rationale="<full Pre-Trade Checklist + reasoning>"
)
```
Then end your response with EXACTLY one line:
```
THESIS: <SYMBOL> conviction=<low|med|high>
```

**If you DON'T find a setup:**
```
state_record_decision(
  agent_name="<your name>",
  kind="no_trade",
  summary="<one-line reason>",
  rationale="<what you scanned + why nothing triggered>"
)
```
Then end with:
```
NO_TRADE: <one-line reason>
```

**Do NOT write a thesis in markdown without recording it.** The orchestrator literally cannot see your text — it only sees the decisions table. A thesis that isn't recorded is a thesis that didn't happen.

**Use your canonical agent name** ("Quant Researcher", not "quant_researcher" or "QR"). The DB layer will normalize, but using the canonical form is cleaner.

## ⚠ BEARISH VIEWS — convert to defined-risk, not naked shorts

**The risk hook categorically blocks naked short futures.** This is non-negotiable. So if your sector analysis points bearish, do NOT propose short futures. Instead:

**Conversion menu (in order of preference):**

1. **Bear put spread** on the underlying's options (defined risk = debit paid; defined upside = strike width − debit). Use when IV is reasonable and we want directional exposure with capped loss.
2. **Bear call spread** (short call + long higher call). Defined risk = strike width − credit. Use when IV is rich (sell premium).
3. **Calendar spread bearish lean** — short the front-month with a long back-month overlay.
4. **Inter-commodity spread** — long one product, short the correlated one (e.g., long natgas / short crude when energy crack should compress). The "short" side is offset by the "long" side, so it's defined risk by structure.
5. **Sit out.** If you can't find a defined-risk way to express the bearish view, the right answer is no trade. Don't force.

**The Volatility Strategist and Options Risk are your routing partners** for option structures. When you have a bearish thesis, the analyst writes the directional view and Options Risk computes the structure. The proposal that reaches PM should already be defined-risk shaped.

**For Quant Researcher specifically:** when your strategy library produces a SHORT signal (e.g., `vol_regime_trend` going short), automatically translate to the bearish defined-risk equivalent before publishing the thesis. Don't publish naked-short theses — they'll be DOA at the risk hook.

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
