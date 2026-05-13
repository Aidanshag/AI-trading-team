"""Tests for tools/signal_queue — the brain/trader interface."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools import signal_queue as sq  # noqa: E402


@pytest.fixture
def tmp_queue(monkeypatch, tmp_path):
    """Redirect the queue file to a temp path for isolated tests."""
    fake = tmp_path / "pending_signals.json"
    monkeypatch.setattr(sq, "QUEUE_PATH", fake)
    return fake


def _build_sig(**overrides):
    base = {
        "symbol": "MNQ", "side": "long",
        "entry_price": 21500.0, "stop_price": 21490.0,
        "target_price": 21520.0,
        "strategy": "fair_value_gap", "session": "Asian",
        "cell_key": "fair_value_gap|MNQ|Asian|long",
    }
    base.update(overrides)
    return sq.make_signal(**base)


def test_enqueue_and_consume_round_trip(tmp_queue):
    sig = _build_sig()
    sq.enqueue(sig)
    out = sq.consume()
    assert len(out) == 1
    assert out[0]["id"] == sig["id"]
    assert out[0]["symbol"] == "MNQ"
    # After consume, queue is empty
    assert sq.consume() == []


def test_consume_removes_signals_from_queue(tmp_queue):
    sq.enqueue(_build_sig())
    assert len(sq.peek()) == 1
    sq.consume()
    assert sq.peek() == []


def test_peek_does_not_consume(tmp_queue):
    sq.enqueue(_build_sig())
    sq.peek()
    sq.peek()
    # Still there after two peeks
    assert len(sq.consume()) == 1


def test_expired_signals_dropped_on_read(tmp_queue, monkeypatch):
    sig = _build_sig()
    # Force the signal to be expired by rewriting its expires_at to past.
    sig["expires_at"] = (datetime.now(timezone.utc)
                          - timedelta(seconds=60)).isoformat(timespec="seconds")
    sq._write_raw([sig])  # bypass enqueue's expiry cleanup
    assert sq.peek() == []
    assert sq.consume() == []


def test_cell_dedup_replaces_prior_signal(tmp_queue):
    sig1 = _build_sig(entry_price=21500.0)
    sig2 = _build_sig(entry_price=21555.0)  # same cell_key
    sq.enqueue(sig1)
    sq.enqueue(sig2)
    # Most recent wins
    out = sq.consume()
    assert len(out) == 1
    assert out[0]["entry_price"] == 21555.0
    assert out[0]["id"] == sig2["id"]


def test_different_cells_coexist(tmp_queue):
    sq.enqueue(_build_sig(symbol="MNQ", cell_key="a|MNQ|Asian|long"))
    sq.enqueue(_build_sig(symbol="GC",  cell_key="b|GC|Asian|long"))
    assert len(sq.consume()) == 2


def test_consume_orders_by_emitted_at(tmp_queue, monkeypatch):
    # Make make_signal deterministic by overriding `now` between calls
    first = _build_sig()
    # Sleep would slow tests; instead manipulate emitted_at directly
    first["emitted_at"] = "2026-05-13T22:00:00+00:00"
    second = _build_sig(cell_key="other|MNQ|Asian|long")
    second["emitted_at"] = "2026-05-13T22:05:00+00:00"
    sq._write_raw([second, first])  # written out of order
    out = sq.consume()
    assert out[0]["emitted_at"] < out[1]["emitted_at"]


def test_consume_limit(tmp_queue):
    for i in range(5):
        sq.enqueue(_build_sig(cell_key=f"cell_{i}|MNQ|Asian|long"))
    first_batch = sq.consume(limit=3)
    assert len(first_batch) == 3
    # Remaining stay
    assert len(sq.peek()) == 2


def test_clear_empties_queue(tmp_queue):
    sq.enqueue(_build_sig())
    sq.enqueue(_build_sig(cell_key="x|GC|Asian|short"))
    n = sq.clear()
    assert n == 2
    assert sq.peek() == []


def test_atomic_write_survives_corrupt_existing_file(tmp_queue):
    # Existing queue file is malformed JSON
    tmp_queue.write_text("{ not valid json", encoding="utf-8")
    # Enqueue should still work (corrupt file = treated as empty)
    sq.enqueue(_build_sig())
    out = sq.consume()
    assert len(out) == 1


def test_missing_file_treated_as_empty(tmp_queue):
    # tmp_queue path doesn't exist yet
    assert not tmp_queue.exists()
    assert sq.peek() == []
    assert sq.consume() == []


def test_make_signal_fields():
    sig = sq.make_signal(
        symbol="ZN", side="short",
        entry_price=110.5, stop_price=110.65, target_price=110.20,
        strategy="gap_fill", session="Asian", cell_key="gap_fill|ZN|Asian|short",
        notes="test",
    )
    assert sig["symbol"] == "ZN"
    assert sig["side"] == "short"
    assert sig["entry_price"] == 110.5
    assert sig["stop_price"] == 110.65
    assert sig["target_price"] == 110.20
    assert sig["qty"] == 1
    assert sig["shadow_only"] is False
    assert "id" in sig and len(sig["id"]) > 0
    # expires_at must be after emitted_at
    assert sig["expires_at"] > sig["emitted_at"]
