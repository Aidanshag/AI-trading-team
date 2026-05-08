---
name: CIO does agent performance management
description: Weekly scorecards; Top/Standard/Watch/Bench tiers; bench recommendation surfaced to user; user decides retire/rewrite
type: feedback
originSessionId: 0fb1ece1-0ed0-47f7-9c25-6b7ec073a6ec
---
The CIO is responsible for evaluating every trading-originating agent's performance over a rolling 100-trade window and classifying them into tiers. Benched agents are paused for routine wakes but kept available; retirement is the user's decision.

**Why:** The user said explicitly: "Keep agents with high success rates. Those with lower success rates should be put aside. The CIO will be able to autonomously refine their trading abilities." The fund is a learning system — agents that don't pull their weight should not be sized up; agents that do should be trusted more. The PM's sizing multiplier incorporates the CIO's tiering.

**How to apply:**
- Tiering lives in `config/agent_performance.yaml` with Top/Standard/Watch/Bench thresholds and sizing multipliers.
- CIO publishes scorecards to `vault/_meta/agent_scorecards.md` every Sunday.
- PM multiplies an agent's base conviction multiplier by the tier sizing factor (Top 1.2x, Standard 1.0x, Watch 0.5x, Bench 0.0x).
- Bench requires 3+ consecutive weeks under Watch thresholds (prevents noise benching).
- CIO cannot retire or rewrite an agent. Only the user can. CIO surfaces the recommendation with evidence.
- Minimum 20 closed trades before any tiering (small-sample protection).
