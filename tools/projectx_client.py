"""ProjectX Gateway REST client for Topstep.

Wraps the TopstepX / ProjectX REST API. Used by the broker tools in
`tools/topstep.py` and the market-data tools in `tools/market_data.py`.

Authentication:
    1. User generates an API key on the TopstepX dashboard.
    2. Client exchanges (username + apiKey) for a short-lived JWT.
    3. Every subsequent call uses `Authorization: Bearer {jwt}`.
    4. On 401, client re-auths automatically (JWT typically ~24h TTL).

Environment variables required:
    PROJECTX_API_KEY       — from TopstepX dashboard
    PROJECTX_USERNAME      — your Topstep login
    PROJECTX_ACCOUNT_ID    — specific account to trade (from get_accounts)
    PROJECTX_BASE_URL      — typically https://api.topstepx.com (optional override)

IMPORTANT: endpoint paths below are based on ProjectX public documentation.
They may drift over time. If a call returns 404, check the TopstepX dashboard
→ API section → current endpoints and update the `_ENDPOINTS` dict below.
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx


_ENDPOINTS = {
    # Auth (confirmed against official Swagger spec)
    "auth_login_key":        "/api/Auth/loginKey",      # retail API-key flow
    "auth_login_app":        "/api/Auth/loginApp",      # application flow (appId + verifyKey)
    "auth_validate":         "/api/Auth/validate",
    "auth_logout":           "/api/Auth/logout",
    # Accounts
    "account_search":        "/api/Account/search",
    # Contracts
    "contract_search":       "/api/Contract/search",
    "contract_by_id":        "/api/Contract/searchById",
    "contract_available":    "/api/Contract/available",
    # Orders
    "order_search":          "/api/Order/search",
    "order_search_open":     "/api/Order/searchOpen",
    "order_place":           "/api/Order/place",
    "order_cancel":          "/api/Order/cancel",
    "order_modify":          "/api/Order/modify",
    # Positions
    "position_search":       "/api/Position/searchOpen",
    "position_close":        "/api/Position/closeContract",
    "position_partial_close":"/api/Position/partialCloseContract",
    # Market data
    "history_retrieve":      "/api/History/retrieveBars",
}


# Auth mode: "key" = simple API-key flow, "app" = application flow with
# appId + verifyKey (stricter; often required for automated trading).
# Auto-detected from which env vars are populated unless PROJECTX_AUTH_MODE
# overrides it explicitly.
AUTH_MODE_KEY = "key"
AUTH_MODE_APP = "app"


class ProjectXError(Exception):
    """Raised when a ProjectX API call returns an error or unexpected shape."""


class ProjectXClient:
    """HTTP client for the ProjectX Gateway REST API."""

    def __init__(
        self,
        api_key: str | None = None,
        username: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
        auth_mode: str | None = None,
        password: str | None = None,
        device_id: str | None = None,
        app_id: str | None = None,
        verify_key: str | None = None,
    ):
        self.username = username or os.environ.get("PROJECTX_USERNAME")
        self.base_url = (
            base_url
            or os.environ.get("PROJECTX_BASE_URL")
            or "https://api.topstepx.com"
        ).rstrip("/")

        # loginKey credentials
        self.api_key = api_key or os.environ.get("PROJECTX_API_KEY")

        # loginApp credentials
        self.password = password or os.environ.get("PROJECTX_PASSWORD")
        self.device_id = device_id or os.environ.get("PROJECTX_DEVICE_ID")
        self.app_id = app_id or os.environ.get("PROJECTX_APP_ID")
        self.verify_key = verify_key or os.environ.get("PROJECTX_VERIFY_KEY")

        # Auth mode selection (env override > auto-detect from creds)
        env_mode = os.environ.get("PROJECTX_AUTH_MODE", "").lower().strip()
        if auth_mode:
            self.auth_mode = auth_mode.lower()
        elif env_mode in (AUTH_MODE_KEY, AUTH_MODE_APP):
            self.auth_mode = env_mode
        elif self.app_id and self.verify_key:
            self.auth_mode = AUTH_MODE_APP
        elif self.api_key:
            self.auth_mode = AUTH_MODE_KEY
        else:
            raise ProjectXError(
                "ProjectX credentials incomplete. Set either:\n"
                "  - API-key flow:  PROJECTX_API_KEY + PROJECTX_USERNAME\n"
                "  - App flow:      PROJECTX_USERNAME + PROJECTX_PASSWORD + "
                "PROJECTX_DEVICE_ID + PROJECTX_APP_ID + PROJECTX_VERIFY_KEY"
            )

        if not self.username:
            raise ProjectXError("PROJECTX_USERNAME must be set.")
        if self.auth_mode == AUTH_MODE_APP:
            missing = [
                k for k, v in [
                    ("PROJECTX_PASSWORD",   self.password),
                    ("PROJECTX_DEVICE_ID",  self.device_id),
                    ("PROJECTX_APP_ID",     self.app_id),
                    ("PROJECTX_VERIFY_KEY", self.verify_key),
                ] if not v
            ]
            if missing:
                raise ProjectXError(
                    f"App auth mode requires: {missing}. Fill in .env."
                )
        elif self.auth_mode == AUTH_MODE_KEY and not self.api_key:
            raise ProjectXError("Key auth mode requires PROJECTX_API_KEY.")

        self._jwt: str | None = None
        self._jwt_issued_at: float = 0.0
        self._jwt_ttl: float = 23 * 3600   # refresh a bit before 24h expiry
        self._client = httpx.Client(timeout=timeout)

    # ── Auth ────────────────────────────────────────────────────
    #
    # Per ProjectX docs (gateway.docs.projectx.com):
    #   - Tokens last 24h
    #   - Use /api/Auth/loginKey for retail API-key auth
    #   - Use /api/Auth/validate to refresh (returns newToken)
    #   - Success = errorCode:0 in response body
    #
    def authenticate(self) -> None:
        """Authenticate via whichever auth_mode is configured. Sets self._jwt."""
        if self.auth_mode == AUTH_MODE_APP:
            self._authenticate_app()
        else:
            self._authenticate_key()

    def _authenticate_key(self) -> None:
        """loginKey flow: exchange (userName + apiKey) for a 24h JWT."""
        url = f"{self.base_url}{_ENDPOINTS['auth_login_key']}"
        r = self._client.post(
            url,
            json={"userName": self.username, "apiKey": self.api_key},
        )
        self._handle_auth_response(r, "loginKey")

    def _authenticate_app(self) -> None:
        """loginApp flow: exchange (userName + password + deviceId + appId +
        verifyKey) for a 24h JWT."""
        url = f"{self.base_url}{_ENDPOINTS['auth_login_app']}"
        r = self._client.post(
            url,
            json={
                "userName":  self.username,
                "password":  self.password,
                "deviceId":  self.device_id,
                "appId":     self.app_id,
                "verifyKey": self.verify_key,
            },
        )
        self._handle_auth_response(r, "loginApp")

    def _handle_auth_response(self, r, flow: str) -> None:
        if r.status_code != 200:
            raise ProjectXError(
                f"Auth [{flow}] failed ({r.status_code}): {r.text[:300]}"
            )
        data = r.json()
        if data.get("errorCode", 0) != 0:
            raise ProjectXError(
                f"Auth [{flow}] errorCode={data.get('errorCode')}: "
                f"{data.get('errorMessage', data)}"
            )
        token = data.get("token")
        if not token:
            raise ProjectXError(f"Auth [{flow}] response missing token: {data}")
        self._jwt = token
        self._jwt_issued_at = time.time()

    def validate_session(self) -> None:
        """Extend session using /api/Auth/validate — cheaper than re-auth.

        Per ProjectX docs: returns `newToken` field. Falls back to full
        authenticate() if the validate call fails.
        """
        if self._jwt is None:
            self.authenticate()
            return
        try:
            url = f"{self.base_url}{_ENDPOINTS['auth_validate']}"
            r = self._client.post(
                url,
                headers={"Authorization": f"Bearer {self._jwt}"},
                json={},
            )
            if r.status_code != 200:
                self.authenticate()
                return
            data = r.json()
            if data.get("errorCode", 0) != 0:
                self.authenticate()
                return
            new_token = data.get("newToken") or data.get("token")
            if new_token:
                self._jwt = new_token
                self._jwt_issued_at = time.time()
            else:
                self.authenticate()
        except Exception:
            self.authenticate()

    def _ensure_auth(self) -> None:
        if self._jwt is None:
            self.authenticate()
            return
        age = time.time() - self._jwt_issued_at
        if age > self._jwt_ttl:
            # Try the cheap refresh path first; fall back to full re-auth
            self.validate_session()

    def _request(
        self,
        method: str,
        endpoint_key: str,
        json: dict | None = None,
        _retried_auth: bool = False,
    ) -> Any:
        self._ensure_auth()
        url = f"{self.base_url}{_ENDPOINTS[endpoint_key]}"
        headers = {"Authorization": f"Bearer {self._jwt}"}
        r = self._client.request(method, url, headers=headers, json=json or {})

        # If expired/invalid token, re-auth once and retry
        if r.status_code == 401 and not _retried_auth:
            self._jwt = None
            return self._request(method, endpoint_key, json=json, _retried_auth=True)

        if r.status_code >= 400:
            raise ProjectXError(
                f"{method} {endpoint_key} failed ({r.status_code}): {r.text[:500]}"
            )
        return r.json()

    # ── Account ─────────────────────────────────────────────────
    def get_accounts(self, only_active: bool = True) -> list[dict]:
        """List accounts accessible to this user (Combine + funded)."""
        data = self._request(
            "POST", "account_search",
            json={"onlyActiveAccounts": only_active},
        )
        return data.get("accounts", []) if isinstance(data, dict) else data

    # ── Positions ───────────────────────────────────────────────
    def get_positions(self, account_id: int | str) -> list[dict]:
        data = self._request(
            "POST", "position_search",
            json={"accountId": int(account_id)},
        )
        return data.get("positions", []) if isinstance(data, dict) else data

    # ── Orders ──────────────────────────────────────────────────
    def get_working_orders(self, account_id: int | str) -> list[dict]:
        data = self._request(
            "POST", "order_search_open",
            json={"accountId": int(account_id)},
        )
        return data.get("orders", []) if isinstance(data, dict) else data

    def get_order_history(
        self,
        account_id: int | str,
        *,
        start_timestamp: str | None = None,
        end_timestamp: str | None = None,
    ) -> list[dict]:
        """Filled / cancelled / rejected orders since `start_timestamp`.
        ISO-8601 with timezone (e.g. '2026-04-29T13:00:00Z').
        Used by reconcile to detect stop-fill closures for anti-tilt cooldown."""
        body: dict[str, Any] = {"accountId": int(account_id)}
        if start_timestamp:
            body["startTimestamp"] = start_timestamp
        if end_timestamp:
            body["endTimestamp"] = end_timestamp
        data = self._request("POST", "order_search", json=body)
        return data.get("orders", []) if isinstance(data, dict) else data

    def place_order(
        self,
        account_id: int | str,
        contract_id: str,
        side: str,               # "buy" or "sell"
        qty: int,
        order_type: str,         # "market" | "limit" | "stop" | "stop_limit"
        limit_price: float | None = None,
        stop_price: float | None = None,
        time_in_force: str = "day",
        client_order_id: str | None = None,
    ) -> dict:
        """Place an order on the specified account.

        ProjectX order-type codes (verify against current API docs):
            1 = Market, 2 = Limit, 3 = Stop, 4 = Stop-Limit, 5 = Trailing Stop.
        Side codes: 0 = Buy, 1 = Sell.
        """
        type_code = {
            "market": 1, "limit": 2, "stop": 3, "stop_limit": 4,
        }.get(order_type.lower())
        if type_code is None:
            raise ValueError(f"Unknown order_type {order_type!r}")
        side_code = {"buy": 0, "sell": 1}.get(side.lower())
        if side_code is None:
            raise ValueError(f"side must be 'buy' or 'sell', got {side!r}")

        body: dict[str, Any] = {
            "accountId": int(account_id),
            "contractId": contract_id,
            "type": type_code,
            "side": side_code,
            "size": int(qty),
            "timeInForce": time_in_force,
        }
        if limit_price is not None:
            body["limitPrice"] = float(limit_price)
        if stop_price is not None:
            body["stopPrice"] = float(stop_price)
        if client_order_id:
            body["customTag"] = client_order_id

        return self._request("POST", "order_place", json=body)

    def cancel_order(self, account_id: int | str, order_id: int | str) -> dict:
        return self._request(
            "POST", "order_cancel",
            json={"accountId": int(account_id), "orderId": int(order_id)},
        )

    def modify_order(
        self,
        account_id: int | str,
        order_id: int | str,
        qty: int | None = None,
        limit_price: float | None = None,
        stop_price: float | None = None,
    ) -> dict:
        """Modify a working order (e.g., trail a stop). Only pass the fields
        you want to change; others are preserved."""
        body: dict = {"accountId": int(account_id), "orderId": int(order_id)}
        if qty is not None:
            body["size"] = int(qty)
        if limit_price is not None:
            body["limitPrice"] = float(limit_price)
        if stop_price is not None:
            body["stopPrice"] = float(stop_price)
        return self._request("POST", "order_modify", json=body)

    # ── Position close helpers (native endpoints — cleaner than reversing) ──
    def close_position(self, account_id: int | str, contract_id: str) -> dict:
        """Fully close a position in the given contract at market."""
        return self._request(
            "POST", "position_close",
            json={"accountId": int(account_id), "contractId": contract_id},
        )

    def partial_close_position(
        self, account_id: int | str, contract_id: str, size: int,
    ) -> dict:
        """Reduce a position by the given quantity at market."""
        return self._request(
            "POST", "position_partial_close",
            json={
                "accountId": int(account_id),
                "contractId": contract_id,
                "size": int(size),
            },
        )

    # ── Auth lifecycle extras ──
    def logout(self) -> dict:
        """Terminate the current session on the server side."""
        data = self._request("POST", "auth_logout", json={})
        self._jwt = None
        return data

    # ── Contracts ───────────────────────────────────────────────
    def search_contracts(self, text: str, live: bool = False) -> list[dict]:
        """Find contract(s) by symbol/name. Returns list — typically pick
        the front-month for trading.

        Default live=False returns all contracts. live=True filters to
        contracts with an active live-data subscription; on a Combine
        without paid live data, that returns 0.
        """
        data = self._request(
            "POST", "contract_search",
            json={"searchText": text, "live": live},
        )
        return data.get("contracts", []) if isinstance(data, dict) else data

    def front_month_contract_id(self, symbol: str) -> str:
        """Convenience: pick the nearest-dated active contract for a symbol.

        Symbols: bare root like 'CL', 'ES', 'GC', '6E' (no slash, no month).

        ProjectX's contract_search does loose substring matching, so a
        search for 'ES' can return Japanese Yen ('JY...') contracts too.
        We filter to contracts whose name starts with the requested root,
        then pick the earliest expiry.
        """
        contracts = self.search_contracts(symbol, live=False)
        if not contracts:
            raise ProjectXError(f"No contracts returned for {symbol!r}")

        # Filter to exact-root match: contract name starts with symbol
        # (case-insensitive). E.g., 'ES' matches 'ESM6', 'ESU6'; not 'JY6'.
        sym_upper = symbol.upper().lstrip("/").rstrip("=F")
        matching = [
            c for c in contracts
            if (c.get("name") or "").upper().startswith(sym_upper)
        ]
        # Fallback: if name-prefix filter is empty, accept all (ProjectX
        # may return the right symbol under a different name field).
        if not matching:
            matching = contracts

        def expiry_key(c: dict) -> str:
            return c.get("expiryDate") or c.get("lastTradeDate") or c.get("name", "")

        sorted_contracts = sorted(matching, key=expiry_key)
        return sorted_contracts[0].get("id") or sorted_contracts[0].get("contractId")

    # ── Market data ─────────────────────────────────────────────
    def get_bars(
        self,
        contract_id: str,
        start_time: str,         # ISO 8601 with tz
        end_time: str,
        unit: int = 2,           # 1=Sec 2=Min 3=Hour 4=Day 5=Week
        unit_number: int = 1,
        limit: int = 1000,
        live: bool = True,
    ) -> list[dict]:
        data = self._request(
            "POST", "history_retrieve",
            json={
                "contractId": contract_id,
                "live": live,
                "startTime": start_time,
                "endTime": end_time,
                "unit": unit,
                "unitNumber": unit_number,
                "limit": limit,
                "includePartialBar": False,
            },
        )
        return data.get("bars", []) if isinstance(data, dict) else data


# ── Module-level singleton helper ───────────────────────────────
_client: ProjectXClient | None = None


def get_client() -> ProjectXClient:
    """Return a cached ProjectXClient instance."""
    global _client
    if _client is None:
        _client = ProjectXClient()
    return _client


def get_account_id() -> int:
    """Return the account ID from env, validated."""
    val = os.environ.get("PROJECTX_ACCOUNT_ID")
    if not val:
        raise ProjectXError(
            "PROJECTX_ACCOUNT_ID not set. Run ProjectXClient.get_accounts() "
            "once to find your account ID, then add it to .env."
        )
    return int(val)
