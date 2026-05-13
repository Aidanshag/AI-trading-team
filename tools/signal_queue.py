"""Signal queue — the brain/trader interface.

The architectural split (per user 2026-05-13):
  Brain  = decides WHAT to trade (strategy execution, session filtering,
           regime filtering, calibration, cooldowns)
  Trader = decides whether it's SAFE to place (last-mile gates) and
           places the bracket

The brain emits signal objects to this queue; the trader consumes them.
Neither knows about the other's internals.

QUEUE STORAGE:
  state/pending_signals.json — atomic write via temp+rename
  Choice rationale: no HIGH_RISK schema change to state/schema.sql,
  file-based is simple, atomic rename gives crash safety.

SIGNAL LIFECYCLE:
  emitted (brain writes)
    → consumed (trader reads + clears its own row)
      → placed / rejected / expired (trader logs outcome elsewhere — orders
        table, risk_events, etc.)
  Signals expire naturally if the trader doesn't pick them up before
  `expires_at`. Stale signals are cleaned on every read.

SIGNAL SCHEMA (one item):
  {
    "id":            str (uuid),
    "emitted_at":    ISO8601 UTC,
    "expires_at":    ISO8601 UTC,
    "symbol":        str  (e.g. "GC", "MNQ"),
    "side":          "long" | "short",
    "entry_price":   float,
    "stop_price":    float,
    "target_price":  float | null,
    "qty":           int (default 1),
    "strategy":      str  (e.g. "narrow_range_break"),
    "session":       str  (e.g. "Asian"),
    "cell_key":      str  (e.g. "narrow_range_break|GC|Asian|long"),
    "shadow_only":   bool (true = trader records but doesn't place),
    "notes":         str
  }
"""
from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
QUEUE_PATH = _PROJECT_ROOT / "state" / "pending_signals.json"

# Default TTL: brain re-emits every scan cycle, so a signal that wasn't
# consumed within this window is stale (price moved, regime shifted).
DEFAULT_SIGNAL_TTL_SEC = 120


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_iso(s: str) -> datetime:
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def make_signal(*, symbol: str, side: str, entry_price: float,
                  stop_price: float, target_price: float | None,
                  strategy: str, session: str, cell_key: str,
                  qty: int = 1, shadow_only: bool = False,
                  notes: str = "",
                  ttl_sec: int = DEFAULT_SIGNAL_TTL_SEC) -> dict[str, Any]:
    """Build a signal dict. Brain calls this then `enqueue(signal)`."""
    now = datetime.now(timezone.utc)
    return {
        "id": uuid.uuid4().hex,
        "emitted_at": now.isoformat(timespec="seconds"),
        "expires_at": (now + timedelta(seconds=ttl_sec)).isoformat(
            timespec="seconds"),
        "symbol": symbol,
        "side": side,
        "entry_price": float(entry_price),
        "stop_price": float(stop_price),
        "target_price": float(target_price) if target_price is not None else None,
        "qty": int(qty),
        "strategy": strategy,
        "session": session,
        "cell_key": cell_key,
        "shadow_only": bool(shadow_only),
        "notes": notes,
    }


def _read_raw() -> list[dict[str, Any]]:
    """Read the queue file. Returns [] on missing or corrupt."""
    if not QUEUE_PATH.exists():
        return []
    try:
        data = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
        items = data.get("signals") if isinstance(data, dict) else data
        if not isinstance(items, list):
            return []
        return items
    except Exception:
        return []


def _write_raw(signals: list[dict[str, Any]]) -> None:
    """Atomic write: temp file + rename."""
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps({"signals": signals}, indent=2, default=str)
    fd, tmp_path = tempfile.mkstemp(prefix=".pending_signals.", suffix=".tmp",
                                       dir=str(QUEUE_PATH.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(body)
        os.replace(tmp_path, QUEUE_PATH)
    except Exception:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        raise


def _is_expired(sig: dict[str, Any], now_utc: datetime | None = None) -> bool:
    now_utc = now_utc or datetime.now(timezone.utc)
    try:
        return _parse_iso(sig["expires_at"]) <= now_utc
    except Exception:
        return True  # malformed = treat as expired


def enqueue(signal: dict[str, Any]) -> None:
    """Append a signal to the queue. Drops expired signals on the way in
    (cheap garbage collection). Brain calls this."""
    current = [s for s in _read_raw() if not _is_expired(s)]
    # Dedup by cell_key — only one pending signal per cell at a time.
    # If a signal for this cell already exists, replace it (most recent wins).
    cell = signal.get("cell_key")
    if cell:
        current = [s for s in current if s.get("cell_key") != cell]
    current.append(signal)
    _write_raw(current)


def consume(limit: int | None = None) -> list[dict[str, Any]]:
    """Read all non-expired signals AND remove them from the queue.

    Atomic relative to file ops, but NOT relative to concurrent writers
    (the brain). If brain enqueues between our read and write, that
    signal is lost. Acceptable for current single-trader architecture;
    if we ever run multiple trader consumers this needs a lock or a
    proper DB queue.

    Trader calls this. Returns list ordered by emitted_at (oldest first).
    """
    current = _read_raw()
    live = [s for s in current if not _is_expired(s)]
    live.sort(key=lambda s: s.get("emitted_at", ""))
    if limit is not None:
        out = live[:limit]
        remaining = live[limit:]
    else:
        out = live
        remaining = []
    _write_raw(remaining)
    return out


def peek() -> list[dict[str, Any]]:
    """Read all non-expired signals WITHOUT removing them. For status/UI."""
    current = _read_raw()
    return [s for s in current if not _is_expired(s)]


def clear() -> int:
    """Remove every signal from the queue. Returns count cleared.
    Used by tests + manual ops (`fund queue clear` if we add it)."""
    n = len(_read_raw())
    _write_raw([])
    return n
