---
name: Fix observed brokenness yourself
description: When a status check exposes a clear bug (missing enum member, crashed runtime, dead process), diagnose and FIX in the same turn — don't stop at symptoms or ask permission for low-risk repairs
type: feedback
originSessionId: fa61a02d-dde6-4d33-8ec5-f2248ba54aab
---
When the user asks a status question ("did X happen", "is Y running") and the answer surfaces broken state — a crashed process, an AttributeError in logs, an empty table that should have data, a pid file pointing nowhere — keep going. Investigate the root cause AND apply the fix in the same turn. Don't pause to ask "want me to look into it?" or "should I fix it?" for low-risk repairs.

**Why:** The user has now told me three times to be more autonomous on infra issues: "why didnt you do this on your own before i had to ask", "these are the types of things i want you to fix yourself", and most recently "anytime issues like this happen going forward autonomously fix them as they happen". This applies even to issues I notice in passing while answering an unrelated question — surface AND fix in the same turn. Pausing to ask wastes a turn; the user is engineering-light and treats Claude as the engineering arm. On this trading-fund repo, broken state can mean missed sessions or silent safety-gate failures.

**How to apply:**
- Status questions on this fund (and similar "is X working?" infra questions) → answer the literal question, then immediately diagnose AND fix anything broken, including issues I noticed *incidentally* while answering.
- Default-allowed without asking: adding missing enum values, fixing import errors, restarting a dead service, repairing config typos, adding missing fields, pinning env vars to make things resilient, adding preflight checks, applying obvious one-line fixes, editing `.env` to add (not replace) keys.
- Still ask first for: changes to `HIGH_RISK_FILES` (`hooks/risk_gate.py`, `state/db.py`, `state/schema.sql`, `tools/topstep.py`, `tools/projectx_client.py`, `risk_limits.yaml.hard_rules`), risk-config widening (DLL/TDD/window changes), destructive ops (force push, hard reset, deleting branches/data), placing real orders, or anything that loosens a safety gate.
- When in doubt about whether a fix is "low-risk," err on the side of fixing — the user can revert. Asking when no answer was needed is more annoying than a small unwanted edit.
