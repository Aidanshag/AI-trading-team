"""Resolve unresolved shadow trades by replaying their entry/stop/target
against subsequent market bars.

Each shadow row in `state.shadow_trades` represents a triggered signal that
the live trader rejected (default-deny gate, focus restriction, etc.). To
keep accumulating evidence on the unvalidated cell, we resolve the shadow's
outcome AS IF the trade had been placed:

  - Entry counts as filled at `entry_price` once a bar tags it (price
    crosses entry within X minutes of signal).
  - From there, walk subsequent bars until either stop_price or target_price
    is touched. Whichever happens first determines outcome:
      stop hit  → outcome="loss",  pnl_r = -1.0
      target hit → outcome="win",   pnl_r = +rr_planned
      timeout (>4h, no resolution) → outcome="expired", pnl_r = 0
  - Update the row via db.resolve_shadow_trade.

Run via:
  python scripts/shadow_trade_resolver.py
Or wire into preflight.py / nightly cron alongside daily_strategy_validation.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from state.db import get_db  # noqa: E402


# Symbol → yfinance ticker for outcome resolution
SYMBOL_TO_YF = {
    "GC":  "GC=F",  "MCL": "CL=F", "NG":  "NG=F",
    "MNQ": "NQ=F",  "MES": "ES=F",
    "ZN":  "ZN=F",  "ZB":  "ZB=F", "ZT":  "ZT=F", "ZF": "ZF=F",
    "6E":  "6E=F",  "6B":  "6B=F", "6J":  "6J=F", "6A": "6A=F", "6C": "6C=F",
}

# Resolution config
ENTRY_FILL_WINDOW_MIN = 15      # bars within this window can fill the entry
RESOLUTION_TIMEOUT_HOURS = 4    # if neither stop nor target hits in this window, expire
SHADOW_MIN_AGE_MINUTES = 30     # don't resolve shadows newer than this — too soon


def fetch_5m_bars_for_window(ticker: str, start_utc: datetime,
                              end_utc: datetime):
    """Pull 5-minute bars covering [start_utc, end_utc] for a ticker."""
    period_days = max(2, (end_utc - start_utc).days + 2)
    df = yf.download(ticker, period=f"{period_days}d", interval="5m",
                     progress=False, auto_adjust=False)
    if df.empty:
        return None
    if hasattr(df.columns, "get_level_values"):
        df.columns = df.columns.get_level_values(0)
    keep = [c for c in ["Open", "High", "Low", "Close"] if c in df.columns]
    df = df[keep].copy().dropna()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert("UTC")
    # Filter to the window we care about
    return df[(df.index >= start_utc - timedelta(minutes=15))
              & (df.index <= end_utc + timedelta(minutes=15))]


def resolve_one(shadow: dict, bars) -> tuple[str, float, str]:
    """Return (outcome, pnl_r, notes) given bars for the symbol."""
    side = (shadow.get("side") or "").lower()
    entry = float(shadow.get("entry_price") or 0)
    stop = float(shadow.get("stop_price") or 0)
    target = float(shadow.get("target_price") or 0)
    if entry <= 0 or stop <= 0 or side not in ("long", "short"):
        return "skipped", 0.0, "missing entry/stop/side"

    rr = (abs(target - entry) / max(abs(entry - stop), 0.0001)) if target else 0.0

    sig_ts = pd.Timestamp(shadow["ts_signal"]).tz_convert("UTC") \
        if pd.Timestamp(shadow["ts_signal"]).tz else \
        pd.Timestamp(shadow["ts_signal"]).tz_localize("UTC")
    fill_window_end = sig_ts + pd.Timedelta(minutes=ENTRY_FILL_WINDOW_MIN)
    timeout = sig_ts + pd.Timedelta(hours=RESOLUTION_TIMEOUT_HOURS)

    # Filter bars after signal
    after = bars[bars.index >= sig_ts]
    if after.empty:
        return "skipped", 0.0, "no bars after signal"

    # 1. Did entry fill within the window?
    fill_bars = after[after.index <= fill_window_end]
    filled = False
    for ts, row in fill_bars.iterrows():
        hi, lo = float(row["High"]), float(row["Low"])
        # Entry crosses if price tags it
        if lo <= entry <= hi:
            filled = True
            after = after[after.index >= ts]
            break
    if not filled:
        return "no_fill", 0.0, "entry not tagged within window"

    # 2. From entry onwards, walk to first stop or target
    for ts, row in after.iterrows():
        if ts > timeout:
            return "expired", 0.0, "no stop/target in 4h"
        hi, lo = float(row["High"]), float(row["Low"])
        if side == "long":
            stop_hit = lo <= stop
            target_hit = (target > 0) and hi >= target
        else:
            stop_hit = hi >= stop
            target_hit = (target > 0) and lo <= target
        # If both hit on same bar, conservative: assume stop hit first
        if stop_hit:
            return "loss", -1.0, f"stop hit at {ts.isoformat()}"
        if target_hit:
            return "win", float(rr), f"target hit at {ts.isoformat()}"
    return "expired", 0.0, "ran out of bars before resolution"


def main() -> int:
    db = get_db()
    print("=== SHADOW TRADE RESOLVER ===\n")

    pending = db.unresolved_shadow_trades(age_min_minutes=SHADOW_MIN_AGE_MINUTES)
    print(f"Pending unresolved shadows: {len(pending)}")
    if not pending:
        return 0

    # Group by symbol so we fetch bars once per symbol
    by_symbol: dict[str, list[dict]] = {}
    for s in pending:
        sym = s.get("symbol") or ""
        by_symbol.setdefault(sym, []).append(s)

    counts = {"win": 0, "loss": 0, "expired": 0, "no_fill": 0, "skipped": 0}
    for sym, shadows in by_symbol.items():
        ticker = SYMBOL_TO_YF.get(sym)
        if not ticker:
            for s in shadows:
                counts["skipped"] += 1
            continue

        # Time window for bar fetch
        start = min(pd.Timestamp(s["ts_signal"]) for s in shadows)
        end = max(pd.Timestamp(s["ts_signal"]) for s in shadows) + pd.Timedelta(hours=5)
        if start.tz is None: start = start.tz_localize("UTC")
        if end.tz is None: end = end.tz_localize("UTC")
        bars = fetch_5m_bars_for_window(ticker, start.to_pydatetime(),
                                         end.to_pydatetime())
        if bars is None or bars.empty:
            for s in shadows:
                counts["skipped"] += 1
            continue

        for s in shadows:
            outcome, pnl_r, note = resolve_one(s, bars)
            counts[outcome] = counts.get(outcome, 0) + 1
            try:
                if outcome in ("win", "loss", "expired", "no_fill"):
                    db.resolve_shadow_trade(
                        shadow_id=s["id"], outcome=outcome,
                        pnl_r=pnl_r, notes=note[:160],
                    )
            except Exception as e:
                print(f"  resolve_shadow_trade failed for id={s['id']}: {e}")

    print("Resolved:")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
