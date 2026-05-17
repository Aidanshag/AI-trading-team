---
type: analysis
status: ATTEMPTED, INCONCLUSIVE — broker rejected during reopen
date: 2026-05-17
purpose: Phase 4 — broker target leg re-test (per backlog P1)
---

# Broker target leg re-test — attempt 2026-05-17

Per backlog item: re-test whether the 2026-05-11 broker target-fill anomaly
has lifted. Workaround (`SKIP_TARGET_LEG=True`) currently active in
`scripts/live_trader.py`.

## Attempt details

- **Time:** 2026-05-17 ~17:50 ET (50 min after Sunday Globex reopen)
- **Symbol:** MGC (micro gold, $1/tick)
- **Order:** SELL LIMIT @ $4546.40 (= last_close $4543.40 + 30 ticks above)
  - Non-marketable: limit is $3 above current — should sit as a working order
- **Script:** `scripts/test_broker_target_leg.py`

## Result

```
ORDER REJECTED: The market is currently crossed or has just opened.
Please try again later.
```

This is **not** the target-fill bug. The broker outright refused the order
due to the Sunday-reopen condition. The bug we're testing for is "limit
auto-fills at next-available market" — we never got past placement to
observe that behavior.

## Status: INCONCLUSIVE

`SKIP_TARGET_LEG = True` remains in effect (correct conservative posture).

## Retry plan

- Re-run `python -m scripts.test_broker_target_leg` once Asian session is
  fully liquid (~19:00 ET / 23:00 UTC). The "market is crossed or just
  opened" reject typically clears within 1-2 hours of reopen.
- If retry succeeds and order rests for 60s → broker bug lifted; flip
  `SKIP_TARGET_LEG = False` for the next deployment.
- If retry succeeds and order auto-fills → bug persists; document and
  leave the workaround in place.

## Auto-merge note

Per backlog: this item is `auto-merge: no — requires manual observation of
broker behavior`. Even if a retry succeeds, the autonomous routine must
NOT flip the flag without user review. The retry will be queued for the
next user-present cycle.
