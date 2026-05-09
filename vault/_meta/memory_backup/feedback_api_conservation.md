---
name: Conserve Claude API usage by default
description: Default to Haiku, heavy prompt caching, event-driven triggers — never polling loops
type: feedback
originSessionId: 0fb1ece1-0ed0-47f7-9c25-6b7ec073a6ec
---
Default every agent to the cheapest viable Claude model and minimize token spend.

**Why:** User explicitly asked agents to conserve API use. A continuously-running multi-agent system with naive polling would burn budget fast with little marginal value.

**How to apply:**
- Default model: Haiku 4.5. Escalate to Sonnet 4.6 or Opus 4.7 only for genuinely hard reasoning (e.g. portfolio construction, novel market regime analysis) — and make the escalation explicit in code/config, not implicit.
- Use prompt caching aggressively on agent system prompts, tool definitions, and stable context blocks.
- Trigger agents on events (new bar close, news, price threshold, risk breach), not on fixed polling intervals. Avoid "while True: sleep(1)" patterns.
- When market is closed for a given asset, agents for that asset should be idle, not looping.
- Prefer one fat prompt with full context over many chatty turns.
