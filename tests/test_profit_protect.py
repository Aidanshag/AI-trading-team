"""Unit tests for tools/profit_protect.py — trailing-profit-lock decisions.

Tests target the PURE decision logic (decide function); end-to-end
check_and_close uses fakes for broker interaction.
"""
from __future__ import annotations

import pandas as pd
import pytest

from tools import profit_protect as pp


# ── decide() — pure decision logic ────────────────────────────

def test_decide_no_action_below_first_tier():
    """Unrealized below any tier threshold and within loss/gain caps -> no close."""
    should, reason = pp.decide(unrealized=10.0, prev_peak=10.0)
    assert should is False
    assert reason == ""


def test_decide_no_hard_gain_cap_by_default():
    """2026-05-11: hard cap removed by default (None). Big peaks should
    not auto-close just because they're big — trailing tier governs."""
    # unrealized $500, peak $500 → tier (750, 400) NOT crossed,
    # tier (400, 200) crossed → floor $200, $500 > $200, no close
    should, reason = pp.decide(unrealized=500.0, prev_peak=500.0)
    assert should is False


def test_decide_hard_gain_cap_when_explicitly_set():
    """Caller can still opt into a hard cap by passing gain_cap value."""
    should, reason = pp.decide(unrealized=500.0, prev_peak=500.0, gain_cap=400.0)
    assert should is True
    assert "hard_cap" in reason


def test_decide_hard_loss_cap_closes():
    """Unrealized <= -LOSS_TIER_HARD_CAP_USD -> close."""
    should, reason = pp.decide(unrealized=-200.0, prev_peak=50.0)
    assert should is True
    assert "loss_hard_cap" in reason


def test_software_target_hit_fires_close_position():
    """End-to-end: register a software take-profit target for a contract,
    then run check_and_close with a price that produces unrealized >=
    target. Must call close_position (not place_order) to flatten, AND
    clear the target registry so we don't double-fire next poll.

    This is the critical integration test for the 2026-05-14 software
    take-profit feature — the strategy's target gets honored even though
    we don't place a broker target leg (5/11 anomaly workaround)."""
    # Setup: 1ct MGC long opened at 4700, target unrealized = $30
    pp._position_high_water.clear()
    pp._target_usd_by_contract.clear()
    contract_id = "CON.F.US.MGC.M26"
    pp.register_software_target(contract_id, target_usd=30.0)
    assert pp._target_usd_by_contract[contract_id] == 30.0

    # Mock client: MGC tick=0.10, tick_value=$1.0
    # Long at 4700, current bar at 4703.5 → +3.5 pts = +35 ticks = +$35
    # That's >= $30 target → must close
    client = _FakeClient(
        positions=[{"contractId": contract_id, "size": 1, "type": 1,
                    "averagePrice": 4700.0}],
        bars_by_symbol={"MGC": _FakeBars([4703.5])},
    )
    closed = pp.check_and_close(client, 1, fetch_bars_fn=_fake_fetch)

    # Build-failing assertions
    assert len(closed) == 1, (
        f"target-hit should produce exactly 1 close, got {len(closed)}"
    )
    assert closed[0]["reason"] == "target_hit", (
        f"close reason must be 'target_hit', got {closed[0]['reason']!r}"
    )
    assert client.closed_contracts == [contract_id], (
        f"must use close_position(), not place_order(market). "
        f"close_position calls: {client.closed_contracts}, "
        f"place_order calls: {client.placed}"
    )
    assert client.placed == [], (
        f"target-hit must NOT call place_order (that path is broken at "
        f"Topstep — silent rejection). place_order calls: {client.placed}"
    )
    # Target should be cleared from registry after close
    assert contract_id not in pp._target_usd_by_contract, (
        f"target should be cleared after close to prevent double-fire"
    )


def test_software_target_not_hit_holds_position():
    """Companion: with target=$30 and unrealized only $15, must NOT close."""
    pp._position_high_water.clear()
    pp._target_usd_by_contract.clear()
    contract_id = "CON.F.US.MGC.M26"
    pp.register_software_target(contract_id, target_usd=30.0)

    # +1.5 pts = +15 ticks = +$15 — below $30 target
    client = _FakeClient(
        positions=[{"contractId": contract_id, "size": 1, "type": 1,
                    "averagePrice": 4700.0}],
        bars_by_symbol={"MGC": _FakeBars([4701.5])},
    )
    closed = pp.check_and_close(client, 1, fetch_bars_fn=_fake_fetch)
    assert closed == [], "should not close — unrealized $15 < target $30"
    assert client.closed_contracts == [], "should not have called close_position"
    # Target STAYS in registry for the next poll
    assert pp._target_usd_by_contract.get(contract_id) == 30.0


