---
type: routine
applies_to: [cio, pm, risk_manager, compliance, all_futures_analysts]
---

# Weekly review — every Sunday (or Saturday evening)

The most important recurring event in the fund. This is where edge actually improves.

## Part 1 — raw scorecard (Compliance)

Compliance pulls these numbers from state:

- **Total trades** (real + shadow) this week.
- **Win rate** overall and per analyst.
- **Average R-multiple** (avg win / avg loss).
- **Risk-hook blocks by rule** — which rules fired, how often.
- **Day P&L vs DLL headroom** — closest we came to the 2% limit on any day.
- **Topstep Combine status** — DLL usage, TDD status, consistency ratio.
- **Token spend by agent, by model** — where the cost lives.

Post to `vault/reviews/weekly_{YYYY-MM-DD}.md`.

## Part 2 — process audit (CIO + Risk Manager)

For each trade this week:

- Was the thesis honest? (Invalidation level named? Evidence independent?)
- Was the entry clean or chasing?
- Was the stop realistic (≥ 1× 20-bar ATR)?
- Was the size correct for conviction?
- Did we honor the stop when hit, or move it?
- Did the exit follow the plan or was it emotional / random?

Score each trade 1–5 on process quality. Trades with a 5 on P&L but a 2 on process are worse than trades with a 1 on P&L and a 5 on process — publicly say so.

## Part 3 — pattern review (each analyst)

Each analyst examines their own shadow/real trades in their sector:

- Which setups worked? (Were they in-trend, with-regime?)
- Which setups failed? (What did they miss?)
- Any pattern worth promoting to `vault/futures/patterns/`?
- Any pattern that should be retired or flagged as decayed?

## Part 4 — playbook update

- Was any playbook tested this week? Did it hold up?
- Any recurring lesson? Promote to `vault/playbooks/lessons_learned.md`.
- Any lesson that's been promoted 3+ times? It becomes a hard rule — file to `config/risk_limits.yaml` or the relevant agent's system prompt.

## Part 5 — regime check (CIO)

- Is our regime read still the right read?
- What would change our mind about the regime next week?
- Any cross-asset signal diverging from our read?
- Update `vault/regime/current.md` with a dated entry.

## Part 6 — refinement asks (all agents)

Each agent appends one or two refinement requests to the weekly review:

- What would make my job easier?
- What data am I missing that would materially improve my theses?
- What rule feels off?

The user reads these Sunday evening and queues changes with Claude for Monday.

## Part 7 — the one metric that counts

Over enough weeks, the only metric that matters is:

**Geometric net return ÷ maximum drawdown.**

Not weekly P&L. Not win rate. Not R-multiple. Returns divided by drawdown — because that's the number that tells you how much capital you can actually put at risk.

Track it weekly. When it improves, something is working. When it degrades, find the leak.
