"""Tests for tools/brain_logic — strategy/session/regime decisions.

Moved from tests/test_live_trader.py 2026-05-13 when the brain functions
were extracted out of scripts/live_trader.py per the standing rule
"trader places, brain decides."
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools import brain_logic as bl  # noqa: E402


# ─── session bucketing ─────────────────────────────────────────

def test_session_now_utc_rth():
    t = datetime(2026, 5, 8, 14, 0, tzinfo=timezone.utc)
    assert bl.session_now_utc(t) == "RTH"


def test_session_now_utc_london():
    t = datetime(2026, 5, 8, 8, 0, tzinfo=timezone.utc)
    assert bl.session_now_utc(t) == "London"


def test_session_now_utc_postclose():
    t = datetime(2026, 5, 8, 22, 0, tzinfo=timezone.utc)
    assert bl.session_now_utc(t) == "PostClose"


def test_session_now_utc_asian():
    t = datetime(2026, 5, 8, 2, 0, tzinfo=timezone.utc)
    assert bl.session_now_utc(t) == "Asian"


# ─── load_live_cells ────────────────────────────────────────────

def test_load_live_cells_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(bl, "LIVE_ALLOWLIST_PATH", tmp_path / "missing.json")
    assert bl.load_live_cells() == []


def test_load_live_cells_valid(tmp_path, monkeypatch):
    state_file = tmp_path / "validation.json"
    state_file.write_text(json.dumps({
        "live_allowlist": [
            {"strategy": "gap_fill", "symbol": "ZN", "session": "Asian", "side": "long"},
            {"strategy": "gap_fill", "symbol": "ZT", "session": "Asian", "side": "short"},
        ]
    }))
    monkeypatch.setattr(bl, "LIVE_ALLOWLIST_PATH", state_file)
    cells = bl.load_live_cells()
    assert len(cells) == 2
    assert cells[0]["symbol"] == "ZN"


def test_load_live_cells_corrupt(tmp_path, monkeypatch):
    state_file = tmp_path / "bad.json"
    state_file.write_text("{not valid json")
    monkeypatch.setattr(bl, "LIVE_ALLOWLIST_PATH", state_file)
    assert bl.load_live_cells() == []


# ─── find_latest_signal lookback ────────────────────────────────

def test_find_latest_signal_short_bars():
    import pandas as pd
    bars = pd.DataFrame(
        {"Open": [1, 2], "High": [1, 2], "Low": [1, 2], "Close": [1, 2], "Volume": [1, 1]},
        index=pd.to_datetime(["2026-05-08 00:00", "2026-05-08 00:05"]),
    )

    def fn(b):
        yield from []

    assert bl.find_latest_signal(bars, fn) is None


def test_find_latest_signal_no_entries():
    import pandas as pd
    n = 50
    bars = pd.DataFrame(
        {"Open": list(range(n)), "High": list(range(n)),
         "Low": list(range(n)), "Close": list(range(n)),
         "Volume": [1] * n},
        index=pd.date_range("2026-05-08", periods=n, freq="5min"),
    )

    def fn(b):
        yield from []

    assert bl.find_latest_signal(bars, fn) is None


# ─── find_latest_signal tick_size injection ───────────

def test_find_latest_signal_injects_tick_size():
    """When the strategy accepts tick_size and tick_size_lookup is given,
    the real tick_size for that symbol should be passed in."""
    import pandas as pd
    from tools.trader_utils import _tick_size
    n = 50
    bars = pd.DataFrame(
        {"Open": list(range(n)), "High": list(range(n)),
         "Low": list(range(n)), "Close": list(range(n)),
         "Volume": [1] * n},
        index=pd.date_range("2026-05-08", periods=n, freq="5min"),
    )
    received: dict = {}

    def fake_strategy(bars, tick_size=None):
        received["tick_size"] = tick_size
        return iter([])

    bl.find_latest_signal(bars, fake_strategy, symbol="ZN",
                            tick_size_lookup=_tick_size)
    assert received["tick_size"] is not None
    assert abs(received["tick_size"] - 0.015625) < 1e-9


def test_find_latest_signal_does_not_inject_when_strategy_lacks_param():
    """Strategies without a tick_size param should be called without it."""
    import pandas as pd
    from tools.trader_utils import _tick_size
    n = 50
    bars = pd.DataFrame(
        {"Open": list(range(n)), "High": list(range(n)),
         "Low": list(range(n)), "Close": list(range(n)),
         "Volume": [1] * n},
        index=pd.date_range("2026-05-08", periods=n, freq="5min"),
    )
    calls = {"n": 0}

    def old_strategy(bars):  # no tick_size kwarg
        calls["n"] += 1
        return iter([])

    bl.find_latest_signal(bars, old_strategy, symbol="ZN",
                            tick_size_lookup=_tick_size)
    assert calls["n"] == 1


def test_find_latest_signal_no_symbol_skips_injection():
    """No symbol → no injection."""
    import pandas as pd
    n = 50
    bars = pd.DataFrame(
        {"Open": list(range(n)), "High": list(range(n)),
         "Low": list(range(n)), "Close": list(range(n)),
         "Volume": [1] * n},
        index=pd.date_range("2026-05-08", periods=n, freq="5min"),
    )
    received: dict = {"tick_size": "untouched"}

    def fake_strategy(bars, tick_size=None):
        received["tick_size"] = tick_size
        return iter([])

    bl.find_latest_signal(bars, fake_strategy)
    assert received["tick_size"] is None


# ─── cell_passes_regime_filter ───────────────────────────────────

def test_cell_passes_regime_filter_no_filter():
    cell = {"strategy": "fair_value_gap", "symbol": "MNQ"}
    regime = {"vol_regime": "low"}
    ok, _ = bl.cell_passes_regime_filter(cell, regime)
    assert ok is True


def test_cell_passes_regime_filter_match():
    cell = {"regime_filter": {"vol_regime": ["high"]}}
    ok, _ = bl.cell_passes_regime_filter(cell, {"vol_regime": "high"})
    assert ok is True


def test_cell_passes_regime_filter_mismatch():
    cell = {"regime_filter": {"vol_regime": ["high"]}}
    for r in ["low", "med"]:
        ok, reason = bl.cell_passes_regime_filter(cell, {"vol_regime": r})
        assert ok is False
        assert "vol_regime" in reason


def test_cell_passes_regime_filter_multikey_all_must_match():
    cell = {"regime_filter": {"vol_regime": ["high"], "trend_regime": ["trending"]}}
    assert bl.cell_passes_regime_filter(cell, {"vol_regime": "high", "trend_regime": "trending"})[0] is True
    assert bl.cell_passes_regime_filter(cell, {"vol_regime": "high", "trend_regime": "ranging"})[0] is False
    assert bl.cell_passes_regime_filter(cell, {"vol_regime": "med", "trend_regime": "trending"})[0] is False


def test_cell_passes_regime_filter_unknown_regime_fail_closed():
    restricted = {"regime_filter": {"vol_regime": ["high"]}}
    open_cell = {"strategy": "x"}
    assert bl.cell_passes_regime_filter(restricted, {})[0] is False
    assert bl.cell_passes_regime_filter(open_cell, {})[0] is True


# ─── news_proximity_for ──────────────────────────────────────────

def test_news_proximity_clear_when_no_events_nearby(monkeypatch):
    monkeypatch.setattr(bl, "_load_calendar_events", lambda sym: [])
    assert bl.news_proximity_for("ZN") == "clear"


def test_news_proximity_inside_within_15min_of_high(monkeypatch):
    now = datetime(2026, 5, 11, 12, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(bl, "_load_calendar_events",
                          lambda sym: [{"ts": now + timedelta(minutes=10), "severity": "HIGH"}])
    assert bl.news_proximity_for("ZN", now=now) == "inside"


def test_news_proximity_near_when_30min_from_high(monkeypatch):
    now = datetime(2026, 5, 11, 12, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(bl, "_load_calendar_events",
                          lambda sym: [{"ts": now + timedelta(minutes=30), "severity": "HIGH"}])
    assert bl.news_proximity_for("ZN", now=now) == "near"


def test_news_proximity_near_when_60min_from_medium(monkeypatch):
    now = datetime(2026, 5, 11, 12, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(bl, "_load_calendar_events",
                          lambda sym: [{"ts": now + timedelta(minutes=50), "severity": "MEDIUM"}])
    assert bl.news_proximity_for("ZN", now=now) == "near"


def test_news_proximity_clear_when_far_from_event(monkeypatch):
    now = datetime(2026, 5, 11, 12, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(bl, "_load_calendar_events",
                          lambda sym: [{"ts": now + timedelta(hours=4), "severity": "HIGH"}])
    assert bl.news_proximity_for("ZN", now=now) == "clear"


# ─── current_regime ──────────────────────────────────────────────

def test_current_regime_includes_news_when_symbol_passed(monkeypatch):
    import pandas as pd
    import numpy as np
    np.random.seed(7)
    n = 200
    rets = np.random.randn(n) * 0.001
    close = 100 * np.exp(np.cumsum(rets))
    bars = pd.DataFrame(
        {"Open": close, "High": close + 0.1, "Low": close - 0.1,
         "Close": close, "Volume": [1] * n},
        index=pd.date_range("2026-05-08", periods=n, freq="5min"),
    )
    monkeypatch.setattr(bl, "_load_calendar_events", lambda sym: [])
    regime = bl.current_regime(bars, symbol="ZN")
    assert "news_proximity" in regime
    assert regime["news_proximity"] == "clear"


def test_current_regime_returns_empty_on_short_bars():
    import pandas as pd
    n = 50
    bars = pd.DataFrame(
        {"Open": list(range(n)), "High": [x + 1 for x in range(n)],
         "Low": [x - 1 for x in range(n)], "Close": list(range(n)),
         "Volume": [1] * n},
        index=pd.date_range("2026-05-08", periods=n, freq="5min"),
    )
    regime = bl.current_regime(bars)
    assert regime == {}


def test_current_regime_returns_dict_on_full_bars():
    import pandas as pd
    import numpy as np
    np.random.seed(7)
    n = 200
    rets = np.random.randn(n) * 0.001
    close = 100 * np.exp(np.cumsum(rets))
    bars = pd.DataFrame(
        {"Open": close, "High": close + 0.1, "Low": close - 0.1,
         "Close": close, "Volume": [1] * n},
        index=pd.date_range("2026-05-08", periods=n, freq="5min"),
    )
    regime = bl.current_regime(bars)
    assert "vol_regime" in regime and regime["vol_regime"] in ("low", "med", "high")
    assert "trend_regime" in regime and regime["trend_regime"] in ("trending", "ranging")