def test_software_target_registration_and_clear():
    """register_software_target adds, _clear_software_target removes.
    2026-05-14 take-profit-at-target feature."""
    pp._target_usd_by_contract.clear()
    pp.register_software_target("CON.TEST", 50.0)
    assert pp._target_usd_by_contract["CON.TEST"] == 50.0
    pp._clear_software_target("CON.TEST")
    assert "CON.TEST" not in pp._target_usd_by_contract
    # Zero/negative targets are ignored
    pp.register_software_target("CON.TEST", 0.0)
    pp.register_software_target("CON.TEST", -10.0)
    assert "CON.TEST" not in pp._target_usd_by_contract


def test_decide_continuous_floor_at_50_peak():
    """Peak $50 → continuous floor = max($20, $50 * 0.70) = $35.
    Current $-5 < $35 → close.
    Updated 2026-05-15: static tier table (40, 18) replaced by continuous
    percent-of-peak retracement. Old behavior: floor $18. New: floor $35.
    Captures $17 more of peak profit per the user-noted leakage incident."""
    should, reason = pp.decide(unrealized=-5.0, prev_peak=50.0)
    assert should is True
    assert "trailing_lock" in reason
    assert "$50" in reason   # peak shown
    assert "$35" in reason   # continuous floor


def test_decide_continuous_floor_at_160_peak():
    """Peak $160 → continuous floor = $160 * 0.70 = $112.
    Current $40 < $112 → close.
    Updated 2026-05-15: old (150, 50) tier gave floor $50; new continuous
    rule floors at $112 — captures $62 more of the run."""
    should, reason = pp.decide(unrealized=40.0, prev_peak=160.0)
    assert should is True
    assert "$112" in reason  # continuous floor at 30% retrace


def test_decide_peak_below_min_floor_no_lock():
    """Peak only reached $10 — below MIN_PEAK_FOR_FLOOR_USD ($20).
    No floor; trade can wander negative without auto-close (broker stop
    still protects).
    Updated 2026-05-15: was $15 (old micro-tier threshold), now $20."""
    should, reason = pp.decide(unrealized=-3.0, prev_peak=10.0)
    assert should is False  # below min-floor threshold, loss cap not breached


def test_decide_continuous_floor_at_300_peak():
    """Peak $300 → continuous floor = $300 * 0.70 = $210.
    Current $80 < $210 → close.
    Updated 2026-05-15: old (250, 100) tier gave floor $100; new continuous
    rule floors at $210 — much tighter protection of mid-size winners."""
    should, reason = pp.decide(unrealized=80.0, prev_peak=300.0)
    assert should is True
    assert "$210" in reason  # continuous floor


def test_decide_above_active_floor_no_close():
    """Peak $300, continuous floor $210. Current $220 > $210 → no close.
    Updated 2026-05-15: was current=$120 vs $100 floor; new floor is
    $210 so the test value needed to rise to stay above floor."""
    should, reason = pp.decide(unrealized=220.0, prev_peak=300.0)
    assert should is False


# ── Continuous percent-of-peak retracement (2026-05-15) ─────────

def test_continuous_floor_at_25_peak_pins_to_min():
    """Peak $25 → $25 * 0.70 = $17.50 < MIN_PEAK_FOR_FLOOR_USD ($20).
    Floor clamps to $20."""
    floor = pp._compute_active_floor(prev_peak=25.0)
    assert floor == 20.0


def test_continuous_floor_at_50_peak():
    """Peak $50 → max($20, $50 * 0.70) = $35."""
    floor = pp._compute_active_floor(prev_peak=50.0)
    assert floor == 35.0


def test_continuous_floor_at_100_peak():
    """Peak $100 → max($20, $70) = $70."""
    floor = pp._compute_active_floor(prev_peak=100.0)
    assert floor == 70.0


def test_continuous_floor_at_200_peak():
    """Peak $200 → max($20, $140) = $140."""
    floor = pp._compute_active_floor(prev_peak=200.0)
    assert floor == 140.0


