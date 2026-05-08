---
name: Bracket OCO race bug + fix history
description: place_bracket places entry+stop+target as 3 separate orders without OCO linkage; orphaned protective legs can fire after the position closes and open unwanted opposite-direction positions
type: project
originSessionId: acace4fd-c68e-4ba1-94a0-a7f901b6cfba
---
place_bracket in scripts/auto_trader.py places entry, stop_limit, and target as THREE INDEPENDENT broker orders. ProjectX has no native OCO primitive, so when one protective leg fills (closing the position) the OTHER stays working and can fire on a price reversal -- opening an UNWANTED opposite-direction position with no protective stop attached.

**Why:** Real bug observed 2026-05-01. 6E short entry at 1.17455 -> target buy limit at 1.17395 filled (closed short, +$70 gross) -> stop buy at 1.17505 still working -> price reversed up -> stop fired -> opened a LONG 6E at 1.17505 with no stop loss. The original orphan-cleanup logic only checked "contract not in positions" but by the time the next scan ran, the unwanted long made the contract appear in positions, so cleanup missed it.

**How to apply:**
- Fix #1 landed in commit 4369d68 (2026-05-01): direction-aware orphan detection in scan_once. Cancels working _stop/_target legs whose entry-side does not match current position direction. Logs `bracket_oco_misdirected_leg` breach.
- Fix #2 landed 2026-05-04 in scripts/reconcile_positions.py: AUTO-FLATTEN of phantom positions. Discriminator: a broker_only position with NO matching recent entry order (within 10 min) on the position's side is a phantom from a misdirected stop-leg fire. Reconciler now market-closes phantoms immediately rather than silently absorbing them, and emits `phantom_position_flattened` breach + Discord alert.
- The 2026-05-04 incident: GC long bracket entered (buy@4531.50, stop sell@4528.90, target sell@4537.10). Price dropped through 4528.90 BEFORE entry buy-limit ever filled. Sell-stop fired into a NEW SHORT @ 4528.60. User had to manually close (got lucky +$300 by reversal). Without manual intervention the unprotected short could have hit DLL.
- Reconcile cycle is 5 min, so worst-case phantom exposure is ~5-7 min between fire and auto-flatten.
- Tests: tests/test_bracket_oco.py covers both race directions, healthy state, user-placed-order safety.
- When resuming/debugging trader after this point, check `risk_events` for `bracket_oco_misdirected_leg` and `phantom_position_flattened` -- both indicate the OCO race fired and was caught.
