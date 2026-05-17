---
name: project-broker-order-semantics
description: "Topstep ProjectX broker quirks discovered 2026-05-14. Order-type codes in tools/projectx_client.py don't match Topstep's actual schema — `place_order(order_type=\"market\")` is REJECTED by broker with \"limit price not set\". The native `close_position` endpoint works correctly. Critical for any close/exit path."
metadata: 
  node_type: memory
  type: project
  originSessionId: b979f9ba-f40d-4fdc-8d30-1f25c42d62e2
---

# Topstep ProjectX broker behavior — what works, what doesn't

**Critical institutional knowledge — discovered 2026-05-14 evening after
the system silently failed to close ~10 positions overnight.**

## The single most important fact

**For closing positions, USE `client.close_position(account_id, contract_id)`.**
**DO NOT use `client.place_order(order_type="market", time_in_force="ioc")`.**

Topstep's broker rejects `place_order` with `type=1` (which our code maps
to "market") with error message: **"limit price not set"**. This means
their schema actually treats `type=1` as a LIMIT order requiring a
`limitPrice` — not as a Market order as our `tools/projectx_client.py`
type-code comment claims. The rejection happens silently from the code's
perspective: `place_order` returns a 200 response with `{"success":
False, "errorMessage": "..."}`, but our code wasn't checking the success
field on close paths.

## What works (verified 2026-05-14)

| Operation | API call | Behavior |
|---|---|---|
| Close a full position | `client.close_position(account_id, contract_id)` | ✅ Reliable — POSTs `/api/Position/closeContract`, returns `{"success": True}` and position is actually flat |
| Partial close | `client.partial_close_position(account_id, contract_id, size)` | Untested but uses same `/api/Position/...` family |
| Place protective stop | `place_order(order_type="stop_limit", ...)` with stopPrice + limitPrice | ✅ Works — type=4 = stop-limit accepted, appears in working orders |
| Cancel order | `client.cancel_order(account_id, order_id)` | ✅ Works |

## What's BROKEN (verified 2026-05-14)

| Operation | API call | Actual broker behavior |
|---|---|---|
| Close via market-IOC | `place_order(order_type="market", time_in_force="ioc")` | ❌ Rejected with "limit price not set" — type=1 is actually a LIMIT |
| Entry via "marketable limit" | `place_order(order_type="limit", limit_price=X)` | ⚠️ Fills at MARKET price ignoring limit — type=2 isn't a strict limit. MGC buy limit @ 4698 filled at 4710 (134-tick adverse slippage) |
| Modify stop price | `client.modify_order(order_id, stop_price=X)` | ❌ Returns success but stopPrice doesn't actually change on the working order. Cancel + replace is the only working path |

## Implications for the codebase

**Close paths fixed 2026-05-14:**
- `tools/profit_protect.check_and_close` — both target-hit AND trailing-lock-close now use `close_position`
- `tools/loss_cap.enforce_loss_cap` — uses `close_position`
- `tools/bracket_placement._emergency_flatten_position` — uses `close_position`

**Trailing stop fixed 2026-05-14:**
- `tools/profit_protect._trail_broker_stop_to_floor` — uses cancel + new place_order(stop_limit) instead of modify_order

**Still UNRESOLVED (P0 in backlog 2026-05-14):**
- Entry order semantics. Strategy emits entry=4697.5, marketable buy limit set to 4698.0 (5-tick buffer), broker fills at 4710.0 (12 points adverse). We don't know which order_type would behave as a proper marketable limit. Mitigated by `MAX_FILL_SLIPPAGE_TICKS=10` in bracket_placement which emergency-flattens if fill is too far from intended entry — but that means trades get blocked instead of getting good fills.

## How to apply

- **Any new close path:** use `close_position`, NOT `place_order(market)`.
- **Any code reading place_order response:** check `result.get("success")` for explicit `False` — broker returns 200 with `success=False` on rejection rather than a 4xx status.
- **Any modify_order call:** verify by re-reading working orders after a brief delay. If the stopPrice didn't change, fall back to cancel + place new.
- **Future investigation of entry types:** test empirically with controlled orders (place a deliberately non-marketable limit at e.g. 50% below current price and check if it sits as working vs immediately fills). Document findings in `vault/research/analysis/`.

## Why this matters

2026-05-14 overnight: 10+ MGC/MNQ trades fired, EVERY ONE had a positive
peak (strategy edge confirmed). Only ~3 closed in the green because every
software-side close attempt was silently rejected by the broker, so
positions rode through their peaks and exited via the broker's eventual
stop fill. The strategies are working; the broker abstraction layer was
broken. This memory exists to prevent future-Claude from making the same
assumption that order_type codes match the documented broker schema.

Related: [[feedback-silent-default-means-off]],
[[project-2026-05-13-overnight-dll-breach]].
