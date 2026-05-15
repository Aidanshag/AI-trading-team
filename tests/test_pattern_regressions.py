"""Pattern A/B regression tests — the n=3 CI escalation.

Per CLAUDE.md "Code-review checklist — Pattern A and Pattern B":

    "If a third real-world incident matching either pattern emerges
    despite this checklist, escalate to hard-encoding the check as a
    CI test that fails the build."

After the 2026-05-10/11 incidents (calibration breakdown + orphan-leg
regression — both already-known patterns recurring despite encoded
defenses), n=3 was hit. This file is the build-failing CI tier.

Two regressions guarded:

  Pattern A — fail-silent defaults
    Concrete check: scripts/live_trader.place_bracket() MUST NOT place
    protective stop/target legs unless the entry fill is confirmed.
    A protective leg placed before fill = orphan-leg incident waiting
    to happen. 2026-05-10 ZB SHORT cost -$137.89 via this exact path.

  Pattern B — wrong-context validation
    Concrete check: ATR-based-stop strategies in STRATEGY_REGISTRY that
    declare `tick_size` + `min_stop_ticks` params MUST refuse to emit
    sub-floor signals when those params are populated. 2026-05-11
    treasury Asian-session degenerate signals (stop ≈ entry) cost a
    full trading session of validation effort.

These tests run with `python -m pytest tests/ -q`. They depend only on
the strategy code and the live_trader module — no broker, no DB, no
network. If they fail, the build is broken regardless of what else
passes.

Cross-references:
- vault/research/analysis/2026-05-11_gap_fill_wide_validation_attempt.md
- vault/lessons/2026-05-11_gap_fill_calibration_and_orphan_leg_incident.md
- vault/_meta/memory_backup/feedback_silent_default_means_off.md
- CLAUDE.md → "Code-review checklist — Pattern A and Pattern B"
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts import live_trader as lt  # noqa: E402
from tools.backtest import strategies as strats  # noqa: E402


# ════════════════════════════════════════════════════════════════════
#  Pattern A — orphan-leg / fail-silent default regression
# ════════════════════════════════════════════════════════════════════
#
# place_bracket() must:
#   1. Place entry order
#   2. Wait for fill confirmation (signature change in get_positions)
#   3. ONLY THEN place protective stop + target
#   4. If fill never confirms within timeout: cancel entry, NO legs
#
# Regression form: protective legs placed before entry-fill confirmation.
# If this test fails, an unintended-direction position can open when an
# unfilled entry's "protective" stop fires alone. That's the 2026-05-01
# incident AND the 2026-05-10 incident — same shape, two-strikes already.

class _NeverFillsBroker:
    """Mock broker: entry order accepted, but the position signature
    never changes — simulates entry-limit placed but never crossing
    market price. This is the orphan-leg trigger condition."""

    def __init__(self):
        self.place_order_calls = []
        self.cancel_order_calls = []

    def front_month_contract_id(self, symbol):
        return f"CON.F.US.{symbol}.M26"

    def get_positions(self, account_id):
        return []   # No fill ever — signature stays (0, 0)

    def get_working_orders(self, account_id):
        return []

    def place_order(self, **kwargs):
        self.place_order_calls.append(dict(kwargs))
        return {"success": True, "orderId": f"mock_{len(self.place_order_calls)}"}

    def cancel_order(self, account_id, order_id):
        self.cancel_order_calls.append({"account_id": account_id, "order_id": order_id})
        return {"success": True}


class _NoOpDB:
    """Mock DB: every operation is a no-op. place_bracket writes one
    INSERT and one UPDATE before reaching the orphan-leg check; both
    are durability nice-to-haves, not correctness-critical here."""

    def connect(self):
        return self

    def execute(self, *args, **kwargs):
        return self

    def commit(self):
        pass

    def cursor(self):
        return self


class _FavorableFillBroker:
    """Mock broker: entry order accepted, then reports a fill at a
    price BETTER than the signal entry by far more than
    MAX_FILL_SLIPPAGE_TICKS. Drives the regression test for the
    2026-05-15 POST_FILL_SLIPPAGE direction-sign fix."""

    def __init__(self, symbol: str, side: str, signal_entry: float,
                 favorable_ticks: int, tick: float):
        self.symbol = symbol
        self.side = side  # 'buy' or 'sell'
        self.tick = tick
        self.signal_entry = signal_entry
        # Favorable fill: buy lower than signal, sell higher.
        if side == "buy":
            self.fill_price = signal_entry - favorable_ticks * tick
            self.pos_type = 1   # long
        else:
            self.fill_price = signal_entry + favorable_ticks * tick
            self.pos_type = 2   # short
        self.place_order_calls: list[dict] = []
        self.cancel_order_calls: list[dict] = []
        self.close_position_calls: list[dict] = []
        self._working_orders: list[dict] = []
        self._entry_placed = False

    def front_month_contract_id(self, symbol):
        return f"CON.F.US.{symbol}.M26"

    def get_positions(self, account_id):
        if not self._entry_placed:
            return []
        return [{
            "contractId": f"CON.F.US.{self.symbol}.M26",
            "size": 1, "type": self.pos_type,
            "averagePrice": self.fill_price,
        }]

    def get_working_orders(self, account_id):
        return list(self._working_orders)

    def place_order(self, **kwargs):
        self.place_order_calls.append(dict(kwargs))
        # Mark the entry as filled after the first call so the next
        # _position_signature() probe sees a position open.
        if not self._entry_placed:
            self._entry_placed = True
        else:
            # protective stop placement — track as a working order
            self._working_orders.append({
                "contractId": kwargs.get("contract_id"),
                "type": 4, "customTag": kwargs.get("client_order_id"),
            })
        return {"success": True, "orderId": f"mock_{len(self.place_order_calls)}"}

    def cancel_order(self, account_id, order_id):
        self.cancel_order_calls.append({"account_id": account_id, "order_id": order_id})
        return {"success": True}

    def close_position(self, account_id, contract_id):
        # If this fires, the regression has reappeared.
        self.close_position_calls.append({"account_id": account_id,
                                           "contract_id": contract_id})
        return {"success": True}


def test_post_fill_slippage_does_not_flatten_on_favorable_fill(monkeypatch):
    """Regression: the POST_FILL_SLIPPAGE gate must be DIRECTION-AWARE.

    2026-05-15 incident: brain emitted MGC long @ 4622.3; broker filled
    @ 4620.2 (21 ticks BETTER than signal). The pre-fix gate computed
    `abs(fill - entry) / tick = 21t > 10t MAX` and emergency-flattened
    a favorable fill for -$3 + fees. Two trades destroyed in one hour
    (5/14 22:24 + 22:39 ET) before the fix.

    This test wires a broker that reports a fill 21t favorable on a
    BUY and asserts place_bracket does NOT emergency-flatten — it
    proceeds to place the protective stop instead.

    If this regresses: every winning entry where the broker fills
    better than signal will be killed at +$0 - fees. Pattern A —
    a gate ran with the wrong sign and silently destroyed edge.
    """
    from scripts import live_trader as lt
    import tools.bracket_placement as _bp

    broker = _FavorableFillBroker(
        symbol="MGC", side="buy",
        signal_entry=4622.3, favorable_ticks=21, tick=0.10,
    )

    db_instance = _NoOpDB()
    monkeypatch.setattr(lt, "get_db", lambda: db_instance)
    monkeypatch.setattr(_bp, "get_db", lambda: db_instance)
    monkeypatch.setattr(lt, "FILL_WAIT_TIMEOUT_S", 1)
    monkeypatch.setattr(lt, "FILL_WAIT_POLL_S", 1)

    signal = {
        "side": "long",
        "price": 4622.3,
        "stop": 4613.5,
        "target": 4641.7,
    }
    result = lt.place_bracket(
        broker, account_id=1, symbol="MGC", signal=signal, qty=1, dry_run=False
    )

    # === Build-failing assertions ===

    assert len(broker.close_position_calls) == 0, (
        f"PATTERN A REGRESSION: POST_FILL_SLIPPAGE gate emergency-flattened "
        f"a FAVORABLE fill ({broker.fill_price} on a long signal @ "
        f"{signal['price']}, 21t better). close_position called "
        f"{len(broker.close_position_calls)}x — should never fire on a "
        f"favorable fill. The gate must be direction-aware, not abs(). "
        f"See tools/bracket_placement.py:263 — fix landed 2026-05-15."
    )
    assert result.get("status") != "post_fill_slippage_flattened", (
        f"PATTERN A REGRESSION: place_bracket returned "
        f"{result.get('status')!r} after a favorable fill. Expected the "
        f"trade to proceed to stop placement, not be flattened."
    )

    # The bracket should have placed entry + protective stop = 2 orders.
    n_orders = len(broker.place_order_calls)
    assert n_orders == 2, (
        f"After a favorable fill, place_bracket should place 1 entry + "
        f"1 protective stop = 2 orders. Got {n_orders}. calls={broker.place_order_calls}"
    )


def test_pattern_a_unfilled_entry_does_not_place_protective_legs(monkeypatch):
    """The build-failing CI check for Pattern A.

    If this fails, scripts/live_trader.place_bracket has regressed to
    placing protective legs before entry-fill confirmation. Roll back
    or fix BEFORE merging — this is the 2026-05-01 / 2026-05-10
    orphan-leg failure mode.

    The mock broker accepts the entry order but reports NO position
    (signature never changes). place_bracket should:
      - Call place_order EXACTLY ONCE (the entry).
      - After FILL_WAIT_TIMEOUT_S, give up.
      - Call cancel_order EXACTLY ONCE (the entry).
      - Return status='cancelled_unfilled'.
      - NEVER place a stop or target leg.
    """
    broker = _NeverFillsBroker()

    # Override the DB so we don't touch real state. Override the fill
    # timeout to 1s so the test completes in <2s.
    # CRITICAL: patch in BOTH lt and tools.bracket_placement — place_bracket
    # imports get_db directly from state.db (not via live_trader). Patching
    # only lt.get_db means real DB writes still go through. 2026-05-14 found
    # this leaked the test stop order into production DB.
    db_instance = _NoOpDB()
    monkeypatch.setattr(lt, "get_db", lambda: db_instance)
    import tools.bracket_placement as _bp
    monkeypatch.setattr(_bp, "get_db", lambda: db_instance)
    monkeypatch.setattr(lt, "FILL_WAIT_TIMEOUT_S", 1)
    monkeypatch.setattr(lt, "FILL_WAIT_POLL_S", 1)

    signal = {
        "side": "long",
        "price": 110.0,
        "stop": 109.75,
        "target": 110.5,
    }
    result = lt.place_bracket(
        broker, account_id=1, symbol="ZN", signal=signal, qty=1, dry_run=False
    )

    # === Build-failing assertions ===

    n_orders = len(broker.place_order_calls)
    assert n_orders == 1, (
        f"PATTERN A REGRESSION: place_bracket made {n_orders} broker "
        f"place_order calls when entry never filled. Expected 1 (entry "
        f"only). place_order_calls={broker.place_order_calls}.\n\n"
        "This is the orphan-leg failure mode that cost -$137.89 on "
        "2026-05-10 ZB SHORT. See "
        "vault/lessons/2026-05-11_gap_fill_calibration_and_orphan_leg_incident.md "
        "and CLAUDE.md → 'Pattern A — fail-silent defaults'."
    )

    # Verify the only call was the entry, not a stop/target.
    only_call = broker.place_order_calls[0]
    order_type = only_call.get("order_type")
    assert order_type == "limit", (
        f"PATTERN A REGRESSION: the single place_order call was "
        f"order_type={order_type!r}, not 'limit' (entry). "
        f"place_bracket may be placing protective legs first."
    )
    assert only_call.get("stop_price") is None, (
        f"PATTERN A REGRESSION: the entry order has stop_price set "
        f"({only_call.get('stop_price')!r}); place_bracket may be "
        f"submitting a protective stop combined with entry."
    )

    assert len(broker.cancel_order_calls) == 1, (
        f"PATTERN A REGRESSION: expected exactly 1 cancel_order call "
        f"for the unfilled entry, got {len(broker.cancel_order_calls)}. "
        f"calls={broker.cancel_order_calls}"
    )

    assert result.get("status") == "cancelled_unfilled", (
        f"PATTERN A REGRESSION: place_bracket returned status="
        f"{result.get('status')!r} when entry never filled. Expected "
        f"'cancelled_unfilled'."
    )


# ════════════════════════════════════════════════════════════════════
#  Pattern B — degenerate calibration / silent-divide regression
# ════════════════════════════════════════════════════════════════════
#
# Strategies that compute stops as a multiple of ATR can collapse to
# sub-tick stops on low-vol bars. When the rr-check then divides by
# `max(stop_dist, 1e-9)`, the ratio becomes astronomical and every
# signal passes — the validation pipeline emits "high-conviction"
# garbage. This is what made gap_fill look like a +11.76 t-stat edge
# until 2026-05-11.
#
# The defense: any strategy declaring `tick_size` + `min_stop_ticks`
# MUST floor stop distance at `min_stop_ticks × tick_size` when
# tick_size is supplied.


# Synthetic bars: 30 quiet bars at 110.00 with 1-tick range noise,
# then one bar with a large gap. ATR converges to ~1 tick → 0.5×ATR
# is sub-tick → without the floor, gap_fill would emit signals with
# stop equal to entry (degenerate).

def _quiet_bars_with_gap(*, n_quiet: int = 30, gap_ticks: int = 10,
                         tick: float = 0.015625, base_price: float = 110.0):
    """Build a synthetic 5m bar DataFrame where ATR is ~1 tick and
    bar n_quiet has a gap of `gap_ticks` ticks from prior close."""
    times = pd.date_range("2026-05-01 00:00", periods=n_quiet + 1,
                          freq="5min", tz="UTC")
    opens, highs, lows, closes = [], [], [], []
    for i in range(n_quiet):
        # Each quiet bar oscillates 1 tick around base_price.
        opens.append(base_price)
        highs.append(base_price + tick)
        lows.append(base_price - tick)
        closes.append(base_price)
    # Gap bar — open is base_price + gap_ticks * tick (so the strategy
    # sees a gap-up vs prior close == base_price).
    gap_open = base_price + gap_ticks * tick
    opens.append(gap_open)
    highs.append(gap_open + tick)
    lows.append(gap_open - tick)
    closes.append(gap_open)
    return pd.DataFrame(
        {"Open": opens, "High": highs, "Low": lows, "Close": closes,
         "Volume": [100] * len(opens)},
        index=times,
    )


def test_pattern_b_gap_fill_floor_active_emits_no_sub_floor_signals():
    """The build-failing CI check for Pattern B.

    If this fails, tools/backtest/strategies.gap_fill has regressed:
    when tick_size + min_stop_ticks are supplied, the strategy should
    NEVER emit a signal whose stop distance is below the floor.

    On the synthetic bars below ATR≈1tick. With min_stop_ticks=3 and
    tick_size=0.015625, the floor is 3 ticks = 0.046875. Any emitted
    signal must satisfy |entry - stop| ≥ 0.046875.
    """
    tick = 0.015625
    min_stop_ticks = 3
    floor = min_stop_ticks * tick

    bars = _quiet_bars_with_gap(tick=tick, gap_ticks=10)
    sigs = list(strats.gap_fill(
        bars, tick_size=tick, min_stop_ticks=min_stop_ticks,
    ))

    # If any signals were emitted, every one of them must respect the floor.
    for sig in sigs:
        stop_dist = abs(sig.price - sig.stop)
        assert stop_dist >= floor - 1e-9, (
            f"PATTERN B REGRESSION: gap_fill emitted signal with "
            f"stop_distance={stop_dist:.6f} (= {stop_dist/tick:.2f} ticks) "
            f"below the {min_stop_ticks}-tick floor "
            f"({floor:.6f}). Side={sig.side!r} price={sig.price} stop={sig.stop}.\n\n"
            "This is the 2026-05-11 calibration failure mode: in low-vol "
            "sessions ATR collapses sub-tick and the strategy emits "
            "degenerate signals that fail live and corrupt validation "
            "stats. See vault/lessons/2026-05-11_gap_fill_calibration_and_orphan_leg_incident.md "
            "and CLAUDE.md → 'Pattern B — wrong-context validation'."
        )


def test_pattern_b_gap_fill_wide_floor_active_emits_no_sub_floor_signals():
    """Companion to the gap_fill test — same check on gap_fill_wide.

    gap_fill_wide is supposed to be the slippage-tolerant variant with
    a built-in 3-tick floor. Same protection guarantee applies. If
    this regresses, gap_fill_wide is no longer wide.
    """
    tick = 0.015625
    min_stop_ticks = 3
    floor = min_stop_ticks * tick

    bars = _quiet_bars_with_gap(tick=tick, gap_ticks=10)
    sigs = list(strats.gap_fill_wide(
        bars, tick_size=tick, min_stop_ticks=min_stop_ticks,
    ))

    for sig in sigs:
        stop_dist = abs(sig.price - sig.stop)
        assert stop_dist >= floor - 1e-9, (
            f"PATTERN B REGRESSION: gap_fill_wide emitted signal with "
            f"stop_distance={stop_dist:.6f} below the floor "
            f"({floor:.6f}). Side={sig.side!r} price={sig.price} stop={sig.stop}."
        )


def test_pattern_b_floor_actually_matters_baseline_check():
    """Sanity / non-vacuous check: without the floor, gap_fill DOES
    emit degenerate signals on the same synthetic bars. This proves
    the regression test above isn't trivially passing because the
    bars happen not to trigger any signal.

    If this stops passing — i.e. gap_fill without floor also emits
    no degenerate signals — the synthetic bar fixture is wrong and
    needs to be recalibrated so the regression test stays meaningful.
    """
    tick = 0.015625

    bars = _quiet_bars_with_gap(tick=tick, gap_ticks=10)
    # No tick_size → no floor → strategy uses raw 0.5×ATR stop
    sigs_no_floor = list(strats.gap_fill(bars))

    # We want SOME signals with sub-floor stops to be emittable when
    # the floor is off. If this assertion fails, the test fixture is
    # stale — adjust gap_ticks or the bar pattern.
    sub_floor_count = sum(
        1 for s in sigs_no_floor
        if abs(s.price - s.stop) < 3 * tick - 1e-9
    )
    assert sub_floor_count > 0, (
        "TEST FIXTURE STALE: the synthetic low-vol bars no longer "
        "trigger sub-floor gap_fill signals when the floor is off, "
        "so the Pattern B regression tests above are vacuously passing. "
        "Adjust _quiet_bars_with_gap() — likely need larger gap or "
        "more bars to drive ATR even smaller."
    )


# ════════════════════════════════════════════════════════════════════
#  Pattern B — wide-stop / no-upper-bound regression  (n=3, 2026-05-13)
# ════════════════════════════════════════════════════════════════════
#
# 2026-05-12/13 overnight: live_trader fired GC long with the strategy's
# native 64-tick ($640) stop. Internal $150 per-trade cap fires only
# AFTER fill, on the 5-min scan tick — too slow in thin Asian tape. The
# trade hit the broker stop for −$640 before the cap could close it.
# Pattern B: calibration mismatch (strategy stop assumed a regime where
# 64 ticks was reasonable; thin overnight tape made it the entire
# account). Encoded defense: signal_passes_max_risk_gate rejects any
# signal whose stop_distance × tick_value × qty > MAX_SIGNAL_RISK_USD
# BEFORE the order leaves the trader.

def test_pattern_b_oversized_gc_stop_rejected_pre_placement():
    """The build-failing CI check for the 2026-05-13 wide-stop incident.

    If this fails, scripts/live_trader has regressed to placing trades
    whose dollar risk exceeds MAX_SIGNAL_RISK_USD. Today that's $150.
    A 64-tick GC stop = $640 — clearly out of bounds and the exact
    shape of the 2026-05-13 GC long that cost −$644.

    The gate is purely arithmetic — tick_size × tick_value × stop_ticks
    — so this test is deterministic. No broker, no DB, no network.
    """
    # GC: tick_size=0.10, tick_value=$10.00 → 64 ticks = $640 risk
    sig = {"side": "long", "price": 4716.5, "stop": 4710.1,
           "target": 4728.3}
    ok, reason = lt.signal_passes_max_risk_gate(sig, "GC", qty=1)
    assert not ok, (
        f"PATTERN B REGRESSION: signal_passes_max_risk_gate ACCEPTED a "
        f"GC bracket with 64-tick ($640) stop — well over the "
        f"${lt.MAX_SIGNAL_RISK_USD:.0f} cap. This is the exact shape of "
        f"the 2026-05-13 overnight GC long that cost −$644 and locked "
        f"the Topstep account. Reason returned: {reason!r}.\n\n"
        "Check: did MAX_SIGNAL_RISK_USD get raised? Did tick_value lookup "
        "for GC break? Did the call site at scripts/live_trader.scan_once "
        "stop calling this gate? See "
        "vault/lessons/2026-05-13_overnight_dll_breach.md."
    )


def test_pattern_b_normal_stop_passes_max_risk_gate():
    """Sanity / non-vacuous companion to the above.

    A sane 6-tick GC stop ($60 risk) MUST pass. If this regresses, the
    gate has been tuned too tight and is rejecting normal trades. Find
    the tuning regression before merging.
    """
    sig = {"side": "long", "price": 4716.5, "stop": 4716.5 - 6 * 0.10,
           "target": 4716.5 + 12 * 0.10}
    ok, reason = lt.signal_passes_max_risk_gate(sig, "GC", qty=1)
    assert ok, (
        f"GATE TOO TIGHT: signal_passes_max_risk_gate rejected a 6-tick "
        f"($60 risk) GC signal that is comfortably under the "
        f"${lt.MAX_SIGNAL_RISK_USD:.0f} cap. Reason: {reason!r}. "
        "MAX_SIGNAL_RISK_USD may have been lowered too far or the "
        "tick_value lookup is broken."
    )


# ════════════════════════════════════════════════════════════════════
#  Pattern A — wrong-config-key DLL gate regression  (n=3, 2026-05-13)
# ════════════════════════════════════════════════════════════════════
#
# 2026-05-12/13 overnight: at day P&L −$683 the trader fired a third
# bracket because dll_breached() read `daily_loss_limit_usd` (= Topstep's
# $1000 hard limit) instead of `internal_dll_target_usd` (the tighter
# soft floor). The default-1000 fallback meant the gate effectively
# disabled itself relative to user intent ("agents target THIS, not
# Topstep's"). Pattern A: a load-bearing safety field read the wrong
# key and silently no-op'd until the broker-side hard limit kicked in.

def test_pattern_a_dll_breached_uses_internal_target(monkeypatch, tmp_path):
    """The build-failing CI check for the 2026-05-13 wrong-key DLL bug.

    Mock risk_limits.yaml to declare internal_dll_target_usd=250 and a
    Topstep daily_loss_limit_usd=1000. Pass a snapshot with day P&L
    of -$300 (above internal, below Topstep). The gate MUST return
    breached=True. If it returns False, dll_breached has regressed to
    reading the Topstep field as primary.
    """
    fake_yaml = {
        "account": {
            "internal_dll_target_usd": 250,
            "daily_loss_limit_usd": 1000,
        }
    }
    # Patch the YAML loader used inside dll_breached
    monkeypatch.setattr(lt, "_load_yaml", lambda _p: fake_yaml)

    snap = {"realized_pl_day_usd": -300.0}
    breached, reason = lt.dll_breached(snap)
    assert breached, (
        f"PATTERN A REGRESSION: dll_breached returned False for day P&L "
        f"-$300 when internal_dll_target_usd=$250. This is the wrong-key "
        f"reading bug from 2026-05-13: the gate read $1000 (Topstep DLL) "
        f"as the primary threshold, letting a third losing bracket fire "
        f"at -$683 day P&L. Reason returned: {reason!r}.\n\n"
        "See vault/lessons/2026-05-13_overnight_dll_breach.md and "
        "CLAUDE.md → 'Pattern A — fail-silent defaults'."
    )
    # The reason should name the internal source so debugging is fast
    assert "internal" in reason.lower(), (
        f"PATTERN A SOFT-REGRESSION: dll_breached fired but didn't "
        f"identify the source as 'internal_dll' in its reason string. "
        f"Reason: {reason!r}. Future incident triage needs the "
        f"source to be obvious; restore the source label."
    )


def test_pattern_a_dll_breached_falls_through_to_topstep_when_internal_zero():
    """Companion: when internal target is missing or zeroed, the gate
    MUST fall through to the Topstep hard limit rather than disabling
    itself. Otherwise a stray config edit could silently turn off the
    DLL check entirely — exactly the failure shape of 2026-04-29 and
    2026-05-05 incidents.
    """
    # Internal missing entirely
    fake_yaml = {"account": {"daily_loss_limit_usd": 1000}}

    snap_under = {"realized_pl_day_usd": -300.0}
    snap_over = {"realized_pl_day_usd": -1100.0}

    import scripts.live_trader as lt_mod
    original_loader = lt_mod._load_yaml
    try:
        lt_mod._load_yaml = lambda _p: fake_yaml
        breached_under, _ = lt_mod.dll_breached(snap_under)
        breached_over, reason_over = lt_mod.dll_breached(snap_over)
    finally:
        lt_mod._load_yaml = original_loader

    assert not breached_under, (
        "Fallback to Topstep failed: -$300 should NOT breach a "
        "$1000 Topstep DLL when internal is absent."
    )
    assert breached_over, (
        "Fallback to Topstep failed: -$1100 SHOULD breach a $1000 "
        "Topstep DLL even when internal_dll_target_usd is missing. "
        "Pattern A: a missing internal field must NOT disable the "
        "outer Topstep guardrail."
    )
    assert "topstep" in reason_over.lower(), (
        "Fallback didn't label the source as 'topstep_dll'; "
        "triage needs the source identified."
    )


# ════════════════════════════════════════════════════════════════════
#  Defensive-ladder projection — pre-trade DLL-projection gate
# ════════════════════════════════════════════════════════════════════
#
# 2026-05-13 followup: even with the post-trade dll_breached gate AND
# the MAX_SIGNAL_RISK pre-trade gate, there's still a window where a
# valid-sized trade can be allowed when it shouldn't be — when the
# trader is already deep in the red and another trade's worst case
# would push past the lockdown threshold. The hook (risk_gate.py)
# already had this projection logic but it doesn't run for live_trader.
# Port: projected_dll_breach() in scripts/live_trader.py.


def test_projected_dll_breach_blocks_when_worst_case_crosses_internal(monkeypatch):
    """If day_pl=-$200 and a proposed trade would risk $150, worst case
    is -$350. Internal DLL is $250 — projection MUST flag breach."""
    fake_yaml = {
        "account": {
            "internal_dll_target_usd": 250,
            "daily_loss_limit_usd": 1000,
        }
    }
    monkeypatch.setattr(lt, "_load_yaml", lambda _p: fake_yaml)

    snap = {"realized_pl_day_usd": -200.0, "unrealized_pl_usd": 0.0}
    breach, reason = lt.projected_dll_breach(snap, signal_risk_usd=150.0)
    assert breach, (
        f"PATTERN A REGRESSION: projection should have flagged a $150 "
        f"trade at day_pl=-$200 against $250 internal DLL. "
        f"Reason returned: {reason!r}. The defensive-ladder projection "
        f"was the encoded defense from hooks/risk_gate that got dropped "
        f"during the auto_trader→live_trader simplification. See "
        f"vault/lessons/2026-05-13_overnight_dll_breach.md."
    )
    assert "internal_dll" in reason.lower(), (
        f"Projection breach didn't label source as internal_dll. "
        f"Reason: {reason!r}"
    )


def test_projected_dll_breach_allows_safe_trade(monkeypatch):
    """Sanity companion: at day_pl=$0 with a $100 risk and $250 internal
    DLL, projection MUST NOT block (worst case = -$100, well above limit).
    If this fails the projection is too aggressive."""
    fake_yaml = {
        "account": {
            "internal_dll_target_usd": 250,
            "daily_loss_limit_usd": 1000,
        }
    }
    monkeypatch.setattr(lt, "_load_yaml", lambda _p: fake_yaml)

    snap = {"realized_pl_day_usd": 0.0, "unrealized_pl_usd": 0.0}
    breach, reason = lt.projected_dll_breach(snap, signal_risk_usd=100.0)
    assert not breach, (
        f"GATE TOO TIGHT: projection blocked a $100 trade at day_pl=$0 "
        f"against $250 internal DLL — worst case -$100 is well above "
        f"the lockdown threshold. Reason: {reason!r}. Check the "
        f"comparison direction in projected_dll_breach()."
    )


def test_projected_dll_breach_uses_unrealized_in_day_pl(monkeypatch):
    """Day P&L for the projection MUST include unrealized — otherwise a
    bleeding open position is invisible to the gate. Mirrors the
    2026-05-05 lesson (`unrealized_pl_usd=0` blinded all projections).

    Setup: realized=-$100, unrealized=-$100 → day_pl=-$200. A $100 risk
    trade would push to -$300, past the $250 internal DLL.
    """
    fake_yaml = {
        "account": {
            "internal_dll_target_usd": 250,
            "daily_loss_limit_usd": 1000,
        }
    }
    monkeypatch.setattr(lt, "_load_yaml", lambda _p: fake_yaml)

    snap = {"realized_pl_day_usd": -100.0, "unrealized_pl_usd": -100.0}
    breach, reason = lt.projected_dll_breach(snap, signal_risk_usd=100.0)
    assert breach, (
        f"PATTERN A REGRESSION: projection ignored unrealized P&L. "
        f"realized=-$100 + unrealized=-$100 + risk=$100 should push "
        f"projected to -$300 vs $250 internal DLL → breach. "
        f"Reason: {reason!r}. See vault/lessons/2026-05-05_*.md "
        f"(`unrealized_pl_usd=0` blinded projections)."
    )


# ════════════════════════════════════════════════════════════════════
#  Pattern A — tick-economics alias coverage  (n=4, 2026-05-14)
# ════════════════════════════════════════════════════════════════════
#
# 2026-05-14 ~20:08 ET: brain emitted a 6E short. Topstep filled the
# contract `CON.F.US.EU6.M26`. tools/profit_protect._contract_to_symbol
# extracted "EU6" from the contract ID, but `_TICK_ECONOMICS` only had
# the "6E" entry — not "EU6". Result: `_resolve_tick_economics("EU6")`
# returned (0,0) at both layers; profit-lock and loss-cap silently
# disabled. The position rode UNPROTECTED for 2h14m. Got lucky:
# realized +$112 vs MFE +$181 vs MAE -$50. Could have been catastrophic.
#
# Pattern A — fail-silent default. The check above logs CRITICAL and
# sends a Discord alert, but does not fail the build. n=4 escalation:
# enforce alias coverage as a build-failing CI invariant.

def test_pattern_a_every_live_filter_symbol_has_tick_economics():
    """Build-failing check that every symbol the brain might emit AND
    every plausible Topstep contract-alias resolves to non-zero tick
    economics.

    Two failure modes guarded:
      1. A symbol in `state/strategy_validation.json:live_strategies_filter`
         emits a signal but `_resolve_tick_economics(symbol)` returns
         (0,0) — would blind profit-lock to live positions.
      2. A Topstep contract-alias variant (e.g. EU6 for 6E) extracted
         by `_contract_to_symbol` from a contract ID returns (0,0).
         This is the 2026-05-14 incident shape exactly.

    If this fails, add the missing alias to
    `tools/profit_protect.py:_TICK_ECONOMICS`. Mirror the empirically
    verified map in `hooks/risk_gate.py:_normalize_root` — that map is
    confirmed live against the broker. See
    `vault/lessons/2026-05-14_eu6_unprotected_position.md` (if added)
    and CLAUDE.md → "Pattern A — fail-silent defaults".
    """
    import json
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools.profit_protect import (
        _resolve_tick_economics, _contract_to_symbol, _strip_exchange_suffix,
    )

    # ── Layer 1: every symbol in live_strategies_filter ──
    val_path = (Path(__file__).resolve().parent.parent /
                "state" / "strategy_validation.json")
    with open(val_path, "r", encoding="utf-8") as f:
        validation = json.load(f)
    live_filter = validation.get("live_strategies_filter") or []
    brain_symbols: set[str] = set()
    for cell in live_filter:
        for sym in (cell.get("symbols") or []):
            if sym:
                brain_symbols.add(sym)
    assert brain_symbols, (
        "TEST FIXTURE STALE: state/strategy_validation.json"
        ":live_strategies_filter contained no symbols. The Pattern A "
        "alias-coverage check is vacuously passing. Investigate."
    )

    missing_brain: list[str] = []
    for sym in sorted(brain_symbols):
        ts, tv = _resolve_tick_economics(sym)
        if not (ts > 0 and tv > 0):
            missing_brain.append(sym)

    assert not missing_brain, (
        f"PATTERN A REGRESSION (n=4): brain-emitted symbol(s) missing "
        f"from tick economics: {missing_brain!r}. With (tick_size, "
        f"tick_value) == (0,0), profit-lock and loss-cap silently "
        f"disable for any open position on that symbol. This is the "
        f"2026-05-14 EU6 incident shape.\n\n"
        f"FIX: add the symbol to `tools/profit_protect.py:_TICK_ECONOMICS` "
        f"or to `config/symbols.yaml`. Verify the tick values against "
        f"the CME contract spec before merging."
    )

    # ── Layer 2: empirically-confirmed Topstep contract aliases ──
    # Sourced from hooks/risk_gate.py:_normalize_root, which is verified
    # against live broker contract IDs. Each alias is encoded as a
    # synthetic contract ID we'd see from `client.get_positions()`. If
    # `_contract_to_symbol → _strip_exchange_suffix → _resolve_tick_economics`
    # returns (0,0) for any of these, we have an unprotected-position
    # bug in the making. Empirical sources cited at each alias.
    confirmed_aliases = [
        # ─ FX (2026-05-14 EU6 incident; brain emits 6E/6B/6J/6A/6C/6M/E7)
        "CON.F.US.EU6.M26",   # → 6E (the 2026-05-14 incident contract)
        "CON.F.US.BP6.M26",   # → 6B
        "CON.F.US.JY6.M26",   # → 6J
        "CON.F.US.DA6.M26",   # → 6A
        "CON.F.US.CA6.M26",   # → 6C
        "CON.F.US.MX6.M26",   # → 6M
        "CON.F.US.EEU.M26",   # → E7
        # ─ Energies (verified hooks/risk_gate)
        "CON.F.US.MCLE.M26",  # → MCL  (4-char suffix; not handled by _strip)
        "CON.F.US.MNGE.M26",  # → MNG
        "CON.F.US.HOE.M26",   # → HO
        "CON.F.US.RBE.M26",   # → RB
        "CON.F.US.CLE.M26",   # → CL   (handled by _strip)
        "CON.F.US.NGE.M26",   # → NG   (handled by _strip)
        # ─ Metals (verified hooks/risk_gate)
        "CON.F.US.GCE.M26",   # → GC   (handled by _strip)
        "CON.F.US.CPE.M26",   # → HG
        # ─ Rates (verified hooks/risk_gate)
        "CON.F.US.TYA.M26",   # → ZN
        "CON.F.US.FVA.M26",   # → ZF
        # ─ Equity index (verified hooks/risk_gate)
        "CON.F.US.EP.M26",    # → ES
        "CON.F.US.ENQ.M26",   # → NQ
        # ─ Grains/livestock (verified hooks/risk_gate)
        "CON.F.US.ZCE.M26",   # → ZC
        "CON.F.US.GLE.M26",   # → LE
        # ─ Other roots seen live
        "CON.F.US.NQG.M26",   # → QG
        "CON.F.US.NQM.M26",   # → QM
        # ─ Native contract IDs (no alias, but live-filter symbols)
        "CON.F.US.MGC.M26",   # → MGC (2026-05-14 same-day fix)
        "CON.F.US.MNQ.M26",   # → MNQ
    ]

    missing_alias: list[tuple[str, str]] = []
    for cid in confirmed_aliases:
        raw = _contract_to_symbol(cid) or ""
        stripped = _strip_exchange_suffix(raw)
        ts, tv = _resolve_tick_economics(stripped)
        if not (ts > 0 and tv > 0):
            missing_alias.append((cid, stripped or raw))

    assert not missing_alias, (
        f"PATTERN A REGRESSION (n=4): Topstep contract alias(es) "
        f"missing from tick economics:\n"
        + "\n".join(f"  {cid} → extracts to {sym!r} → "
                    f"_resolve_tick_economics returned (0,0)"
                    for cid, sym in missing_alias)
        + "\n\nThis is the 2026-05-14 EU6 incident shape: brain emits a "
        "symbol, broker fills under a different contract-root token, "
        "and `_resolve_tick_economics` returns (0,0) → profit-lock + "
        "loss-cap silently disabled. A position can ride UNPROTECTED.\n\n"
        "FIX: add the alias to `tools/profit_protect.py:_TICK_ECONOMICS` "
        "pointing at the same (tick_size, tick_value) tuple as the "
        "canonical symbol. Mirror the map in "
        "`hooks/risk_gate.py:_normalize_root` — that's the empirically-"
        "confirmed source of truth. See "
        "vault/_meta/improvement_backlog.md 'Queued 2026-05-15 — EU6/6E "
        "symbol alias for tick economics' for context."
    )


# ════════════════════════════════════════════════════════════════════
#  Escalation surface for future Pattern incidents
# ════════════════════════════════════════════════════════════════════
#
# When the next Pattern A or B incident occurs (n=4), append a test
# here that reproduces it on synthetic inputs. Each new incident
# raises the floor: anything that broke once must remain detectable
# by a build-failing CI test, forever.
#
# Format:
#   - Name the incident in the docstring (date + slug).
#   - Cross-reference the lesson file.
#   - Make the failure message explicit about what regressed and what
#     the original cost was. Help future Claudes / contributors
#     understand they're looking at a known-bad pattern, not a stylistic
#     preference.
