"""Tests for the queue-consumer path in live_trader.

Confirms `consume_pending_signals` applies the same last-mile safety
gates as the legacy `scan_once` and that the queue is actually drained.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts import live_trader as lt  # noqa: E402
from tools import signal_queue as sq  # noqa: E402


class _StubBroker:
    """Minimal stub: get_accounts/get_positions/place_order/front_month."""

    def __init__(self, balance=51568.71, can_trade=True, positions=None):
        self._balance = balance
        self._can_trade = can_trade
        self._positions = positions or []
        self.place_order_calls = []
        self.cancel_order_calls = []
        # Signature flip after first place_order so _wait_for_entry_fill returns True
        self._fill_triggered = False

    def get_accounts(self):
        return [{"id": 1, "balance": self._balance,
                 "canTrade": self._can_trade}]

    def get_positions(self, account_id):
        if self._fill_triggered:
            return [{"contractId": "CON.F.US.MNQ.M26", "size": 1,
                     "type": 1, "averagePrice": 21500.0}]
        return self._positions

    def get_working_orders(self, account_id):
        # Return the stop order as "landed" so _verify_stop_landed passes
        return [{"customTag": call.get("client_order_id")}
                for call in self.place_order_calls
                if call.get("order_type") == "stop"]

    def front_month_contract_id(self, symbol):
        return f"CON.F.US.{symbol}.M26"

    def place_order(self, **kwargs):
        self.place_order_calls.append(dict(kwargs))
        # Trigger position-fill after the entry order goes in
        if kwargs.get("order_type") == "limit":
            self._fill_triggered = True
        return {"success": True, "orderId": f"mock_{len(self.place_order_calls)}"}

    def cancel_order(self, account_id, order_id):
        self.cancel_order_calls.append({"account_id": account_id,
                                          "order_id": order_id})
        return {"success": True}


@pytest.fixture
def tmp_queue(monkeypatch, tmp_path):
    fake = tmp_path / "pending_signals.json"
    monkeypatch.setattr(sq, "QUEUE_PATH", fake)
    return fake


@pytest.fixture
def stub_environment(monkeypatch, tmp_queue):
    """Patch broker + DB + snapshot + halt-state for a clean test env."""
    broker = _StubBroker()
    monkeypatch.setattr(lt, "get_client", lambda: broker)
    monkeypatch.setattr(lt, "get_account_id", lambda: 1)
    # Snapshot writer: return a healthy snap, write nothing
    monkeypatch.setattr(lt, "capture_snapshot",
                          lambda c, a: {"can_trade": True,
                                          "open_contracts_total": 0,
                                          "balance_usd": 51568.71,
                                          "realized_pl_day_usd": 0.0,
                                          "unrealized_pl_usd": 0.0,
                                          "trailing_dd_usd": 0.0})
    # Not halted, not Sunday blackout
    monkeypatch.setattr(lt, "is_halted", lambda: (False, ""))
    monkeypatch.setattr(lt, "is_sunday_reopen_blackout", lambda _now: False)
    # No prior trades today
    monkeypatch.setattr(lt, "todays_trade_count", lambda: 0)
    monkeypatch.setattr(lt, "recent_thesis_for", lambda _s: False)
    # Skip hard-flatten window
    import tools.hard_flatten_clock as hfc
    monkeypatch.setattr(hfc, "should_block_new_entries", lambda: False)
    monkeypatch.setattr(hfc, "enforce_hard_flatten",
                          lambda c, a, log_fn=None: {"flattened": [],
                                                       "cancelled": 0,
                                                       "window": "outside"})
    # DB no-ops
    class _DB:
        def execute(self, *a, **k): return self
        def fetchone(self): return None
        def commit(self): pass
        def cursor(self): return self
        def connect(self): return self
        def record_shadow_trade(self, **k): pass
    monkeypatch.setattr(lt, "get_db", lambda: _DB())
    # Speed up fill polling so tests are fast
    monkeypatch.setattr(lt, "FILL_WAIT_TIMEOUT_S", 1)
    monkeypatch.setattr(lt, "FILL_WAIT_POLL_S", 1)
    # cleanup_orphan_brackets no-op
    monkeypatch.setattr(lt, "cleanup_orphan_brackets",
                          lambda c, a: 0)
    return broker


def _enqueue_sig(**overrides):
    base = {
        "symbol": "MNQ", "side": "long",
        "entry_price": 21500.0, "stop_price": 21490.0,
        "target_price": 21520.0,
        "strategy": "fair_value_gap", "session": "Asian",
        "cell_key": "fair_value_gap|MNQ|Asian|long",
    }
    base.update(overrides)
    sig = sq.make_signal(**base)
    sq.enqueue(sig)
    return sig


def test_consume_empty_queue_returns_status(stub_environment):
    result = lt.consume_pending_signals()
    assert result.get("status") == "empty_queue"


def test_consume_places_safe_signal(stub_environment):
    _enqueue_sig()
    result = lt.consume_pending_signals()
    # Either placed, or hit some downstream check that's outside the gate
    # surface — but at minimum we should have consumed and not blocked.
    assert result.get("consumed", 0) == 1, (
        f"queue consumer didn't drain the queue: {result}"
    )
    assert result.get("blocked", 0) == 0, (
        f"safe signal was blocked: {result}"
    )


def test_consume_blocks_oversized_risk(stub_environment):
    # GC: tick=0.10, tick_value=$10. 70-tick stop = $700 risk → over $150 cap
    _enqueue_sig(
        symbol="GC", strategy="narrow_range_break",
        entry_price=4716.5, stop_price=4709.5,  # 7 points = 70 ticks = $700
        cell_key="narrow_range_break|GC|Asian|long",
    )
    result = lt.consume_pending_signals()
    assert result.get("consumed", 0) == 1
    assert result.get("blocked", 0) == 1, (
        f"queue consumer didn't block oversized risk: {result}"
    )
    # Most importantly: no broker order should have been placed
    broker = stub_environment
    assert len(broker.place_order_calls) == 0, (
        f"PATTERN B REGRESSION on queue path: broker received "
        f"place_order calls for a signal that should have been blocked. "
        f"calls={broker.place_order_calls}"
    )


def test_consume_blocks_sub_floor_stop(stub_environment):
    # 1-tick stop on MNQ (0.25 tick) → fails MIN_SIGNAL_R_TICKS=6 gate
    _enqueue_sig(
        entry_price=21500.0, stop_price=21500.25,  # 1 tick only
    )
    result = lt.consume_pending_signals()
    assert result.get("blocked", 0) == 1


def test_consume_blocks_when_dll_breach_projected(stub_environment, monkeypatch):
    # Already at -$200, $100 risk would push to -$300 vs $250 internal DLL
    monkeypatch.setattr(lt, "capture_snapshot",
                          lambda c, a: {"can_trade": True,
                                          "open_contracts_total": 0,
                                          "balance_usd": 50000.0,
                                          "realized_pl_day_usd": -200.0,
                                          "unrealized_pl_usd": 0.0,
                                          "trailing_dd_usd": 200.0})
    # MNQ tick_value $0.50, want 200 ticks = $100 → entry-stop = 200 × 0.25 = 50
    _enqueue_sig(entry_price=21500.0, stop_price=21450.0)
    result = lt.consume_pending_signals()
    assert result.get("blocked", 0) == 1


def test_consume_skips_when_in_position(stub_environment, monkeypatch):
    monkeypatch.setattr(lt, "capture_snapshot",
                          lambda c, a: {"can_trade": True,
                                          "open_contracts_total": 1,
                                          "balance_usd": 51568.71,
                                          "realized_pl_day_usd": 0.0,
                                          "unrealized_pl_usd": 0.0,
                                          "trailing_dd_usd": 0.0})
    _enqueue_sig()
    result = lt.consume_pending_signals()
    assert result.get("status") == "in_position"
    # Queue was NOT drained — signal remains for next clear scan
    assert len(sq.peek()) == 1


def test_consume_shadow_signal_records_not_places(stub_environment):
    _enqueue_sig(symbol="GC", entry_price=4716.5, stop_price=4716.0,
                  cell_key="narrow_range_break|GC|Asian|long")
    # Mark experimental — should record to shadow_trades, not place
    sq.clear()  # restart fresh
    sig = sq.make_signal(
        symbol="GC", side="long",
        entry_price=4716.5, stop_price=4716.0, target_price=4717.0,
        strategy="narrow_range_break", session="Asian",
        cell_key="narrow_range_break|GC|Asian|long",
        shadow_only=True,
    )
    sq.enqueue(sig)
    broker = stub_environment
    result = lt.consume_pending_signals()
    assert result.get("shadow", 0) == 1
    assert len(broker.place_order_calls) == 0


def test_consume_halt_returns_halt_status(stub_environment, monkeypatch):
    monkeypatch.setattr(lt, "is_halted", lambda: (True, "manual halt"))
    monkeypatch.setattr(lt, "SHADOW_ON_HALT", False)
    _enqueue_sig()
    result = lt.consume_pending_signals()
    assert result.get("status") == "halted"


def test_consume_dll_breach_returns_dll_halt(stub_environment, monkeypatch):
    monkeypatch.setattr(lt, "capture_snapshot",
                          lambda c, a: {"can_trade": True,
                                          "open_contracts_total": 0,
                                          "balance_usd": 50000.0,
                                          "realized_pl_day_usd": -300.0,
                                          "unrealized_pl_usd": 0.0,
                                          "trailing_dd_usd": 300.0})
    _enqueue_sig()
    result = lt.consume_pending_signals()
    assert result.get("status") == "dll_halt"


def test_consume_broker_locked_returns_can_trade_false(stub_environment, monkeypatch):
    monkeypatch.setattr(lt, "capture_snapshot",
                          lambda c, a: {"can_trade": False,
                                          "open_contracts_total": 0,
                                          "balance_usd": 51000.0,
                                          "realized_pl_day_usd": 0.0,
                                          "unrealized_pl_usd": 0.0,
                                          "trailing_dd_usd": 0.0})
    _enqueue_sig()
    result = lt.consume_pending_signals()
    assert result.get("status") == "broker_can_trade_false"
