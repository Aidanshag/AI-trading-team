"""Event model for the fund's event loop.

The orchestrator consumes events and fans them out to the appropriate agents.
Keep this set small and purposeful — every new event type is a new code path
to reason about.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EventKind(str, Enum):
    # Session / schedule events
    SESSION_OPEN       = "session_open"
    SESSION_CLOSE      = "session_close"
    TICK               = "tick"              # periodic CIO heartbeat (e.g., every 30 min)
    IDLE_TICK          = "idle_tick"         # off-hours tick (markets closed) — gated by idle_work_enabled
    BOOK_MONITOR_TICK  = "book_monitor_tick" # 5-min position-watcher wake (only when positions > 0)
    WEEKLY_REVIEW      = "weekly_review"     # Sunday 18:00 CT scheduled review
    STRESS_TEST_DUE    = "stress_test_due"   # 06:00 CT daily — run portfolio stress scenarios
    DAILY_METRICS_DUE  = "daily_metrics_due" # 17:00 CT daily — Compliance metrics sweep

    # Market events
    NEWS          = "news"
    ECON_RELEASE  = "econ_release"
    PRICE_ALERT   = "price_alert"       # threshold cross

    # Internal events
    THESIS_READY     = "thesis_ready"
    CHALLENGE_READY  = "challenge_ready"  # Red Team output
    PROPOSAL         = "order_proposal"
    RISK_VOTE        = "risk_vote"
    FILL             = "fill"
    RISK_BREACH      = "risk_breach"
    BOOK_EMERGENCY   = "book_emergency"   # Book Monitor escalation (stop crossed, halt, etc.)
    KILL_SWITCH      = "kill_switch"


@dataclass
class Event:
    kind: EventKind
    payload: dict[str, Any] = field(default_factory=dict)
    ts: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    source: str = "system"
