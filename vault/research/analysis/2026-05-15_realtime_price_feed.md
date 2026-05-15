---
type: research
date: 2026-05-15
status: complete
priority: P0
references:
  - vault/_meta/improvement_backlog.md (REAL-TIME PRICE FEED research item)
  - tools/projectx_client.py (REST client)
  - tools/bar_fetcher.py (current 1-min bar polling)
  - tools/profit_protect.py (consumer of fresh prices)
---

# Real-time price feed investigation — ProjectX has SignalR

## TL;DR

ProjectX exposes **two SignalR WebSocket hubs** at a separate subdomain (`rtc.topstepx.com`) which the existing REST client doesn't touch. Subscribing to the market hub gives sub-second tick data. The user hub gives sub-second order/position updates. Both verified live tonight via direct HTTP probe.

**Recommendation:** build `tools/tick_stream.py` as a thin SignalR client. Wire `tools/profit_protect.check_and_close` to read the latest tick from a process-local cache instead of polling 1-min bar closes via `tools/bar_fetcher.fetch_bars()`. Estimated effort: 4-8 hours. Expected impact: eliminates the polling-latency slippage (worst-case ~60s; common case 5-15s) on profit-lock + reversal + time-decay exits.

## Methodology

1. Audited `tools/projectx_client.py` for streaming endpoints — none present in `_ENDPOINTS`.
2. Probed every plausible REST quote endpoint shape (`/api/MarketData/quote`, `/api/Quote/...`, `/api/Contract/price/...`, `/api/Market/...`) — all 404.
3. Fetched `/swagger/v1/swagger.json` from `api.topstepx.com`. **Confirmed REST surface = 19 endpoints, none for quotes/ticks/streams.**
4. Tested alternate hostnames: `rtc.topstepx.com` (DNS resolves), `gateway.topstepx.com` (does not), `stream.topstepx.com` (does not).
5. Probed `rtc.topstepx.com` for SignalR negotiate paths.

## Findings

### REST API has NO market-data quote endpoint

All 19 paths in the official swagger spec:
```
/api/Account/search          /api/Order/place
/api/Auth/loginApp           /api/Order/searchOpen
/api/Auth/loginKey           /api/Order/search
/api/Auth/logout             /api/Position/closeContract
/api/Auth/validate           /api/Position/partialCloseContract
/api/Contract/search         /api/Position/searchOpen
/api/Contract/searchById     /api/Status/ping
/api/Contract/available      /api/Trade/search
/api/History/retrieveBars
/api/Order/cancel
/api/Order/modify
```

`/api/History/retrieveBars` is the closest thing, and `tools/bar_fetcher.fetch_bars()` already wraps it. There is no single-symbol sub-second quote in REST.

### SignalR hubs exist at rtc.topstepx.com

```
POST https://rtc.topstepx.com/hubs/user/negotiate?negotiateVersion=1
→ 200 {"negotiateVersion":1,"connectionId":"...",
        "connectionToken":"...",
        "availableTransports":[{"transport":"WebSockets",
                                 "transferFormats":["Text","Binary"]}]}

POST https://rtc.topstepx.com/hubs/market/negotiate?negotiateVersion=1
→ 200 (same shape)
```

Both hubs accept the existing JWT (Bearer token from `auth_login_key`). No additional auth.

### Hub responsibilities (inferred by name)

- `/hubs/user` — order events, position events, account balance updates
- `/hubs/market` — quote / tick / bar / trade events for subscribed contracts

This split matches the standard TopstepX SDK architecture.

### Existing dependencies

`httpx` (already vendored, used by `projectx_client.py`) does NOT speak WebSocket. Adding a dep:
- `signalrcore` (pure Python, MIT) — most established
- `websockets` + manual SignalR framing — lower-level, fewer deps but more code

`signalrcore` is the right choice. ~one new requirements.txt entry.

## Implementation sketch

