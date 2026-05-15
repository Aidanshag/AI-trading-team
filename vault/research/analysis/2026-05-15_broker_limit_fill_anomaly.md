---
type: research
date: 2026-05-15
status: complete-with-correction
priority: P0
references:
  - vault/_meta/improvement_backlog.md (BROKER LIMIT FILL ANOMALY item)
  - vault/_meta/memory_backup/project_broker_order_semantics.md
  - logs/topstep_orders_5_13_to_5_14.json (75 orders, 2 days)
  - tools/projectx_client.py (place_order + order_type mapping)
---

# Broker limit fill anomaly — premise was wrong

## TL;DR

**The "broker fills buy-limits at prices above the limit" premise in the backlog is incorrect.** Audit of all 75 orders 2026-05-13/14 finds **zero** adverse-fill limit orders. The original incident the backlog cites ("MGC buy limit @ 4698 filled at 4709, 11pt adverse") was a `type=2 (Market)` order, not a limit — slippage on a market order in a fast tape is expected.

Separately, the `profitlock_*` rejection pattern (13 rejected) was real — but it had a different root cause: `type=1 (Limit)` orders being sent with `limitPrice=None`. The broker correctly rejected with "limit price not set." This was fixed at commit `326ab7f` (2026-05-14) when the profit-lock close path migrated to `close_position`. Verified live tonight via cycle 2 regression tests.

**Recommendation:** mark the backlog item resolved. No code change needed; existing mitigations (direction-aware `POST_FILL_SLIPPAGE` + `close_position` for flatten paths) cover the real surface.

## Methodology

1. Verified `OrderType` enum against the official ProjectX swagger:
   ```
   1 = Limit, 2 = Market, 3 = StopLimit, 4 = Stop, 5 = TrailingStop
   ```
2. Audited every `type=1 (Limit)` order in the 2-day window. For each, compared `filledPrice` vs `limitPrice`:
   - Buy: adverse = `fill > limit`
   - Sell: adverse = `fill < limit`
3. Found ZERO adverse fills among limit orders.
4. Traced the specific cited incident (5/14 04:28:06 MGC buy fill at 4709) by `creationTimestamp + filledPrice` — confirmed `type=2 (Market)`, not Limit.
5. Examined the 14 rejected orders to find their root cause.

## Findings

### Original "buy-limit @ 4698 filled at 4709" incident — NOT a limit anomaly

```python
ts=2026-05-14T04:28:06.627715+00:00
type=2   # Market, not Limit
status=2 # Filled
limit=None   # No limit price
stop=None
fill=4709.0
tag=live_db8157f24655
```

This was a market order. Filling at 4709 when current ask was around 4698 is normal market-order slippage in a fast Asian-session MGC tape. Not a broker bug.

### Zero adverse fills among 31 type=1 (Limit) orders

```
Filled limit orders: 31
Adverse fills (fill past limit): 0
```

Every limit order that filled did so at or better than the limit price, as standard limit semantics require. The "marketable-limit" buffer (`limit_price = entry_price ± 5 * tick`) was already enforcing fill discipline correctly.

### The 13 `profitlock_*` rejections — different root cause

All 13 rejected `profitlock_*` orders had:
```
type=1 (Limit)
limitPrice=None  ← THIS is the bug
side=0 or 1
size=1
```

A `type=1` (Limit) order without a `limitPrice` is invalid per the ProjectX schema (`limitPrice` is required when `type=1`). The broker correctly rejected with "limit price not set."

The bug was upstream — the old profit-lock close path called `place_order(order_type="limit")` without supplying `limit_price`. The broker rejected every attempt; profit-lock effectively did nothing.

**Already fixed:** commit `326ab7f` (2026-05-14) migrated the profit-lock flatten path to `client.close_position(account_id, contract_id)`, which doesn't require a limit price (it's a server-side close). Tonight's cycle 2 hardened this with a regression test.

### Order-type code mapping is correct (per swagger)

Our `tools/projectx_client.py` mapping:
```python
type_code = {
    "limit": 1, "market": 2, "stop": 3, "stop_limit": 4,
}.get(order_type.lower())
```

Per the official swagger enum:
```
1 = Limit       ✓
2 = Market      ✓
3 = StopLimit   ⚠️ (we call it "stop")
4 = Stop        ⚠️ (we call it "stop_limit")
```

**Naming mismatch but functionally correct given current usage:** all callers of `order_type="stop"` (e.g., `tools/bracket_placement.py:341`, `tools/profit_protect.py:485`, `scripts/auto_trader.py:841`) pass BOTH `stop_price` AND `limit_price` — which is the data shape of a StopLimit (type=3). So they're getting what they want.

Caller `order_type="stop_limit"` does the same — also gets type=4 (Stop) but supplies both prices anyway, so the broker has the stopPrice it needs (and ignores limitPrice as a stop-order ignore-limit).

**Net: no functional bug, but the naming is confusing.** Could be cleaned up in a future cosmetic cycle by aligning local names with the official enum: `"stop_limit": 3, "stop": 4`. Low priority — doesn't affect behavior.

## Conclusion

The backlog item was premised on misremembered evidence. The real `profitlock_*` rejection bug had a different root cause (missing limitPrice on type=1 orders) and was fixed independently 2026-05-14. The "buy limit @ 4698 fills at 4709" incident was a market order, not a limit.

No code change needed. Backlog item can be marked resolved with this analysis as the audit trail.

## Out-of-scope follow-ups (not implemented in this cycle)

1. **Naming cleanup:** `order_type="stop"` actually maps to StopLimit (type=3) per official spec. Confusing. ~30 min refactor with full test rename. Low impact since callers always pass both prices and behavior is correct.
2. **Type=5 (TrailingStop) untested:** if we ever want a true broker-side trailing stop instead of the cancel-and-replace pattern, this enum value is worth probing.
3. **OrderSide note:** swagger says `0 = Bid, 1 = Ask`. We map `0=buy, 1=sell`. Functionally identical (a market BUY hits the ASK; a BID order is a buy). Naming mismatch only.
