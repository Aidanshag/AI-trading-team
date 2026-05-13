"""Brain logic — strategy/session/regime decisions.

The trader (`scripts/live_trader.py`) is the execution layer; the brain
is everything else. This module hosts the pure decision functions:
  - Which cells are live (allowlist)
  - What session we're in (Asian/London/RTH/PostClose)
  - Current regime (vol + trend + news proximity)
  - Strategy execution + signal extraction
  - Cell-vs-regime matching

Extracted from `scripts/live_trader.py` 2026-05-13 as part of the
brain/trader split. The trader now consumes pre-computed signals from
`tools/signal_queue` rather than running strategies itself.

Pure functions only — no broker IO, no DB writes, no orchestration.
Anything stateful belongs in `scripts/brain_signaler.py`.
"""
from __future__ import annotations

import inspect
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
LIVE_ALLOWLIST_PATH = _PROJECT_ROOT / "state" / "strategy_validation.json"

LOOKBACK_BARS = 6   # find_latest_signal cutoff (30 min on 5m bars)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def load_live_cells() -> list[dict]:
    """Read the brain's validated allowlist from
    state/strategy_validation.json:live_allowlist."""
    if not LIVE_ALLOWLIST_PATH.exists():
        return []
    try:
        st = json.loads(LIVE_ALLOWLIST_PATH.read_text(encoding="utf-8"))
        return st.get("live_allowlist") or []
    except Exception:
        return []


def session_now_utc(now_utc: datetime) -> str:
    """Map UTC to ET session bucket.
      RTH       09:30-16:00 ET
      London    04:00-09:30 ET
      PostClose 16:00-20:00 ET
      Asian     20:00-04:00 ET
    """
    et_hour = (now_utc.hour - 4 + now_utc.minute / 60.0) % 24
    if 9.5 <= et_hour < 16:    return "RTH"
    if 4 <= et_hour < 9.5:     return "London"
    if 16 <= et_hour < 20:     return "PostClose"
    return "Asian"


def _load_calendar_events(symbol: str) -> list[dict]:
    """Load HIGH/MEDIUM economic events affecting `symbol` from
    vault/economic_calendar/*.json. Returns [{'ts': datetime, 'severity': str}].
    Never raises; returns [] on any error or missing files."""
    cal_dir = _PROJECT_ROOT / "vault" / "economic_calendar"
    if not cal_dir.exists():
        return []
    out: list[dict] = []
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
                        dt = dt.replace(tzinfo=timezone(timedelta(hours=-4)))
                except Exception:
                    continue
                severity = "HIGH" if symbol in primary else "MEDIUM"
                out.append({"ts": dt, "severity": severity})
        except Exception:
            pass
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
    ±60 min of MEDIUM), or 'clear' (otherwise)."""
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
    """Compute the current vol+trend regime of the latest bar."""
    if len(bars) < max(vol_ref_window, trend_ref_window) + vol_lookback:
        return {}
    try:
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
    Cells with no `regime_filter` always pass. Fail-closed when regime
    is unknown (don't fire restricted cells without context)."""
    cell_filter = cell.get("regime_filter")
    if not cell_filter:
        return True, ""
    if not regime:
        return False, "regime unknown"
    for key, allowed in cell_filter.items():
        if regime.get(key) not in allowed:
            return False, f"{key}={regime.get(key)} not in {allowed}"
    return True, ""


def find_latest_signal(bars: pd.DataFrame, strategy_fn,
                        symbol: str | None = None,
                        lookback_bars: int = LOOKBACK_BARS,
                        tick_size_lookup=None) -> dict | None:
    """Run strategy on bars, return the most recent entry signal in the
    last `lookback_bars` bars. Returns None if no fresh signal.

    `tick_size_lookup` is a callable(symbol) -> tick_size, used to inject
    `tick_size` into strategies that accept it (activates the
    floor-the-stop logic in gap_fill etc.). Caller passes
    tools.trader_utils._tick_size.
    """
    if len(bars) < 30:
        return None
    cutoff_idx = max(0, len(bars) - lookback_bars)
    cutoff = bars.index[cutoff_idx]
    call = strategy_fn
    if symbol is not None and tick_size_lookup is not None:
        try:
            sig_params = inspect.signature(strategy_fn).parameters
            if "tick_size" in sig_params:
                tick = tick_size_lookup(symbol)
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