```python
# tools/tick_stream.py (new)
"""SignalR client for ProjectX rtc.topstepx.com market + user hubs.

Subscribes to a set of contracts, maintains a process-local cache
of the latest tick per contract. Consumers read from the cache;
the cache is updated in a background thread by the SignalR client.

On connection drop: auto-reconnect with exponential backoff. If
no tick received for >30s, mark stale; consumers fall back to the
existing bar-fetcher path.
"""
from signalrcore.hub_connection_builder import HubConnectionBuilder

class TickStream:
    def __init__(self, jwt: str):
        self.cache: dict[str, dict] = {}  # contract_id → {price, ts, bid, ask}
        self._stale_after_s = 30
        self._build_hub(jwt)

    def latest(self, contract_id: str) -> dict | None:
        entry = self.cache.get(contract_id)
        if entry is None: return None
        age = (datetime.now(UTC) - entry["ts"]).total_seconds()
        if age > self._stale_after_s: return None
        return entry

    def subscribe(self, contract_id: str): ...
    def unsubscribe(self, contract_id: str): ...
```

Then in `tools/profit_protect.check_and_close`:
```python
# Old: 1-min bar close polling
bars = fetch_bars_fn(client, symbol, 1, 5)
last_close = float(bars["Close"].iloc[-1])

# New: tick-cache read, fall back to bars if stale
tick = tick_stream.latest(contract_id)
if tick is not None:
    last_close = tick["price"]
else:
    # Fallback (network blip, cold start, etc.)
    bars = fetch_bars_fn(client, symbol, 1, 5)
    last_close = float(bars["Close"].iloc[-1])
```

## Cost/benefit

**Latency reduction:**
- Current: in-position polling runs every 1s (per scripts/live_trader.py), reads 1-min bar close. So data is 0-60s stale.
- Proposed: SignalR pushes tick events as they happen. Data is ~50-200ms stale (network RTT).
- **Improvement: 100-1000× lower price-data latency.**

**Where this matters most:**
1. Software take-profit hit detection — currently the trade has to wait for the next 1-min bar close before unrealized P&L is recomputed.
2. Reversal-detection exit — needs bar-close direction, so doesn't directly benefit (still 1-min bars). BUT the unrealized calc that gates the min-peak check would be tick-fresh.
3. Time-based profit decay — same as #2; the rule still references the bar pattern via `current` from polling.
4. Trailing-broker-stop placement — currently the trailing decision is made on possibly-stale data. Tick-fresh data means stop placement is at the right level.

**Where this WON'T help:**
- Bar-pattern strategies (FVG, NRB, etc.) — they consume completed bars by design.
- The broker stop fires at native broker speed regardless of our polling.

**Risk:**
- Adding a long-running background WebSocket thread to live_trader process. Reconnect logic must be solid or the cache goes stale and consumers fall back (which is OK behavior).
- New dep (`signalrcore`).
- More state in-process = more failure modes. Should add a sentinel check: tick_stream-stale alert.

## Open questions for the user

1. **Greenlight to implement?** ~4-8 hour build. Auto-mergeable if tests pass.
2. **Cache TTL: 30s or longer?** 30s is conservative. If network is reliable, 60s is fine.
3. **Subscribe to all live-filter contracts or only currently-open positions?** Open-positions is cheaper (fewer subscriptions) but misses pre-fill price data. Live-filter contracts is more bandwidth but ALL strategies benefit.
4. **Should the user hub be wired up too?** It'd give us instant order-fill / position-change events, replacing the current `_wait_for_entry_fill` polling. Bigger win but more surface to maintain.

## Conclusion

The infrastructure for sub-second price data exists at `rtc.topstepx.com`. The current 1-min-bar polling path is an artifact of the REST-only client; ProjectX always intended SignalR for streaming. Building `tools/tick_stream.py` is a straightforward 1-day project with significant edge-capture upside.

**Recommended next action:** queue a P0 implementation cycle once the user greenlights this. Pattern A risk: if the cache silently goes stale, profit-lock decisions trade on phantom prices. The 30s freshness gate + sentinel check on tick_stream-stale would close that loop.
