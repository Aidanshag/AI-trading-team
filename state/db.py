"""SQLite state store.

Single-writer discipline: all writes go through the `state_store` MCP server.
Readers (risk hook, agents via tools) use the same `Database` class but
should never call `execute` directly — use the typed helpers.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
DEFAULT_DB_PATH = Path(os.environ.get("DB_PATH", "./state/fund.db"))


def utcnow_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


# Canonical agent names — the form the orchestrator uses for wake_agent
# and the form _latest_thesis_for / chain helpers expect. record_decision
# normalizes any input to one of these. Add new agents to this set.
_CANONICAL_AGENT_NAMES = frozenset({
    "CIO", "Portfolio Manager", "Risk Manager", "Options Risk",
    "Execution Trader", "Compliance",
    "Research", "Red Team", "Book Monitor", "Diamond Hunter",
    "Fund Engineer", "Quant Researcher", "Macro Strategist",
    "Flow Analyst", "Volatility Strategist", "Edge Hunter",
    "Energies Analyst", "Metals Analyst", "Grains Analyst",
    "Softs Analyst", "Livestock Analyst", "Rates Analyst",
    "FX Futures Analyst", "Index/Macro Analyst",
    # Pseudo-agents used by the orchestrator + driver scripts:
    "orchestrator", "manual_pm_bypass",
    # Retired 2026-04-27 (equities desk dormant): Equity PM, Equity
    # Execution Trader, Cyclicals/Defensive/Financials/Growth-Tech
    # Analysts, Single-Name Options Specialist, Execution Specialist.
})


def _canonicalize_agent_name(agent: str) -> str:
    """Map any case/separator variant to the canonical form.

    Examples:
      "quant_researcher"     → "Quant Researcher"
      "QUANT RESEARCHER"     → "Quant Researcher"
      "Quant-Researcher"     → "Quant Researcher"
      "RiskManager"          → "Risk Manager" (camelCase split)
      "manual_injection"     → "manual_injection" (unmapped, preserve)
    """
    if not agent:
        return agent
    # Already canonical?
    if agent in _CANONICAL_AGENT_NAMES:
        return agent

    # Build a normalized lookup: lowercase, strip separators
    def _norm(s: str) -> str:
        s = s.lower()
        for ch in ("_", "-", "/", " ", "."):
            s = s.replace(ch, "")
        return s

    target = _norm(agent)
    for canonical in _CANONICAL_AGENT_NAMES:
        if _norm(canonical) == target:
            return canonical
    # Unknown agent — preserve as-is (could be a manual_injection or
    # custom test agent). Better to log it than to silently drop.
    return agent


class Database:
    def __init__(self, path: Path | str = DEFAULT_DB_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    # ── lifecycle ─────────────────────────────────────────────
    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.path, isolation_level=None)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def init_schema(self) -> None:
        conn = self.connect()
        conn.executescript(SCHEMA_PATH.read_text())

    @contextmanager
    def tx(self):
        conn = self.connect()
        try:
            conn.execute("BEGIN")
            yield conn
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    # ── typed helpers (extend as needed) ─────────────────────
    def latest_account_snapshot(self) -> dict[str, Any] | None:
        row = self.connect().execute(
            "SELECT * FROM account_snapshots ORDER BY ts DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    def current_positions(self) -> list[dict[str, Any]]:
        rows = self.connect().execute("SELECT * FROM positions").fetchall()
        return [dict(r) for r in rows]

    def realized_pl_today(self) -> float:
        snap = self.latest_account_snapshot()
        return float(snap["realized_pl_day_usd"]) if snap else 0.0

    def record_decision(
        self,
        agent: str,
        kind: str,
        summary: str,
        rationale: str,
        *,
        symbol: str | None = None,
        vault_path: str | None = None,
        model: str | None = None,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
    ) -> int:
        # Normalize agent name to canonical form ("Quant Researcher",
        # "Risk Manager", etc) regardless of how the caller wrote it.
        # Catches the bug where agents called state_record_decision with
        # snake_case or lowercase names and the chain couldn't find them.
        agent = _canonicalize_agent_name(agent)
        with self.tx() as c:
            cur = c.execute(
                """INSERT INTO decisions
                    (ts, agent, kind, symbol, summary, rationale, vault_path,
                     model, tokens_in, tokens_out)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (utcnow_iso(), agent, kind, symbol, summary, rationale,
                 vault_path, model, tokens_in, tokens_out),
            )
            return int(cur.lastrowid or 0)

    def record_risk_event(
        self,
        severity: str,
        rule: str,
        *,
        agent: str | None = None,
        order_id: int | None = None,
        detail: str | dict | None = None,
    ) -> int:
        if isinstance(detail, dict):
            detail = json.dumps(detail)
        with self.tx() as c:
            cur = c.execute(
                """INSERT INTO risk_events (ts, severity, rule, agent, order_id, detail)
                   VALUES (?,?,?,?,?,?)""",
                (utcnow_iso(), severity, rule, agent, order_id, detail),
            )
            return int(cur.lastrowid or 0)


_DB: Database | None = None


def get_db() -> Database:
    global _DB
    if _DB is None:
        _DB = Database()
    return _DB


def _cli() -> int:
    if len(sys.argv) < 2 or sys.argv[1] != "init":
        print("usage: python -m state.db init")
        return 2
    db = get_db()
    db.init_schema()
    print(f"Initialized schema at {db.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
