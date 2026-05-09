"""Tests for scripts/cell_auto_promote.py.

Safety-critical because the script writes to state/strategy_validation.json
which is the live trader's source of truth for what fires.

Coverage:
  - Atomic write doesn't corrupt the target file
  - Promote fires only when (n>=10, live_E>0, |live-OOS|<1.0R)
  - Demote fires only when (n>=10, live_E<0, streak>=3)
  - User pin override blocks promotion outside the filter
  - Insufficient n → hold
  - Cell already in live_allowlist isn't double-added
  - Cell already shadow isn't double-removed
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import cell_auto_promote as cap


def _make_validation(filter_strats=None, filter_syms=None,
                     live_cells=None, oos_map=None) -> dict:
    """Build a minimal validation payload for tests."""
    fl = []
    if filter_strats:
        fl.append({"strategy": filter_strats[0],
                   "symbols": filter_syms or [],
                   "rationale": "test"})
    return {
        "version": 1,
        "live_strategies_filter": fl,
        "live_allowlist": list(live_cells or []),
        "live_allowlist_generated_at": "2026-05-08T00:00:00+00:00",
        "cells": oos_map or {},
        "history": [],
    }


def _live_payload(by_cell: dict) -> dict:
    return {"date": "2026-05-08", "trades_evaluated": sum(c["n"] for c in by_cell.values()),
            "by_cell": by_cell, "underperforming": []}


class TestPromotionRules(unittest.TestCase):
    """Promote shadow → live: n>=10, live_E>0, |live-OOS|<1.0."""

    def setUp(self):
        # Filter: gap_fill × ZN allowed; everything else outside pin
        self.validation = _make_validation(
            filter_strats=["gap_fill"], filter_syms=["ZN"],
            live_cells=[],
            oos_map={
                "gap_fill|ZN|Asian|long":     {"oos": {"e": 1.10}},
                "gap_fill|ZN|Asian|short":    {"oos": {"e": 1.20}},
                "gap_fill|MNQ|Asian|long":    {"oos": {"e": 0.50}},
                "narrow_range_break|GC|Asian|short": {"oos": {"e": 0.50}},
            },
        )

    def test_promote_fires_when_all_conditions_met(self):
        live = _live_payload({
            "gap_fill|ZN|Asian|long": {"n": 12, "live_mean_r": 0.95}
        })
        decisions = cap.evaluate_cells(self.validation, live, min_n=10,
                                       oos_gap=1.0, window_days=30)
        promote = [d for d in decisions if d["action"] == "promote"]
        self.assertEqual(len(promote), 1)
        self.assertEqual(promote[0]["cell"], "gap_fill|ZN|Asian|long")

    def test_no_promote_below_min_n(self):
        live = _live_payload({
            "gap_fill|ZN|Asian|long": {"n": 9, "live_mean_r": 0.95}
        })
        decisions = cap.evaluate_cells(self.validation, live, min_n=10,
                                       oos_gap=1.0, window_days=30)
        self.assertFalse(any(d["action"] == "promote" for d in decisions))

    def test_no_promote_when_live_e_negative(self):
        live = _live_payload({
            "gap_fill|ZN|Asian|long": {"n": 12, "live_mean_r": -0.10}
        })
        decisions = cap.evaluate_cells(self.validation, live, min_n=10,
                                       oos_gap=1.0, window_days=30)
        self.assertFalse(any(d["action"] == "promote" for d in decisions))

    def test_no_promote_when_gap_too_wide(self):
        # OOS=1.10, live=2.50 → gap=1.40 > 1.0 → reject
        live = _live_payload({
            "gap_fill|ZN|Asian|long": {"n": 12, "live_mean_r": 2.50}
        })
        decisions = cap.evaluate_cells(self.validation, live, min_n=10,
                                       oos_gap=1.0, window_days=30)
        promote = [d for d in decisions if d["action"] == "promote"]
        self.assertEqual(len(promote), 0)

    def test_user_pin_blocks_promotion_outside_filter(self):
        # gap_fill|MNQ is OUTSIDE the user's pin (gap_fill × {ZN})
        live = _live_payload({
            "gap_fill|MNQ|Asian|long": {"n": 12, "live_mean_r": 0.50}
        })
        decisions = cap.evaluate_cells(self.validation, live, min_n=10,
                                       oos_gap=1.0, window_days=30)
        self.assertFalse(any(d["action"] == "promote" for d in decisions))
        # Verify reason cites the pin
        d = next(d for d in decisions if d["cell"] == "gap_fill|MNQ|Asian|long")
        self.assertIn("pin", d["reason"].lower())

    def test_no_promote_if_already_in_allowlist(self):
        self.validation["live_allowlist"] = [{
            "strategy": "gap_fill", "symbol": "ZN",
            "session": "Asian", "side": "long",
        }]
        live = _live_payload({
            "gap_fill|ZN|Asian|long": {"n": 12, "live_mean_r": 0.95}
        })
        decisions = cap.evaluate_cells(self.validation, live, min_n=10,
                                       oos_gap=1.0, window_days=30)
        # Already in allowlist → routed to demotion path; live_e>0 → hold
        self.assertFalse(any(d["action"] == "promote" for d in decisions))


class TestDemotionRules(unittest.TestCase):
    """Demote live → shadow: n>=10, live_E<0, streak>=3."""

    def setUp(self):
        self.validation = _make_validation(
            filter_strats=["gap_fill"], filter_syms=["ZN", "ZB"],
            live_cells=[
                {"strategy": "gap_fill", "symbol": "ZN",
                 "session": "Asian", "side": "long"},
                {"strategy": "gap_fill", "symbol": "ZB",
                 "session": "Asian", "side": "short"},
            ],
            oos_map={
                "gap_fill|ZN|Asian|long":   {"oos": {"e": 1.10}},
                "gap_fill|ZB|Asian|short":  {"oos": {"e": 1.19}},
            },
        )

    @patch("scripts.cell_auto_promote.consecutive_losers_for_cell",
           return_value=4)
    def test_demote_fires_when_all_conditions_met(self, _streak):
        live = _live_payload({
            "gap_fill|ZN|Asian|long": {"n": 15, "live_mean_r": -0.5}
        })
        decisions = cap.evaluate_cells(self.validation, live, min_n=10,
                                       oos_gap=1.0, window_days=30)
        demote = [d for d in decisions if d["action"] == "demote"]
        self.assertEqual(len(demote), 1)

    @patch("scripts.cell_auto_promote.consecutive_losers_for_cell",
           return_value=2)
    def test_no_demote_when_streak_below_threshold(self, _streak):
        live = _live_payload({
            "gap_fill|ZN|Asian|long": {"n": 15, "live_mean_r": -0.5}
        })
        decisions = cap.evaluate_cells(self.validation, live, min_n=10,
                                       oos_gap=1.0, window_days=30)
        self.assertFalse(any(d["action"] == "demote" for d in decisions))

    @patch("scripts.cell_auto_promote.consecutive_losers_for_cell",
           return_value=4)
    def test_no_demote_when_live_e_positive(self, _streak):
        live = _live_payload({
            "gap_fill|ZN|Asian|long": {"n": 15, "live_mean_r": 0.5}
        })
        decisions = cap.evaluate_cells(self.validation, live, min_n=10,
                                       oos_gap=1.0, window_days=30)
        self.assertFalse(any(d["action"] == "demote" for d in decisions))


class TestApplyAndAtomicWrite(unittest.TestCase):
    """Verify apply_decisions mutates correctly and write_atomic is safe."""

    def test_apply_promote_appends_cell(self):
        v = _make_validation(filter_strats=["gap_fill"],
                             filter_syms=["ZN"], live_cells=[])
        decisions = [{
            "cell": "gap_fill|ZN|Asian|long", "action": "promote",
            "live_n": 12, "live_e": 0.95, "oos_e": 1.10, "reason": "test",
        }]
        new_v, n_pro, n_dem = cap.apply_decisions(v, decisions)
        self.assertEqual(n_pro, 1)
        self.assertEqual(n_dem, 0)
        self.assertEqual(len(new_v["live_allowlist"]), 1)
        self.assertEqual(new_v["live_allowlist"][0]["symbol"], "ZN")

    def test_apply_demote_removes_cell(self):
        v = _make_validation(
            filter_strats=["gap_fill"], filter_syms=["ZN", "ZB"],
            live_cells=[
                {"strategy": "gap_fill", "symbol": "ZN",
                 "session": "Asian", "side": "long"},
                {"strategy": "gap_fill", "symbol": "ZB",
                 "session": "Asian", "side": "short"},
            ],
        )
        decisions = [{
            "cell": "gap_fill|ZN|Asian|long", "action": "demote",
            "live_n": 12, "live_e": -0.5, "oos_e": 1.10, "reason": "test",
        }]
        new_v, n_pro, n_dem = cap.apply_decisions(v, decisions)
        self.assertEqual(n_pro, 0)
        self.assertEqual(n_dem, 1)
        # Only ZB remains
        self.assertEqual(len(new_v["live_allowlist"]), 1)
        self.assertEqual(new_v["live_allowlist"][0]["symbol"], "ZB")

    def test_atomic_write_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "validation.json"
            # Patch the module-level path to point at our temp file
            old = cap.VALIDATION_PATH
            try:
                cap.VALIDATION_PATH = target
                payload = _make_validation()
                cap.write_atomic(payload)
                self.assertTrue(target.exists())
                # Write again with different content — file should fully replace
                payload["live_allowlist_generated_at"] = "REWRITTEN"
                cap.write_atomic(payload)
                loaded = json.loads(target.read_text(encoding="utf-8"))
                self.assertEqual(loaded["live_allowlist_generated_at"], "REWRITTEN")
            finally:
                cap.VALIDATION_PATH = old

    def test_atomic_write_no_partial_file_on_crash(self):
        """If json.dump crashes mid-write, the original file is untouched."""
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "validation.json"
            old = cap.VALIDATION_PATH
            try:
                cap.VALIDATION_PATH = target
                # Write good baseline
                cap.write_atomic({"baseline": True})
                self.assertTrue(target.exists())
                baseline = target.read_text(encoding="utf-8")
                # Now attempt write that fails inside json.dump
                class Unserializable:
                    pass
                bad_payload = {"obj": Unserializable()}
                with self.assertRaises(TypeError):
                    cap.write_atomic(bad_payload)
                # Original file should be unchanged (atomic write safety)
                self.assertEqual(target.read_text(encoding="utf-8"), baseline)
            finally:
                cap.VALIDATION_PATH = old


class TestOOSExpectancyExtraction(unittest.TestCase):
    """Verify get_oos_e handles common cell-record shapes."""

    def test_nested_oos_e(self):
        cells = {"gap_fill|ZN|Asian|long": {"oos": {"e": 1.10}}}
        self.assertAlmostEqual(cap.get_oos_e(cells, "gap_fill|ZN|Asian|long"), 1.10)

    def test_walk_forward_nested(self):
        cells = {"foo|X|Y|long": {"walk_forward": {"oos": {"e": 0.85}}}}
        self.assertAlmostEqual(cap.get_oos_e(cells, "foo|X|Y|long"), 0.85)

    def test_flat_e(self):
        cells = {"foo|X|Y|long": {"e": 1.50}}
        self.assertAlmostEqual(cap.get_oos_e(cells, "foo|X|Y|long"), 1.50)

    def test_missing_returns_none(self):
        self.assertIsNone(cap.get_oos_e({}, "absent"))


if __name__ == "__main__":
    unittest.main()
