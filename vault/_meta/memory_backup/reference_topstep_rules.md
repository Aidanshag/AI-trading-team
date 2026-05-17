---
name: Reference — Topstep operational rules
description: Full Topstep XFA / Combine / Live rules reference at vault/_meta/topstep_rules.md. Read when reasoning about account safety, payout mechanics, MLL/DLL/consistency.
type: reference
originSessionId: 050d245a-e481-4632-9707-935db0dc239f
---
Two reference docs (user-imported 2026-05-12 from Claude-compiled summaries):
- `vault/_meta/topstep_combine_rules.md` — Combine rules. **We are CURRENTLY in the Combine — read this one first.**
- `vault/_meta/topstep_rules.md` — XFA / Live rules (for after we pass).

Read it when:
- Designing any change to risk gates / position sizing
- Reasoning about MLL, DLL, consistency rule, scaling plan
- Considering payout requests (and their reset effects on MLL)
- Adding time-of-day enforcement (3:10 PM CT hard flatten = XFA rule)
- Building news-event filtering
- Planning for Combine → XFA → Live transitions

Key facts to keep front-of-mind:
- We are currently in **Combine** (account name `50KTC-V2-DLL-585394-27954833`). MLL is INTRADAY trailing in Combine (more aggressive than XFA's end-of-day trailing).
- Only 0.71% of XFA traders reach Live. Don't over-engineer for Live yet.
- Consistency rule (50% single-day profit cap) is in effect in Combine. CLAUDE.md says our check is currently `warn-tier, doesn't block`.
- After any payout (XFA): MLL resets to $0. Major recalibration required.
