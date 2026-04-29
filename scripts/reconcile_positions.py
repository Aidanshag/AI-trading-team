"""Position reconciliation — DB ↔ broker truth.

Trusts the broker. For each broker-side position, ensure a matching row
in `positions`. For each DB row not matching a broker position, mark
closed. Surfaces every drift as a `risk_event` so we know our state
store ever fell out of sync.

Usage:
  python -m scripts.reconcile_positions [--quiet]

Wired into the orchestrator's per-tick safety chain (runs BEFORE
verify_position_stops so the stop-check operates on accurate state).
"""
from __future__ import annotations

import argparse
import sys
from typing import Any

from state.db import get_db, utcnow_iso
from tools.projectx_client import ProjectXError, get_client


def _broker_positions() -> list[dict[str, Any]]:
    """Return broker positions normalized to the shape we store."""
    from tools.topstep import get_account_id  # lazy: env may not be ready
    client = get_client()
    raw = client.get_positions(get_account_id())
    out = []
    for p in raw:
        contract = p.get("contractId") or p.get("contract") or ""
        if not contract:
            continue
        size = int(p.get("size") or p.get("netQuantity") or 0)
        if size == 0:
            continue
        # ProjectX type: 1=long, 2=short
        type_code = int(p.get("type") or 0)
        side = "long" if type_code == 1 else "short" if type_code == 2 else None
        if side is None:
            # Some endpoints return positive=long, negative=short on size
            side = "long" if size > 0 else "short"
            size = abs(size)
        out.append({
            "contract_id": str(contract),
            "symbol": _root(contract),
            "side": side,
            "contracts": size,
            "avg_price": float(p.get("avgPrice") or p.get("averagePrice") or 0.0),
        })
    return out


def _root(contract_id: str) -> str:
    """Extract the trading root from a ProjectX contract id like
    'CON.F.US.TYA.M26' → 'TYA' → mapped to our 'ZN'."""
    from hooks.risk_gate import _normalize_root
    parts = str(contract_id).split(".")
    for tok in parts[::-1]:
        # Skip month-year suffix like 'M26', 'Z25'
        if len(tok) <= 3 and tok and tok[0].isalpha() and tok[1:].isdigit():
            continue
        if tok in ("CON", "F", "US", ""):
            continue
        return _normalize_root(tok)
    return contract_id


def reconcile(verbose: bool = True) -> dict[str, Any]:
    db = get_db()
    try:
        broker = _broker_positions()
    except ProjectXError as e:
        return {"status": "broker_unavailable", "error": str(e)}
    except Exception as e:
        return {"status": "error", "error": str(e)}

    db_rows = db.current_positions()
    drifts: list[dict[str, Any]] = []

    # Index DB by (symbol, side) — UNIQUE in schema
    by_db = {(r["symbol"], r["side"]): r for r in db_rows}
    by_brk = {(p["symbol"], p["side"]): p for p in broker}

    # 1. Broker has it, DB doesn't → INSERT
    for key, p in by_brk.items():
        if key in by_db:
            # Both sides exist — verify size + avg price
            db_row = by_db[key]
            if int(db_row["contracts"]) != p["contracts"]:
                drifts.append({
                    "kind": "size_mismatch",
                    "symbol": p["symbol"], "side": p["side"],
                    "db": db_row["contracts"], "broker": p["contracts"],
                })
                with db.tx() as c:
                    c.execute(
                        "UPDATE positions SET contracts=?, avg_price=? "
                        "WHERE symbol=? AND side=?",
                        (p["contracts"], p["avg_price"], p["symbol"], p["side"]),
                    )
            continue
        drifts.append({
            "kind": "broker_only",
            "symbol": p["symbol"], "side": p["side"],
            "contracts": p["contracts"], "avg_price": p["avg_price"],
        })
        with db.tx() as c:
            c.execute(
                """INSERT OR IGNORE INTO positions
                    (symbol, contract_month, side, contracts, avg_price, opened_at)
                   VALUES (?,?,?,?,?,?)""",
                (p["symbol"], None, p["side"], p["contracts"], p["avg_price"],
                 utcnow_iso()),
            )

    # 2. DB has it, broker doesn't → DELETE (closed at broker, never recorded)
    closures: list[dict[str, Any]] = []
    for key, db_row in by_db.items():
        if key in by_brk:
            continue
        closure = {
            "kind": "db_only_stale",
            "symbol": db_row["symbol"], "side": db_row["side"],
            "contracts": db_row["contracts"],
        }
        drifts.append(closure)
        closures.append(closure)
        with db.tx() as c:
            c.execute(
                "DELETE FROM positions WHERE symbol=? AND side=?",
                (db_row["symbol"], db_row["side"]),
            )

    # 2b. Closure classification — for each closed position, query broker
    # order history to see if a STOP order filled in the last hour. If so,
    # emit `stop_hit_observed` so the post-stop cooldown engages.
    if closures:
        try:
            _emit_stop_hit_signals(closures)
        except Exception as e:
            db.record_risk_event(
                severity="warn", rule="stop_classification_failed",
                agent="reconciler", detail={"error": str(e)[:300]},
            )

    # 3. Surface every drift as a risk_event
    for d in drifts:
        sev = "warn" if d["kind"] == "size_mismatch" else "info"
        db.record_risk_event(
            severity=sev, rule="position_drift",
            agent="reconciler", detail=d,
        )

    if verbose and drifts:
        print(f"reconcile: {len(drifts)} drift(s) repaired")
        for d in drifts:
            print(f"  {d}")
    return {"status": "ok", "drifts": drifts, "broker_count": len(broker),
            "db_count": len(db_rows)}


