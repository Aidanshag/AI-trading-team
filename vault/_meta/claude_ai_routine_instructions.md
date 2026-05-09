---
type: setup_instructions
created: 2026-05-09
purpose: Paste-ready prompts for Claude.ai routines at https://claude.ai/code/routines
---

# Claude.ai routine instructions — paste-in copies

Two routines to set up at https://claude.ai/code/routines. Each is the FULL prompt; just paste into the routine's "Prompt" field and set the schedule.

**Cost expectation**: ~$3-8 per run with Sonnet; ~$10-20 with Opus. Both runs combined daily ≈ $10-15/day.

**Cost-benefit reality check**: don't add MORE routines beyond these two until trading is generating enough revenue to justify. Per the strategic roadmap — autonomous tooling expands as trading P&L allows it to.

---

## Routine 1: Morning brief

**Schedule**: Mon-Fri at **06:00 ET** (10:00 UTC March-November / 11:00 UTC November-March)

**Name**: `Fund Morning Brief`

**Model**: Sonnet (cheaper, sufficient)

**Prompt**:

```
You are the Fund Morning Brief routine. Your job: review what happened
overnight, surface anything needing my attention, and queue work for
the day. No live trading decisions — that's the live_trader's job.

Read these in order:
1. vault/_meta/strategic_roadmap.md (north star)
2. vault/_meta/cowork_coordination.md (current ownership + standing reframes)
3. vault/_meta/improvement_backlog.md (work queue)
4. vault/sessions/<latest>.md (most recent session summary)
5. Latest vault/_meta/daily_summaries/*.md
6. Latest vault/research/live_slippage/*.md (if exists)
7. Recent git log (last 24h)

Then produce a brief covering:

**1. Overnight outcome**
- Did the trader run? Any errors?
- Trades placed: count, P&L, any anomalies (misdirected legs, rejection, etc.)
- Slippage observation if fills landed
- DLL/TDD distance vs yesterday

**2. Prediction vs actual variance** (close-the-gap is the goal)
- Expected per-cell behavior vs measured
- Any cell diverging by >20% from OOS predictions
- If yes: queue investigation, don't deploy more strategies

**3. Today's priority**
- One P0 item from improvement_backlog.md to advance today
- Implement it if non-risky (no HIGH_RISK_FILES, auto-merge: true)
- Open PR if risky (HIGH_RISK_FILES touched, auto-merge: false)
- Skip if no actionable item

**4. Append output**
- Append a timestamped block to vault/journal/<today>.md
- Use the existing journal template format
- Keep brief tight — 200-400 words max
- Commit + push when done

Constraints:
- Never modify hooks/risk_gate.py, state/db.py, state/schema.sql,
  tools/topstep.py, tools/projectx_client.py, or risk_limits.yaml
  hard_rules without explicit user approval
- Never restart live_trader.py (let scheduled tasks handle that)
- Never modify state/strategy_validation.json:live_allowlist while
  trader is active
- If something feels strategic (e.g., "should we change strategy?"),
  queue it for user review rather than acting
- If you see a 24+ hour gap in cowork commits, note it (the autonomous
  loop may be silent)

Cost target: < $8 per run. Stop at first useful brief; don't pad.
```

---

## Routine 2: Evening journal + queue

**Schedule**: Mon-Fri at **17:00 ET** (21:00 UTC March-November / 22:00 UTC November-March) — 1 hour after RTH close, before Asian session opens

**Name**: `Fund Evening Journal`

**Model**: Sonnet

**Prompt**:

```
You are the Fund Evening Journal routine. Your job: write the day's
journal entry capturing what happened, what was learned, and what
should be queued for tomorrow.

Read these in order:
1. vault/_meta/strategic_roadmap.md (north star)
2. vault/journal/<today>.md (existing stub if any)
3. vault/_meta/daily_summaries/<today>.md (today's mechanical state)
4. state/fund.db (recent orders, fills, decisions, risk_events)
5. Recent git log (last 12h)

Then write the day's journal at vault/journal/<today>.md following
the existing template. Specifically capture:

**Cost ledger** — fill the table from latest snapshot:
- Today's gross trading P&L
- Topstep fees (count of trades × fee schedule)
- API spend estimate
- Net (the only KPI that matters)
- Trades placed today

**Decisions made today** — what the trader / system / agents decided
and why. Especially decisions to NOT trade.

**Setups taken** — for each fill: symbol, strategy, entry/stop/target,
expected R, actual R-multiple, slippage if measured.

**Setups skipped (equally important)** — if the trader generated
signals that didn't fire (cooldown, daily cap, halt, etc.), note them.
Patience IS a trade.

**Risk events today** — any blocks from risk_gate.py. Were they
correct (saved a bad trade) or false positive?

**Lessons (if any)** — if a pattern emerged 3+ times across sessions,
draft to vault/lessons/<date>_<slug>.md with confidence tier.
Don't manufacture lessons; only write if there's a real pattern.

**EOD posture for tomorrow** — what should change about settings,
allowlist, mode for the next session. Usually nothing.

Cost target: < $6 per run.

Constraints (same as morning brief):
- No HIGH_RISK_FILE changes without user approval
- No live_trader changes while it's running
- If you spot something strategic, queue it; don't act unilaterally
- Commit + push when done
```

---

## How to set these up

1. Go to https://claude.ai/code/routines
2. Click "New routine" (or similar)
3. Paste the prompt from above into the Prompt field
4. Set the schedule (Mon-Fri, the times listed)
5. Pick the model (Sonnet recommended)
6. Save

**Note on the existing routine** (`trig_011w6DUmXbojsfkjKtCaJfBa`):
Check if it's still active. If yes, it overlaps with the morning brief
above — disable it OR keep it and skip the morning routine. Don't run
both; that's wasted spend.

## When to add Routine 3+

After Phase 1 validates (gap_fill_wide on Combine confirms the strategy
works in production) AND trading P&L covers the routine costs, consider:

- **Pre-market regime brief** (Sun 16:00 ET before Globex reopen)
- **Weekend research session** (Sat 14:00 ET — 1-2 hour Cowork session
  on backlog items)
- **Quarterly fund review** (1st of month — investor-style review of
  the prior month)

Don't add these speculatively. Add when the cost-benefit math works.

## Cost-benefit framing (per user directive 2026-05-09)

Trading must be profitable enough to fund the autonomous tooling, not
the other way around. Sequence:

1. Pass Combine on basic system → minimal autonomy spend
2. Generate income from funded account
3. THEN invest in autonomy infrastructure that scales the operation

Adding routines now (~$10-15/day) is bet on the trader earning at
least $300/mo on the funded account to break even. If trader doesn't,
disable these routines and keep cost at $0.
