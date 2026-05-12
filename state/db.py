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
    "Energies Analyst", "Metals Analyst", "Ag Analyst",
    "Rates Analyst", "FX Futures Analyst", "Index/Macro Analyst",
    # Legacy names kept for historical thesis lookup (decisions table
    # may still hold rows recorded under these prior identities):
    "Grains Analyst", "Livestock Analyst", "Softs Analyst",
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
        self._migrate_columns(conn)

    def _migrate_columns(self, conn: sqlite3.Connection) -> None:
        """Idempotent column additions for existing databases.

        SQLite's CREATE TABLE IF NOT EXISTS won't add new columns to a table
        that already exists, so any column added to schema.sql after the
        first init needs an explicit ALTER TABLE here. Each entry is a
        no-op if the column is already present.
        """
        migrations = [
            ("account_snapshots", "can_trade",
             "ALTER TABLE account_snapshots ADD COLUMN can_trade INTEGER NOT NULL DEFAULT 1"),
        ]
        for table, col, ddl in migrations:
            cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
            if col not in cols:
                conn.execute(ddl)

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

    def first_snapshot_today_utc(self) -> dict[str, Any] | None:
        """Earliest account_snapshot for today (UTC). Used as the start-of-day
        balance anchor when computing realized day P&L."""
        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        row = self.connect().execute(
            "SELECT * FROM account_snapshots WHERE ts LIKE ? "
            "ORDER BY ts ASC LIMIT 1",
            (f"{today}%",),
        ).fetchone()
        return dict(row) if row else None

    def peak_eod_balance(self, *, fallback: float = 0.0) -> float:
        """High-water mark of EOD balances seen so far. Used as the TDD
        anchor (TDD floor = peak − 2000, capped at starting balance)."""
        rows = self.connect().execute(
            "SELECT MAX(balance_usd) AS peak FROM account_snapshots"
        ).fetchone()
        if not rows or rows[0] is None:
            return fallback
        return max(float(rows[0]), fallback)

    def record_account_snapshot(
        self,
        *,
        balance_usd: float,
        environment: str = "combine",
        unrealized_pl_usd: float = 0.0,
        realized_pl_day_usd: float = 0.0,
        trailing_dd_usd: float = 0.0,
        open_contracts_total: int = 0,
        can_trade: bool = True,
    ) -> int:
        """Append a snapshot row. Used by the per-tick capture path."""
        with self.tx() as c:
            cur = c.execute(
                """INSERT INTO account_snapshots
                       (ts, environment, balance_usd, unrealized_pl_usd,
                        realized_pl_day_usd, trailing_dd_usd,
                        open_contracts_total, can_trade)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (utcnow_iso(), environment, balance_usd, unrealized_pl_usd,
                 realized_pl_day_usd, trailing_dd_usd, open_contracts_total,
                 1 if can_trade else 0),
            )
            return int(cur.lastrowid or 0)

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

    # ── Shadow trades (cross-ticker hypothetical signal screening) ──
    def record_shadow_trade(
        self,
        *,
        agent: str,
        symbol: str,
        strategy: str,
        side: str,
        entry_price: float,
        stop_price: float,
        target_price: float,
        shadow_reason: str,
        risk_usd: float | None = None,
        rr_planned: float | None = None,
        conviction: str | None = None,
        horizon: str | None = None,
        notes: str | None = None,
    ) -> int:
        """Record a hypothetical TRIGGER for after-the-fact performance review.

        shadow_reason is one of:
          focus_universe_blocked | risk_block | sector_disabled |
          scout_only | budget_exhausted | duplicate_position
        """
        agent = _canonicalize_agent_name(agent)
        if side not in ("long", "short"):
            raise ValueError(f"side must be 'long' or 'short', got {side!r}")
        with self.tx() as c:
            cur = c.execute(
                """INSERT INTO shadow_trades
                    (ts_signal, agent, symbol, strategy, side,
                     entry_price, stop_price, target_price, risk_usd,
                     rr_planned, conviction, horizon, shadow_reason, notes)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (utcnow_iso(), agent, symbol, strategy, side,
                 entry_price, stop_price, target_price, risk_usd,
                 rr_planned, conviction, horizon, shadow_reason, notes),
            )
            return int(cur.lastrowid or 0)

    def unresolved_shadow_trades(self, *, age_min_minutes: int = 0) -> list[dict[str, Any]]:
        """Return shadow trades with outcome IS NULL.

        age_min_minutes: only return trades older than this (avoids resolving
        trades that haven't had time to play out yet). Comparison is done
        Python-side to keep ISO-8601 timezone formatting consistent with
        utcnow_iso() (SQLite's datetime() strips timezone)."""
        from datetime import datetime, timedelta, timezone
        cutoff = (datetime.now(tz=timezone.utc) - timedelta(minutes=age_min_minutes)
                  ).isoformat(timespec="seconds")
        rows = self.connect().execute(
            """SELECT * FROM shadow_trades
                WHERE outcome IS NULL
                  AND ts_signal <= ?
                ORDER BY ts_signal""",
            (cutoff,),
        ).fetchall()
        return [dict(r) for r in rows]

    def resolve_shadow_trade(
        self,
        shadow_id: int,
        *,
        outcome: str,
        pnl_r: float,
        notes: str | None = None,
        exec_mirror_outcome: str | None = None,
        exec_mirror_pnl_r: float | None = None,
        exec_mirror_notes: str | None = None,
    ) -> None:
        """Set outcome on a shadow trade.

        outcome ∈ target_hit | stop_hit | time_stopped | invalidated (theoretical)
        exec_mirror_outcome ∈ stop_hit | profit_lock | loss_cap | gain_cap |
                              hard_flatten | time_stopped | no_fill | invalidated
                              (what production would have realized — see
                              tools/exec_mirror.py)
        """
        with self.tx() as c:
            c.execute(
                """UPDATE shadow_trades
                      SET ts_resolved=?,
                          outcome=?, pnl_r=?, notes=COALESCE(?, notes),
                          exec_mirror_outcome=COALESCE(?, exec_mirror_outcome),
                          exec_mirror_pnl_r=COALESCE(?, exec_mirror_pnl_r),
                          exec_mirror_notes=COALESCE(?, exec_mirror_notes)
                    WHERE id=?""",
                (utcnow_iso(), outcome, pnl_r, notes,
                 exec_mirror_outcome, exec_mirror_pnl_r, exec_mirror_notes,
                 shadow_id),
            )

    def shadow_trade_stats(self, *, days: int = 14) -> list[dict[str, Any]]:
        """Per-(symbol, strategy) hit-rate + avg R over the last N days.

        Only counts resolved trades. Used by shadow_trade_recap.py to
        recommend candidates for promotion to the active universe.
        """
        from datetime import datetime, timedelta, timezone
        cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=days)
                  ).isoformat(timespec="seconds")
        rows = self.connect().execute(
            """SELECT symbol, strategy,
                      COUNT(*)                                   AS n,
                      SUM(CASE WHEN outcome='target_hit' THEN 1 ELSE 0 END) AS wins,
                      AVG(pnl_r)                                 AS avg_r,
                      MIN(pnl_r)                                 AS min_r,
                      MAX(pnl_r)                                 AS max_r
                 FROM shadow_trades
                WHERE outcome IS NOT NULL
                  AND ts_signal >= ?
                GROUP BY symbol, strategy
                ORDER BY n DESC""",
            (cutoff,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Daily P&L history (Topstep consistency rule) ─────────
    def upsert_daily_pl(
        self,
        *,
        day: str,
        realized_pl_usd: float,
        peak_realized_pl_usd: float | None = None,
        trade_count: int | None = None,
    ) -> None:
        """Finalize a UTC trading day's realized P&L. Idempotent on `day`."""
        with self.tx() as c:
            c.execute(
                """INSERT INTO daily_pl
                       (day, realized_pl_usd, peak_realized_pl_usd, trade_count, closed_at)
                   VALUES (?,?,?,?,?)
                   ON CONFLICT(day) DO UPDATE SET
                       realized_pl_usd      = excluded.realized_pl_usd,
                       peak_realized_pl_usd = excluded.peak_realized_pl_usd,
                       trade_count          = excluded.trade_count,
                       closed_at            = excluded.closed_at""",
                (day, realized_pl_usd, peak_realized_pl_usd, trade_count, utcnow_iso()),
            )

    def daily_pl_history(self, *, exclude_day: str | None = None) -> list[dict[str, Any]]:
        """All finalized daily_pl rows. Optionally exclude a given day
        (used to keep today's running P&L separate from history)."""
        if exclude_day:
            rows = self.connect().execute(
                "SELECT * FROM daily_pl WHERE day != ? ORDER BY day",
                (exclude_day,),
            ).fetchall()
        else:
            rows = self.connect().execute(
                "SELECT * FROM daily_pl ORDER BY day"
            ).fetchall()
        return [dict(r) for r in rows]

    def total_realized_to_date(self, *, exclude_day: str | None = None) -> float:
        """Sum of realized_pl across all finalized daily_pl rows. Used by
        the Topstep consistency-rule advisory check."""
        if exclude_day:
            row = self.connect().execute(
                "SELECT COALESCE(SUM(realized_pl_usd), 0) AS total "
                "FROM daily_pl WHERE day != ?",
                (exclude_day,),
            ).fetchone()
        else:
            row = self.connect().execute(
                "SELECT COALESCE(SUM(realized_pl_usd), 0) AS total FROM daily_pl"
            ).fetchone()
        return float(row[0]) if row else 0.0

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