def test_continuous_floor_at_500_peak():
    """Peak $500 → max($20, $350) = $350."""
    floor = pp._compute_active_floor(prev_peak=500.0)
    assert floor == 350.0


def test_continuous_floor_at_750_boundary():
    """Peak $750 is the boundary: continuous formula gives $525.
    The runner-zone tier (750, 525) gives the same — continuous design."""
    floor = pp._compute_active_floor(prev_peak=750.0)
    assert floor == 525.0


def test_runner_zone_at_800_peak():
    """Peak just over $750 enters runner zone. Tier (750, 525) is the
    only crossed tier — floor $525. Matches the continuous formula at
    the boundary, then loosens at higher tiers."""
    floor = pp._compute_active_floor(prev_peak=800.0)
    assert floor == 525.0


def test_below_min_peak_no_floor():
    """Peak $15 < MIN_PEAK_FOR_FLOOR_USD ($20): returns None (no floor)."""
    floor = pp._compute_active_floor(prev_peak=15.0)
    assert floor is None


def test_user_incident_peak_113_now_floors_at_79():
    """Regression-guard for the user-noted give-back incident:
    overnight 2026-05-14, a trade peaked at +$113 and gave back to +$29
    under the old static tiers — the (70, 32) tier was the active floor.
    Under the new continuous rule, peak $113 floors at $113 * 0.70 = $79.10.
    A retrace to $50 (still well above $29) now CLOSES the trade,
    locking in 70% of peak instead of letting it bleed to 25%."""
    floor = pp._compute_active_floor(prev_peak=113.0)
    assert abs(floor - 79.10) < 0.01
    # Trade retraces to $50 — should close under new rule.
    should, reason = pp.decide(unrealized=50.0, prev_peak=113.0)
    assert should is True
    assert "$79" in reason  # continuous floor


# ── Runner-zone tiers (2026-05-11 expansion) ──────────────────

def test_decide_runner_tier_2500_locks_1500():
    """Peak $2700 crosses (2500, 1500) tier. Current $1400 < $1500 → close."""
    should, reason = pp.decide(unrealized=1400.0, prev_peak=2700.0)
    assert should is True
    assert "$1500" in reason  # floor


def test_decide_runner_tier_5000_locks_3000():
    """Peak $5500 crosses (5000, 3000) tier. Current $2900 < $3000 → close."""
    should, reason = pp.decide(unrealized=2900.0, prev_peak=5500.0)
    assert should is True
    assert "$3000" in reason


def test_decide_giant_winner_can_run():
    """Today's GC trade peaked at +$2,616. With current $2,000 (still
    >$1500 floor for the $2500 tier), no close — let it run."""
    should, reason = pp.decide(unrealized=2000.0, prev_peak=2616.0)
    assert should is False


def test_decide_giant_winner_closes_on_proper_retracement():
    """Same GC peak ($2616). Current drops to $1200 < $1500 → close
    on the (2500, 1500) tier. Tightest active floor wins even when
    multiple tiers are crossed."""
    should, reason = pp.decide(unrealized=1200.0, prev_peak=2616.0)
    assert should is True
    assert "$1500" in reason


# ── check_and_close() — end-to-end with fake broker ───────────

class _FakeBars:
    """Minimal bars stand-in: just exposes a Close series."""
    def __init__(self, prices):
        self._df = pd.DataFrame({"Close": prices})
    def __len__(self):
        return len(self._df)
    def __getitem__(self, key):
        return self._df[key]


class _FakeClient:
    def __init__(self, positions, bars_by_symbol):
        self._positions = positions
        self._bars = bars_by_symbol
        self.placed: list[dict] = []
        self.closed_contracts: list[str] = []
    def get_positions(self, account_id):
        return self._positions
    def place_order(self, **kwargs):
        self.placed.append(kwargs)
        return {"orderId": 999, "success": True}
    def close_position(self, account_id, contract_id):
        # 2026-05-14: profit-lock + loss-cap now use this endpoint instead
        # of place_order(market-IOC) — broker rejects market-IOC because
        # type=1 in Topstep's schema means LIMIT not MARKET.
        self.closed_contracts.append(contract_id)
        return {"success": True, "errorCode": 0, "errorMessage": None}
    def get_working_orders(self, account_id):
        return []


