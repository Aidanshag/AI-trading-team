"""Tests for tools/exit_reasoner — the LLM-based exit veto layer.

These tests cover the GUARD RAILS (authority limits, error fallback,
response parsing) WITHOUT making real API calls. The real API is
exercised in shadow-replay (scripts/shadow_replay_agent.py) where each
call's outcome is verifiable against historical bar data.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from tools.exit_reasoner import (
    ExitDecision, TradeContext,
    decide_exit_with_agent,
    _parse_agent_response,
    MAX_CONSECUTIVE_HOLDS, MAX_AGENT_HOLD_DURATION_SECONDS,
    MIN_PEAK_USD_TO_INVOKE_AGENT, MAX_PEAK_USD_FOR_AGENT,
)


def _ctx(*, consecutive_holds=0, peak_usd=100.0,
          minutes_in_trade=5, current_usd=20.0):
    return TradeContext(
        symbol="GC", side="long", strategy="fair_value_gap",
        contract_id="CON.F.US.GCE.M26",
        entry_price=4000, avg_fill_price=4000,
        entry_ts=datetime.now(tz=timezone.utc) - timedelta(minutes=minutes_in_trade),
        current_price=4002,
        peak_unrealized_usd=peak_usd,
        current_unrealized_usd=current_usd,
        tier_floor_usd=20.0,
        risk_usd=1000.0,
        recent_bars=[{"t": "2026-05-12T14:00", "o": 4000, "h": 4001, "l": 3999.5, "c": 4000}],
        regime={"vol_regime": "med", "trend_regime": "trending"},
        consecutive_holds=consecutive_holds,
    )


# ─── Guard-rail authority limits (no API call should happen) ──────

def test_disabled_flag_returns_close_without_calling_agent():
    with patch("tools.exit_reasoner._call_agent") as mock_call:
        d = decide_exit_with_agent(_ctx(), enabled=False)
        assert d.action == "CLOSE"
        assert "disabled" in d.reason
        mock_call.assert_not_called()


def test_max_consecutive_holds_forces_close():
    with patch("tools.exit_reasoner._call_agent") as mock_call:
        d = decide_exit_with_agent(
            _ctx(consecutive_holds=MAX_CONSECUTIVE_HOLDS), enabled=True,
        )
        assert d.action == "CLOSE"
        assert "max_consecutive_holds" in d.reason
        mock_call.assert_not_called()


def test_time_cap_forces_close():
    """Trade open >MAX_AGENT_HOLD_DURATION_SECONDS → close, no API."""
    over = MAX_AGENT_HOLD_DURATION_SECONDS // 60 + 1
    with patch("tools.exit_reasoner._call_agent") as mock_call:
        d = decide_exit_with_agent(
            _ctx(minutes_in_trade=over), enabled=True,
        )
        assert d.action == "CLOSE"
        assert "time_in_trade" in d.reason
        mock_call.assert_not_called()


def test_below_min_peak_forces_close():
    with patch("tools.exit_reasoner._call_agent") as mock_call:
        d = decide_exit_with_agent(
            _ctx(peak_usd=MIN_PEAK_USD_TO_INVOKE_AGENT - 1), enabled=True,
        )
        assert d.action == "CLOSE"
        assert "below_agent_threshold" in d.reason
        mock_call.assert_not_called()


def test_above_max_peak_forces_close():
    """Big runners stay under mechanical control."""
    with patch("tools.exit_reasoner._call_agent") as mock_call:
        d = decide_exit_with_agent(
            _ctx(peak_usd=MAX_PEAK_USD_FOR_AGENT + 1), enabled=True,
        )
        assert d.action == "CLOSE"
        assert "above_runner_tier_authority" in d.reason
        mock_call.assert_not_called()


# ─── API failure fallback ──────────────────────────────────────────

def test_api_error_falls_back_to_close():
    with patch("tools.exit_reasoner._call_agent",
                side_effect=ConnectionError("timeout")):
        d = decide_exit_with_agent(_ctx(), enabled=True)
        assert d.action == "FALLBACK_CLOSE"
        assert "ConnectionError" in d.reason


# ─── Response parsing ──────────────────────────────────────────────

def test_parse_well_formed_hold():
    text = ("DECISION: HOLD\n"
             "CONFIDENCE: high\n"
             "REASON: Normal FVG retest before continuation")
    d, c, r = _parse_agent_response(text)
    assert d == "HOLD"
    assert c == "high"
    assert r == "Normal FVG retest before continuation"


def test_parse_well_formed_close():
    text = ("DECISION: CLOSE\n"
             "CONFIDENCE: medium\n"
             "REASON: Lower-high pattern + volume confirms reversal")
    d, c, r = _parse_agent_response(text)
    assert d == "CLOSE"
    assert c == "medium"
    assert "Lower-high" in r


def test_parse_garbled_falls_back_to_close():
    """If the agent returns malformed output, we default to CLOSE."""
    text = "yes I think we should let it run because the trend is up"
    d, c, r = _parse_agent_response(text)
    assert d == "CLOSE"
    assert c == "low"


def test_parse_truncates_long_reason():
    long_reason = "x" * 500
    text = (f"DECISION: HOLD\n"
             f"CONFIDENCE: high\n"
             f"REASON: {long_reason}")
    _, _, r = _parse_agent_response(text)
    assert len(r) <= 200


# ─── End-to-end with mocked API: HOLD path is honored ─────────────

def test_agent_hold_returns_hold():
    def fake_call(_prompt):
        return ("DECISION: HOLD\n"
                "CONFIDENCE: high\n"
                "REASON: Bar action looks like consolidation, not reversal"), {
            "elapsed_ms": 1234, "input_tokens": 500,
            "output_tokens": 50, "model": "fake",
        }
    with patch("tools.exit_reasoner._call_agent", side_effect=fake_call):
        d = decide_exit_with_agent(_ctx(), enabled=True)
        assert d.action == "HOLD"
        assert "consolidation" in d.reason
        assert d.response_ms == 1234


def test_agent_close_returns_close():
    def fake_call(_prompt):
        return ("DECISION: CLOSE\n"
                "CONFIDENCE: medium\n"
                "REASON: Volume dropped, momentum stalled"), {
            "elapsed_ms": 800, "input_tokens": 500,
            "output_tokens": 30, "model": "fake",
        }
    with patch("tools.exit_reasoner._call_agent", side_effect=fake_call):
        d = decide_exit_with_agent(_ctx(), enabled=True)
        assert d.action == "CLOSE"
        assert d.confidence == "medium"


# ─── DB logging ────────────────────────────────────────────────────

def test_circuit_breaker_trips_after_threshold_failures():
    """3 API failures within the window must trip the breaker so subsequent
    calls bypass the agent entirely."""
    import tools.exit_reasoner as er
    # Reset breaker state
    er._recent_failure_timestamps.clear()
    er._breaker_tripped_at = None

    with patch("tools.exit_reasoner._call_agent",
                side_effect=ConnectionError("timeout")):
        for _ in range(er.CIRCUIT_BREAKER_THRESHOLD):
            d = er.decide_exit_with_agent(_ctx(), enabled=True)
            assert d.action == "FALLBACK_CLOSE"

        # Next call should hit the open breaker (no API call attempted)
        with patch("tools.exit_reasoner._call_agent",
                    side_effect=ConnectionError("would_not_be_called")
                    ) as mock_call:
            d = er.decide_exit_with_agent(_ctx(), enabled=True)
            assert d.action == "CLOSE"
            assert "circuit_breaker_open" in d.reason
            mock_call.assert_not_called()

    # Reset for next test
    er._recent_failure_timestamps.clear()
    er._breaker_tripped_at = None


def test_circuit_breaker_resets_after_cooldown():
    """After CIRCUIT_BREAKER_COOLDOWN_SECONDS, the breaker re-closes."""
    import time as _time
    import tools.exit_reasoner as er
    # Trip the breaker manually
    er._breaker_tripped_at = _time.time() - er.CIRCUIT_BREAKER_COOLDOWN_SECONDS - 1
    # Should re-close on next check
    assert er._circuit_breaker_is_open() is False
    assert er._breaker_tripped_at is None


def test_log_veto_writes_row_to_db():
    """When db_conn is provided, every decision must write a row."""
    con = sqlite3.connect(":memory:")
    con.executescript("""
        CREATE TABLE agent_exit_vetoes (
            id INTEGER PRIMARY KEY,
            ts TEXT NOT NULL,
            contract_id TEXT,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            strategy TEXT,
            tier_floor_usd REAL NOT NULL,
            peak_unrealized_usd REAL NOT NULL,
            current_unrealized_usd REAL NOT NULL,
            time_in_trade_seconds INTEGER NOT NULL,
            consecutive_holds INTEGER NOT NULL DEFAULT 0,
            decision TEXT NOT NULL,
            confidence TEXT,
            reason TEXT NOT NULL,
            agent_model TEXT,
            agent_response_ms INTEGER,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            actual_exit_usd REAL,
            actual_exit_ts TEXT,
            agent_verdict TEXT
        )
    """)
    # Disabled path still logs
    decide_exit_with_agent(_ctx(), enabled=False, db_conn=con)
    rows = con.execute("SELECT COUNT(*) FROM agent_exit_vetoes").fetchone()
    assert rows[0] == 1