def _emit_stop_hit_signals(closures: list[dict[str, Any]]) -> None:
    """For each just-closed position, look at broker order history. If a
    STOP-type order filled within the last 60 minutes for that contract,
    emit `stop_hit_observed` so the anti-tilt cooldown engages.

    Single API call per reconcile, regardless of closure count — caller
    pulls history once, then matches per-closure.
    """
    from datetime import datetime, timedelta, timezone
    from tools.topstep import get_account_id
    db = get_db()
    client = get_client()
    start_ts = (datetime.now(tz=timezone.utc) - timedelta(minutes=60)
                ).isoformat(timespec="seconds")
    try:
        history = client.get_order_history(get_account_id(), start_timestamp=start_ts)
    except Exception:
        return  # broker unavailable; under-trigger silently
    # ProjectX order types: 1=market, 2=limit, 3=stop, 4=stop_limit, 5=trailing_stop
    STOP_TYPES = {3, 4, 5}
    # ProjectX status: filled is typically 2; we tolerate either int code
    # or string label since ProjectX has documented both.
    def _is_filled(o: dict) -> bool:
        s = o.get("status")
        if isinstance(s, int):
            return s == 2
        return str(s or "").lower() in ("filled", "fully_filled", "complete")

    closure_roots = {(c["symbol"], c["side"]) for c in closures}
    for o in history or []:
        if not _is_filled(o):
            continue
        if int(o.get("type") or 0) not in STOP_TYPES:
            continue
        contract = str(o.get("contractId") or o.get("contract") or "")
        sym = _root(contract) if contract else None
        if not sym:
            continue
        # ProjectX side: 0=buy, 1=sell. A stop SELL closes a long; stop BUY
        # closes a short. Map back to the original position side that closed.
        order_side = int(o.get("side") or 0)
        closed_position_side = "long" if order_side == 1 else "short"
        if (sym, closed_position_side) not in closure_roots:
            continue
        db.record_risk_event(
            severity="info", rule="stop_hit_observed",
            agent="reconciler",
            detail={
                "symbol": sym,
                "closed_position_side": closed_position_side,
                "broker_order_id": o.get("id"),
                "fill_ts": o.get("updateTimestamp") or o.get("creationTimestamp"),
            },
        )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()
    res = reconcile(verbose=not args.quiet)
    if not args.quiet:
        print(res)
    return 0 if res.get("status") == "ok" else 2


if __name__ == "__main__":
    sys.exit(main())
