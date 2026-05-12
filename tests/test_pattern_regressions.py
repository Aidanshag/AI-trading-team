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
    monkeypatch.setattr(lt, "get_db", lambda: _NoOpDB())
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
