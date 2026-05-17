"""Tests for tools/trader_utils symbol alias canonicalization."""
from __future__ import annotations

import pytest

from tools.trader_utils import (
    _tick_size, _tick_value, _canonicalize_symbol,
    _SYMBOL_ALIAS_TO_CANONICAL,
)


def test_canonical_symbol_passes_through():
    """6E stays 6E, not aliased."""
    assert _canonicalize_symbol("6E") == "6E"
    assert _canonicalize_symbol("GC") == "GC"
    assert _canonicalize_symbol("MGC") == "MGC"


def test_topstep_alias_resolves_to_canonical():
    for alias, canon in _SYMBOL_ALIAS_TO_CANONICAL.items():
        assert _canonicalize_symbol(alias) == canon, \
            f"{alias} should canonicalize to {canon}"


def test_eu6_tick_size_matches_6e():
    """EU6 (Topstep root) and 6E (CME canonical) must return same tick econ."""
    assert _tick_size("EU6") == _tick_size("6E")
    assert _tick_value("EU6") == _tick_value("6E")


def test_bp6_tick_size_matches_6b():
    assert _tick_size("BP6") == _tick_size("6B")
    assert _tick_value("BP6") == _tick_value("6B")


def test_zce_tick_size_matches_zc():
    assert _tick_size("ZCE") == _tick_size("ZC")
    assert _tick_value("ZCE") == _tick_value("ZC")


def test_alias_returns_nonzero_for_known_symbols():
    """The 2026-05-14 EU6 incident was caused by EU6 returning 0/default
    tick economics. This guards against that recurring."""
    for alias in ["EU6", "BP6", "JY6", "DA6", "CA6", "ZCE", "GLE", "CPE"]:
        assert _tick_size(alias) > 0, f"{alias} tick_size should be > 0"
        assert _tick_value(alias) > 0, f"{alias} tick_value should be > 0"


def test_unknown_symbol_returns_defaults():
    """Truly unknown symbol → default tick_size=0.01, tick_value=0.0."""
    assert _tick_size("UNKNOWN_XYZ") == 0.01
    assert _tick_value("UNKNOWN_XYZ") == 0.0
