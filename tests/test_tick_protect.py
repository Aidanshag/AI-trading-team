"""Tests for tools/tick_protect.py — millisecond-latency profit-lock exits."""
from __future__ import annotations

import time
import threading
from typing import Any

import pytest


@pytest.fixture(autouse=True)
def reset_state():
    """Wipe tick_protect and profit_protect shared state between tests."""
    from tools import tick_protect
    from tools import profit_protect
    tick_protect.reset_for_test()
    profit_protect._position_high_water.clear()
    profit_protect._position_peak_ts.clear()
    profit_protect._target_usd_by_contract.clear()
    yield
    tick_protect.reset_for_test()
    profit_protect._position_high_water.clear()
    profit_protect._position_peak_ts.clear()
    profit_protect._target_usd_by_contract.clear()


class MockClient:
    """Records every close_position call."""
    def __init__(self, success: bool = True):
        self.closes: list[tuple[int, str]] = []
        self.success = success
        self._lock = threading.Lock()

    def close_position(self, account_id: int, contract_id: str) -> dict:
        with self._lock:
            self.closes.append((account_id, contract_id))
        if self.success:
            return {"success": True}
        return {"success": False, "errorMessage": "test rejected"}


def _register_long_mgc(unrealized_starting_peak: float = 0.0):
    """Helper: register an MGC long with peak already set if provided."""
    from tools import tick_protect, profit_protect
    tick_protect.register_position(
        contract_id="CON.F.US.MGC.M26", symbol="MGC", side="long",
        size=1, avg_price=4500.0, tick_size=0.10, tick_value=1.0,
        account_id=42,
    )
    if unrealized_starting_peak > 0:
        profit_protect._position_high_water["MGC_long"] = unrealized_starting_peak
        from datetime import datetime, timezone
        profit_protect._position_peak_ts["MGC_long"] = datetime.now(tz=timezone.utc)


def test_on_tick_does_not_close_when_unrealized_below_floor_threshold():
    """If unrealized is < $20 and there's no peak, decide() returns False — no close."""
    from tools import tick_protect
    client = MockClient()
    tick_protect.configure(client=client, log_fn=lambda _: None)
    _register_long_mgc()
    # Tick price moves up by 10 ticks ($10) — peak is $10 < $20 floor threshold
    tick_protect.on_tick("CON.F.US.MGC.M26",
                          {"price": 4501.0, "ts": None})
    # Give worker thread time if it were spawned
    time.sleep(0.1)
    assert client.closes == [], f"Should not have closed, but got: {client.closes}"


def test_on_tick_fires_close_when_unrealized_falls_below_trailing_floor():
    """Peak hit $40, floor = max($20, $40*0.7) = $28. Current $25 < $28 → close fires."""
    from tools import tick_protect
    client = MockClient()
    tick_protect.configure(client=client, log_fn=lambda _: None)
    _register_long_mgc(unrealized_starting_peak=40.0)
    # Tick: 25 ticks above entry = +$25 unrealized < $28 floor
    tick_protect.on_tick("CON.F.US.MGC.M26",
                          {"price": 4502.5, "ts": None})
    # Worker dispatches close in background thread; give it time
    time.sleep(0.3)
    assert client.closes == [(42, "CON.F.US.MGC.M26")], \
        f"Expected one close, got: {client.closes}"


def test_close_in_flight_prevents_double_close():
    """A second tick during the close window must not fire another close."""
    from tools import tick_protect
    # Slow client — close takes 200ms — so a tick fired during this window
    # must be ignored
    class SlowClient:
        def __init__(self):
            self.closes = []
            self.lock = threading.Lock()
        def close_position(self, account_id, contract_id):
            time.sleep(0.2)
            with self.lock:
                self.closes.append((account_id, contract_id))
            return {"success": True}
    client = SlowClient()
    tick_protect.configure(client=client, log_fn=lambda _: None)
    _register_long_mgc(unrealized_starting_peak=40.0)
    # Fire two ticks back-to-back. The first dispatches the close; the
    # second should see _close_in_flight set and skip.
    tick_protect.on_tick("CON.F.US.MGC.M26", {"price": 4502.5, "ts": None})
    time.sleep(0.05)  # let the worker start
    tick_protect.on_tick("CON.F.US.MGC.M26", {"price": 4502.5, "ts": None})
    time.sleep(0.5)   # let close complete
    assert len(client.closes) == 1, \
        f"Expected 1 close (in-flight blocked dup), got: {len(client.closes)}"


def test_target_hit_fires_close_immediately():
    """If unrealized >= target_usd registered in profit_protect, fire close."""
    from tools import tick_protect, profit_protect
    client = MockClient()
    tick_protect.configure(client=client, log_fn=lambda _: None)
    _register_long_mgc()
    # Register a $20 target
    profit_protect._target_usd_by_contract["CON.F.US.MGC.M26"] = 20.0
    # Tick at +$25 unrealized (25 ticks above entry)
    tick_protect.on_tick("CON.F.US.MGC.M26", {"price": 4502.5, "ts": None})
    time.sleep(0.3)
    assert client.closes == [(42, "CON.F.US.MGC.M26")]


def test_unregister_position_stops_callbacks_from_firing_close():
    from tools import tick_protect
    client = MockClient()
    tick_protect.configure(client=client, log_fn=lambda _: None)
    _register_long_mgc(unrealized_starting_peak=40.0)
    tick_protect.unregister_position("CON.F.US.MGC.M26")
    tick_protect.on_tick("CON.F.US.MGC.M26", {"price": 4502.5, "ts": None})
    time.sleep(0.2)
    assert client.closes == []


def test_peak_tracking_updates_on_tick():
    """Each tick that exceeds prior peak updates _position_high_water."""
    from tools import tick_protect, profit_protect
    client = MockClient()
    tick_protect.configure(client=client, log_fn=lambda _: None)
    _register_long_mgc()
    # 5 ticks up = $5
    tick_protect.on_tick("CON.F.US.MGC.M26", {"price": 4500.5, "ts": None})
    assert profit_protect._position_high_water.get("MGC_long") == 5.0
    # 15 ticks = $15
    tick_protect.on_tick("CON.F.US.MGC.M26", {"price": 4501.5, "ts": None})
    assert profit_protect._position_high_water.get("MGC_long") == 15.0
    # Pulls back to 10 — peak stays at 15
    tick_protect.on_tick("CON.F.US.MGC.M26", {"price": 4501.0, "ts": None})
    assert profit_protect._position_high_water.get("MGC_long") == 15.0


def test_on_tick_for_unregistered_contract_is_noop():
    from tools import tick_protect
    client = MockClient()
    tick_protect.configure(client=client, log_fn=lambda _: None)
    # No register_position call
    tick_protect.on_tick("CON.F.US.UNK.M26", {"price": 100.0, "ts": None})
    time.sleep(0.1)
    assert client.closes == []


def test_on_tick_without_configure_is_safe_noop():
    """If client was never configured, on_tick must not crash."""
    from tools import tick_protect
    _register_long_mgc(unrealized_starting_peak=40.0)
    # No configure() call
    tick_protect.on_tick("CON.F.US.MGC.M26", {"price": 4502.5, "ts": None})
    # If we got here without exception, the test passes
