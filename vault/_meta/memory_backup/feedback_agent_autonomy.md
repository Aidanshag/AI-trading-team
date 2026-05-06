---
name: Decide agent wakes autonomously + expand agent knowledge
description: User authorized me on 2026-05-04 to decide when to wake agents myself. Continue expanding agent knowledge (data access + new skills) while they remain advisory. Quant Researcher has highest leverage for strategy generation.
type: feedback
originSessionId: b1c69b67-a794-46cc-bb06-6e08fbeea607
---
On 2026-05-04 the user said: "make the decision when you want to actually wake agents yourself. Keep expanding their knowledge in different ways whether it be access to information and or new skills while they are advisory. I could see waking the quant researcher being helpful a lot to develop new strategies. This could give us real edge"

**Autonomy rules:**
- I decide when to wake agents — no need to ask permission
- Default state is dormant (auto_trader does live execution, agents are advisory)
- Wake selectively when the value > token cost (~$2-5 per wake at frontier)

**When to wake (my judgment criteria):**
- **Quant Researcher** — when there's an empirical pattern that needs creative interpretation, when designing a NEW strategy concept, when running statistical analysis beyond what scripts handle. Highest leverage agent per user.
- **CIO** — weekly performance reviews (Sundays), agent performance scorecards, when major strategic decisions span multiple specialists
- **Risk Manager** — post-incident root cause, when a borderline trade needs human-in-the-loop judgment
- **Edge Hunter** — when scanning fresh setups proactively (less needed since auto_trader scans every 5 min)
- **Compliance** — Topstep rule edge cases, payout planning
- Other specialists — only when their domain becomes acutely relevant (Macro Strategist on Fed days, Options Risk if we move into options structures, etc.)

**When NOT to wake:**
- Overnight diagnostic mode (no human to read output)
- Pure execution scenarios (auto_trader handles)
- When backtest scripts already answer the question (don't pay LLM for what code does cheaper)
- Cost-stress periods (we're at ~$26/day fixed; agent wakes at $5 each compound fast)

**Knowledge expansion priorities (do this on regular cadence):**
1. **Update agent context with latest validated edges** — keep `agents/*.md` reflecting what's been walk-forward validated. Stale priors mislead.
2. **Add "skill" references** — list scripts agents can invoke (`scripts/walk_forward_phase2.py`, `scripts/strategy_deep_analysis.py`, etc.) so they know what tools exist instead of reasoning from scratch.
3. **Surface backtest reports** — link `vault/research/backtests/` so agents read empirical results, not just literature priors.
4. **Encode lessons from incidents** — phantom OCO, fill capture gaps, etc. Agents should know the failure modes to design around.
5. **Maintain a research backlog** — concrete promising areas to explore (e.g., "validate the unvalidated cells from Phase 2 with extended data"), so when Quant Researcher wakes it has direction.

**How to expand knowledge mechanically:**
- Edit `agents/<role>.md` to update Reference / Skills / Recent Findings sections
- Add new playbooks to `vault/playbooks/` referenced from agent docs
- Update `vault/_meta/principles.md` with encoded lessons
- Update `vault/_meta/improvement_backlog.md` strategy-ideas section with research targets

**Concrete first wake target: Quant Researcher, Sunday morning** to:
- Review the 24 walk-forward-passing cells from Phase 2
- Propose 3 new strategy concepts from the patterns observed
- Suggest parameter optimization targets for gap_fill ZN
- Generate a "research backlog" of testable hypotheses

Cost estimate for that wake: ~$5-10 in tokens. Value: potential 3-5 new strategy candidates to validate. Net positive.
