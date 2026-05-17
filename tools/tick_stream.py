"""SignalR market-data tick stream for ProjectX.

Connects to wss://rtc.topstepx.com/hubs/market and maintains a
process-local cache of the latest tick per contract. Consumers
(tools/profit_protect) read from the cache; the cache is updated in
the signalrcore background thread when GatewayQuote events arrive.

Why this exists (2026-05-15):
The trader currently polls 1-min bar closes via tools/bar_fetcher.
Software take-profit + percent-of-peak floor monitor live unrealized
P&L; in fast-moving tape (MGC/GC Asian, RTH news), 60-second-stale
data is the difference between catching a +$100 peak and watching
it retrace to +$30 before the next bar prints.

Verified against rtc.topstepx.com 2026-05-15 with the JWT-based auth.
Subscribe method is `SubscribeContractQuotes`; events arrive as
`GatewayQuote` with args `[contract_id, {lastPrice, bestBid, bestAsk,
volume, lastUpdated, ...}]`.

DESIGN NOTES — Pattern A safety:
The cache is FAIL-SAFE: `latest(contract_id)` returns None if the
tick is older than `STALE_AFTER_S` (30s default). Consumers MUST
treat None as "fall back to the existing bar-fetcher path" — never
trust a stale cache. The sentinel check_tick_stream_stale invariant
adds a second layer: alerts if any subscribed contract has been
stale for >5min, which would indicate the WebSocket died silently.

Usage:
    from tools.tick_stream import get_stream
    stream = get_stream()
    stream.subscribe("CON.F.US.MGC.M26")
    tick = stream.latest("CON.F.US.MGC.M26")
    if tick is not None:
        last_price = tick["price"]
"""
from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Configuration
HUB_URL = "https://rtc.topstepx.com/hubs/market"
STALE_AFTER_S: float = 30.0       # caller treats older-than-this as no data
SUBSCRIBE_METHOD = "SubscribeContractQuotes"
EVENT_METHOD = "GatewayQuote"

# Reconnect policy: signalrcore handles auto-reconnect when configured;
# we additionally watch for "no events received" gaps via the sentinel.


