"""Layer 1 minimal-knife trader.

The simple, reliable execution layer. Reads validated cells from the
brain (state/strategy_validation.json), trades them via Topstep direct
API, halts on hard DLL. Nothing else.

What this DOES:
  - Read live_allowlist from state/strategy_validation.json
  - For each (strategy, symbol, session, side) cell, fetch bars + run strategy
  - On signal: place bracket (entry-limit + stop-limit + target-limit)
  - Verify protective legs working after entry fills
  - Force-close any position whose unrealized loss exceeds per-trade cap
  - Halt for the day on DLL breach

What this does NOT do (per the simplification):
  - Multi-tier strategy roster, cell allowlist, time windows (brain handles)
  - Defensive ladder, trailing profit lock, multiple safety floors
  - Orphan cleanup, misdirected leg detection, grace periods
  - Snapshot freshness gates, autonomy guardrails, agent integration
  - Memory, lessons, validation pipeline (those run separately as the brain)

The brain (Layer 2) is unchanged. This file replaces auto_trader.py
in production. The 2,900-line auto_trader.py is preserved as
auto_trader_v1_complex.py for reference.

USAGE:
  python -m scripts.live_trader              # live continuous loop
  python -m scripts.live_trader --once       # single scan + exit
  python -m scripts.live_trader --dry-run    # signals + decisions, no orders
  python -m scripts.live_trader --paper      # paper-mode (bars, signals, simulated fills)

Environment:
  FUND_MODE=live|paper          (paper = no orders placed)
  PROJECTX_*                    (broker credentials)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from dotenv import load_dotenv
load_dotenv()

# Project root
_HERE = Path(__file__).resolve().parent.parent
os.chdir(_HERE)
sys.path.insert(0, str(_HERE))

from tools.backtest import strategies as strats  # noqa: E402
from tools.projectx_client import (
    get_client, get_account_id, ProjectXError,  # noqa: E402
)
from state.db import get_db  # noqa: E402


# ────────────────────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────────────────────

SCAN_INTERVAL_SEC = 300          # 5-minute cadence
POSITION_POLL_SEC = 30            # sub-minute poll for per-trade cap / trailing-lock.
                                  # 2026-05-13 fix: the previous "$150 per-trade cap"
                                  # fired only on the 5-min scan tick. A position could
                                  # blow past the cap in thin tape before the next scan
                                  # — the 2026-05-12 GC long went from +$70 to −$210
                                  # in a single scan window, then to −$640 by the next.
                                  # A separate background thread now polls
                                  # tools/profit_protect.check_and_close every 30s so
                                  # the cap fires within ~30s of being exceeded.
LOOKBACK_BARS = 6                 # find_latest_signal cutoff (30 min on 5m bars)
PER_TRADE_LOSS_CAP_USD = 150.0    # force-close if unrealized < -this
SAME_SYMBOL_COOLDOWN_MIN = 45     # don't re-fire same symbol within window
MAX_TRADES_PER_DAY = 8            # hard cap on entries per UTC day
MIN_SIGNAL_R_TICKS = 6            # reject signals whose stop OR target distance is < N ticks
                                  # (rationale: place_bracket adds a 5-tick marketable-limit
                                  # buffer; if the strategy R-distance is smaller than the buffer,
                                  # the trade can't escape the buffer for a profit and may
                                  # degenerate into an orphan-leg fill. 2026-05-10 incident.)
MAX_SIGNAL_RISK_USD = 150.0       # reject signals whose stop-distance × tick_value × qty
                                  # exceeds this dollar amount. Symmetric with the per-trade
                                  # loss cap. 2026-05-12/13 incident: GC long fired with a
                                  # 6.4-point ($640) stop — the only floor was Topstep's
                                  # $1,000 DLL, so a single trade chewed 64% of the daily
                                  # limit. Equivalent of `per_trade_risk_pct_of_equity: 0.005`
                                  # (50 bps on $30K active risk capital). Pattern B —
                                  # calibration mismatch (strategy stop assumed a regime
                                  # where 64 ticks was reasonable; thin overnight tape made
                                  # it the entire account).
SKIP_TARGET_LEG = True            # 2026-05-11 evening: enabled per user direction after
                                  # confirming the broker target-fill anomaly. Target LIMIT
                                  # orders were auto-filling within ~100ms at next-available
                                  # market price (limit price essentially ignored). Workaround:
                                  # place ONLY entry + stop. Position runs until stop fires,
                                  # per-trade loss cap ($150), or manual flatten.
                                  # See vault/research/analysis/2026-05-11_broker_target_fill_anomaly.md
SHADOW_ON_HALT = True             # 2026-05-12: when halt is active, continue scanning + record
                                  # what would have been placed as shadow trades. Lets us collect
                                  # validation data during the daily-profit-cap halt window
                                  # (~21h) instead of going dark. Shadow trades land in the
                                  # `shadow_trades` table and get resolved by
                                  # scripts/shadow_trade_resolver.py at next preflight.
LIVE_ALLOWLIST_PATH = _HERE / "state" / "strategy_validation.json"
HALT_FILE = _HERE / "state" / "live_trader_halt"   # touch to halt; remove to resume


# Pure utility helpers — extracted to tools/trader_utils.py 2026-05-08.
# Re-imported with leading-underscore aliases so existing call-sites and
# tests (which use lt._foo) keep working.
from tools.trader_utils import (
    _load_yaml,
    _now_utc,
    _utcnow_iso,
    is_sunday_reopen_blackout,
)


def _log(msg: str) -> None:
    print(f"[{_now_utc().strftime('%Y-%m-%d %H:%M:%S')} UTC] {msg}", flush=True)


# ────────────────────────────────────────────────────────────────
# Halt + DLL gates
# ────────────────────────────────────────────────────────────────

def is_halted() -> tuple[bool, str]:
    """Manual halt via touch-file OR config halt timestamp."""
    if HALT_FILE.exists():
        return True, "manual halt file present"
    risk = _load_yaml("config/risk_limits.yaml")
    halt_ts = risk.get("hard_rules", {}).get("trading_halt_until", "")
    if halt_ts:
        try:
            halt_dt = datetime.fromisoformat(str(halt_ts).replace("Z", "+00:00"))
            if halt_dt > _now_utc():
                return True, f"trading_halt_until={halt_ts}"
        except Exception:
            pass
    if risk.get("hard_rules", {}).get("trading_halted"):
        return True, "trading_halted=true"
    return False, ""


def dll_breached(snap: dict) -> tuple[bool, str]:
    """True if today's realized P&L breaches the INTERNAL daily-loss
    target (tighter floor; per-user direction "agents target THIS, not
    Topstep's"). Falls through to Topstep's `daily_loss_limit_usd` as a
    backstop if the internal target is missing.

    2026-05-13 fix: prior version read only `daily_loss_limit_usd`
    (= Topstep's $1,000 hard limit). At -$683 day P&L the gate returned
    False and the trader fired a third bracket, taking the account to
    -$1,005 and triggering Topstep server-side canTrade=0. See
    vault/lessons/2026-05-13_overnight_dll_breach.md.
    """
    acct = _load_yaml("config/risk_limits.yaml").get("account", {}) or {}
    internal = acct.get("internal_dll_target_usd")
    topstep = float(acct.get("daily_loss_limit_usd", 1000))
    # Internal first; fall through to Topstep if internal is missing.
    # Treat 0 or None as "not configured" so a wiped value can't silently
    # disable the gate (Pattern A defense).
    dll = float(internal) if internal not in (None, 0, 0.0) else topstep
    source = "internal_dll" if internal not in (None, 0, 0.0) else "topstep_dll"
    realized = float(snap.get("realized_pl_day_usd") or 0)
    if realized <= -dll:
        return True, f"{source} breach: realized_day=${realized:+.2f} <= -${dll:.0f}"
    return False, ""


# ────────────────────────────────────────────────────────────────
# Snapshot capture (heartbeat + DLL)
# ────────────────────────────────────────────────────────────────
# capture_snapshot extracted to tools/snapshot_writer.py 2026-05-08
# (continuous trim, mirrors the compute_unrealized extraction). The
# function body is unchanged — degraded-heartbeat fallback preserved.
from tools.snapshot_writer import capture_snapshot  # noqa: E402

# compute_unrealized extracted to tools/unrealized_pnl.py 2026-05-08 (continuous trim).
from tools.unrealized_pnl import compute_unrealized  # noqa: E402


# ────────────────────────────────────────────────────────────────
# Brain interface — read live cells
# ────────────────────────────────────────────────────────────────

def load_live_cells() -> list[dict]:
    """Read the brain's validated allowlist."""
    if not LIVE_ALLOWLIST_PATH.exists():
        return []
    try:
        st = json.loads(LIVE_ALLOWLIST_PATH.read_text(encoding="utf-8"))
        return st.get("live_allowlist") or []
    except Exception:
        return []


def session_now_utc(now_utc: datetime) -> str:
    """Map UTC to ET session bucket."""
    et_hour = (now_utc.hour - 4 + now_utc.minute / 60.0) % 24
    if 9.5 <= et_hour < 16:    return "RTH"
    if 4 <= et_hour < 9.5:     return "London"
    if 16 <= et_hour < 20:     return "PostClose"
    return "Asian"


# ────────────────────────────────────────────────────────────────
# Bars + signals
# ────────────────────────────────────────────────────────────────

# fetch_bars extracted to tools/bar_fetcher.py 2026-05-08 (continuous trim).
# Wrapper preserves call signature so scan_once doesn't change.
from tools.bar_fetcher import fetch_bars as _fetch_bars_impl  # noqa: E402

def fetch_bars(client, symbol: str, minutes: int = 5, lookback: int = 200):
    return _fetch_bars_impl(client, symbol, minutes, lookback, log_fn=_log)


def _load_calendar_events(symbol: str) -> list[dict]:
    """Load HIGH/MEDIUM economic events affecting `symbol` from
    vault/economic_calendar/*.json. Returns [{'ts': datetime, 'severity': str}].
    Never raises; returns [] on any error or missing files. 2026-05-11."""
    cal_dir = _HERE / "vault" / "economic_calendar"
    if not cal_dir.exists():
        return []
    out: list[dict] = []
    # 1. Fed speakers / Fed releases
    fs = cal_dir / "fed_speakers.json"
    if fs.exists():
        try:
            data = json.loads(fs.read_text(encoding="utf-8"))
            for e in data.get("events", []) or []:
                infl = str(e.get("influence", "")).upper()
                if infl not in ("HIGH", "MEDIUM"):
                    continue
                ts = e.get("ts_utc")
                if not ts:
                    continue
                try:
                    dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                except Exception:
                    continue
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                out.append({"ts": dt, "severity": infl})
        except Exception:
            pass
    # 2. Treasury auctions for this symbol
    ta = cal_dir / "treasury_auctions.json"
    if ta.exists():
        try:
            data = json.loads(ta.read_text(encoding="utf-8"))
            for a in data.get("auctions", []) or []:
                primary = a.get("affected_primary", []) or []
                basis = a.get("affected_basis", []) or []
                if symbol not in primary and symbol not in basis:
                    continue
                ts = a.get("auction_dt_et")
                if not ts:
                    continue
                try:
                    dt = datetime.fromisoformat(str(ts))
                    if dt.tzinfo is None:
                        # ET is UTC-4 in DST. Approximate; events span ±15min anyway.
                        dt = dt.replace(tzinfo=timezone(timedelta(hours=-4)))
                except Exception:
                    continue
                severity = "HIGH" if symbol in primary else "MEDIUM"
                out.append({"ts": dt, "severity": severity})
        except Exception:
            pass
    # 3. today.json (econ data prints — EIA, CPI, NFP, etc.)
    tj = cal_dir / "today.json"
    if tj.exists():
        try:
            raw = json.loads(tj.read_text(encoding="utf-8"))
            events_iter = raw.get("events", []) if isinstance(raw, dict) else (raw or [])
            for e in events_iter:
                impact = str(e.get("impact", "")).lower()
                if impact not in ("high", "medium"):
                    continue
                ts = e.get("ts_utc") or e.get("time_utc")
                if not ts:
                    continue
                try:
                    dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                except Exception:
                    continue
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                out.append({"ts": dt, "severity": impact.upper()})
        except Exception:
            pass
    return out


def news_proximity_for(symbol: str, now: datetime | None = None) -> str:
    """Distance to nearest HIGH/MEDIUM economic event affecting `symbol`.
    Returns 'inside' (±15 min of HIGH), 'near' (15-60 min of HIGH OR
    ±60 min of MEDIUM), or 'clear' (otherwise). 2026-05-11.

    Used to gate cells around scheduled-event volatility. Strategies like
    vol_spike_fade can be tagged news_proximity=['near','inside'] for
    surgical fire-only-near-news deployment.
    """
    if now is None:
        now = _now_utc()
    events = _load_calendar_events(symbol)
    if not events:
        return "clear"
    closest_high = None
    closest_med = None
    for e in events:
        try:
            mins = abs((e["ts"] - now).total_seconds() / 60)
        except Exception:
            continue
        if e["severity"] == "HIGH":
            if closest_high is None or mins < closest_high:
                closest_high = mins
        elif e["severity"] == "MEDIUM":
            if closest_med is None or mins < closest_med:
                closest_med = mins
    if closest_high is not None and closest_high <= 15:
        return "inside"
    if (closest_high is not None and closest_high <= 60) or \
       (closest_med is not None and closest_med <= 60):
        return "near"
    return "clear"


def current_regime(bars: pd.DataFrame,
                    vol_lookback: int = 14, vol_ref_window: int = 100,
                    trend_lookback: int = 14, trend_ref_window: int = 100,
                    symbol: str | None = None) -> dict:
    """Compute the current vol+trend regime of the latest bar.

    Mirrors `scripts/regime_classifier.py` logic but computes inline so
    the trader doesn't need to read a stale per-day tag file.

    Returns:
        {'vol_regime': 'low'|'med'|'high',
         'trend_regime': 'trending'|'ranging',
         'news_proximity': 'clear'|'near'|'inside'}     # if symbol provided
    Returns {} if bars too short to classify.
    """
    if len(bars) < max(vol_ref_window, trend_ref_window) + vol_lookback:
        return {}
    try:
        # Vol regime: 14-bar realized vol vs 100-bar median
        returns = bars["Close"].pct_change()
        realized = returns.rolling(vol_lookback).std() * (252 * 78) ** 0.5
        median = realized.rolling(vol_ref_window, min_periods=20).median()
        last_realized = float(realized.iloc[-1])
        last_median = float(median.iloc[-1])
        if pd.isna(last_realized) or pd.isna(last_median) or last_median == 0:
            vol_regime = "med"
        elif last_realized < 0.7 * last_median:
            vol_regime = "low"
        elif last_realized > 1.4 * last_median:
            vol_regime = "high"
        else:
            vol_regime = "med"
        # Trend regime: 14-bar range vs 100-bar mean range
        rng = (bars["High"] - bars["Low"]).rolling(trend_lookback).mean()
        mean_rng = rng.rolling(trend_ref_window, min_periods=20).mean()
        last_rng = float(rng.iloc[-1])
        last_mean = float(mean_rng.iloc[-1])
        if pd.isna(last_rng) or pd.isna(last_mean) or last_mean == 0:
            trend_regime = "ranging"
        elif last_rng > 1.3 * last_mean:
            trend_regime = "trending"
        else:
            trend_regime = "ranging"
    except Exception:
        return {}
    result = {"vol_regime": vol_regime, "trend_regime": trend_regime}
    if symbol:
        try:
            result["news_proximity"] = news_proximity_for(symbol)
        except Exception:
            pass
    return result


def cell_passes_regime_filter(cell: dict, regime: dict) -> tuple[bool, str]:
    """Check if current regime matches the cell's optional regime_filter.

    Cells can declare a `regime_filter` dict like:
        {"vol_regime": ["high"], "trend_regime": ["trending", "ranging"]}
    A cell passes iff EVERY declared key matches one of its allowed values.
    Cells with no `regime_filter` always pass (backward-compatible).

    2026-05-11: enables surgical deployment of volatility-aware strategies
    (keltner_breakout, vol_spike_fade) so they fire only in their target
    regime, not on every signal.
    """
    cell_filter = cell.get("regime_filter")
    if not cell_filter:
        return True, ""
    if not regime:
        # If we couldn't compute regime, fail-closed: don't fire restricted cells
        return False, "regime unknown"
    for key, allowed in cell_filter.items():
        if regime.get(key) not in allowed:
            return False, f"{key}={regime.get(key)} not in {allowed}"
    return True, ""


def compute_signal_risk_usd(sig: dict, symbol: str, qty: int = 1) -> float | None:
    """Compute the dollar risk of a signal: stop_ticks × tick_value × qty.

    Returns None when economics can't be computed (missing price/stop,
    invalid tick, missing tick_value). Callers MUST treat None as
    'unknown — refuse to gate on it' (fail closed).
    """
    if sig.get("price") is None or sig.get("stop") is None:
        return None
    tick = _tick_size(symbol)
    if tick <= 0:
        return None
    tval = _tick_value(symbol)
    if tval <= 0:
        return None
    stop_ticks = abs(float(sig["price"]) - float(sig["stop"])) / tick
    return stop_ticks * tval * max(1, int(qty))


def signal_passes_max_risk_gate(sig: dict, symbol: str, qty: int = 1,
                                  max_risk_usd: float = MAX_SIGNAL_RISK_USD,
                                  ) -> tuple[bool, str]:
    """Reject signals whose stop-distance dollar risk exceeds max_risk_usd.

    Symmetric with the per-trade loss cap. Pattern B defense for the
    2026-05-12/13 GC incident: a strategy returned a 64-tick stop and
    the trader placed it unchecked, blowing through the $150 per-trade
    cap (which only fires AFTER fill, on a 5-min scan tick) and ending
    up at the broker stop for -$640.

    Returns (passes, reason). On reject, reason is human-readable.

    Default-deny: missing tick_value or stop → reject. Treating a missing
    value as 'unknown ok' would replicate the Pattern A failure pattern.
    """
    risk_usd = compute_signal_risk_usd(sig, symbol, qty)
    if risk_usd is None:
        return False, "missing price/stop or tick economics — refusing to gate"
    if risk_usd > max_risk_usd:
        tick = _tick_size(symbol)
        tval = _tick_value(symbol)
        stop_ticks = abs(float(sig["price"]) - float(sig["stop"])) / tick
        return False, (f"risk too large (${risk_usd:.0f} > ${max_risk_usd:.0f} cap; "
                        f"stop={stop_ticks:.1f}t × ${tval:.2f}/tick × {qty}ct)")
    return True, ""


def projected_dll_breach(snap: dict, signal_risk_usd: float
                          ) -> tuple[bool, str]:
    """True if (current day P&L − this signal's worst-case loss) would
    cross the internal DLL target. Pre-trade projection — mirrors
    hooks/risk_gate._check_combine_defensive_ladder's projection logic
    but lives in the live_trader path (auto_trader/SDK hook isn't
    invoked here).

    The defensive ladder's warn/restrict tiers are advisory only (target
    prompt-level discipline). The lockdown tier (= internal_dll_target)
    is the actual hard halt — and we already enforce it post-trade in
    dll_breached(). This function adds the PRE-TRADE projection so we
    don't fire a signal that would necessarily push us past lockdown.

    Uses day P&L = realized + unrealized (matches the hook). Falls
    through to Topstep DLL if internal is missing or zero — same
    Pattern A defense as dll_breached().
    """
    if signal_risk_usd <= 0:
        return False, ""
    acct = _load_yaml("config/risk_limits.yaml").get("account", {}) or {}
    internal = acct.get("internal_dll_target_usd")
    topstep = float(acct.get("daily_loss_limit_usd", 1000))
    dll = float(internal) if internal not in (None, 0, 0.0) else topstep
    source = "internal_dll" if internal not in (None, 0, 0.0) else "topstep_dll"
    realized = float(snap.get("realized_pl_day_usd") or 0)
    unrealized = float(snap.get("unrealized_pl_usd") or 0)
    day_pl = realized + unrealized
    projected = day_pl - signal_risk_usd
    if projected <= -dll:
        return True, (f"{source} projection: day_pl ${day_pl:+.2f} − "
                        f"${signal_risk_usd:.0f} worst-case = ${projected:+.2f} "
                        f"<= -${dll:.0f}")
    return False, ""


def signal_passes_min_r_gate(sig: dict, symbol: str,
                              min_r_ticks: int = MIN_SIGNAL_R_TICKS,
                              ) -> tuple[bool, str]:
    """Reject signals whose stop-distance OR target-distance is below
    min_r_ticks. Returns (passes, reason). On reject, reason is a
    human-readable diagnostic string.

    Rationale (2026-05-10 incident): place_bracket() places the entry
    as a marketable limit with a 5-tick slippage buffer. When the
    strategy's R-distance is smaller than the buffer, the trade can't
    escape the buffer for a profit; worse, when the strategy stop is
    closer than the buffer's full range to entry, a single tick of
    adverse movement can fire the stop leg alone (entry limit never
    fills), opening an unintended reversed position via the orphan-leg
    pathway. Block both before placement.
    """
    if sig.get("price") is None or sig.get("stop") is None:
        return False, "missing price or stop"
    tick = _tick_size(symbol)
    if tick <= 0:
        return False, f"invalid tick size for {symbol}"
    sig_price = float(sig["price"])
    sig_stop = float(sig["stop"])
    stop_ticks = abs(sig_price - sig_stop) / tick
    target_val = sig.get("target")
    target_ticks = (abs(sig_price - float(target_val)) / tick
                    if target_val is not None else float("inf"))
    if stop_ticks < min_r_ticks:
        return False, (f"stop too close ({stop_ticks:.1f}t < {min_r_ticks}t min)")
    if target_ticks < min_r_ticks:
        return False, (f"target too close ({target_ticks:.1f}t < {min_r_ticks}t min)")
    return True, ""


def find_latest_signal(bars: pd.DataFrame, strategy_fn,
                        symbol: str | None = None) -> dict | None:
    """Run strategy on bars, return the most recent entry signal in
    the last LOOKBACK_BARS bars (ignore stale).

    2026-05-11: when `symbol` is provided AND the strategy accepts a
    `tick_size` keyword, the symbol's tick_size is auto-injected. This
    activates floor-the-stop logic (min_stop_ticks) inside strategies
    like `gap_fill` / `gap_fill_wide` so they refuse to emit degenerate
    sub-tick-stop signals at the strategy layer. The trader-side
    MIN_SIGNAL_R_TICKS gate remains as defense-in-depth.
    """
    import inspect
    if len(bars) < 30:
        return None
    cutoff_idx = max(0, len(bars) - LOOKBACK_BARS)
    cutoff = bars.index[cutoff_idx]
    # Build a callable that optionally injects tick_size for strategies
    # that accept it. Cheap to do per-call; no state side effects.
    call = strategy_fn
    if symbol is not None:
        try:
            sig_params = inspect.signature(strategy_fn).parameters
            if "tick_size" in sig_params:
                tick = _tick_size(symbol)
                if tick > 0:
                    call = lambda b, _f=strategy_fn, _t=tick: _f(b, tick_size=_t)
        except (TypeError, ValueError):
            pass
    latest = None
    try:
        for sig in call(bars):
            if sig.kind != "entry":
                continue
            if sig.date >= cutoff:
                latest = sig
    except Exception:
        return None
    if latest is None:
        return None
    return {
        "date": latest.date, "side": latest.side,
        "price": float(latest.price),
        "stop": float(latest.stop) if latest.stop is not None else None,
        "target": float(latest.target) if latest.target is not None else None,
        "reason": latest.reason,
    }


# ────────────────────────────────────────────────────────────────
# Bracket placement
# ────────────────────────────────────────────────────────────────

# Tick math extracted to tools/trader_utils.py
from tools.trader_utils import _tick_size, _tick_value, _round_to_tick  # noqa: E402


FILL_WAIT_TIMEOUT_S = 30          # how long to wait for entry to fill before cancelling
FILL_WAIT_POLL_S = 2              # polling cadence while waiting


def _position_signature(client, account_id, contract_id: str) -> tuple[int, int]:
    """(type, size) for the contract, or (0, 0) if flat. Used to detect
    entry fills without trusting any single API field."""
    try:
        for p in client.get_positions(account_id):
            if p.get("contractId") == contract_id:
                size = int(p.get("size", 0))
                if size != 0:
                    return (int(p.get("type", 0)), size)
    except Exception:
        pass
    return (0, 0)


def _position_avg_price(client, account_id, contract_id: str) -> float | None:
    """Return the averagePrice for the open position on this contract,
    or None if flat. 2026-05-11: needed to recalculate the stop AFTER
    fill — see place_bracket comment on the MNQ 39-point-favorable-fill
    bug that left the position unprotected."""
    try:
        for p in client.get_positions(account_id):
            if p.get("contractId") == contract_id and int(p.get("size", 0)) != 0:
                px = p.get("averagePrice")
                if px is not None:
                    return float(px)
    except Exception:
        pass
    return None


def _verify_stop_landed(client, account_id, contract_id: str,
                        stop_cid: str, poll_attempts: int = 3,
                        poll_s: float = 1.0) -> bool:
    """Confirm the stop order shows up in working orders after placement.
    Polls a few times with short delay because brokers can lag in
    surfacing newly-placed orders. Returns True iff the order is found.
    2026-05-11."""
    for _ in range(poll_attempts):
        try:
            for o in client.get_working_orders(account_id) or []:
                if str(o.get("customTag") or "") == stop_cid:
                    return True
        except Exception:
            pass
        time.sleep(poll_s)
    return False


def _emergency_flatten_position(client, account_id, contract_id: str,
                                 side_to_close: str, qty: int,
                                 reason: str) -> bool:
    """Market-close a position that has no working protective stop.
    2026-05-11: belt-and-suspenders for stop-placement failures."""
    import uuid as _uuid
    cid = f"emergency_flat_{_uuid.uuid4().hex[:8]}"
    try:
        client.place_order(
            account_id=account_id, contract_id=contract_id,
            side=side_to_close, qty=int(qty), order_type="market",
            time_in_force="ioc", client_order_id=cid,
        )
        _log(f"  EMERGENCY FLATTEN: {contract_id} {side_to_close} x{qty} -- {reason}")
        return True
    except Exception as e:
        _log(f"  EMERGENCY FLATTEN FAILED for {contract_id}: {e}")
        return False


def _wait_for_entry_fill(client, account_id, contract_id: str,
                          baseline_sig: tuple[int, int],
                          timeout_s: int = FILL_WAIT_TIMEOUT_S,
                          poll_s: int = FILL_WAIT_POLL_S) -> bool:
    """Poll until the position signature changes (= entry filled) or
    timeout. Returns True iff a change was detected. Default-deny:
    timeout → not filled → caller cancels entry."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if _position_signature(client, account_id, contract_id) != baseline_sig:
            return True
        time.sleep(poll_s)
    return False


def place_bracket(client, account_id, symbol: str, signal: dict,
                  qty: int = 1, dry_run: bool = False) -> dict:
    """Place entry-limit; on confirmed fill, place stop + target.

    Sequence (orphan-leg-safe, 2026-05-10):
      1. Snapshot the position signature for this contract.
      2. Place entry as marketable-limit.
      3. Poll positions; if the signature changes within FILL_WAIT_TIMEOUT_S
         seconds, the entry filled -> place protective stop and target.
      4. If the timeout expires with no signature change, cancel the
         entry. NO protective legs are placed.

    Rationale: the prior implementation placed all three legs back-to-back.
    When the entry limit never filled but the stop-trigger price was close
    enough to be hit by routine price movement, the stop leg would fire
    alone and OPEN an unintended reversed position. The 2026-05-10
    incident cost $137.89 via this exact pathway. See
    project_alerting_infrastructure.md and the bracket OCO history."""
    side = "buy" if signal["side"] == "long" else "sell"
    cid = f"live_{uuid.uuid4().hex[:12]}"
    db = get_db()
    tick = _tick_size(symbol)
    entry_price = float(signal["price"])
    # Marketable-limit: 5-tick slippage buffer (matches v1 behavior, proven)
    if side == "buy":
        limit_px = _round_to_tick(entry_price + 5 * tick, tick)
    else:
        limit_px = _round_to_tick(entry_price - 5 * tick, tick)
    stop_px = _round_to_tick(float(signal["stop"]), tick)
    target_px = _round_to_tick(float(signal["target"]), tick) if signal.get("target") else None

    if dry_run:
        _log(f"  DRY: would place {symbol} {side} qty={qty} entry={limit_px} "
              f"stop={stop_px} target={target_px} cid={cid}")
        return {"status": "dry_run", "client_order_id": cid}

    # Front-month contract id
    try:
        contract_id = client.front_month_contract_id(symbol)
    except ProjectXError as e:
        _log(f"  contract lookup failed for {symbol}: {e}")
        return {"status": "failed", "error": str(e)}

    # Record entry in DB before submitting
    db.connect().execute(
        """INSERT INTO orders (client_order_id, agent, ts_proposed, symbol, side,
                                 order_type, qty, limit_price, stop_price,
                                 status, risk_verdict)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (cid, "live_trader", _utcnow_iso(), symbol, side, "limit", int(qty),
         limit_px, stop_px, "proposed", "allow"),
    )
    db.connect().commit()

    # 1. Snapshot baseline position for fill detection (must precede placement)
    baseline_sig = _position_signature(client, account_id, contract_id)

    # 2. Entry as marketable-limit
    try:
        result = client.place_order(
            account_id=account_id, contract_id=contract_id,
            side=side, qty=int(qty), order_type="limit",
            limit_price=limit_px, stop_price=None,
            time_in_force="day", client_order_id=cid,
        )
    except ProjectXError as e:
        _log(f"  entry place failed: {e}")
        return {"status": "failed", "error": str(e)}

    if isinstance(result, dict) and result.get("success") is False:
        err = result.get("errorMessage") or "broker rejected"
        _log(f"  entry rejected: {err}")
        return {"status": "rejected", "error": err}

    broker_oid = (result.get("orderId") or result.get("id") if isinstance(result, dict) else None)
    db.connect().execute(
        "UPDATE orders SET ts_submitted=?, status=?, broker_order_id=? WHERE client_order_id=?",
        (_utcnow_iso(), "submitted", str(broker_oid) if broker_oid else None, cid),
    )
    db.connect().commit()

    # 3. WAIT for fill confirmation before placing protective legs.
    # Without this gate the protective stop/target can fire alone when
    # the entry limit never fills, opening an unintended reversed
    # position (2026-05-10 incident).
    _log(f"  {symbol} entry placed, polling fill (timeout {FILL_WAIT_TIMEOUT_S}s)")
    filled = _wait_for_entry_fill(client, account_id, contract_id, baseline_sig)
    if not filled:
        _log(f"  {symbol} entry {cid} UNFILLED after {FILL_WAIT_TIMEOUT_S}s -- "
              f"cancelling; no protective legs placed")
        try:
            if broker_oid is not None:
                client.cancel_order(account_id, broker_oid)
        except Exception as e:
            _log(f"  entry cancel failed (will remain working): {e}")
        db.connect().execute(
            "UPDATE orders SET status=?, ts_cancelled=? WHERE client_order_id=?",
            ("cancelled_unfilled", _utcnow_iso(), cid),
        )
        db.connect().commit()
        return {"status": "cancelled_unfilled", "client_order_id": cid}
    # 3a. Recalculate stop relative to ACTUAL fill price.
    # 2026-05-11 MNQ incident: signal entry was 29448.5, marketable-limit fill
    # was 29409.25 (39 pts favorable slippage). Original signal stop at 29437.75
    # ended up on the wrong side of the actual fill -> broker rejected -> position
    # ran unprotected. Fix: keep the signal's RISK DISTANCE but anchor it to the
    # fill price instead of the signal's expected entry.
    actual_fill = _position_avg_price(client, account_id, contract_id) or entry_price
    signal_risk = abs(entry_price - float(signal["stop"]))
    if side == "buy":
        stop_px = _round_to_tick(actual_fill - signal_risk, tick)
    else:
        stop_px = _round_to_tick(actual_fill + signal_risk, tick)
    _log(f"  {symbol} entry FILLED @ {actual_fill}; "
          f"stop recalculated to {stop_px} (risk={signal_risk:.4f} from fill)")

    # 4. Stop-limit (1-tick offset for Topstep's tight-limit rule)
    # NOTE: when SKIP_TARGET_LEG is True (broker target-fill anomaly workaround),
    # we place only the stop and skip the target leg below.
    opp = "sell" if side == "buy" else "buy"
    stop_limit_px = (stop_px - tick) if opp == "sell" else (stop_px + tick)
    stop_limit_px = _round_to_tick(stop_limit_px, tick)
    stop_cid = cid + "_stop"
    stop_placed_ok = False
    try:
        sr = client.place_order(
            account_id=account_id, contract_id=contract_id,
            side=opp, qty=int(qty), order_type="stop_limit",
            limit_price=stop_limit_px, stop_price=stop_px,
            time_in_force="gtc", client_order_id=stop_cid,
        )
        sboid = (sr.get("orderId") or sr.get("id")) if isinstance(sr, dict) else None
        # Detect broker-side rejection of the stop (returns success=False).
        sr_ok = (not isinstance(sr, dict)) or sr.get("success") is not False
        if not sr_ok:
            err = sr.get("errorMessage") or "rejected"
            _log(f"  stop placement REJECTED by broker: {err}")
        else:
            db.connect().execute(
                """INSERT INTO orders (client_order_id, agent, ts_proposed, ts_submitted,
                                         symbol, side, order_type, qty, stop_price,
                                         status, risk_verdict, broker_order_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (stop_cid, "live_trader", _utcnow_iso(), _utcnow_iso(),
                 symbol, opp, "stop", int(qty), stop_px,
                 "submitted", "allow", str(sboid) if sboid else None),
            )
            db.connect().commit()
            # 4a. VERIFY the stop is actually working at the broker.
            # 2026-05-11: rejection returned success=False but in earlier
            # implementations rejection still slipped past silently. Belt:
            # poll working orders for the stop_cid. If absent, emergency-flatten.
            stop_placed_ok = _verify_stop_landed(client, account_id, contract_id, stop_cid)
            if not stop_placed_ok:
                _log(f"  CRITICAL: stop {stop_cid} not visible in working orders "
                      f"after placement; emergency-flattening position")
                _emergency_flatten_position(
                    client, account_id, contract_id,
                    side_to_close=opp, qty=int(qty),
                    reason=f"stop {stop_cid} did not land at broker",
                )
                return {"status": "stop_placement_failed_flattened",
                        "client_order_id": cid}
    except ProjectXError as e:
        _log(f"  stop placement failed: {e}")
        # No stop at broker -> emergency-flatten the now-unprotected position
        _emergency_flatten_position(
            client, account_id, contract_id,
            side_to_close=opp, qty=int(qty),
            reason=f"stop place_order raised: {e}",
        )
        return {"status": "stop_placement_failed_flattened",
                "client_order_id": cid}
        # Continue — target may still place; verification will catch missing stop

    # 3. Target as limit (only if target price provided AND target legs not skipped)
    if target_px is not None and not SKIP_TARGET_LEG:
        target_cid = cid + "_target"
        try:
            tr = client.place_order(
                account_id=account_id, contract_id=contract_id,
                side=opp, qty=int(qty), order_type="limit",
                limit_price=target_px, stop_price=None,
                time_in_force="gtc", client_order_id=target_cid,
            )
            tboid = (tr.get("orderId") or tr.get("id")) if isinstance(tr, dict) else None
            db.connect().execute(
                """INSERT INTO orders (client_order_id, agent, ts_proposed, ts_submitted,
                                         symbol, side, order_type, qty, limit_price,
                                         status, risk_verdict, broker_order_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (target_cid, "live_trader", _utcnow_iso(), _utcnow_iso(),
                 symbol, opp, "limit", int(qty), target_px,
                 "submitted", "allow", str(tboid) if tboid else None),
            )
            db.connect().commit()
        except ProjectXError as e:
            _log(f"  target placement failed: {e}")

    _log(f"  PLACED {symbol} {side} qty={qty} entry≈{limit_px} stop={stop_px} "
          f"target={target_px or '—'} cid={cid}")
    return {"status": "submitted", "client_order_id": cid,
            "broker_order_id": broker_oid}


# ────────────────────────────────────────────────────────────────
# Per-trade loss-cap enforcement
# ────────────────────────────────────────────────────────────────

def enforce_loss_cap(client, account_id) -> int:
    """Force-close any position whose unrealized loss < -PER_TRADE_LOSS_CAP_USD.
    Returns # positions closed."""
    closed = 0
    try:
        positions = client.get_positions(account_id) or []
    except Exception:
        return 0
    syms = _load_yaml("config/symbols.yaml").get("symbols", {})
    for p in positions:
        size = int(p.get("size") or 0)
        if size == 0:
            continue
        contract = p.get("contractId") or ""
        avg = float(p.get("avgPrice") or 0)
        if avg <= 0 or not contract:
            continue
        type_code = int(p.get("type") or 0)
        sign = 1 if type_code == 1 else -1 if type_code == 2 else (1 if size > 0 else -1)
        size = abs(size)
        root = None
        for tok in contract.split("."):
            if tok in ("CON", "F", "US", ""): continue
            if len(tok) <= 3 and tok and tok[0].isalpha() and tok[1:].isdigit(): continue
            root = tok; break
        meta = syms.get(root or "", {})
        tick_size = float(meta.get("tick_size") or 0)
        tick_value = float(meta.get("tick_value") or 0)
        if tick_size <= 0 or tick_value <= 0:
            continue
        try:
            bars = client.get_bars(contract_id=contract,
                                    start_time=(_now_utc() - timedelta(minutes=10)).isoformat(),
                                    end_time=_now_utc().isoformat(),
                                    unit=2, unit_number=1, limit=5, live=False)
            mark = float(bars[-1].get("c") or 0) if bars else 0
        except Exception:
            continue
        if mark <= 0:
            continue
        unrealized = sign * size * ((mark - avg) / tick_size) * tick_value
        if unrealized < -PER_TRADE_LOSS_CAP_USD:
            opp = "sell" if type_code == 1 else "buy"
            cid = f"livecap_{uuid.uuid4().hex[:8]}"
            try:
                client.place_order(account_id=account_id, contract_id=contract,
                                     side=opp, qty=size, order_type="market",
                                     time_in_force="ioc", client_order_id=cid)
                _log(f"  LOSS-CAP CLOSE: {root} unrealized=${unrealized:+.2f} < -${PER_TRADE_LOSS_CAP_USD:.0f}")
                closed += 1
            except Exception as e:
                _log(f"  loss-cap close failed for {root}: {e}")
    return closed


# ────────────────────────────────────────────────────────────────
# Orphan-bracket cleanup
# ────────────────────────────────────────────────────────────────

ORPHAN_GRACE_SEC = 120  # 2-min grace before any cancel


def cleanup_orphan_brackets(client, account_id) -> int:
    """Cancel working bracket legs whose underlying position is flat.

    Why: ProjectX `place_order` has no native bracket linkage; v2 places
    entry/stop/target as 3 independent orders. If broker's implicit OCO
    fails (or simply doesn't exist), one leg filling leaves the others
    working. This sweep cancels orders that no longer protect a position.

    Safe-by-default:
      - 2-min grace per order: never cancels a freshly-placed bracket
        whose position hasn't propagated through the API yet.
      - Only acts on orders tagged 'live_' (our customTag prefix). Won't
        touch user-placed manual orders.
      - Only cancels when position is verifiably flat (not inferred).

    Returns # orders cancelled.
    """
    cancelled = 0
    try:
        positions = client.get_positions(account_id) or []
        working = client.get_working_orders(account_id) or []
    except Exception as e:
        _log(f"  cleanup skipped (broker fetch failed): {type(e).__name__}: {e}")
        return 0

    # Map contractId → True if position is non-zero
    has_position: dict[str, bool] = {}
    for p in positions:
        cid = p.get("contractId")
        if not cid:
            continue
        size = int(p.get("size") or 0)
        if size != 0:
            has_position[cid] = True

    now = _now_utc()
    for o in working:
        tag = str(o.get("customTag") or "")
        if not tag.startswith("live_"):
            continue  # not ours
        cid = o.get("contractId")
        if not cid:
            continue
        if has_position.get(cid):
            continue  # position is open; bracket is legitimate

        # Position is flat for this contract. Apply grace period.
        try:
            ts_str = o.get("creationTimestamp") or ""
            if ts_str:
                order_ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                age_sec = (now - order_ts).total_seconds()
            else:
                age_sec = ORPHAN_GRACE_SEC + 1  # no timestamp → assume old enough
        except Exception:
            age_sec = ORPHAN_GRACE_SEC + 1

        if age_sec < ORPHAN_GRACE_SEC:
            continue  # too fresh; broker may still be propagating fill state

        oid = o.get("id") or o.get("orderId")
        if not oid:
            continue
        try:
            client.cancel_order(account_id, oid)
            _log(f"  cleaned orphan {tag} (id={oid}, age={age_sec:.0f}s, contract={cid})")
            cancelled += 1
        except Exception as e:
            _log(f"  cleanup cancel failed for {oid}: {type(e).__name__}: {e}")

    return cancelled


# Cooldown / daily-count queries extracted to tools/trade_state.py 2026-05-08.
from tools.trade_state import recent_thesis_for as _recent_thesis_for_impl  # noqa: E402
from tools.trade_state import todays_trade_count  # noqa: E402

def recent_thesis_for(symbol: str, minutes: int = SAME_SYMBOL_COOLDOWN_MIN) -> bool:
    return _recent_thesis_for_impl(symbol, minutes)


# ────────────────────────────────────────────────────────────────
# Main scan loop
# ────────────────────────────────────────────────────────────────

def scan_once(*, dry_run: bool = False, paper: bool = False) -> dict:
    """One scan pass: snapshot, gates, signal-detect, place.

    2026-05-12: when halt is active AND `SHADOW_ON_HALT=True`, continue
    scanning and record what would have been placed as shadow trades.
    No broker calls; just validation-data accumulation."""
    summary = {"scanned": 0, "triggers": 0, "placed": 0, "blocked": 0,
               "skipped_in_trade": 0, "skipped_cooldown": 0, "errors": 0,
               "shadow": 0}
    halted, reason = is_halted()
    shadow_only = halted and SHADOW_ON_HALT and not paper
    if halted and not shadow_only:
        _log(f"HALTED: {reason}")
        return {"status": "halted", "reason": reason}
    if shadow_only:
        _log(f"HALTED (shadow mode active — no broker writes): {reason}")

    # Sunday-reopen first-30-min blackout: skip new entries when spreads are widest.
    # Snapshots + cleanup still run; we just don't place new trades.
    if is_sunday_reopen_blackout(_now_utc()):
        _log("Sunday-reopen blackout (17:00-17:30 ET): skipping new entries this scan")
        return {"status": "sunday_reopen_blackout"}

    try:
        client = get_client()
        account_id = get_account_id()
    except Exception as e:
        _log(f"broker unavailable: {e}")
        return {"status": "broker_unavailable", "error": str(e)}

    snap = capture_snapshot(client, account_id)
    if snap and not snap.get("can_trade", True):
        _log(f"can_trade=false; halt scan")
        return {"status": "broker_can_trade_false"}

    # DLL hard kill
    if snap:
        breached, why = dll_breached(snap)
        if breached:
            _log(f"DLL BREACH: {why}")
            return {"status": "dll_halt", "reason": why}

    # 3:10 PM CT hard-flatten enforcement (Topstep Combine + XFA rule).
    # Must run BEFORE entry/exit logic so the deadline is honored even
    # if signals fire. See tools/hard_flatten_clock.py for window logic.
    if not dry_run and not paper:
        from tools.hard_flatten_clock import (enforce_hard_flatten,
                                                should_block_new_entries)
        _hf_result = enforce_hard_flatten(client, account_id, log_fn=_log)
        if _hf_result["flattened"] or _hf_result["cancelled"]:
            _log(f"  HARD_FLATTEN window={_hf_result['window']}: "
                  f"flattened {len(_hf_result['flattened'])} position(s), "
                  f"cancelled {_hf_result['cancelled']} order(s)")
        if should_block_new_entries():
            _log(f"  Within 3:10 PM CT closing window — blocking new entries this scan")
            return {"status": "hard_flatten_window", **_hf_result}

    # Per-trade loss-cap enforcement + trailing-profit-lock + daily cap
    if not dry_run and not paper:
        enforce_loss_cap(client, account_id)
        # 2026-05-12: periodic protection sweep — verify each open position
        # still has a working broker stop. Catches stops that the broker
        # cancelled mid-session (session-end cleanup, server error, etc.).
        # Complements `_verify_stop_landed` which only checks at placement.
        from tools.position_protection import sweep as _protection_sweep
        _protection_sweep(client, account_id, log_fn=_log)
        # 2026-05-11 evening: with SKIP_TARGET_LEG=True, the broker doesn't
        # auto-take profit (no target leg). This call provides software-side
        # take-profit via the trailing-profit-lock + hard-cap rules in
        # tools/profit_protect.py. See module docstring for tier definitions.
        from tools.profit_protect import check_and_close as _profit_lock_check
        _profit_lock_check(client, account_id, log_fn=_log)
        # 2026-05-12: daily-profit cap (Combine-only). Caps a single day's
        # gains to keep the 50% consistency rule satisfied. Auto-disabled
        # when account_stage != combine (see config/account_stage.yaml).
        from tools.account_stage import (combine_daily_profit_cap_usd,
                                          daily_window_reset_hour_ct)
        from tools.daily_profit_cap import check_and_enforce as _profit_cap_check
        _cap = combine_daily_profit_cap_usd()
        # Skip cap check under shadow_only — halt is already active that
        # was caused by the cap; re-running would just spam the log.
        if _cap is not None and not shadow_only:
            def _set_halt_to(dt_utc):
                # Use the same halt mechanism as scripts/halt.py: text-edits
                # config/risk_limits.yaml's trading_halt_until line (preserving
                # comments). _write_halt is module-private but we use it here
                # to avoid duplicating the regex-edit logic.
                from scripts.halt import _write_halt
                _write_halt(dt_utc, reason="daily_profit_cap")
            _cap_result = _profit_cap_check(
                client, account_id, cap_usd=_cap,
                reset_hour_ct=daily_window_reset_hour_ct(),
                log_fn=_log, halt_setter=_set_halt_to,
            )
            # 2026-05-12 hotfix: if the cap triggered THIS scan, the halt was
            # just set but is_halted() at the top of scan_once already ran
            # before the halt was written. Short-circuit the rest of this
            # scan so we don't accidentally place new entries between the
            # cap firing and the next scan's halt-check.
            if _cap_result.get("triggered"):
                return {"status": "daily_profit_cap_hit", **_cap_result}
        cleanup_orphan_brackets(client, account_id)

    # Cells to scan
    cells = load_live_cells()
    if not cells:
        _log(f"no live cells in allowlist; skipping")
        return {"status": "no_cells"}

    sess_now = session_now_utc(_now_utc())
    # Group cells by symbol so we fetch bars once per symbol
    cells_by_symbol: dict[str, list[dict]] = {}
    for c in cells:
        cells_by_symbol.setdefault(c["symbol"], []).append(c)

    syms = sorted(cells_by_symbol.keys())
    _log(f"scanning {len(syms)} symbols (session={sess_now}): {syms}")

    # Open contract count — bound concurrent trades
    open_pos = (snap.get("open_contracts_total") or 0) if snap else 0
    if open_pos > 0:
        _log(f"  {open_pos} open contracts; skipping new entries")
        return {"status": "in_position", **summary}

    # Daily trade cap
    today_count = todays_trade_count()
    if today_count >= MAX_TRADES_PER_DAY:
        _log(f"  daily trade cap hit ({today_count}/{MAX_TRADES_PER_DAY}); halt for today")
        return {"status": "daily_cap_hit", "today_count": today_count, **summary}

    for symbol in syms:
        # Cooldown check
        if recent_thesis_for(symbol):
            summary["skipped_cooldown"] += 1
            continue

        # Pull bars once per symbol
        bars = fetch_bars(client, symbol)
        if bars is None or len(bars) < 30:
            continue

        # Current vol+trend regime (+ news_proximity for this symbol)
        regime = current_regime(bars, symbol=symbol)

        # For each cell, check session+side match and try to fire
        fired_for_symbol = False
        for cell in cells_by_symbol[symbol]:
            if fired_for_symbol:
                break
            if cell.get("session") != sess_now:
                continue
            # Regime filter (2026-05-11): cells with `regime_filter` only fire
            # when current regime matches. No filter → cell always passes.
            ok_regime, regime_reason = cell_passes_regime_filter(cell, regime)
            if not ok_regime:
                summary.setdefault("skipped_regime", 0)
                summary["skipped_regime"] += 1
                continue
            strat_name = cell.get("strategy")
            strat_fn = getattr(strats, strat_name, None)
            if strat_fn is None:
                continue
            sig = find_latest_signal(bars, strat_fn, symbol=symbol)
            summary["scanned"] += 1
            if sig is None:
                continue
            if sig.get("stop") is None:
                continue
            # Side must match the cell
            sig_side = str(sig.get("side", "")).lower()
            if sig_side != cell.get("side"):
                continue
            ok, reason = signal_passes_min_r_gate(sig, symbol)
            if not ok:
                _log(f"  {symbol} {strat_name} {sig_side} signal rejected: {reason}")
                summary["blocked"] += 1
                continue
            ok, reason = signal_passes_max_risk_gate(sig, symbol, qty=1)
            if not ok:
                _log(f"  {symbol} {strat_name} {sig_side} signal rejected: {reason}")
                summary["blocked"] += 1
                continue
            # Defensive-ladder projection: would this trade's worst-case
            # loss push day P&L past the internal DLL lockdown? Block
            # pre-placement if so, rather than letting it fire and trip
            # dll_breached on the next scan.
            if snap:
                signal_risk = compute_signal_risk_usd(sig, symbol, qty=1)
                if signal_risk is not None:
                    breach, breach_why = projected_dll_breach(snap, signal_risk)
                    if breach:
                        _log(f"  {symbol} {strat_name} {sig_side} signal "
                              f"rejected: {breach_why}")
                        summary["blocked"] += 1
                        continue
            summary["triggers"] += 1
            # Place bracket — OR record shadow if halted/paper
            try:
                if shadow_only:
                    # Halted but shadow-mode active: record the trigger to the
                    # shadow_trades table so we can validate hypothetical
                    # performance during the halt window. Resolved later by
                    # scripts/shadow_trade_resolver.py.
                    try:
                        tick_v = _tick_size(symbol)
                        risk_usd = None
                        if sig.get("stop") is not None:
                            risk_ticks = abs(float(sig["price"]) - float(sig["stop"])) / tick_v
                            risk_usd = risk_ticks * (
                                {"GC": 10.0, "NG": 10.0, "ZN": 15.625, "ZB": 31.25,
                                 "ZT": 15.625, "ZF": 7.8125, "MNQ": 0.5, "MES": 1.25,
                                 "MCL": 1.0, "6E": 6.25, "6B": 6.25, "6C": 10.0
                                }.get(symbol, 1.0)
                            )
                        get_db().record_shadow_trade(
                            agent="live_trader",
                            symbol=symbol, strategy=strat_name, side=sig_side,
                            entry_price=float(sig["price"]),
                            stop_price=float(sig["stop"]),
                            target_price=float(sig.get("target") or sig["price"]),
                            shadow_reason="halt_active",
                            risk_usd=risk_usd,
                            notes=f"halt_reason={reason}",
                        )
                        _log(f"  SHADOW recorded: {symbol} {strat_name} {sig_side} "
                              f"@ {sig['price']} stop={sig['stop']} "
                              f"target={sig.get('target')} risk≈${risk_usd}")
                        summary["shadow"] += 1
                    except Exception as e:
                        _log(f"  shadow record failed: {e}")
                        summary["errors"] += 1
                elif paper:
                    _log(f"  PAPER: would place {symbol} {strat_name} {sig_side} "
                          f"@ {sig['price']} stop={sig['stop']} target={sig.get('target')}")
                    summary["placed"] += 1
                else:
                    result = place_bracket(client, account_id, symbol, sig, dry_run=dry_run)
                    if result.get("status") in ("submitted", "dry_run"):
                        summary["placed"] += 1
                    else:
                        summary["errors"] += 1
                fired_for_symbol = True
            except Exception as e:
                _log(f"  place_bracket exception: {e}")
                summary["errors"] += 1

    _log(f"  summary: {summary}")
    return summary


def _position_polling_loop(stop_event, dry_run: bool, paper: bool,
                            interval_sec: int = POSITION_POLL_SEC) -> None:
    """Background thread: poll open positions every interval_sec and
    force-close any that breach the per-trade loss cap or trailing-lock
    tiers via tools/profit_protect.check_and_close.

    This runs in PARALLEL with the main 5-min scan loop so the loss cap
    fires within ~30s of being exceeded instead of waiting for the next
    scan tick. Dry-run and paper modes skip the polling entirely (no
    broker writes).

    Safe to run alongside scan_once's own call to check_and_close — both
    paths are idempotent (broker market-IOC orders fire-and-forget; a
    second close on a flat position is a no-op).
    """
    if dry_run or paper:
        return
    from tools.profit_protect import check_and_close
    while not stop_event.is_set():
        try:
            client = get_client()
            account_id = get_account_id()
            check_and_close(client, account_id, log_fn=_log)
        except Exception as e:
            _log(f"position-poll error: {type(e).__name__}: {e}")
        stop_event.wait(interval_sec)


def main() -> int:
    p = argparse.ArgumentParser(prog="live_trader")
    p.add_argument("--once", action="store_true", help="single scan + exit")
    p.add_argument("--dry-run", action="store_true", help="signals + decisions, no orders")
    p.add_argument("--paper", action="store_true", help="paper-mode (no broker orders)")
    p.add_argument("--interval", type=int, default=SCAN_INTERVAL_SEC)
    args = p.parse_args()

    if os.environ.get("FUND_MODE", "live").lower() == "paper":
        args.paper = True

    if args.once:
        scan_once(dry_run=args.dry_run, paper=args.paper)
        return 0

    _log(f"=== live_trader started: interval={args.interval}s, "
          f"dry_run={args.dry_run}, paper={args.paper} ===")

    # Sub-minute position polling thread for the per-trade loss cap.
    import threading
    poll_stop = threading.Event()
    poll_thread = None
    if not args.dry_run and not args.paper:
        poll_thread = threading.Thread(
            target=_position_polling_loop,
            args=(poll_stop, args.dry_run, args.paper),
            kwargs={"interval_sec": POSITION_POLL_SEC},
            daemon=True,
            name="position-poller",
        )
        poll_thread.start()
        _log(f"position-poller started (interval={POSITION_POLL_SEC}s)")

    try:
        while True:
            try:
                scan_once(dry_run=args.dry_run, paper=args.paper)
            except KeyboardInterrupt:
                _log("interrupted; exiting")
                return 0
            except Exception as e:
                _log(f"scan error (will retry): {type(e).__name__}: {e}")
            time.sleep(args.interval)
    finally:
        poll_stop.set()
        if poll_thread is not None:
            poll_thread.join(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