def _fake_fetch(client, symbol, minutes, lookback):
    return client._bars.get(symbol)


def setup_function(_):
    """Reset high-water dict between tests so state doesn't leak."""
    pp._position_high_water.clear()


def test_check_and_close_no_positions_returns_empty():
    client = _FakeClient(positions=[], bars_by_symbol={})
    closed = pp.check_and_close(client, account_id=1, fetch_bars_fn=_fake_fetch)
    assert closed == []
    assert client.placed == []


def test_check_and_close_lets_big_winner_run():
    """2026-05-11: hard cap removed. GC long at 4750, now 4790 = +$4000.
    Without hard cap, position should NOT auto-close — trailing tier
    floor at $1500 is well below current. Let it run."""
    client = _FakeClient(
        positions=[{"contractId": "CON.F.US.GCE.M26", "size": 1, "type": 1,
                    "averagePrice": 4750.0}],
        bars_by_symbol={"GC": _FakeBars([4790.0])},
    )
    closed = pp.check_and_close(client, 1, fetch_bars_fn=_fake_fetch)
    assert closed == []  # no close: $4000 unrealized > $1500 floor
    assert client.placed == []
    # Peak captured for next-scan trailing logic
    assert pp._position_high_water.get("GC_long", 0) == pytest.approx(4000, abs=1)


def test_check_and_close_closes_runaway_after_retracement():
    """Same setup but two scans: first push to $4000 peak, then drop to
    $1000 — below the (2500, 1500) tier floor → close."""
    client = _FakeClient(
        positions=[{"contractId": "CON.F.US.GCE.M26", "size": 1, "type": 1,
                    "averagePrice": 4750.0}],
        bars_by_symbol={"GC": _FakeBars([4790.0])},  # +$4000
    )
    pp.check_and_close(client, 1, fetch_bars_fn=_fake_fetch)
    assert pp._position_high_water["GC_long"] >= 3999
    client._bars["GC"] = _FakeBars([4760.0])  # +10 pts = +$1000
    closed = pp.check_and_close(client, 1, fetch_bars_fn=_fake_fetch)
    assert len(closed) == 1
    assert closed[0]["unrealized"] <= 1100
    assert "trailing_lock" in closed[0]["reason"]
    # 2026-05-14: closes now go through close_position endpoint, not place_order
    assert client.closed_contracts == ["CON.F.US.GCE.M26"]


def test_check_and_close_locks_breakeven_after_30_peak():
    """Sim two calls: first push unrealized to +$50 (peak captured),
    then drop to -$5 -> trailing lock fires (never let gain become loss).

    GC tick=0.10, tick_value=$10. +5 ticks = +$50. So bar 4750.5 = +$50."""
    client = _FakeClient(
        positions=[{"contractId": "CON.F.US.GCE.M26", "size": 1, "type": 1,
                    "averagePrice": 4750.0}],
        bars_by_symbol={"GC": _FakeBars([4750.5])},  # +0.5 pts = +5 ticks = +$50
    )
    # First check: peak captured, no close
    pp.check_and_close(client, 1, fetch_bars_fn=_fake_fetch)
    assert client.placed == []
    # Second check: price drops to -$5 -> close
    client._bars["GC"] = _FakeBars([4749.95])  # -0.05 pts = -0.5 ticks = -$5
    closed = pp.check_and_close(client, 1, fetch_bars_fn=_fake_fetch)
    assert len(closed) == 1
    assert "trailing_lock" in closed[0]["reason"]
    # 2026-05-14: closes now go through close_position endpoint
    assert client.closed_contracts == ["CON.F.US.GCE.M26"]


def test_check_and_close_short_position_math():
    """Short MNQ: avg 29500, now 29490 = +10 pts profit on short. With MNQ
    tick=0.25 value=$0.50: 40 ticks × $0.50 = +$20. Below $30 tier so no
    close yet but high-water captured correctly."""
    client = _FakeClient(
        positions=[{"contractId": "CON.F.US.MNQ.M26", "size": 1, "type": 2,
                    "averagePrice": 29500.0}],
        bars_by_symbol={"MNQ": _FakeBars([29490.0])},
    )
    closed = pp.check_and_close(client, 1, fetch_bars_fn=_fake_fetch)
    assert closed == []
    # Peak captured
    assert pp._position_high_water.get("MNQ_short", 0) == pytest.approx(20.0, abs=0.01)


