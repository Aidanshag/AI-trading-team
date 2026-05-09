"""Tests for the nightly pipeline pieces:
  - economic calendar generator
  - lesson auto-promoter
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from scripts.build_economic_calendar import (
    build_for_date, _events_for_date,
    _first_friday_of_month, _first_business_day_of_month,
)
from scripts.auto_promote_lessons import (
    _parse_front_matter, _eligible_lesson, _has_entry,
)


# ── build_economic_calendar ──────────────────────────────────────

def test_thursday_includes_eia_natgas_and_jobless_claims():
    # 2026-04-30 is a Thursday
    d = datetime(2026, 4, 30, tzinfo=timezone.utc)
    assert d.weekday() == 3
    events = _events_for_date(d)
    names = [e["event"] for e in events]
    assert "Initial Jobless Claims" in names
    assert "EIA Natural Gas Storage" in names


def test_wednesday_includes_eia_crude():
    # 2026-04-29 is a Wednesday
    d = datetime(2026, 4, 29, tzinfo=timezone.utc)
    assert d.weekday() == 2
    events = _events_for_date(d)
    assert any(e["event"] == "EIA Crude Oil Inventory" for e in events)


def test_first_friday_includes_nfp():
    # 2026-05-01 is the first Friday of May 2026
    d = datetime(2026, 5, 1, tzinfo=timezone.utc)
    assert _first_friday_of_month(d) == d
    events = _events_for_date(d)
    assert any("Nonfarm" in e["event"] for e in events)


def test_first_business_day_includes_ism():
    # 2026-06-01 is a Monday → first business day of June
    d = datetime(2026, 6, 1, tzinfo=timezone.utc)
    assert _first_business_day_of_month(d) == d
    events = _events_for_date(d)
    assert any("ISM" in e["event"] for e in events)


def test_saturday_has_no_recurring_events():
    # Saturday — none of the recurring patterns fire
    d = datetime(2026, 5, 2, tzinfo=timezone.utc)  # Saturday
    assert d.weekday() == 5
    events = _events_for_date(d)
    assert events == []


def test_event_ts_is_iso_with_z():
    d = datetime(2026, 4, 30, tzinfo=timezone.utc)
    events = _events_for_date(d)
    for e in events:
        assert e["ts_utc"].endswith("Z")
        # parseable
        datetime.fromisoformat(e["ts_utc"].replace("Z", "+00:00"))


def test_build_for_date_merges_overrides(tmp_path, monkeypatch):
    # Set up a temporary overrides file
    overrides = tmp_path / "overrides.yaml"
    overrides.write_text(yaml.safe_dump({
        "events": [{
            "ts_utc": "2026-04-30T18:00:00Z",
            "impact": "high",
            "event": "Custom Fed Speaker",
            "symbols_affected": ["ZN"],
        }]
    }), encoding="utf-8")
    monkeypatch.setattr("scripts.build_economic_calendar.OVERRIDES", overrides)
    d = datetime(2026, 4, 30, tzinfo=timezone.utc)
    events = build_for_date(d)
    names = [e["event"] for e in events]
    assert "Custom Fed Speaker" in names
    # Recurring events still present
    assert "Initial Jobless Claims" in names


def test_build_for_date_filters_overrides_to_target_day(tmp_path, monkeypatch):
    overrides = tmp_path / "overrides.yaml"
    overrides.write_text(yaml.safe_dump({
        "events": [
            {"ts_utc": "2026-04-30T18:00:00Z", "impact": "high", "event": "On day"},
            {"ts_utc": "2026-05-01T18:00:00Z", "impact": "high", "event": "Next day"},
        ]
    }), encoding="utf-8")
    monkeypatch.setattr("scripts.build_economic_calendar.OVERRIDES", overrides)
    events = build_for_date(datetime(2026, 4, 30, tzinfo=timezone.utc))
    names = [e["event"] for e in events]
    assert "On day" in names
    assert "Next day" not in names


# ── auto_promote_lessons ──────────────────────────────────────────

def test_parse_front_matter_extracts_yaml():
    text = ("---\n"
            "confidence: RULE\n"
            "applies_to_symbol: ZN\n"
            "applies_to_strategy: opening_range_breakout\n"
            "reason: thin overnight\n"
            "---\n\n"
            "Body of the lesson.\n")
    meta = _parse_front_matter(text)
    assert meta["confidence"] == "RULE"
    assert meta["applies_to_symbol"] == "ZN"


def test_parse_front_matter_returns_empty_on_missing_delimiters():
    assert _parse_front_matter("no front matter here") == {}


def test_parse_front_matter_handles_malformed_yaml():
    text = "---\n: : :\n---\nbody"
    meta = _parse_front_matter(text)
    assert isinstance(meta, dict)


def test_eligible_lesson_requires_rule_tier():
    base = {"applies_to_symbol": "ZN", "applies_to_strategy": "orb"}
    assert _eligible_lesson({**base, "confidence": "RULE"}) is True
    assert _eligible_lesson({**base, "confidence": "HARD"}) is True
    assert _eligible_lesson({**base, "confidence": "PATTERN"}) is False
    assert _eligible_lesson({**base, "confidence": "ADVISORY"}) is False


def test_eligible_lesson_requires_both_symbol_and_strategy():
    assert _eligible_lesson({"confidence": "RULE",
                             "applies_to_symbol": "ZN"}) is False
    assert _eligible_lesson({"confidence": "RULE",
                             "applies_to_strategy": "orb"}) is False


def test_has_entry_case_insensitive():
    existing = [{"symbol": "ZN", "strategy": "opening_range_breakout"}]
    assert _has_entry(existing, "ZN", "opening_range_breakout") is True
    assert _has_entry(existing, "zn", "opening_range_breakout") is True  # _has_entry uppercases
    assert _has_entry(existing, "ZN", "vol_regime_trend") is False
    assert _has_entry(existing, "ES", "opening_range_breakout") is False


def test_auto_promote_idempotent_via_module_main(tmp_path, monkeypatch):
    """Running the promoter twice produces the same blacklist content."""
    # Set up isolated lessons + risk_limits
    lessons = tmp_path / "lessons"
    lessons.mkdir()
    (lessons / "zn_orb.md").write_text(
        "---\nconfidence: RULE\napplies_to_symbol: ZN\n"
        "applies_to_strategy: opening_range_breakout\n"
        "reason: test reason\n---\nBody\n",
        encoding="utf-8",
    )
    risk = tmp_path / "risk_limits.yaml"
    risk.write_text(yaml.safe_dump({"strategy_blacklist": []}),
                    encoding="utf-8")

    monkeypatch.setattr("scripts.auto_promote_lessons.LESSONS", lessons)
    monkeypatch.setattr("scripts.auto_promote_lessons.RISK_LIMITS", risk)

    from scripts.auto_promote_lessons import main as promote_main
    import sys

    # First run — adds the entry
    monkeypatch.setattr(sys, "argv", ["x", "--quiet"])
    rc = promote_main()
    assert rc == 0
    cfg = yaml.safe_load(risk.read_text(encoding="utf-8"))
    assert len(cfg["strategy_blacklist"]) == 1

    # Second run — must be idempotent
    monkeypatch.setattr(sys, "argv", ["x", "--quiet"])
    rc = promote_main()
    assert rc == 0
    cfg = yaml.safe_load(risk.read_text(encoding="utf-8"))
    assert len(cfg["strategy_blacklist"]) == 1


def test_auto_promote_skips_advisory_tier(tmp_path, monkeypatch):
    lessons = tmp_path / "lessons"
    lessons.mkdir()
    (lessons / "low.md").write_text(
        "---\nconfidence: ADVISORY\napplies_to_symbol: ZN\n"
        "applies_to_strategy: orb\n---\n",
        encoding="utf-8",
    )
    risk = tmp_path / "risk_limits.yaml"
    risk.write_text(yaml.safe_dump({"strategy_blacklist": []}),
                    encoding="utf-8")
    monkeypatch.setattr("scripts.auto_promote_lessons.LESSONS", lessons)
    monkeypatch.setattr("scripts.auto_promote_lessons.RISK_LIMITS", risk)

    import sys
    from scripts.auto_promote_lessons import main as promote_main
    monkeypatch.setattr(sys, "argv", ["x", "--quiet"])
    promote_main()
    cfg = yaml.safe_load(risk.read_text(encoding="utf-8"))
    assert cfg["strategy_blacklist"] == []
