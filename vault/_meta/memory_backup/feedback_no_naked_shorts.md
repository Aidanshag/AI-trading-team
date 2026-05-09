---
name: Naked-shorts policy (futures relaxed, options still blocked)
description: Naked short OPTIONS remain hard-blocked; naked short FUTURES were relaxed 2026-04-29 — verify config before asserting either way
type: feedback
originSessionId: 0fb1ece1-0ed0-47f7-9c25-6b7ec073a6ec
---
Policy split as of 2026-04-29:

- **Naked short options: still forbidden, non-negotiable.** Enforced via `config/risk_limits.yaml:options` — `allow_naked_short_calls/puts/strangles/straddles` all `false`. This is the genuine unbounded-risk failure mode and stays closed.
- **Naked short futures: ALLOWED** as of 2026-04-29 user directive. `hard_rules.no_naked_shorts: false`. Defensive ladder, $250 per-trade cap, stop-loss requirement, and Topstep DLL remain as backstops.

**Why:** Original rule was a blanket ban (any asset class). User relaxed the futures side to roughly double the trigger surface in mixed markets, judging that the multi-layered backstops (ladder + DLL + stops + per-trade cap) are sufficient for futures shorts. Options naked shorts stay banned because their loss profile is unbounded by definition and no per-trade cap can fix that.

**How to apply:**
- Before citing this rule in either direction, read `config/risk_limits.yaml:hard_rules.no_naked_shorts` and `config/risk_limits.yaml:options.allow_naked_short_*` — the config is the source of truth, this memory just explains the *why*.
- Risk-hook enforcement: `_check_no_naked_shorts` in `hooks/risk_gate.py` only fires when `hard_rules.no_naked_shorts: true`; the options block is enforced separately via `_check_options_structure_allowed` against the `allowed_structures` allowlist.
- If the user asks to re-tighten futures: flip `hard_rules.no_naked_shorts` back to `true`. If the user asks to allow short option structures: that's a much bigger policy change — push back and confirm.