# ── Regression guard: profit-lock close primitive (2026-05-15) ─

def test_profit_lock_close_uses_close_position_not_limit_order():
    """Hard regression guard against the 13-rejected-LIMIT-order incident
    (2026-05-13/14) — see `vault/_meta/improvement_backlog.md` + memory
    `project_broker_order_semantics.md`.

    The pre-fix code path used `place_order(order_type="market", ioc, tag=
    "profitlock_*")` which Topstep's schema treats as a LIMIT (type=1)
    and rejects with "limit price not set" — across 2026-05-13/14 this
    cost 13 missed profit-lock fires. Fix landed at commit 326ab7f.

    This test asserts the primitive used to flatten a profit-locked
    position is `close_position`, NOT `place_order(...)` with any limit-
    type or profitlock_* tag. If a future refactor reintroduces the bad
    path, this test breaks the build before it can ship."""
    pp._position_high_water.clear()
    pp._target_usd_by_contract.clear()
    contract_id = "CON.F.US.GCE.M26"
    client = _FakeClient(
        positions=[{"contractId": contract_id, "size": 1, "type": 1,
                    "averagePrice": 4750.0}],
        bars_by_symbol={"GC": _FakeBars([4790.0])},  # +$4000 peak
    )
    # Scan 1: peak captured, no close yet.
    pp.check_and_close(client, 1, fetch_bars_fn=_fake_fetch)
    assert pp._position_high_water["GC_long"] >= 3999
    # Scan 2: drop below tier floor → trailing_lock fires.
    client._bars["GC"] = _FakeBars([4760.0])    # +$1000 < $1500 floor
    closed = pp.check_and_close(client, 1, fetch_bars_fn=_fake_fetch)

    # === Build-failing assertions ===
    assert len(closed) == 1, (
        f"profit-lock should fire exactly once after retracement, got "
        f"{len(closed)} closes"
    )
    assert "trailing_lock" in closed[0]["reason"], (
        f"close reason must be trailing_lock, got {closed[0]['reason']!r}"
    )
    # Primary assertion: close_position was the primitive used.
    assert client.closed_contracts == [contract_id], (
        f"profit-lock close MUST use client.close_position(). "
        f"close_position calls: {client.closed_contracts}"
    )
    # Negative assertion: NO place_order call with a profitlock_* tag OR
    # any limit-typed flatten attempt. (The fake client records every
    # place_order call as a dict of kwargs.)
    for kwargs in client.placed:
        tag = str(kwargs.get("client_order_id") or "")
        otype = str(kwargs.get("order_type") or "")
        assert not tag.startswith("profitlock_"), (
            f"REGRESSION: place_order called with profitlock_* tag — "
            f"this is the 2026-05-13/14 broker-rejection path that was "
            f"fixed in commit 326ab7f. kwargs={kwargs}"
        )
        assert otype != "limit" or not tag.startswith("profitlock"), (
            f"REGRESSION: profit-lock close used a LIMIT order, broker "
            f"rejects these. kwargs={kwargs}"
        )


