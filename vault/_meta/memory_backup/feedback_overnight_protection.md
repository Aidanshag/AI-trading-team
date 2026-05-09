---
name: Watch trading + fix bugs in real time + protect against losses
description: User explicitly authorized me to continue monitoring and patching while they sleep. Priority: prevent waking up to a $1000 loss (Topstep DLL breach). Bias toward protective fixes over feature work.
type: feedback
originSessionId: b1c69b67-a794-46cc-bb06-6e08fbeea607
---
On 2026-05-04 the user said: "continue to watch trading and fix any bugs that emerge. Make sure risk is being managed properly and not have me come back to a 1000 dollar loss"

This is broader than the silently-dead-agent directive — it covers ANY emerging bug AND active risk management while user is away (sleep, work, etc.).

**Priority order when acting alone:**
1. **Cap loss exposure first.** If a bug pattern could result in unbounded loss, market-flatten the position even if it means realizing a loss. A $200 forced exit beats a $1000 DLL breach.
2. **Patch the bug.** Same process I've been using: discriminator/recovery logic in the relevant scan loop or reconciler, never silent fallback.
3. **Test what I patched.** Static parse + integration smoke test against current DB state.
4. **Discord alert.** Hook into existing webhook so the user knows what was caught.
5. **Save the bug pattern to memory** so future-me recognizes it faster.

**Specific risk thresholds the user cares about (in order):**
- Topstep DLL: -$1000 (hard server-side block beyond this) — this is the "wake-up nightmare"
- Topstep TDD: -$2000 from peak balance — Combine fail
- Defensive ladder: -$150/-$300/-$500 progressive tightening
- Per-trade cap: $250 (one trade can't single-handedly hit DLL)

**What protective fixes I CAN deploy without approval:**
- Add auto-flatten paths in `scripts/reconcile_positions.py` (already did for phantoms)
- Add gate checks in `scripts/auto_trader.py` (NOT in `hooks/risk_gate.py` per HIGH_RISK_FILES)
- Tighten existing checks (lower thresholds) — but not relax them
- Add monitoring/alerting

**What I CANNOT deploy without approval:**
- Edit `hooks/risk_gate.py`, `state/db.py`, `state/schema.sql`, `tools/topstep.py`, `tools/projectx_client.py`, or `risk_limits.yaml.hard_rules`
- Disable or relax any safety floor (DLL, TDD, ladder, per-trade cap)
- Halt trading without justification (user wants edge to fire while away)

**How to know if a "bug" warrants a halt vs a patch:**
- Patch and continue: phantom positions, missing stops, strategy mis-firing on one symbol, log/snapshot issues
- HALT new entries: DLL approaching, peak-to-trough TDD warning, broker rejection rate >50%, reconciler unable to read broker, two consecutive scans with `bracket_stop_failed`
- HALT and ALERT immediately: any unbounded-loss pattern that auto-flatten can't catch within 5 min

**Don't:**
- Defer obvious protective patches with "I'll wait to ask the user"
- Make speculative refactors during overnight watch
- Add new strategies — the user wants the validated edge to compound, not new candidates introduced while they sleep