class TickStream:
    """Thread-safe tick cache. One instance per process; access via get_stream().

    The constructor doesn't open a connection — call .start() explicitly,
    or it will auto-start on the first .subscribe() call.
    """

    def __init__(self, jwt: str):
        self._jwt = jwt
        self._cache: dict[str, dict[str, Any]] = {}   # contract_id -> {price, bid, ask, ts}
        self._lock = threading.Lock()
        self._hub = None  # lazy-built
        self._subscribed: set[str] = set()
        self._started = False
        self._start_lock = threading.Lock()
        self._last_event_ts: Optional[datetime] = None
        # Per-contract on-tick callbacks. Invoked synchronously in the
        # WebSocket bg thread when a new GatewayQuote arrives. Used by
        # tick_protect to evaluate exit rules within milliseconds of a
        # price move instead of waiting for the 1-sec position poll.
        # Callback signature: fn(contract_id: str, tick_entry: dict) -> None.
        # Exceptions in callbacks are caught and logged to avoid killing the
        # bg thread or skipping cache updates.
        self._callbacks: dict[str, Any] = {}  # contract_id -> callable

    # ── Public API ───────────────────────────────────────────────

    def start(self) -> None:
        """Open the WebSocket connection. Idempotent."""
        with self._start_lock:
            if self._started:
                return
            self._build_and_start_hub()
            self._started = True

    def stop(self) -> None:
        """Close the WebSocket connection."""
        with self._start_lock:
            if not self._started:
                return
            try:
                if self._hub is not None:
                    self._hub.stop()
            except Exception:
                pass
            self._started = False

    def subscribe(self, contract_id: str) -> None:
        """Subscribe to a contract. Auto-starts the stream if not running."""
        if not self._started:
            self.start()
        if contract_id in self._subscribed:
            return
        try:
            self._hub.send(SUBSCRIBE_METHOD, [contract_id])
            self._subscribed.add(contract_id)
        except Exception:
            # Swallow — caller will retry on next poll
            pass

    def latest(self, contract_id: str) -> Optional[dict[str, Any]]:
        """Return the latest tick for `contract_id`, or None if stale or absent.

        Stale = older than STALE_AFTER_S. None is the "fall back" signal —
        consumers MUST treat this as no-data and use the bar-fetcher path.

        Auto-subscribes on first read.
        """
        if contract_id not in self._subscribed:
            self.subscribe(contract_id)
            return None  # first read; no data yet
        with self._lock:
            entry = self._cache.get(contract_id)
        if entry is None:
            return None
        age = (datetime.now(tz=timezone.utc) - entry["ts"]).total_seconds()
        if age > STALE_AFTER_S:
            return None
        return entry

    def is_alive(self, max_event_gap_s: float = 60.0) -> bool:
        """True if the stream has received SOMETHING within `max_event_gap_s`.

        Used by the sentinel to detect silent-WebSocket-death. Different
        from per-contract staleness — a contract with no recent ticks
        during a slow tape is normal; the whole stream going silent is not.
        """
        if not self._started or self._last_event_ts is None:
            return False
        age = (datetime.now(tz=timezone.utc) - self._last_event_ts).total_seconds()
        return age <= max_event_gap_s

    def subscribed_contracts(self) -> list[str]:
        return list(self._subscribed)

    def register_on_tick(self, contract_id: str, callback) -> None:
        """Register a per-contract on-tick callback. Replaces any prior
        callback for the same contract. Pass `None` to clear.

        Callback runs in the WebSocket bg thread on EVERY GatewayQuote
        for the registered contract. Must be FAST (synchronous tier-checks
        only); long-running work (network calls, DB writes) must be
        dispatched to a worker thread by the callback itself.

        Auto-subscribes the contract if not already subscribed.
        """
        if not self._started:
            self.start()
        if contract_id not in self._subscribed:
            self.subscribe(contract_id)
        with self._lock:
            if callback is None:
                self._callbacks.pop(contract_id, None)
            else:
                self._callbacks[contract_id] = callback

    def unregister_on_tick(self, contract_id: str) -> None:
        """Remove the on-tick callback for `contract_id`. No-op if absent."""
        with self._lock:
            self._callbacks.pop(contract_id, None)

    def registered_callbacks(self) -> list[str]:
        """List contract_ids with registered on-tick callbacks. For testing."""
        with self._lock:
            return list(self._callbacks.keys())

    def cache_snapshot(self) -> dict[str, dict[str, Any]]:
        """Return a shallow copy of the cache. For sentinel inspection."""
        with self._lock:
            return dict(self._cache)

    # ── Internal ─────────────────────────────────────────────────

    def _build_and_start_hub(self) -> None:
        # Lazy import so the module is import-safe even if signalrcore
        # isn't installed in dev environments.
        from signalrcore.hub_connection_builder import HubConnectionBuilder

        jwt = self._jwt
        hub = (
            HubConnectionBuilder()
            .with_url(
                HUB_URL,
                options={
                    "access_token_factory": lambda: jwt,
                    "skip_negotiation": False,
                },
            )
            .configure_logging(50)  # CRITICAL — quiet operation
            .with_automatic_reconnect({
                "type": "interval",
                "keep_alive_interval": 10,
                "intervals": [1, 2, 5, 10, 30],
            })
            .build()
        )
        hub.on(EVENT_METHOD, self._on_event)
        hub.start()
        self._hub = hub
        # signalrcore start is async-ish; let the handshake complete
        time.sleep(1.0)

        # Re-subscribe everything that was subscribed before a reconnect
        # would have wiped the broker-side state.
        for cid in list(self._subscribed):
            try:
                hub.send(SUBSCRIBE_METHOD, [cid])
            except Exception:
                pass

    def _on_event(self, args: list) -> None:
        """GatewayQuote event handler. Runs in signalrcore's bg thread.

        args = [contract_id, payload_dict].
        """
        try:
            if not isinstance(args, list) or len(args) < 2:
                return
            contract_id = args[0]
            payload = args[1]
            if not isinstance(payload, dict):
                return
            last_price = payload.get("lastPrice")
            if last_price is None:
                return
            entry = {
                "contract_id": contract_id,
                "price": float(last_price),
                "bid": float(payload.get("bestBid") or 0) or None,
                "ask": float(payload.get("bestAsk") or 0) or None,
                "volume": int(payload.get("volume") or 0) or None,
                "ts": datetime.now(tz=timezone.utc),
            }
            with self._lock:
                self._cache[contract_id] = entry
                self._last_event_ts = entry["ts"]
                cb = self._callbacks.get(contract_id)
            # Invoke the callback OUTSIDE the lock so a slow callback
            # (e.g. one that takes a short pause) can't block cache writes.
            if cb is not None:
                try:
                    cb(contract_id, entry)
                except Exception:
                    # Per the contract: never let a bad callback kill the
                    # bg thread. The next tick will re-invoke; if the bug
                    # is persistent, sentinel checks will surface it.
                    pass
        except Exception:
            # Never let the bg thread crash on a bad payload
            pass


# Module-level singleton + getter ─────────────────────────────────

_stream: Optional[TickStream] = None
_stream_lock = threading.Lock()


def get_stream(jwt: Optional[str] = None) -> TickStream:
    """Return the process-local TickStream singleton.

    First call constructs the stream and must be passed a JWT. Subsequent
    calls return the existing instance. Pattern: live_trader hands the
    stream its JWT on startup, then profit_protect reads via get_stream().
    """
    global _stream
    with _stream_lock:
        if _stream is None:
            if jwt is None:
                raise RuntimeError(
                    "TickStream not initialized — first caller must pass a JWT"
                )
            _stream = TickStream(jwt)
        return _stream


def reset_for_test() -> None:
    """Test-only: clear the singleton so tests start fresh."""
    global _stream
    with _stream_lock:
        if _stream is not None:
            try:
                _stream.stop()
            except Exception:
                pass
        _stream = None