def test_profit_lock_close_writes_decisions_row():
    """Audit-trail guard: when profit-lock fires a close, a `decisions`
    row must be recorded so the close is auditable (close_position
    doesn't produce an orders-table row the way the old place_order
    path did).

    Uses an in-memory sqlite DB monkey-patched into state.db.get_db so
    the test doesn't touch fund.db. Asserts a decisions row exists with
    agent='profit_lock' and kind='close' after the trailing_lock fires."""
    import sqlite3
    pp._position_high_water.clear()
    pp._target_usd_by_contract.clear()

    # Build an in-memory DB with the same `decisions` schema the real
    # fund.db uses (see state/schema.sql). Just the columns record_decision
    # writes — kept minimal to avoid a heavy schema-import dep.
    test_conn = sqlite3.connect(":memory:")
    test_conn.execute("""
        CREATE TABLE decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            agent TEXT NOT NULL,
            kind TEXT NOT NULL,
            symbol TEXT,
            summary TEXT,
            rationale TEXT,
            vault_path TEXT,
            model TEXT,
            tokens_in INTEGER,
            tokens_out INTEGER
        )
    """)
    test_conn.commit()

    # Monkey-patch get_db() so _record_close_decision writes to test_conn.
    import state.db as db_mod
    real_get_db = db_mod.get_db

    class _StubDB:
        def record_decision(self, agent, kind, summary, rationale, *,
                              symbol=None, vault_path=None, model=None,
                              tokens_in=None, tokens_out=None):
            from datetime import datetime, timezone
            cur = test_conn.execute(
                """INSERT INTO decisions
                    (ts, agent, kind, symbol, summary, rationale, vault_path,
                     model, tokens_in, tokens_out)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (datetime.now(tz=timezone.utc).isoformat(), agent, kind, symbol,
                 summary, rationale, vault_path, model, tokens_in, tokens_out),
            )
            test_conn.commit()
            return int(cur.lastrowid or 0)

    db_mod.get_db = lambda: _StubDB()
    try:
        contract_id = "CON.F.US.GCE.M26"
        client = _FakeClient(
            positions=[{"contractId": contract_id, "size": 1, "type": 1,
                        "averagePrice": 4750.0}],
            bars_by_symbol={"GC": _FakeBars([4790.0])},  # +$4000 peak
        )
        pp.check_and_close(client, 1, fetch_bars_fn=_fake_fetch)
        client._bars["GC"] = _FakeBars([4760.0])
        closed = pp.check_and_close(client, 1, fetch_bars_fn=_fake_fetch)

        assert len(closed) == 1
        rows = test_conn.execute(
            "SELECT agent, kind, symbol FROM decisions WHERE agent=?",
            ("profit_lock",),
        ).fetchall()
        assert len(rows) == 1, (
            f"expected exactly one decisions row from profit_lock, got "
            f"{len(rows)}: {rows}"
        )
        assert rows[0] == ("profit_lock", "close", "GC"), (
            f"decisions row content unexpected: {rows[0]}"
        )
    finally:
        db_mod.get_db = real_get_db
        test_conn.close()


# ── Reversal-detection exit (2026-05-15, exit-roadmap step 4) ────

def test_detect_reversal_long_3_lower_closes_returns_true():
    """LONG with 3 strictly-descending closes (4700 → 4699 → 4698) = reversal."""
    bars = _FakeBars([4701.0, 4700.5, 4700.0, 4699.0, 4698.0])
    assert pp._detect_reversal("long", bars) is True


def test_detect_reversal_short_3_higher_closes_returns_true():
    """SHORT with 3 strictly-ascending closes = reversal."""
    bars = _FakeBars([4700.0, 4700.5, 4701.0, 4702.0, 4703.0])
    assert pp._detect_reversal("short", bars) is True


def test_detect_reversal_long_2_lower_closes_returns_false():
    """LONG with only 2 lower closes — not enough evidence."""
    # closes: 4700, 4699, 4700.5 — only one lower close in last 3
    bars = _FakeBars([4700.0, 4699.0, 4700.5])
    assert pp._detect_reversal("long", bars) is False


def test_detect_reversal_long_3_higher_closes_returns_false():
    """LONG with 3 HIGHER closes — that's WITH the position, not against."""
    bars = _FakeBars([4698.0, 4699.0, 4700.0, 4701.0, 4702.0])
    assert pp._detect_reversal("long", bars) is False


def test_detect_reversal_insufficient_bars_returns_false():
    """Fewer than REVERSAL_BARS_REQUIRED bars — no signal."""
    bars = _FakeBars([4700.0, 4699.0])  # only 2 bars, need 3
    assert pp._detect_reversal("long", bars) is False


def test_detect_reversal_flat_close_returns_false():
    """Strictly-descending required — flat closes don't trigger.
    closes 4700, 4700, 4700 — not strictly lower → no reversal."""
    bars = _FakeBars([4700.0, 4700.0, 4700.0])
    assert pp._detect_reversal("long", bars) is False


def test_check_and_close_fires_reversal_exit_on_long():
    """End-to-end: long position with peak $40, then 3 strictly-descending
    1-min closes → REVERSAL_EXIT fires close_position.

    First call uses ASCENDING bars to push peak to $40 without triggering
    reversal (peak-set call). Second call uses descending bars to trigger.
    """
    pp._position_high_water.clear()
    pp._target_usd_by_contract.clear()
    contract_id = "CON.F.US.MGC.M26"
    # MGC math: tick=$0.10, tick_value=$1.00 → 1pt = 10ticks = $10.
    # 4700 → 4704 = +$40
    client = _FakeClient(
        positions=[{"contractId": contract_id, "size": 1, "type": 1,
                    "averagePrice": 4700.0}],
        # Ascending closes — peak gets pushed to +$40, but the last 3
        # closes are strictly INCREASING (not against the long) → no reversal.
        bars_by_symbol={"MGC": _FakeBars([4700.5, 4701.5, 4702.5, 4703.5, 4704.0])},
    )
    pp.check_and_close(client, 1, fetch_bars_fn=_fake_fetch)
    assert pp._position_high_water["MGC_long"] == pytest.approx(40.0, abs=1.0), (
        f"peak should be $40 from 4704 close, got "
        f"{pp._position_high_water.get('MGC_long')}"
    )
    # Now feed 3 strictly descending closes — reversal pattern, peak >= $15
    client._bars["MGC"] = _FakeBars([4703.5, 4703.0, 4702.5])
    closed = pp.check_and_close(client, 1, fetch_bars_fn=_fake_fetch)
    assert len(closed) == 1, (
        f"expected REVERSAL_EXIT to fire 1 close, got {len(closed)}"
    )
    assert closed[0]["reason"] == "reversal_exit", (
        f"reason should be 'reversal_exit', got {closed[0]['reason']!r}"
    )
    assert client.closed_contracts == [contract_id], (
        f"must use close_position, got close_position={client.closed_contracts} "
        f"place_order={client.placed}"
    )
    assert client.placed == [], (
        f"must NOT use place_order, got {client.placed}"
    )


def test_check_and_close_skips_reversal_below_min_peak():
    """If peak < REVERSAL_MIN_PEAK_USD ($15), reversal pattern is ignored.
    Avoids false exits on noisy small wins where bar-to-bar wobble is normal."""
    pp._position_high_water.clear()
    contract_id = "CON.F.US.MGC.M26"
    # Push peak to only $10 (below the $15 floor for reversal)
    client = _FakeClient(
        positions=[{"contractId": contract_id, "size": 1, "type": 1,
                    "averagePrice": 4700.0}],
        # +$1 — peak only $10 (MGC: 1 pt = $10? No — 1 pt = 10t × $1/tick = $10)
        # 4700 → 4701 = +$10 unrealized
        bars_by_symbol={"MGC": _FakeBars([4701.0])},
    )
    pp.check_and_close(client, 1, fetch_bars_fn=_fake_fetch)
    assert pp._position_high_water["MGC_long"] == pytest.approx(10.0, abs=1.0)
    # Now feed 3 lower closes — reversal pattern but peak too small
    client._bars["MGC"] = _FakeBars([4700.8, 4700.5, 4700.2])
    closed = pp.check_and_close(client, 1, fetch_bars_fn=_fake_fetch)
    # Reversal should NOT have fired (peak < $15). May or may not close
    # on other rules (loss cap or trailing), but the reason must NOT be
    # reversal_exit.
    for c in closed:
        assert c["reason"] != "reversal_exit", (
            f"reversal_exit fired below MIN peak ($10 < $15): {c}"
        )


# ── Time-based profit decay (2026-05-15, exit-roadmap step 6) ──

def test_is_profit_stale_both_conditions_met_returns_true():
    """Peak hit >15 min ago AND current is below peak by >30% → True."""
    from datetime import datetime, timezone, timedelta
    now = datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
    peak_ts = now - timedelta(minutes=20)  # 20 min stale
    # peak $80, current $50 (37% retrace) → > 30% threshold
    assert pp._is_profit_stale(peak=80.0, peak_ts=peak_ts,
                                  current=50.0, now=now) is True


def test_is_profit_stale_within_time_window_returns_false():
    """Peak hit <15 min ago — too fresh to call stale even with retrace."""
    from datetime import datetime, timezone, timedelta
    now = datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
    peak_ts = now - timedelta(minutes=5)  # only 5 min
    assert pp._is_profit_stale(peak=80.0, peak_ts=peak_ts,
                                  current=50.0, now=now) is False


def test_is_profit_stale_insufficient_retrace_returns_false():
    """Peak hit 20 min ago BUT current still within 30% of peak."""
    from datetime import datetime, timezone, timedelta
    now = datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
    peak_ts = now - timedelta(minutes=20)
    # peak $80, current $60 — 25% retrace, below 30% threshold
    assert pp._is_profit_stale(peak=80.0, peak_ts=peak_ts,
                                  current=60.0, now=now) is False


def test_is_profit_stale_handles_none_peak_ts():
    """Defensive: missing peak_ts returns False without crashing."""
    assert pp._is_profit_stale(peak=80.0, peak_ts=None, current=40.0) is False


def test_is_profit_stale_handles_negative_peak():
    """Defensive: peak <= 0 returns False (no decay rule for losers)."""
    from datetime import datetime, timezone, timedelta
    now = datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
    peak_ts = now - timedelta(minutes=20)
    assert pp._is_profit_stale(peak=0.0, peak_ts=peak_ts,
                                  current=-10.0, now=now) is False


def test_is_profit_stale_fires_on_small_peak_below_continuous_floor():
    """KEY VALUE-ADD over percent-of-peak: time-based fires on sub-$20
    peaks where percent-of-peak intentionally returns no floor.
    Peak $10, stale 20 min, retraced to $5 (50% retrace) → close.
    Percent-of-peak would do nothing here (peak below MIN_PEAK)."""
    from datetime import datetime, timezone, timedelta
    now = datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
    peak_ts = now - timedelta(minutes=20)
    # percent-of-peak: peak $10 < $20 MIN → returns None
    assert pp._compute_active_floor(prev_peak=10.0) is None
    # but time-decay catches it
    assert pp._is_profit_stale(peak=10.0, peak_ts=peak_ts,
                                  current=5.0, now=now) is True


def test_check_and_close_time_decay_clears_peak_ts():
    """After a close, _position_peak_ts must be cleared so the next
    position on the same key starts fresh."""
    from datetime import datetime, timezone, timedelta
    pp._position_high_water.clear()
    pp._position_peak_ts.clear()
    pp._target_usd_by_contract.clear()
    contract_id = "CON.F.US.MGC.M26"
    # Seed peak directly to avoid two scan calls
    pp._position_high_water["MGC_long"] = 50.0
    pp._position_peak_ts["MGC_long"] = datetime.now(tz=timezone.utc) - timedelta(minutes=20)
    # Now current at +$25 (50% retrace from peak $50)
    client = _FakeClient(
        positions=[{"contractId": contract_id, "size": 1, "type": 1,
                    "averagePrice": 4700.0}],
        bars_by_symbol={"MGC": _FakeBars([4702.5])},  # +$25 unrealized
    )
    closed = pp.check_and_close(client, 1, fetch_bars_fn=_fake_fetch)
    assert len(closed) == 1
    assert closed[0]["reason"] == "time_decay_exit", (
        f"expected time_decay_exit, got {closed[0]['reason']!r}"
    )
    assert client.closed_contracts == [contract_id]
    # State cleared
    assert "MGC_long" not in pp._position_high_water
    assert "MGC_long" not in pp._position_peak_ts


def test_check_and_close_reversal_uses_close_position_not_place_order():
    """Regression-guard mirroring test_software_target — reversal_exit must
    use the close_position endpoint, not place_order. The latter was the
    known-broken path that caused profitlock_* rejections (2026-05-13/14).
    This guards against the same regression in the new exit path."""
    pp._position_high_water.clear()
    contract_id = "CON.F.US.MGC.M26"
    # Push peak to $30 (above min) then trigger reversal
    client = _FakeClient(
        positions=[{"contractId": contract_id, "size": 1, "type": 1,
                    "averagePrice": 4700.0}],
        bars_by_symbol={"MGC": _FakeBars([4703.0])},  # +$30 peak
    )
    pp.check_and_close(client, 1, fetch_bars_fn=_fake_fetch)
    client._bars["MGC"] = _FakeBars([4702.5, 4702.0, 4701.5])
    closed = pp.check_and_close(client, 1, fetch_bars_fn=_fake_fetch)
    assert closed[0]["reason"] == "reversal_exit"
    assert client.closed_contracts == [contract_id]
    # Critical: no place_order call with limit-marketable tag pattern
    for call in client.placed:
        tag = call.get("client_order_id") or ""
        assert "reversal" not in tag.lower(), (
            f"reversal_exit must use close_position, not place_order: {call}"
        )
