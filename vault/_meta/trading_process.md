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

## ⚠ BEARISH VIEWS — naked short futures permitted, naked short options forbidden

**Policy split (effective 2026-04-29 — verify in `config/risk_limits.yaml` before citing):**

- **Naked short futures: PERMITTED.** Relaxed by user directive. Backstops still bind: stop-loss requirement, $250 per-trade cap, defensive ladder, Topstep $1000 DLL, $500 internal soft-DLL. Risk hook does NOT block outright short futures — propose them when the read is bearish and the structural-stop level is clean.
- **Naked short options: HARD-BLOCKED.** `allow_naked_short_calls/puts/strangles/straddles` all `false`. Any naked short option proposal will be vetoed at the hook layer. The unbounded loss profile cannot be capped by per-trade rules.

**For bearish views on instruments where you'd prefer defined risk anyway** (rich IV, event risk, thin liquidity, or just "I want a capped tail"), the structures below remain available:

1. **Bear put spread** — defined risk = debit paid. Use when IV is reasonable and you want directional exposure with capped loss.
2. **Bear call spread** (short call + long higher call) — defined risk = strike width − credit. Use when IV is rich (sell premium).
3. **Calendar spread bearish lean** — short the front-month with a long back-month overlay.
4. **Inter-commodity spread** — long one product, short the correlated one. The "short" side is offset by the "long", so structurally defined risk.

**The Volatility Strategist and Options Risk are your routing partners** for option structures. When you have a bearish thesis and want defined risk, the analyst writes the directional view and Options Risk computes the structure.

**For Quant Researcher specifically:** when your strategy library produces a SHORT signal (e.g., `vol_regime_trend` going short), you may now publish it as an outright short futures proposal. The earlier "convert to defined-risk before publishing" rule no longer applies for futures (still applies if you'd otherwise want a naked short option).

## 🎯 PRIMARY GOAL — pass Topstep Combine, get funded, earn cash

**Read `vault/_meta/topstep_pass_strategy.md` and `vault/_meta/economic_health.md` on first wake.** Those documents are the single source of truth.

**Headline:** don't lose $1,000 in any one day; don't give back $2,000 from peak; accumulate $3,000 profit slowly across ≥5 trading days; no day > 50% of total profit. Pass → get funded → earn monthly cash. **"Win small, win consistently."** Even +$100/day passes in 30 days. Don't chase $3K in a week — breaks consistency rule.

**Firm-imposed caps:** $500 internal DLL (50% of Topstep's $1K), $700 daily profit cap (consistency-rule protection).

**Monthly cost baseline:** ~$575 (API $250 + Claude sub $100 + Topstep $175 + buffer $50). Targets: breakeven $575/mo, worthwhile $1,150/mo, comfortable $1,725/mo. Discipline IS profit — wasted wakes burn $0.05-0.30 each. CIO daily brief reports MTD profit vs these thresholds.

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

---

## 🛡 Risk safety floor — what changed in this week's overhaul (added 2026-04-29)

The PreToolUse risk hook had several P&L-aware rules that *looked* armed in config but silently no-op'd because the data they read didn't exist. As of this week the gaps are closed. Agents should know what the hook now actually catches:

### Snapshot pipeline (the foundation)
- `runtime/orchestrator.py:capture_account_snapshot` runs at session open and at the start of every TICK. It pulls live broker balance, position list, and `canTrade` flag, computes unrealized P&L from positions × latest 1-min bar close, and writes a row to `account_snapshots`.
- Before this, the table was empty — DLL, TDD, defensive ladder, daily-target-lock, and consistency-rule checks all early-returned. They now have data.
- Realized day P&L is anchored to the first snapshot of the UTC day. Backfill of yesterday's `daily_pl` row runs at first tick of a new day if `session_close_workflow` didn't get a chance to finalize it.

### `canTrade` enforcement (new check `_check_broker_can_trade`)
- If Topstep flips the account to `canTrade=false` server-side (DLL hit at their layer, account paused, post-loss cooldown), the hook blocks all order proposals and logs a `broker_can_trade_false` warn event.
- Auto-clears once the broker flips it back and the next snapshot lands. No manual intervention needed.

### Pre-trade projection on DLL / TDD / defensive ladder
- Old behavior: "are we already breached?". New behavior: "would this trade's *worst-case loss* push us over?".
- New rules surfaced in `risk_events`: `daily_loss_limit_projected`, `trailing_drawdown_projected`, `defensive_ladder_projected`.
- Worst-case is resolved from the order in this order: defined-risk structure max_loss → stop+limit + tick metadata → fallback `per_trade_risk_pct_of_equity × balance` (50 bps).
- Practical implication for analysts: a $250-risk trade proposed when day P&L is already at -$760 will be blocked even though we're still above the $1000 DLL — the projection sees the $1010 outcome and stops it.

### Consistency-rule advisory (advisory tier — does NOT block)
- `_check_consistency_rule` reads `daily_pl` history (finalized at session close) and computes today's share of net profit-to-date. If today exceeds the 50% cap, a `consistency_rule_advisory` warn event is logged.
- It is advisory because the consistency rule applies at *payout* time, not pre-trade. Risk Manager should factor sizing-down based on these warns; PM should respect any `allow_with_modifications` verdict that cites the advisory.
- Will be promoted to a hard block once a Combine is run through to payout and we're confident in the math.

### Stop-out detection — typed signal, not LIKE-match
- `_check_post_stop_cooldown` no longer parses summary text. It reads `risk_events.rule='stop_hit_observed'` (primary) and falls back to `decisions.kind='stop_hit'` (legacy).
- The reconciler emits `stop_hit_observed` automatically when a position closure is paired with a recently-filled STOP-type broker order. No agent needs to write this — but if Execution Trader logs a manual stop-out, use `kind='stop_hit'`, not free-form "stopped out" prose.

### Sector caps actually enforced now
- `symbols.yaml` had `grains` and `livestock` sectors but `risk_limits.yaml:sector_limits` only had the merged `ag` — the basket cap silently disabled for 7 ag symbols. Fixed: every per_symbol entry now maps to a sector that exists in sector_limits, and a regression test locks this in.

### Where to look when something blocks
- `risk_events` table is the audit trail. Every `severity='block'` row has `rule` (which check tripped) and `detail.reason` (human-readable explanation). Query: `SELECT ts, rule, json_extract(detail,'$.reason') FROM risk_events WHERE severity='block' ORDER BY id DESC LIMIT 20`.
- The hook is the *floor*. If it blocks, the policy or config is the source of truth — don't try to route around it. If it's wrong, fix `config/risk_limits.yaml`, not the hook.
