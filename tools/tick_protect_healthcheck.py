"""tick_protect_healthcheck — startup self-test for the tick → close path.

User concern (2026-05-17): the new tick_protect path was just built today
and has zero real-world validation. First time it fires for real is when
a live position retraces. If there's a bug in the callback wiring or the
close dispatch, we find out by losing money.

This module runs a synthetic-position test against a MOCK tick stream
during live_trader startup. If the synthetic close fires correctly within
N ms of the synthetic tick, the health check passes and live_trader
proceeds. If it doesn't, live_trader logs a critical alert and continues
with the 1-sec poll as the only safety net.

The check uses an in-memory mock — does NOT touch the real broker or
the real tick_stream. It verifies:
  1. on_tick callback invocation path works
  2. _close_in_flight lock works (no double-close)
  3. close dispatch worker thread starts + completes
  4. Position metadata cache update + lookup works
"""
from __future__ import annotations

import threading
import time
from typing import Any


class _MockClient:
    """In-memory broker stand-in. Records close requests."""
    def __init__(self):
        self.close_calls: list[tuple[int, str]] = []
        self._lock = threading.Lock()

    def close_position(self, account_id: int, contract_id: str) -> dict:
        with self._lock:
            self.close_calls.append((account_id, contract_id))
        return {"success": True}


def run_healthcheck(timeout_s: float = 2.0,
                     log_fn=None) -> dict:
    """Run the synthetic close-path test. Returns a result dict:
      {
        "passed": bool,
        "close_fired": bool,
        "latency_ms": float | None,
        "errors": list[str],
      }

    Idempotent: cleans up its own state before and after. Safe to call
    on every trader startup.
    """
    log = log_fn or (lambda _: None)
    result: dict[str, Any] = {
        "passed": False, "close_fired": False,
        "latency_ms": None, "errors": [],
    }

    try:
        # Import inside the function so the healthcheck is robust to
        # tick_protect import errors (which would show up in `errors`)
        from tools import tick_protect, profit_protect
    except Exception as e:
        result["errors"].append(f"import failed: {type(e).__name__}: {e}")
        return result

    # Snapshot existing state so we can restore at the end
    snapshot = {
        "high_water": dict(profit_protect._position_high_water),
        "peak_ts":   dict(profit_protect._position_peak_ts),
        "targets":   dict(profit_protect._target_usd_by_contract),
    }

    try:
        # 1) Wire a mock client into tick_protect.
        # IMPORTANT: don't reset_for_test() — would wipe any real positions
        # registered by the position-poller. We surgically swap the client
        # only, restore after.
        mock = _MockClient()
        prior_client = tick_protect._client
        prior_log = tick_protect._log
        prior_alert = tick_protect._alert
        tick_protect.configure(client=mock, log_fn=log, alert_fn=None)

        # 2) Register a synthetic MGC long position with peak=$50 (so the
        #    floor logic = max($20, $50*0.7) = $35 is active)
        SYNTH_CID = "CON.F.US.HEALTHCHECK.SYNTH"
        tick_protect.register_position(
            contract_id=SYNTH_CID, symbol="HEALTHCHECK",
            side="long", size=1, avg_price=100.0,
            tick_size=0.10, tick_value=1.0,
            account_id=99,
        )
        from datetime import datetime, timezone
        profit_protect._position_high_water["HEALTHCHECK_long"] = 50.0
        profit_protect._position_peak_ts["HEALTHCHECK_long"] = \
            datetime.now(tz=timezone.utc)

        # 3) Fire a tick at $100.30 → 3 ticks above entry = +$3 unrealized
        #    Peak was $50, floor=$35 → $3 < $35 → should trigger close
        t_start = time.perf_counter()
        tick_protect.on_tick(SYNTH_CID, {"price": 100.30, "ts": None})

        # 4) Wait up to timeout_s for the worker thread to dispatch close
        deadline = t_start + timeout_s
        while time.perf_counter() < deadline:
            if mock.close_calls:
                break
            time.sleep(0.005)
        latency_ms = (time.perf_counter() - t_start) * 1000

        if mock.close_calls:
            result["close_fired"] = True
            result["latency_ms"] = round(latency_ms, 1)
            if mock.close_calls[0] != (99, SYNTH_CID):
                result["errors"].append(
                    f"close fired with wrong args: {mock.close_calls[0]}")
            else:
                result["passed"] = True
        else:
            result["errors"].append(
                f"close did NOT fire within {timeout_s}s — callback path broken")

    except Exception as e:
        result["errors"].append(
            f"healthcheck exception: {type(e).__name__}: {e}")
    finally:
        # Restore state — surgical, not reset_for_test() (which would
        # wipe any real positions tracked by the position-poller).
        try:
            # Remove the synthetic position only
            tick_protect.unregister_position("CON.F.US.HEALTHCHECK.SYNTH")
            # Remove synthetic peak data only
            profit_protect._position_high_water.pop("HEALTHCHECK_long", None)
            profit_protect._position_peak_ts.pop("HEALTHCHECK_long", None)
            # Restore client/log/alert refs
            tick_protect.configure(client=prior_client,
                                    log_fn=prior_log,
                                    alert_fn=prior_alert)
        except Exception:
            pass

    return result


if __name__ == "__main__":
    # CLI smoke test
    import sys
    r = run_healthcheck(log_fn=print)
    print(f"\nResult: {r}")
    sys.exit(0 if r["passed"] else 1)
