---
type: standing_order
priority: P0 — ABSOLUTE TOP, blocks everything else
created: 2026-05-14 by user explicit direction
status: open
deadline: complete before next overnight Asian session (~18:00 ET 2026-05-14)
---

# MORNING 2026-05-14: BROKER EXECUTION FIX — TOP PRIORITY

**User direction 2026-05-14 04:55 UTC, verbatim:**
*"please confirm that no matter what you will investigate these issues
in the morning. if you have to schedule a windows task or something to
ensure this is done. Your sole priority now is the execution fix:
nothing matters until this is done. we have a validated edge that could
be extremely profitable"*

## Nothing else gets done before this is solved

Strategies are validated (10+ positive-peak trades overnight
2026-05-13/14). Execution layer is the entire reason the wins weren't
captured. Until the execution fix is verified live, no other backlog
item, no refactor, no audit, no new feature.

## What "fix" means concretely

The trader can place an entry order and have it fill within a sensible
buffer of the strategy's intended entry price. Today's MGC long signal
at entry=4697.5 filled at 4710.9 (134 ticks adverse). That's the bug to
solve.

Verification: after the fix, place a MGC entry where the strategy's
intended entry is X and verify the actual fill is within ±10 ticks of
X. Document the result in `vault/research/analysis/`.

## Investigation roadmap (ordered)

### Step 1 — Topstep ProjectX type-code semantics (~60 min)

Empirically determine what each `type` value actually means at the
broker. The current mapping in `tools/projectx_client.py:place_order`
claims `{"market": 1, "limit": 2, "stop": 3, "stop_limit": 4}` but
verified-broken evidence:

- `type=1` (we call "market") → broker rejects with "limit price not set"
- `type=2` (we call "limit") with limitPrice=4698 filled at market 4710

Hypothesis: Topstep's actual codes may be `{1: Limit, 2: Market}` —
inverted from our mapping. Test by:
1. Place `place_order(order_type="market", limit_price=None)` on a tiny
   trade. If still rejected, type=1 is NOT market.
2. Place `place_order(order_type="limit", limit_price=<far-from-market>)`
   and check if it sits as a working order (proper limit) or fills
   immediately (marketable). If it sits, type=2 IS a real limit.
3. Try other order_type strings if available: "trailing_stop", "market_if_touched", etc.
4. Look for ProjectX/TopstepX API docs in repo or via web search for the
   correct type-code schema.

### Step 2 — Apply the fix (~30 min)

Once correct codes known, update the type_code mapping in
`tools/projectx_client.py:place_order`. This is a HIGH_RISK_FILE per
CLAUDE.md — requires user explicit approval if doing autonomously.
Include in the commit: which codes were verified, with what test, what
result.

### Step 3 — Verify end-to-end on a controlled MGC trade (~30 min)

After the fix:
1. Wait for a clean Asian-session signal (or manually trigger a test
   trade outside live hours if possible)
2. Confirm entry fills within ±10 ticks of strategy entry
3. Confirm broker stop is placed correctly
4. Confirm software take-profit, profit-lock, and trailing-broker-stop
   all fire correctly on a normal lifecycle
5. Document in `vault/lessons/2026-05-14_execution_fix.md`

### Step 4 — Re-enable normal trading

If verified, the system is back to a state where overnight trades can
be trusted. If NOT verified by 18:00 ET, set `trading_halt_until` in
`config/risk_limits.yaml` to the next morning to skip the next
overnight session (don't lose money on broken execution).

## Currently in place (don't break these)

Memory: [[project-broker-order-semantics]] documents every confirmed
broker quirk discovered 2026-05-13/14. READ FIRST before touching
any place_order code.

- `close_position` endpoint works (verified)
- `place_order(type=stop_limit)` works (verified — protective stops appear in working orders)
- `cancel_order` works (verified)
- `modify_order` returns success but doesn't actually modify — use cancel+replace
- `MAX_FILL_SLIPPAGE_TICKS=10` protects against bad entries (post-fill check) — keep this safeguard active during the investigation, do not raise it

## Discord alerts

User wants the investigation result posted to Discord on completion:
- Test outcomes (which type codes do what)
- Whether the fix was applied
- Whether end-to-end verification passed
- Recommendation on next overnight session
