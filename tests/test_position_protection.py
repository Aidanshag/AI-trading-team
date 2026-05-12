"""Tests for tools/position_protection — periodic stop-presence sweep."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from tools import position_protection as pp


def _ts_iso_ago(seconds: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()


class _FakeClient:
    def __init__(self, positions=None, working_orders=None):
        self._positions = positions or []
        self._working = working_orders or []
        self.placed: list[dict] = []
    def get_positions(self, _aid):
        return self._positions
    def get_working_orders(self, _aid):
        return self._working
    def place_order(self, **kwargs):
        self.placed.append(kwargs)
        return {"orderId": 999}


def test_sweep_noop_when_no_positions():
    client = _FakeClient()
    out = pp.sweep(client, 1)
    assert out["checked"] == 0
    assert out["flattened"] == []


def test_sweep_skips_position_within_grace_period():
    """Freshly-opened position (<grace_sec) is skipped — gives place_bracket
    time to land the stop."""
    client = _FakeClient(
        positions=[{
            "contractId": "CON.F.US.GCE.M26", "size": 1, "type": 1,
            "creationTimestamp": _ts_iso_ago(30),  # 30s ago, within grace (90s default)
        }],
        working_orders=[],  # no stop yet
    )
    out = pp.sweep(client, 1)
    assert out["skipped_grace"] == 1
    assert out["flattened"] == []
    assert client.placed == []


def test_sweep_finds_stop_no_flatten():
    """Position has a working stop with right tag → no action."""
    client = _FakeClient(
        positions=[{
            "contractId": "CON.F.US.GCE.M26", "size": 1, "type": 1,
            "creationTimestamp": _ts_iso_ago(300),
        }],
        working_orders=[
            {"contractId": "CON.F.US.GCE.M26", "type": 4,
             "customTag": "live_abc123_stop"},
        ],
    )
    out = pp.sweep(client, 1)
    assert out["checked"] == 1
    assert out["flattened"] == []
    assert client.placed == []


def test_sweep_flattens_when_stop_missing():
    """Past grace period, no working stop → emergency-flatten."""
    client = _FakeClient(
        positions=[{
            "contractId": "CON.F.US.GCE.M26", "size": 1, "type": 1,
            "creationTimestamp": _ts_iso_ago(300),
        }],
        working_orders=[],
    )
    out = pp.sweep(client, 1)
    assert len(out["flattened"]) == 1
    assert client.placed[0]["side"] == "sell"  # closing long
    assert client.placed[0]["order_type"] == "market"


def test_sweep_ignores_non_live_tags():
    """Working orders with non-live tags don't count as protection."""
    client = _FakeClient(
        positions=[{
            "contractId": "CON.F.US.GCE.M26", "size": 1, "type": 1,
            "creationTimestamp": _ts_iso_ago(300),
        }],
        working_orders=[
            {"contractId": "CON.F.US.GCE.M26", "type": 3,
             "customTag": "manual_stop_xyz"},  # not live_..._stop
        ],
    )
    out = pp.sweep(client, 1)
    assert len(out["flattened"]) == 1


def test_sweep_short_position_buys_to_close():
    """Short position (type=2) closes via market buy."""
    client = _FakeClient(
        positions=[{
            "contractId": "CON.F.US.GCE.M26", "size": 1, "type": 2,
            "creationTimestamp": _ts_iso_ago(300),
        }],
        working_orders=[],
    )
    out = pp.sweep(client, 1)
    assert client.placed[0]["side"] == "buy"


def test_sweep_handles_broker_error():
    """If broker fetch raises, fail-open (don't flatten on bad data)."""
    class Bad:
        def get_positions(self, _aid):
            raise RuntimeError("broker down")
        def get_working_orders(self, _aid):
            return []
    out = pp.sweep(Bad(), 1)
    assert out["flattened"] == []
