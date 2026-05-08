"""Tests for the bracket-OCO misdirected-leg detection.

Background: place_bracket places entry + stop + target as 3 SEPARATE orders.
ProjectX has no native OCO primitive, so when one protective leg fills (e.g.
target), the other (stop) stays working. If price oscillates back through
the now-orphaned stop, it FIRES and opens an unwanted opposite-direction
position. Caught 2026-05-01: 6E short -> target hit at 1.17395 -> stop at
1.17505 fired -> opened a LONG 6E at 1.17505 with no protective stop.

The fix: in scan_once orphan cleanup, detect working _stop or _target legs
whose entry-side does not match the current position direction, and cancel
them. Logs a breach risk_event so the user knows about the unwanted state.

These tests don't run scan_once end-to-end -- they exercise the inline
direction-mismatch logic by mirroring it.
"""

from __future__ import annotations


def _detect_misdirected(working_orders: list[dict],
                        positions: list[dict],
                        entry_sides: dict[str, str]) -> list[dict]:
    """Replica of the misdirected-leg detection inside scan_once.

    Args:
      working_orders: list of broker working orders, each with `customTag`
                      and `contractId`.
      positions: list of broker positions, each with `contractId`, `size`,
                 `type` (1=long, 2=short).
      entry_sides: map of base_tag (auto_XXX without _stop/_target suffix)
                   -> intended entry side ("buy" or "sell").

    Returns: list of working orders that should be cancelled as misdirected.
    """
    pos_dir_by_contract: dict[str, str] = {}
    for p in positions:
        sz = int(p.get("size") or 0)
        if sz == 0:
            continue
        cid = p.get("contractId")
        pos_type = int(p.get("type") or 0)
        if pos_type == 1:
            pos_dir_by_contract[cid] = "long"
        elif pos_type == 2:
            pos_dir_by_contract[cid] = "short"

    misdirected = []
    for o in working_orders:
        tag = str(o.get("customTag") or "")
        if not (tag.startswith("auto_") or tag.startswith("recovery_")):
            continue
        if not (tag.endswith("_stop") or tag.endswith("_target")):
            continue
        base_tag = tag
        for suffix in ("_stop", "_target"):
            if base_tag.endswith(suffix):
                base_tag = base_tag[: -len(suffix)]
                break
        entry_side = (entry_sides.get(base_tag) or "").lower()
        if not entry_side:
            continue
        expected_pos = "long" if entry_side == "buy" else "short"
        actual_pos = pos_dir_by_contract.get(o.get("contractId"))
        if actual_pos != expected_pos:
            misdirected.append(o)
    return misdirected


# ----------------------------------------------------------------------------
# The actual bug we hit on 2026-05-01
# ----------------------------------------------------------------------------

def test_orphan_stop_after_target_fill_with_unwanted_long():
    """6E short entered, target hit, then stop fired and opened a LONG.
    The stop tag is auto_X_stop, entry was sell (short), but position is
    now LONG. Cancel."""
    working = [
        {"customTag": "auto_abc_stop", "contractId": "CON.F.US.EU6.M26",
         "id": 9001},
    ]
    positions = [
        # Unwanted long opened by the stop fire
        {"contractId": "CON.F.US.EU6.M26", "size": 1, "type": 1},
    ]
    entry_sides = {"auto_abc": "sell"}
    misdirected = _detect_misdirected(working, positions, entry_sides)
    assert len(misdirected) == 1
    assert misdirected[0]["id"] == 9001


def test_orphan_target_after_stop_fill_with_unwanted_short():
    """Mirror case: long entered, stop hit, then target fired and opened a
    SHORT. Cancel."""
    working = [
        {"customTag": "auto_def_target", "contractId": "CON.F.US.NGE.M26",
         "id": 9002},
    ]
    positions = [
        {"contractId": "CON.F.US.NGE.M26", "size": 1, "type": 2},
    ]
    entry_sides = {"auto_def": "buy"}
    misdirected = _detect_misdirected(working, positions, entry_sides)
    assert len(misdirected) == 1


def test_orphan_when_position_flat():
    """Target filled, position is flat, stop is still working. The original
    orphan-cleanup logic catches this via 'no position on contract' — but
    the misdirection detection should ALSO flag it (expected short, actual
    None != short). Defense in depth."""
    working = [
        {"customTag": "auto_xyz_stop", "contractId": "CON.F.US.EU6.M26",
         "id": 9003},
    ]
    positions = []  # flat
    entry_sides = {"auto_xyz": "sell"}
    misdirected = _detect_misdirected(working, positions, entry_sides)
    assert len(misdirected) == 1


# ----------------------------------------------------------------------------
# Healthy-state cases (no false positives)
# ----------------------------------------------------------------------------

def test_healthy_short_with_protective_stop_not_flagged():
    """Position is SHORT, stop is buy-stop tagged for the short entry.
    This is the normal protective state — do not cancel."""
    working = [
        {"customTag": "auto_abc_stop", "contractId": "CON.F.US.EU6.M26",
         "id": 9004},
    ]
    positions = [
        {"contractId": "CON.F.US.EU6.M26", "size": 1, "type": 2},
    ]
    entry_sides = {"auto_abc": "sell"}
    assert _detect_misdirected(working, positions, entry_sides) == []


def test_healthy_long_with_protective_target_not_flagged():
    """Position is LONG, target is sell-limit tagged for the long entry.
    Normal protective state."""
    working = [
        {"customTag": "auto_abc_target", "contractId": "CON.F.US.NGE.M26",
         "id": 9005},
    ]
    positions = [
        {"contractId": "CON.F.US.NGE.M26", "size": 1, "type": 1},
    ]
    entry_sides = {"auto_abc": "buy"}
    assert _detect_misdirected(working, positions, entry_sides) == []


def test_user_placed_orders_not_flagged():
    """Orders without auto_ or recovery_ tag prefix must never be flagged
    by this logic — they are user-placed and we don't manage them."""
    working = [
        {"customTag": "manual_user_thing", "contractId": "CON.F.US.EU6.M26",
         "id": 9006},
        {"customTag": "", "contractId": "CON.F.US.EU6.M26",
         "id": 9007},
    ]
    positions = []
    entry_sides = {}
    assert _detect_misdirected(working, positions, entry_sides) == []


def test_entry_legs_never_flagged():
    """Entry orders (no _stop/_target suffix) are not subject to the
    misdirection check — only protective legs are."""
    working = [
        {"customTag": "auto_abc", "contractId": "CON.F.US.EU6.M26",
         "id": 9008},
    ]
    positions = []  # flat — but this is an entry leg, not protective
    entry_sides = {"auto_abc": "sell"}
    assert _detect_misdirected(working, positions, entry_sides) == []
