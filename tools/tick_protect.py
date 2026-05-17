"""tick_protect — millisecond-latency profit-lock exits.

Ships 2026-05-17 per user directive: "the biggest thing this week is not
letting the winners turn into losers. I want the trader running tick by
tick when positions are open to allow for positions to be closed
immediately, in milliseconds."

Architecture:
  - TickStream (tools.tick_stream) maintains a per-contract WebSocket
    cache + supports `register_on_tick(contract_id, callback)`.
  - tick_protect's `on_tick` is registered as that callback when a
    position opens. It runs in the WebSocket bg thread on EVERY tick.
  - On each tick: compute unrealized vs cached position metadata,
    delegate to `profit_protect.decide()` (pure tier-floor logic),
    and if it returns should_close=True, fire `close_position` in a
    short-lived worker thread (so we don't block the WS thread).

Safety:
  - `_close_in_flight` set prevents double-close when ticks fire faster
    than the broker round-trip.
  - 1-second position poll in live_trader stays as backup (if a tick
    is missed, the poll catches it).
  - Shares `_position_high_water` and `_target_usd_by_contract` state
    with `tools.profit_protect` — both paths read/write the same dicts,
    so tier-floor calculations stay consistent.

Tests in tests/test_tick_protect.py cover:
  - decide-true path fires close exactly once
  - decide-false path doesn't fire
  - re-entrancy / close-in-flight blocks duplicate close
  - peak tracking updates correctly
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from tools.profit_protect import (
    decide,
    _position_high_water,
    _position_peak_ts,
    _target_usd_by_contract,
    _clear_software_target,
    _record_close_decision,
    _unrealized_usd,
    reset_trailed_floor,
)


# ── Position metadata cache ────────────────────────────────────────
# Populated by live_trader's _position_polling_loop. Keyed by
# contract_id. Updated atomically — the WebSocket callback reads from
# this without locking (single dict read is atomic in CPython).

class PositionMeta:
    __slots__ = ("contract_id", "symbol", "side", "size", "avg_price",
                  "tick_size", "tick_value", "account_id", "registered_at")

    def __init__(self, contract_id: str, symbol: str, side: str, size: int,
                 avg_price: float, tick_size: float, tick_value: float,
                 account_id: int):
        self.contract_id = contract_id
        self.symbol = symbol
        self.side = side
        self.size = size
        self.avg_price = avg_price
        self.tick_size = tick_size
        self.tick_value = tick_value
        self.account_id = account_id
        self.registered_at = datetime.now(tz=timezone.utc)


_positions: dict[str, PositionMeta] = {}
_positions_lock = threading.Lock()

# Per-contract close-in-flight flag. Set when we dispatch a close,
# cleared when the close request returns. While set, additional ticks
# for the same contract skip evaluation.
_close_in_flight: set[str] = set()
_close_lock = threading.Lock()

# Client + logger references injected by live_trader on startup. The
# WebSocket callback needs these to actually fire close_position.
_client: Optional[Any] = None
_log: Optional[Callable[[str], None]] = None
# Optional Discord alerter — best-effort; missing module is fine.
_alert: Optional[Callable[..., None]] = None


def configure(client: Any, log_fn: Optional[Callable[[str], None]] = None,
              alert_fn: Optional[Callable[..., None]] = None) -> None:
    """Inject the broker client + log function. Must be called once before
    `register_position` / `on_tick` can fire any closes."""
    global _client, _log, _alert
    _client = client
    _log = log_fn or (lambda _m: None)
    _alert = alert_fn


# ── Registration ───────────────────────────────────────────────────

def register_position(contract_id: str, symbol: str, side: str, size: int,
                      avg_price: float, tick_size: float, tick_value: float,
                      account_id: int) -> None:
    """Track an open position. Called by live_trader's position-poller
    whenever it sees a position that isn't already tracked.

    Once registered, the WebSocket on-tick callback can evaluate this
    position on every tick. Updates an existing entry if `contract_id`
    is already tracked (handles size changes from add-ons).
    """
    with _positions_lock:
        _positions[contract_id] = PositionMeta(
            contract_id=contract_id, symbol=symbol, side=side, size=size,
            avg_price=avg_price, tick_size=tick_size, tick_value=tick_value,
            account_id=account_id,
        )


def unregister_position(contract_id: str) -> None:
    """Remove a closed position from tracking. Idempotent."""
    with _positions_lock:
        _positions.pop(contract_id, None)
    with _close_lock:
        _close_in_flight.discard(contract_id)


def tracked_positions() -> list[str]:
    """Return list of tracked contract_ids. Used by live_trader's poller
    to compute (open positions) vs (tracked) deltas for register/unregister."""
    with _positions_lock:
        return list(_positions.keys())


def is_close_in_flight(contract_id: str) -> bool:
    """True if a close is currently being dispatched for `contract_id`."""
    with _close_lock:
        return contract_id in _close_in_flight


# ── The tick handler — the hot path ────────────────────────────────

def on_tick(contract_id: str, tick_entry: dict) -> None:
    """Called by TickStream on every GatewayQuote for a registered contract.
    Synchronous + fast. Must NOT block — close_position is dispatched to
    a worker thread.

    Returns None always. Errors are swallowed (logged via _log) so the
    WebSocket thread never dies.
    """
    if _client is None:
        return
    with _positions_lock:
        meta = _positions.get(contract_id)
    if meta is None:
        return
    # Skip if a close for this contract is already in flight
    with _close_lock:
        if contract_id in _close_in_flight:
            return

    try:
        last_price = float(tick_entry.get("price") or 0)
        if last_price <= 0:
            return
        unrealized = _unrealized_usd(
            meta.side, meta.size, meta.avg_price, last_price,
            meta.tick_size, meta.tick_value,
        )
        key = f"{meta.symbol}_{meta.side}"
        prev_peak = _position_high_water.get(key, 0.0)
        if unrealized > prev_peak:
            _position_high_water[key] = unrealized
            _position_peak_ts[key] = datetime.now(tz=timezone.utc)
            prev_peak = unrealized

        # ── Software target hit ──
        target_usd = _target_usd_by_contract.get(contract_id)
        if target_usd is not None and unrealized >= target_usd:
            _dispatch_close(meta, unrealized, prev_peak, "target_hit")
            return

        # ── Tier floor / hard caps via the pure decide() function ──
        should_close, reason = decide(unrealized, prev_peak)
        if should_close:
            # Parse out short reason tag for the decision-log row
            tag = "trailing_lock"
            if "hard_cap" in reason:
                tag = "hard_cap"
            elif "loss_hard_cap" in reason:
                tag = "loss_hard_cap"
            _dispatch_close(meta, unrealized, prev_peak, tag)
    except Exception as e:
        if _log:
            _log(f"  tick_protect on_tick error {contract_id}: "
                  f"{type(e).__name__}: {e}")


def _dispatch_close(meta: PositionMeta, unrealized: float, peak: float,
                    reason_tag: str) -> None:
    """Mark close-in-flight and spawn a worker thread to fire close_position.
    Returns immediately so the WebSocket thread isn't blocked on broker IO."""
    with _close_lock:
        if meta.contract_id in _close_in_flight:
            return
        _close_in_flight.add(meta.contract_id)

    def _worker():
        try:
            if _log:
                _log(f"  tick_protect FIRE: {meta.symbol} {meta.side} "
                      f"{meta.size}ct unrealized=${unrealized:+.2f} "
                      f"peak=${peak:.2f} reason={reason_tag}")
            result = _client.close_position(meta.account_id, meta.contract_id)
            if isinstance(result, dict) and result.get("success") is False:
                err = result.get("errorMessage") or "broker rejected"
                if _log:
                    _log(f"  tick_protect close REJECTED for "
                          f"{meta.contract_id}: {err}")
                if _alert:
                    try:
                        _alert(
                            f"CRITICAL: tick_protect close REJECTED for "
                            f"{meta.symbol}: {err}. Position still OPEN.",
                            level="crit",
                        )
                    except Exception:
                        pass
                return
            # Success — clear all per-position state
            key = f"{meta.symbol}_{meta.side}"
            _position_high_water.pop(key, None)
            _position_peak_ts.pop(key, None)
            _clear_software_target(meta.contract_id)
            reset_trailed_floor(meta.contract_id)
            unregister_position(meta.contract_id)
            # Skip DB write for synthetic healthcheck positions — avoids
            # SQLite cross-thread errors when the healthcheck worker runs
            # in a different thread than the connection's owner.
            if "HEALTHCHECK" not in meta.contract_id:
                _record_close_decision(
                    symbol=meta.symbol, side=meta.side, size=meta.size,
                    contract_id=meta.contract_id, unrealized=unrealized,
                    peak=peak, reason=f"tick_protect:{reason_tag}",
                    kind="close",
                )
            if _alert:
                try:
                    _alert(
                        f"⚡ tick_protect {reason_tag} {meta.symbol} "
                        f"{meta.side} {meta.size}ct @ ${unrealized:+.0f} "
                        f"(peak ${peak:.0f})",
                        level="info",
                    )
                except Exception:
                    pass
        except Exception as e:
            if _log:
                _log(f"  tick_protect close FAILED {meta.contract_id}: "
                      f"{type(e).__name__}: {e}")
        finally:
            with _close_lock:
                _close_in_flight.discard(meta.contract_id)

    t = threading.Thread(target=_worker, name=f"tick_close_{meta.contract_id}",
                          daemon=True)
    t.start()


def reset_for_test() -> None:
    """Test-only: wipe all state between tests."""
    global _client, _log, _alert
    with _positions_lock:
        _positions.clear()
    with _close_lock:
        _close_in_flight.clear()
    _client = None
    _log = None
    _alert = None
