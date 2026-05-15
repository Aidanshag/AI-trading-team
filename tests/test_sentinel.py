"""Tests for tools/sentinel.py — anomaly watcher invariants.

Each check is tested with an injectable broker / DB so no real API
calls happen during pytest.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools import sentinel as sn  # noqa: E402


@pytest.fixture
def inmem_db():
    """In-memory SQLite with the orders + decisions schema (subset)."""
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_order_id TEXT,
            agent TEXT, ts_proposed TEXT, ts_submitted TEXT,
            ts_filled TEXT, ts_cancelled TEXT,
            symbol TEXT, contract_month TEXT, side TEXT,
            order_type TEXT, qty INTEGER,
            limit_price REAL, stop_price REAL,
            status TEXT, risk_verdict TEXT, risk_reason TEXT,
            broker_order_id TEXT, avg_fill_price REAL, structure_id TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT, agent TEXT, kind TEXT, symbol TEXT,
            summary TEXT, rationale TEXT, vault_path TEXT,
            model TEXT, tokens_in INTEGER, tokens_out INTEGER
        )
    """)
    yield conn
    conn.close()


# ── check_mock_orders_in_db ───────────────────────────────────────

def test_check_mock_orders_clean_db(inmem_db):
    """Empty DB → no findings."""
    findings = sn.check_mock_orders_in_db(inmem_db)
    assert findings == []


def test_check_mock_orders_finds_polluted_db(inmem_db):
    """One mock_ order → critical finding."""
    inmem_db.execute(
        "INSERT INTO orders (client_order_id, broker_order_id, ts_proposed) "
        "VALUES (?, ?, ?)",
        ("live_real_abc", "mock_42", "2026-05-15T03:00:00+00:00"),
    )
    inmem_db.commit()
    findings = sn.check_mock_orders_in_db(inmem_db)
    assert len(findings) == 1
    assert findings[0].severity == "crit"
    assert findings[0].check_name == "mock_orders_in_db"
    assert findings[0].detail["count"] == 1


def test_check_mock_orders_catches_client_id_variant(inmem_db):
    """mock_ in client_order_id (not just broker_order_id) also flagged."""
    inmem_db.execute(
        "INSERT INTO orders (client_order_id, broker_order_id, ts_proposed) "
        "VALUES (?, ?, ?)",
        ("mock_42", "real_123", "2026-05-15T03:00:00+00:00"),
    )
    inmem_db.commit()
    findings = sn.check_mock_orders_in_db(inmem_db)
    assert len(findings) == 1


# ── check_open_position_economics ─────────────────────────────────

def test_check_economics_clean_when_known_symbol(inmem_db):
    """Open MGC position with known economics → no findings."""
    positions = [{"contractId": "CON.F.US.MGC.M26", "size": 1, "type": 1}]
    findings = sn.check_open_position_economics(
        inmem_db, get_positions=lambda: positions
    )
    assert findings == []


def test_check_economics_clean_with_eu6_after_alias_landed(inmem_db):
    """EU6 (Topstep alias for 6E) — should resolve after the 2026-05-15
    alias fix (e8eddbe). Regression-guard for that fix."""
    positions = [{"contractId": "CON.F.US.EU6.M26", "size": 1, "type": 2}]
    findings = sn.check_open_position_economics(
        inmem_db, get_positions=lambda: positions
    )
    assert findings == [], (
        f"EU6 should resolve to (0.00005, 6.25) after the 2026-05-15 alias "
        f"fix. If this fires, the alias regressed. findings={findings}"
    )


def test_check_economics_flags_unknown_symbol(inmem_db):
    """Bogus contract that doesn't resolve → critical."""
    positions = [{"contractId": "CON.F.US.XYZBOGUS.M26", "size": 1, "type": 1}]
    findings = sn.check_open_position_economics(
        inmem_db, get_positions=lambda: positions
    )
    assert len(findings) == 1
    assert findings[0].severity == "crit"
    assert findings[0].check_name == "open_position_economics"


def test_check_economics_ignores_flat_positions(inmem_db):
    """size=0 means the position is closed/flat — not a real open."""
    positions = [{"contractId": "CON.F.US.XYZBOGUS.M26", "size": 0, "type": 1}]
    findings = sn.check_open_position_economics(
        inmem_db, get_positions=lambda: positions
    )
    assert findings == []


# ── check_orphan_working_orders ───────────────────────────────────

def test_check_orphans_clean_when_stop_matches_position():
    """Stop with matching open position → no orphan."""
    positions = [{"contractId": "CON.F.US.MGC.M26", "size": 1}]
    working = [{"contractId": "CON.F.US.MGC.M26",
                 "customTag": "live_abc123_stop", "type": 4}]
    findings = sn.check_orphan_working_orders(
        get_positions=lambda: positions,
        get_working_orders=lambda: working,
    )
    assert findings == []


