"""Interactive Brokers API client — DATA-ONLY by design (2026-05-17).

Read-only wrapper around ib_insync. Parallel to tools/projectx_client.py
but for IB, which has a wider instrument universe (stocks, options, FX,
bonds, crypto, futures) and 10+ years of historical bar data.

DESIGN PRINCIPLE — per memory feedback_topstep_vs_ib_separate_workstreams:
  Topstep = prop fund / Combine path (CURRENT priority)
  IB      = personal/invested capital (FUTURE, parallel)

Until the user explicitly enables IB trading, this client REFUSES to
place orders. The only methods exposed are:
  - get_accounts
  - get_account_summary
  - search_contracts
  - get_historical_bars
  - get_market_data_snapshot
  - get_positions
  - is_connected

Prerequisites:
  - IB Gateway must be running locally
  - Logged into LIVE or PAPER mode
  - API enabled in Configure > Settings > API
  - Connection allowed from 127.0.0.1
  - Socket port noted (default 4001 IBG live, 4002 IBG paper)

Python 3.14 fix: asyncio.get_event_loop() removed default-create
behavior. We explicitly create one before ib_insync imports it.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Optional

# Python 3.14 event-loop fix — must run before ib_insync import
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from ib_insync import IB, Contract, Stock, Future, ContFuture  # noqa: E402


# Default connection — can be overridden via env vars
IB_HOST = os.environ.get("IB_HOST", "127.0.0.1")
IB_PORT = int(os.environ.get("IB_PORT", "4001"))  # 4001=IBG live, 4002=IBG paper
IB_CLIENT_ID = int(os.environ.get("IB_CLIENT_ID", "1"))


class IBError(Exception):
    """Raised on IB API failures."""


class IBClient:
    """Read-only IB Gateway client. Mirrors tools/projectx_client.py
    interface where overlap is meaningful (data access methods)."""

    def __init__(self, host: str = IB_HOST, port: int = IB_PORT,
                 client_id: int = IB_CLIENT_ID, timeout: float = 10.0):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.timeout = timeout
        self._ib: Optional[IB] = None

    # ── Connection lifecycle ────────────────────────────────────

    def connect(self) -> None:
        """Open the socket connection to IB Gateway.

        readonly=True skips the executions/orders handshake which
        otherwise hangs when the gateway's API is in Read-Only mode
        (our default state — data collection only).
        """
        if self._ib is not None and self._ib.isConnected():
            return
        self._ib = IB()
        try:
            self._ib.connect(self.host, self.port,
                              clientId=self.client_id, timeout=self.timeout,
                              readonly=True)
        except Exception as e:
            raise IBError(f"connect to {self.host}:{self.port} failed: "
                           f"{type(e).__name__}: {e}")

    def disconnect(self) -> None:
        if self._ib is not None and self._ib.isConnected():
            self._ib.disconnect()

    def is_connected(self) -> bool:
        return self._ib is not None and self._ib.isConnected()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()

    def _require_connected(self) -> IB:
        if self._ib is None or not self._ib.isConnected():
            raise IBError("not connected — call connect() first")
        return self._ib

    # ── Account / positions ─────────────────────────────────────

    def get_accounts(self) -> list[str]:
        """Return managed account IDs."""
        ib = self._require_connected()
        return list(ib.managedAccounts())

    def get_account_summary(self, account: str | None = None) -> dict:
        """Return account summary tags as a dict."""
        ib = self._require_connected()
        entries = ib.accountSummary(account or "")
        result: dict = {}
        for e in entries:
            if account and e.account != account:
                continue
            result[e.tag] = e.value
        return result

    def get_positions(self, account: str | None = None) -> list[dict]:
        """Return current positions as dicts."""
        ib = self._require_connected()
        positions = ib.positions(account or "")
        return [
            {
                "account": p.account,
                "symbol": p.contract.symbol,
                "secType": p.contract.secType,
                "exchange": p.contract.exchange,
                "currency": p.contract.currency,
                "position": p.position,
                "avgCost": p.avgCost,
            }
            for p in positions
        ]

    # ── Instrument lookup ───────────────────────────────────────

    def search_contracts(self, query: str, sec_type: str | None = None) -> list[dict]:
        """Search for contracts matching `query` (e.g., 'AAPL', 'ES')."""
        ib = self._require_connected()
        matches = ib.reqMatchingSymbols(query)
        results = []
        for m in matches:
            c = m.contract
            results.append({
                "conId": c.conId, "symbol": c.symbol,
                "secType": c.secType, "primaryExchange": c.primaryExchange,
                "currency": c.currency, "description": m.derivativeSecTypes,
            })
            if sec_type and c.secType != sec_type:
                continue
        return results

    # ── Historical bars ────────────────────────────────────────

    def get_historical_bars(
        self,
        symbol: str,
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
        end_datetime: str = "",   # empty = now
        duration: str = "30 D",   # IB duration string e.g. "30 D", "1 Y", "1000 S"
        bar_size: str = "1 day",  # "1 day", "1 hour", "5 mins", "1 min", "30 secs"
        what_to_show: str = "TRADES",  # "TRADES", "MIDPOINT", "BID", "ASK"
        use_rth: bool = True,
    ) -> list[dict]:
        """Pull historical bars. Returns list of dicts with t/o/h/l/c/v
        (matches the ProjectX client format for downstream consistency).

        For futures, use sec_type='CONTFUT' (continuous future) for
        backtest purposes, or 'FUT' with a specific expiry.
        """
        ib = self._require_connected()
        if sec_type in ("CONTFUT", "ContFuture"):
            contract = ContFuture(symbol, exchange=exchange or "GLOBEX",
                                    currency=currency)
        elif sec_type in ("FUT", "Future"):
            contract = Future(symbol, exchange=exchange or "GLOBEX",
                               currency=currency)
        elif sec_type in ("STK", "Stock"):
            contract = Stock(symbol, exchange=exchange or "SMART",
                              currency=currency)
        else:
            contract = Contract(symbol=symbol, secType=sec_type,
                                 exchange=exchange, currency=currency)
        ib.qualifyContracts(contract)
        bars = ib.reqHistoricalData(
            contract, endDateTime=end_datetime, durationStr=duration,
            barSizeSetting=bar_size, whatToShow=what_to_show,
            useRTH=int(use_rth), formatDate=2,
        )
        return [
            {
                "t": bar.date.isoformat() if hasattr(bar.date, "isoformat") else str(bar.date),
                "o": bar.open, "h": bar.high, "l": bar.low,
                "c": bar.close, "v": bar.volume,
            }
            for bar in bars
        ]

    # ── Real-time snapshot ──────────────────────────────────────

    def get_market_data_snapshot(self, symbol: str, sec_type: str = "STK",
                                    exchange: str = "SMART",
                                    currency: str = "USD") -> dict:
        """One-shot snapshot quote. Requires data subscription for some
        symbols (delayed quotes are usually free)."""
        ib = self._require_connected()
        if sec_type in ("CONTFUT", "ContFuture"):
            contract = ContFuture(symbol, exchange=exchange or "GLOBEX",
                                    currency=currency)
        elif sec_type in ("FUT", "Future"):
            contract = Future(symbol, exchange=exchange or "GLOBEX",
                               currency=currency)
        elif sec_type in ("STK", "Stock"):
            contract = Stock(symbol, exchange=exchange or "SMART",
                              currency=currency)
        else:
            contract = Contract(symbol=symbol, secType=sec_type,
                                 exchange=exchange, currency=currency)
        ib.qualifyContracts(contract)
        # snapshot=True does one-shot then unsubscribes
        ticker = ib.reqMktData(contract, "", snapshot=True, regulatorySnapshot=False)
        ib.sleep(3)  # let ticks arrive
        result = {
            "symbol": symbol, "secType": sec_type,
            "bid": ticker.bid, "ask": ticker.ask,
            "last": ticker.last, "close": ticker.close,
            "high": ticker.high, "low": ticker.low,
            "volume": ticker.volume,
            "marketPrice": ticker.marketPrice(),
            "time": str(ticker.time) if ticker.time else None,
        }
        ib.cancelMktData(contract)
        return result


# Module-level convenience
_singleton: Optional[IBClient] = None


def get_ib_client() -> IBClient:
    """Get the process-local IB client singleton, connected."""
    global _singleton
    if _singleton is None:
        _singleton = IBClient()
    if not _singleton.is_connected():
        _singleton.connect()
    return _singleton
