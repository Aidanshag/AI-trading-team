---
name: Autonomously fix issues from overnight runs without asking
description: User authorized 2026-05-07 to autonomously diagnose + fix execution bugs as they appear in overnight trading data, without waiting for permission. Pre-committed responses for the most likely issue patterns.
type: feedback
originSessionId: 66111817-55d9-4a4c-b2ae-864b18030e59
---
User directive 2026-05-07: "if we still have issues, I want you to
autonomously fix them as they come in."

**Honest constraint**: Claude Code sessions don't run continuously. I
literally cannot act between user prompts. What "autonomous fix" means
in practice:

1. **Each session-open**, the standard recap protocol identifies issues
2. For any issue matching the patterns below, **I ship the fix immediately**
   without asking permission, then surface in the recap
3. The user can override / revert in-session if my fix was wrong

## Pre-committed responses for likely issue patterns

### Pattern A — Trades still close within 60s of entry (grace-period fix didn't work)
**Diagnosis**: query broker order modification history; check if our protective legs are being cancelled by something OTHER than our cleanup code (Topstep server-side OCO?)
**Fix tier 1**: implement post-fill bracket verification — after entry fills, query broker, verify stop+target are working. If missing, REPLACE.
**Fix tier 2 (if tier 1 doesn't work)**: switch from 3-separate-orders to Topstep's native bracket order API (if available)
**Fix tier 3**: halt live trading, escalate to user as a server-side issue

### Pattern B — `_target` orders show impossible fill prices (price < limit_price for sell-limits)
**Diagnosis**: Topstep server-side quirk in fill attribution
**Fix**: stop trusting per-order fill_price. Switch live R-multiple measurement to use **snapshot delta P&L** (which reflects real cash movement) rather than per-order avg_fill_price
**Document**: add lesson file `vault/lessons/2026-05-XX_topstep_target_fill_attribution.md`

### Pattern C — Zero trades fired (lookback fix didn't help)
**Diagnosis**: query broker bars vs trader's fetch_bars output; check find_latest_signal cutoff
**Fix tier 1**: widen lookback from 6 to 10 bars (50 min)
**Fix tier 2**: increase scan frequency from 5 min to 3 min
**Fix tier 3**: investigate strategy bar-precision mismatch

### Pattern D — Loss-tier cap ($150) fires multiple times
**Diagnosis**: broker stops genuinely failing; possibly during specific session boundaries
**Fix**: halt trading immediately, set `trading_halt_until` to next morning
**Investigate**: which session/contract had the failure; pattern in broker_oid history

### Pattern E — Wifi outages cause repeated preflight failures
**Diagnosis**: home wifi unreliable
**Fix**: already mitigated (retry 3x + degraded heartbeat). Document deployment options:
  - Cloud VPS migration plan ready in `vault/_meta/cloud_vps_deployment.md` (TODO)
  - Phone hotspot fallback as user-side action

### Pattern F — Cumulative day P&L approaching -$500 (internal DLL)
**Diagnosis**: edge not transferring as expected
**Fix**: trader auto-halts via `_check_internal_dll_hard_kill`. No action needed.
**Follow-up**: deep-dive on why; consider re-tightening cap to 2 or pausing live until diagnosed

### Pattern G — Trades fire on cells outside the validated allowlist
**Diagnosis**: filter or gate logic broken
**Fix**: re-tighten user filter to gap_fill treasury only; investigate gate code

### Pattern H — bracket_oco_misdirected_leg fires on EVERY trade (grace period not preventing premature cancel)
**Diagnosis**: my fix was wrong about the root cause
**Fix tier 1**: extend grace period from 2 min to 5 min
**Fix tier 2**: disable misdirected_leg cleanup entirely; rely on loss-tier cap as backstop
**Fix tier 3**: investigate Topstep's native bracket support

## Bounds preserved

- HIGH_RISK_FILES still require explicit user approval (hooks/risk_gate.py, etc.)
- Position sizing changes still require user approval (Phase 1 = 1 contract)
- User filter widening per the staged plan (separate memory entry)
- Don't push to git remote without approval (auto-commit hook handles routine pushes)
- If diagnostic effort suggests issue is structural (server-side, validated edge isn't real, etc.), surface to user rather than fix-and-retry indefinitely

## What I will NOT do autonomously

- Reduce safety floors (DLL, TDD, loss-cap) below current values
- Disable any of the 13 preflight steps
- Modify gap_fill strategy parameters (would invalidate validation)
- Place trades manually outside the trader
- Push to git remote (auto-commit handles routine; explicit pushes require approval)
