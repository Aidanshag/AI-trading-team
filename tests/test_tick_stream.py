"""Tests for tools/tick_stream.py — SignalR tick cache.

Live WebSocket connection is NOT exercised here (that requires a
running broker). These tests exercise the cache logic + staleness
gate + thread-safety via direct event injection.

Live verification (one-shot, manual): `python -m scripts.probe_signalr`.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone, timedelta

import pytest

from tools import tick_stream as ts


@pytest.fixture(autouse=True)
def _reset_singleton():
    ts.reset_for_test()
    yield
    ts.reset_for_test()


def _make_stream() -> ts.TickStream:
    """Build a stream without opening a connection."""
    return ts.TickStream(jwt="fake-jwt-for-tests")


def _inject_tick(stream, contract_id: str, price: float,
                   age_seconds: float = 0.0) -> None:
    """Directly write a tick into the cache, bypassing the WebSocket.
    `age_seconds` lets tests simulate stale entries."""
    now = datetime.now(tz=timezone.utc) - timedelta(seconds=age_seconds)
    entry = {
        "contract_id": contract_id,
        "price": float(price),
        "bid": None, "ask": None, "volume": None,
        "ts": now,
    }
    with stream._lock:
        stream._cache[contract_id] = entry
        stream._last_event_ts = now
    stream._subscribed.add(contract_id)  # pretend we subscribed


# ── Cache freshness ─────────────────────────────────────────────

def test_latest_returns_none_when_unsubscribed():
    """First read of an unknown contract returns None (auto-subscribe
    would happen but no data is in the cache yet)."""
    s = _make_stream()
    # We never call subscribe (which would try to open a connection).
    # Manually mark subscribed so latest() doesn't try to auto-subscribe.
    s._subscribed.add("CON.F.US.MGC.M26")
    assert s.latest("CON.F.US.MGC.M26") is None


def test_latest_returns_fresh_tick():
    s = _make_stream()
    _inject_tick(s, "CON.F.US.MGC.M26", price=4700.0, age_seconds=0.0)
    tick = s.latest("CON.F.US.MGC.M26")
    assert tick is not None
    assert tick["price"] == 4700.0


def test_latest_returns_none_when_stale():
    """Stale entry (older than STALE_AFTER_S) returns None — fail-safe
    so consumers fall back to the bar-fetcher path."""
    s = _make_stream()
    _inject_tick(s, "CON.F.US.MGC.M26", price=4700.0,
                  age_seconds=ts.STALE_AFTER_S + 5)
    assert s.latest("CON.F.US.MGC.M26") is None


def test_latest_returns_fresh_just_under_threshold():
    """Just under the staleness boundary still returns the tick."""
    s = _make_stream()
    _inject_tick(s, "CON.F.US.MGC.M26", price=4700.0,
                  age_seconds=ts.STALE_AFTER_S - 1)
    tick = s.latest("CON.F.US.MGC.M26")
    assert tick is not None
    assert tick["price"] == 4700.0


# ── is_alive (sentinel-facing) ──────────────────────────────────

def test_is_alive_false_before_start():
    s = _make_stream()
    assert s.is_alive() is False


def test_is_alive_true_with_recent_event():
    s = _make_stream()
    s._started = True
    _inject_tick(s, "CON.F.US.MGC.M26", price=4700.0, age_seconds=0.0)
    assert s.is_alive(max_event_gap_s=60.0) is True


def test_is_alive_false_after_long_gap():
    s = _make_stream()
    s._started = True
    _inject_tick(s, "CON.F.US.MGC.M26", price=4700.0,
                  age_seconds=120.0)  # 2 min ago
    assert s.is_alive(max_event_gap_s=60.0) is False


# ── _on_event payload parsing ───────────────────────────────────

def test_on_event_parses_gateway_quote_payload():
    """The handler should extract lastPrice and store the entry."""
    s = _make_stream()
    payload = {
        "symbol": "F.US.MGC", "symbolName": "/MGC",
        "lastPrice": 4548.1, "bestBid": 4548.0, "bestAsk": 4548.2,
        "volume": 368686,
        "lastUpdated": "2026-05-15T15:42:30Z",
    }
    s._on_event(["CON.F.US.MGC.M26", payload])
    entry = s._cache["CON.F.US.MGC.M26"]
    assert entry["price"] == 4548.1
    assert entry["bid"] == 4548.0
    assert entry["ask"] == 4548.2
    assert entry["volume"] == 368686


def test_on_event_ignores_malformed_payload():
    """Bad shapes don't crash the bg thread or write garbage."""
    s = _make_stream()
    # Missing lastPrice
    s._on_event(["CON.F.US.MGC.M26", {"foo": "bar"}])
    # Wrong arg shape
    s._on_event(["only-one-arg"])
    s._on_event("not-a-list")
    s._on_event(None)
    # Payload that's not a dict
    s._on_event(["CON.F.US.MGC.M26", "string-not-dict"])
    # None of these should have written to the cache
    assert s._cache == {}


