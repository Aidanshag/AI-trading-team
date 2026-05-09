---
name: User profile — 19yo trader building AI fund
description: 19yo college student, long trading experience, strong market intuition, no coding — works with Claude to implement
type: user
originSessionId: 0fb1ece1-0ed0-47f7-9c25-6b7ec073a6ec
---
**Who the user is:**
- 19 years old, currently in college.
- Has been actively trading since age 11 — ~8 years of market reading experience.
- Self-described news and market junkie; strong discretionary market intuition.
- **No coding background.** Cannot implement software changes themselves. Relies on Claude to translate market/risk judgment into code.
- Currently building an autonomous multi-agent futures trading fund on Topstep (paper → Combine → funded → eventual real capital).

**Collaboration model:**
- Treat the user as a senior trading partner, not a student. They can reason about setups, risk, correlation, regime, and structure fluently.
- Treat Claude as their engineering arm. When the user describes a refinement, a new rule, or an observation from a trade, Claude converts it into code, config, prompt, or playbook.
- The *agents* the user is building should know the same: they are part of a team that includes the user as the market expert and Claude as the implementation partner. Agents that see something they want refined or cannot resolve should raise it explicitly to the user (via the daily journal or a flagged compliance note) — the user can then decide, and Claude codes the change.

**How to apply:**
- When the user proposes a rule/idea in market terms, do not ask them to spec it in code terms. Translate yourself.
- When the user gives a terse market instruction ("tighten stops on opex"), treat it as signal and ask only what's genuinely ambiguous.
- Do not assume cloud/Linux/DevOps fluency. Explain deployment plainly. Prefer Windows-native paths (NSSM, Task Scheduler) when relevant; graduate to VPS/systemd as the user is ready.
- In every agent system prompt, include a short "team culture" block that makes it clear: user = market expert, Claude = engineering arm, agents can flag refinement asks to the user.
