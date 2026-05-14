"""Account snapshot writer — extracted from live_trader.py.

Per cowork_coordination.md 2026-05-08 priority #6 ("Trim trader: extract
snapshot capture to tools/snapshot_writer.py"). Mirrors the established
extraction pattern (`tools/unrealized_pnl.py:compute_unrealized` was
extracted previously the same way).

PURPOSE:
  Pull broker state (balance, positions, can_trade), compute realized
  + unrealized P&L + trailing drawdown, write one row to
  account_snapshots. On failure, write a "degraded heartbeat" row using
  last-known balance with `can_trade=False` — the trader's snapshot-age
  check stays fresh while the gate refuses new orders.

USAGE (from live_trader.py):
  from tools.snapshot_writer import capture_snapshot
  snap = capture_snapshot(client, account_id)

Why this shape:
  - Single function that returns the snapshot dict (or None on hard fail).
  - Takes broker client + account_id as args; resolves db + config
    inside via the project's standard `get_db()` and yaml loader.
  - No side effects beyond writing to account_snapshots.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from state.db import get_db
from tools.trader_utils import topstep_trading_day_start_utc
from tools.unrealized_pnl import compute_unrealized

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


# Local alias kept for callers that imported the private name; new code
# should use `topstep_trading_day_start_utc` from tools.trader_utils.
_topstep_trading_day_start_utc = topstep_trading_day_start_utc


def _first_snapshot_since(db, boundary_utc: datetime) -> dict | None:
    """First account_snapshot row at or after `boundary_utc`. Used as the
    start-of-trading-day balance anchor. Bypasses the older
    `db.first_snapshot_today_utc` (which anchored at UTC midnight)."""
    iso = boundary_utc.strftime("%Y-%m-%dT%H:%M:%S")
    row = db.connect().execute(
        "SELECT * FROM account_snapshots WHERE ts >= ? "
        "ORDER BY ts ASC LIMIT 1",
        (iso,),
    ).fetchone()
    return dict(row) if row else None


def _load_yaml(rel_path: str) -> dict:
    """Read a project YAML file (relative to repo root). Returns empty
    dict on missing/parse-failure to keep snapshot capture resilient."""
    p = _PROJECT_ROOT / rel_path
    if not p.exists():
        return {}
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def capture_snapshot(client, account_id) -> dict | None:
    """Pull broker state, compute realized P&L, write snapshot row.

    Returns the snapshot summary dict on success, None on hard failure
    (where even the degraded-heartbeat fallback couldn't write).
    """
    db = get_db()
    try:
        accounts = client.get_accounts()
        mine = next(
            (a for a in accounts if str(a.get("id")) == str(account_id)),
            None,
        )
        if not mine:
            return None
        balance = float(mine.get("balance", 0))
        can_trade = bool(mine.get("canTrade", True))
        positions = client.get_positions(account_id) or []
        open_contracts = sum(int(p.get("size") or 0) for p in positions)

        first_today = _first_snapshot_since(db, _topstep_trading_day_start_utc())
        realized_day = (balance - float(first_today["balance_usd"])
                        if first_today else 0.0)
        starting = float(_load_yaml("config/risk_limits.yaml")
                         .get("account", {}).get("starting_balance", 50000))
        peak = db.peak_eod_balance(fallback=starting)
        trailing_dd = max(0.0, peak - balance)

        # Unrealized P&L computed from positions × latest bar mark.
        # Pulling this via the existing helper preserves the
        # 2026-05-05 fix that landed unrealized in snapshots in the
        # first place (see vault/lessons/2026-05-05_*.md).
        unrealized = compute_unrealized(client, positions)

        db.record_account_snapshot(
            balance_usd=balance, environment="combine",
            unrealized_pl_usd=unrealized,
            realized_pl_day_usd=realized_day,
            trailing_dd_usd=trailing_dd,
            open_contracts_total=open_contracts,
            can_trade=can_trade,
        )
        return {
            "balance_usd": balance,
            "realized_pl_day_usd": realized_day,
            "unrealized_pl_usd": unrealized,
            "open_contracts_total": open_contracts,
            "can_trade": can_trade,
        }
    except Exception as e:
        # Degraded-heartbeat fallback. Per the 2026-05-07 fix, when
        # snapshot fetch fails (DNS dropout, broker timeout), we write
        # a synthetic row using last-known balance with can_trade=False.
        # The trader's age-check stays fresh; the gate refuses orders.
        try:
            last = db.latest_account_snapshot()
            if last:
                db.record_account_snapshot(
                    balance_usd=float(last.get("balance_usd") or 0),
                    environment="combine",
                    unrealized_pl_usd=0.0,
                    realized_pl_day_usd=float(last.get("realized_pl_day_usd") or 0),
                    trailing_dd_usd=float(last.get("trailing_dd_usd") or 0),
                    open_contracts_total=int(last.get("open_contracts_total") or 0),
                    can_trade=False,
                )
        except Exception:
            pass
        # Surface the original error to the caller's logger without
        # raising — snapshot loop should keep going.
        try:
            from scripts.live_trader import _log  # type: ignore
            _log(f"snapshot capture failed: {type(e).__name__}: {e}")
        except Exception:
            pass
        return None