def test_check_orphans_flags_stop_without_position():
    """Stop tagged live_*_stop with no matching open position → critical."""
    positions = []
    working = [{"contractId": "CON.F.US.MGC.M26",
                 "customTag": "live_abc123_stop", "type": 4,
                 "stopPrice": 4700.0}]
    findings = sn.check_orphan_working_orders(
        get_positions=lambda: positions,
        get_working_orders=lambda: working,
    )
    assert len(findings) == 1
    assert findings[0].severity == "crit"


def test_check_orphans_ignores_non_live_tags():
    """Working orders with tags that aren't 'live_*_stop' aren't ours."""
    positions = []
    working = [{"contractId": "CON.F.US.MGC.M26",
                 "customTag": "manual_stop_xyz", "type": 4}]
    findings = sn.check_orphan_working_orders(
        get_positions=lambda: positions,
        get_working_orders=lambda: working,
    )
    assert findings == []


# ── check_duplicate_trader_procs ──────────────────────────────────

def test_check_duplicates_clean_single_instance():
    """1 PID = healthy single instance."""
    findings = sn.check_duplicate_trader_procs(ps_command_runner=lambda: [27652])
    assert findings == []


def test_check_duplicates_clean_parent_child():
    """2 PIDs = Windows parent + child for I/O redirection. Healthy."""
    findings = sn.check_duplicate_trader_procs(
        ps_command_runner=lambda: [27652, 29776]
    )
    assert findings == []


def test_check_duplicates_flags_3_or_more():
    """3+ PIDs = race risk. Critical."""
    findings = sn.check_duplicate_trader_procs(
        ps_command_runner=lambda: [27652, 29776, 31000, 31001]
    )
    assert len(findings) == 1
    assert findings[0].severity == "crit"
    assert findings[0].check_name == "duplicate_trader_procs"


# ── check_close_slippage_vs_floor ─────────────────────────────────

def test_check_slippage_clean_when_realized_at_floor(inmem_db):
    """Close at exactly the floor → no slippage flag."""
    # Peak $100 → continuous floor $70. Realized $70.
    inmem_db.execute(
        "INSERT INTO decisions (ts, agent, kind, symbol, rationale) "
        "VALUES (?, 'profit_lock', 'close', 'MGC', "
        "'profit_lock close: peak=$100.00 realized=$70.00 reason=trailing_lock')",
        ("2026-05-15T03:00:00+00:00",),
    )
    inmem_db.commit()
    findings = sn.check_close_slippage_vs_floor(inmem_db)
    assert findings == []


def test_check_slippage_flags_significant_drop_past_floor(inmem_db):
    """Peak $100 (floor $70), realized $40 — $30 slippage past floor."""
    inmem_db.execute(
        "INSERT INTO decisions (ts, agent, kind, symbol, rationale) "
        "VALUES (?, 'profit_lock', 'close', 'MGC', "
        "'profit_lock close: peak=$100.00 realized=$40.00 reason=trailing_lock')",
        ("2026-05-15T03:00:00+00:00",),
    )
    inmem_db.commit()
    findings = sn.check_close_slippage_vs_floor(inmem_db)
    assert len(findings) == 1
    assert findings[0].severity == "warn"
    assert findings[0].detail["slippage_usd"] == 30.0


# ── run_all_checks aggregator ─────────────────────────────────────

def test_run_all_checks_returns_list_without_crashing(monkeypatch, tmp_path):
    """End-to-end: run_all_checks shouldn't crash on a clean DB.
    We can't fully mock the broker without significant work, so this
    just confirms the function returns a list."""
    # Point sentinel at a fresh in-memory DB by temporarily replacing
    # the path constant.
    db_file = tmp_path / "sentinel_test.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            client_order_id TEXT, broker_order_id TEXT, ts_proposed TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE decisions (
            id INTEGER PRIMARY KEY, ts TEXT, agent TEXT, kind TEXT,
            symbol TEXT, rationale TEXT
        )
    """)
    conn.commit()
    conn.close()
    monkeypatch.setattr(sn, "_DB_PATH", db_file)
    # Stub out the broker-touching checks (they'd raise without real auth)
    monkeypatch.setattr(sn, "check_open_position_economics",
                          lambda *a, **k: [])
    monkeypatch.setattr(sn, "check_orphan_working_orders",
                          lambda *a, **k: [])
    monkeypatch.setattr(sn, "check_duplicate_trader_procs",
                          lambda *a, **k: [])
    findings = sn.run_all_checks()
    assert isinstance(findings, list)


def test_main_dry_run_exits_zero_on_clean(monkeypatch, tmp_path, capsys):
    """--dry path doesn't post Discord; returns 0 on clean."""
    monkeypatch.setattr(sn, "run_all_checks", lambda: [])
    rc = sn.main(["--dry"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "0 finding" in out


def test_main_returns_one_on_critical(monkeypatch):
    """Critical finding → exit code 1."""
    monkeypatch.setattr(sn, "run_all_checks", lambda: [
        sn.Finding(check_name="test", severity="crit", summary="test crit"),
    ])
    rc = sn.main(["--dry"])
    assert rc == 1
