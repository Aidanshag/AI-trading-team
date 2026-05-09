"""Abstract broker interface for multi-broker future.

Per cowork_coordination.md weekly queue #6: 'broker adapter pattern stub
(tools/broker_adapter.py) — refactor for future multi-broker.'

═══════════════════════════════════════════════════════════════════
PREDICTION + MEASUREMENT + VARIANCE (per 2026-05-08 coordination rule)
═══════════════════════════════════════════════════════════════════

PREDICTION:
  This stub introduces no behavior change. live_trader.py and
  tests will pass with the existing TopstepAdapter (which delegates
  to tools/projectx_client.py — no logic change). The IBKRAdapter
  raises NotImplementedError on every method. When the user later
  decides to support IBKR, only IBKRAdapter needs implementation;
  live_trader.py is unchanged.

MEASUREMENT:
  - The existing `tests/test_live_trader.py` should pass without
    modification once live_trader is updated to use the adapter
    (proving zero-behavior-change refactor).
  - A new BROKER_ADAPTER env var lets scripts swap implementations
    without code changes.

VARIANCE TRIGGER:
  - If any live order placed via TopstepAdapter behaves differently
    than via the direct projectx_client (different price, qty, type,
    or success/failure), the adapter has accidentally added logic.
    Roll back.
  - This adapter is a STUB. Live trading must continue to use
    projectx_client directly until live_trader is migrated and tested.
    Until that migration, the adapter is reference architecture only.

═══════════════════════════════════════════════════════════════════

USAGE (future, post-migration):
  from tools.broker_adapter import get_adapter
  adapter = get_adapter()                         # picks via env or default
  account_id = adapter.get_account_id()
  result = adapter.place_order(
      account_id=account_id,
      contract_id="CON.F.US.ZN.M26",
      side="buy", qty=1,
      order_type="limit", limit_price=110.92,
      time_in_force="day",
      client_order_id="auto_abc123",
  )

ENV VAR:
  BROKER_ADAPTER=topstep   (default)
  BROKER_ADAPTER=ibkr      (future, currently NotImplementedError)
  BROKER_ADAPTER=paper     (future — paper-trading sim)
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any


# ── Abstract interface ────────────────────────────────────────

class BrokerAdapter(ABC):
    """Abstract broker. Concrete implementations wrap a specific
    broker SDK (Topstep/ProjectX, IBKR, paper-sim, etc.).

    The interface is the union of capabilities live_trader.py and
    related scripts use today. Adding a method here is non-trivial
    — every adapter must implement it. Default behaviors live in
    concrete classes, not in this abstract base.
    """

    name: str = "abstract"   # subclasses override

    # ── Account / state ────────────────────────────────────────

    @abstractmethod
    def get_account_id(self) -> str | int:
        """Return the active account identifier."""
        ...

    @abstractmethod
    def get_accounts(self) -> list[dict]:
        """List all accessible accounts. Each dict has at minimum:
        id, name, balance, canTrade."""
        ...

    @abstractmethod
    def get_positions(self, account_id: str | int) -> list[dict]:
        """List currently held positions for the account. Each dict:
        contractId, side or netQuantity, size, avgPrice."""
        ...

    @abstractmethod
    def get_working_orders(self, account_id: str | int) -> list[dict]:
        """List unfilled / working orders. Used for orphan-cancel sweeps."""
        ...

    # ── Order placement ───────────────────────────────────────

    @abstractmethod
    def place_order(self, *, account_id: str | int, contract_id: str,
                    side: str, qty: int, order_type: str,
                    limit_price: float | None = None,
                    stop_price: float | None = None,
                    time_in_force: str = "day",
                    client_order_id: str | None = None) -> dict:
        """Submit an order. Returns a dict with at minimum:
        success (bool), orderId/id (broker-side), and fields the
        caller might use for follow-up (price, qty, etc.).

        order_type: "limit" | "market" | "stop_limit" | "stop"
        side: "buy" | "sell"
        time_in_force: "day" | "gtc" | "ioc" | "fok" | "day_post_only"
        """
        ...

    @abstractmethod
    def cancel_order(self, account_id: str | int,
                     order_id: str | int) -> dict:
        """Cancel a working order. Returns a dict with success status."""
        ...

    # ── Market data ───────────────────────────────────────────

    @abstractmethod
    def get_bars(self, *, contract_id: str,
                 start_time: str, end_time: str,
                 unit: int, unit_number: int,
                 limit: int = 200, live: bool = False) -> list[dict]:
        """Fetch OHLCV bars. Each dict: t (timestamp), o, h, l, c, v.
        unit + unit_number define resolution (e.g., unit=2 unit_number=5
        is 5-minute bars in ProjectX convention)."""
        ...

    @abstractmethod
    def search_contracts(self, root: str, *, live: bool = False) -> list[dict]:
        """Find contracts for a symbol root (e.g., 'ZN'). Each dict:
        id, contractId, expiryDate, lastTradeDate."""
        ...

    @abstractmethod
    def front_month_contract_id(self, symbol: str) -> str:
        """Convenience: return the front-month contract id for a
        symbol root. Most adapters implement via search_contracts +
        sort by expiry."""
        ...


# ── Topstep / ProjectX adapter ────────────────────────────────

class TopstepAdapter(BrokerAdapter):
    """Wraps tools/projectx_client.py. Pure delegation — no logic
    change vs calling the client directly. The point of this class is
    to satisfy the BrokerAdapter contract so callers can swap to
    other brokers without changing call sites."""

    name = "topstep"

    def __init__(self):
        # Lazy import so the broker_adapter module can be imported
        # offline / in tests without requiring projectx credentials.
        from tools.projectx_client import get_client, get_account_id
        self._client = get_client()
        self._account_id = get_account_id()

    def get_account_id(self) -> str | int:
        return self._account_id

    def get_accounts(self) -> list[dict]:
        return self._client.get_accounts()

    def get_positions(self, account_id) -> list[dict]:
        return self._client.get_positions(account_id) or []

    def get_working_orders(self, account_id) -> list[dict]:
        return self._client.get_working_orders(account_id) or []

    def place_order(self, **kw) -> dict:
        return self._client.place_order(**kw)

    def cancel_order(self, account_id, order_id) -> dict:
        return self._client.cancel_order(account_id, order_id)

    def get_bars(self, **kw) -> list[dict]:
        return self._client.get_bars(**kw) or []

    def search_contracts(self, root: str, *, live: bool = False) -> list[dict]:
        return self._client.search_contracts(root, live=live) or []

    def front_month_contract_id(self, symbol: str) -> str:
        return self._client.front_month_contract_id(symbol)


# ── IBKR adapter (stub) ───────────────────────────────────────

class IBKRAdapter(BrokerAdapter):
    """Stub for Interactive Brokers integration. Every method raises
    NotImplementedError. Lights up if BROKER_ADAPTER=ibkr is set —
    used as a placeholder for future multi-broker support after
    Combine passes."""

    name = "ibkr"

    def _nyi(self, what: str):
        raise NotImplementedError(
            f"IBKRAdapter.{what} is not yet implemented. "
            "Set BROKER_ADAPTER=topstep until IBKR migration completes."
        )

    def get_account_id(self): self._nyi("get_account_id")
    def get_accounts(self): self._nyi("get_accounts")
    def get_positions(self, account_id): self._nyi("get_positions")
    def get_working_orders(self, account_id): self._nyi("get_working_orders")
    def place_order(self, **kw): self._nyi("place_order")
    def cancel_order(self, account_id, order_id): self._nyi("cancel_order")
    def get_bars(self, **kw): self._nyi("get_bars")
    def search_contracts(self, root, **kw): self._nyi("search_contracts")
    def front_month_contract_id(self, symbol): self._nyi("front_month_contract_id")


# ── Paper adapter (stub) ──────────────────────────────────────

class PaperAdapter(BrokerAdapter):
    """Stub for an internal paper-trading simulator. Useful for
    testing strategy + risk-floor changes without touching real
    broker APIs. Currently raises NotImplementedError; future
    implementation maintains an in-memory positions/orders book and
    fills against the same yfinance bars the strategies use."""

    name = "paper"

    def _nyi(self, what: str):
        raise NotImplementedError(
            f"PaperAdapter.{what} is not yet implemented. "
            "Use FUND_MODE=paper on live_trader for the existing "
            "paper-mode behavior until this adapter is built out."
        )

    def get_account_id(self): self._nyi("get_account_id")
    def get_accounts(self): self._nyi("get_accounts")
    def get_positions(self, account_id): self._nyi("get_positions")
    def get_working_orders(self, account_id): self._nyi("get_working_orders")
    def place_order(self, **kw): self._nyi("place_order")
    def cancel_order(self, account_id, order_id): self._nyi("cancel_order")
    def get_bars(self, **kw): self._nyi("get_bars")
    def search_contracts(self, root, **kw): self._nyi("search_contracts")
    def front_month_contract_id(self, symbol): self._nyi("front_month_contract_id")


# ── Selector ──────────────────────────────────────────────────

_ADAPTER_REGISTRY = {
    "topstep": TopstepAdapter,
    "ibkr":    IBKRAdapter,
    "paper":   PaperAdapter,
}


def get_adapter(name: str | None = None) -> BrokerAdapter:
    """Return a broker adapter instance. Selects via:
    1. explicit `name` argument
    2. BROKER_ADAPTER environment variable
    3. default "topstep"

    Caller can pin a specific adapter:
        adapter = get_adapter("topstep")

    Or honor user/operator preference:
        adapter = get_adapter()   # reads BROKER_ADAPTER env
    """
    chosen = (name or os.environ.get("BROKER_ADAPTER") or "topstep").lower()
    cls = _ADAPTER_REGISTRY.get(chosen)
    if cls is None:
        raise ValueError(
            f"Unknown broker adapter {chosen!r}. "
            f"Valid: {list(_ADAPTER_REGISTRY)}"
        )
    return cls()


# ── Migration notes (for live_trader.py refactor) ─────────────
#
# This adapter is a stub until live_trader.py is migrated. Migration
# steps (do NOT do this autonomously — needs user/CC sign-off):
#
# 1. In scripts/live_trader.py replace direct projectx_client imports:
#       from tools.projectx_client import get_client, get_account_id
#    with:
#       from tools.broker_adapter import get_adapter
#       broker = get_adapter()
#       account_id = broker.get_account_id()
#
# 2. Replace direct client method calls:
#       client.place_order(...)        →  broker.place_order(...)
#       client.get_positions(account)  →  broker.get_positions(account)
#       ...etc
#
# 3. Run tests/test_live_trader.py — should pass unchanged.
#
# 4. Run live_trader on demo for 1 session — all order behaviors
#    should match the pre-migration baseline. Variance trigger from
#    this file's header applies.
#
# 5. Only after that signal goes green: ship the migration.
#
# This stub commits the contract; the migration commits the swap.
# Two-phase intentional — surface the contract for review before
# touching live trading code.