def test_on_event_handles_zero_bid_ask_as_none():
    """Topstep sometimes sends 0 for bid/ask outside session. The handler
    should normalize to None rather than treating 0 as a real quote."""
    s = _make_stream()
    payload = {"lastPrice": 4700.0, "bestBid": 0, "bestAsk": 0}
    s._on_event(["CON.F.US.MGC.M26", payload])
    entry = s._cache["CON.F.US.MGC.M26"]
    assert entry["price"] == 4700.0
    assert entry["bid"] is None
    assert entry["ask"] is None


# ── Thread safety (cache reads + writes can interleave) ──────────

def test_concurrent_reads_and_writes_dont_crash():
    """Stress test: hundreds of cache writes + reads concurrently.
    No data corruption (None or float, never something else)."""
    s = _make_stream()
    s._subscribed.add("CON.F.US.MGC.M26")
    s._started = True

    def writer():
        for i in range(500):
            s._on_event([
                "CON.F.US.MGC.M26",
                {"lastPrice": 4700.0 + (i % 10)},
            ])

    def reader():
        for _ in range(500):
            t = s.latest("CON.F.US.MGC.M26")
            if t is not None:
                assert isinstance(t["price"], float)
                assert t["price"] >= 4700.0
                assert t["price"] < 4710.0

    threads = [threading.Thread(target=writer) for _ in range(3)] + \
               [threading.Thread(target=reader) for _ in range(3)]
    for t in threads: t.start()
    for t in threads: t.join()
    # If we got here without an assertion error, thread-safe.


# ── Singleton lifecycle ─────────────────────────────────────────

def test_get_stream_requires_jwt_on_first_call():
    """First call with no JWT raises (caller must initialize)."""
    with pytest.raises(RuntimeError, match="first caller must pass a JWT"):
        ts.get_stream()


def test_get_stream_returns_singleton():
    """Subsequent calls return the same instance."""
    s1 = ts.get_stream(jwt="test-jwt")
    s2 = ts.get_stream()  # no JWT needed; uses existing
    assert s1 is s2


def test_reset_for_test_clears_singleton():
    """reset_for_test should allow re-initialization with a new JWT."""
    s1 = ts.get_stream(jwt="jwt-1")
    ts.reset_for_test()
    s2 = ts.get_stream(jwt="jwt-2")
    assert s1 is not s2
    assert s2._jwt == "jwt-2"


# ── Subscription tracking ───────────────────────────────────────

def test_subscribed_contracts_tracks_subscriptions():
    """After subscribe() (which would call hub.send), the contract is
    in the subscribed set. We bypass hub.send by adding directly."""
    s = _make_stream()
    s._subscribed.add("CON.F.US.MGC.M26")
    s._subscribed.add("CON.F.US.MNQ.M26")
    assert set(s.subscribed_contracts()) == {
        "CON.F.US.MGC.M26", "CON.F.US.MNQ.M26"
    }


def test_cache_snapshot_returns_independent_copy():
    """sentinel.check_tick_stream_stale needs a stable snapshot."""
    s = _make_stream()
    _inject_tick(s, "CON.F.US.MGC.M26", price=4700.0)
    snap = s.cache_snapshot()
    assert "CON.F.US.MGC.M26" in snap
    # Modifying the snapshot doesn't affect the cache
    snap["bogus"] = {"price": 0.0}
    assert "bogus" not in s._cache
