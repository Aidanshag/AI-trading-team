"""Brain signaler — emits trade signals to the queue.

The brain side of the brain/trader split. Runs continuously, every
SCAN_INTERVAL_SEC:
  1. Reads the live_allowlist (which cells are tradeable)
  2. Filters cells by current session (Asian/London/RTH/PostClose)
  3. Fetches bars per symbol
  4. Computes regime; filters cells whose regime_filter doesn't match
  5. Runs each cell's strategy on the bars
  6. Emits matching entry signals to `state/pending_signals.json` via
     `tools.signal_queue.enqueue`

The trader (`scripts/live_trader.py`) is a SEPARATE process that reads
from the same queue, applies last-mile safety gates, and places orders.

Why a separate process:
  - Brain can be restarted/iterated without disturbing live execution.
  - Multi-account scaling: 1 brain → N trader processes, each reading
    the same queue (per copy-trading roadmap).
  - Crash isolation: brain Python error doesn't kill the trader.

Usage:
  python -m scripts.brain_signaler              # continuous loop
  python -m scripts.brain_signaler --once       # single scan + exit
  python -m scripts.brain_signaler --dry-run    # signals computed, not enqueued

Environment:
  PROJECTX_*       broker credentials (for fetch_bars)
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

_HERE = Path(__file__).resolve().parent.parent
os.chdir(_HERE)
sys.path.insert(0, str(_HERE))

from tools.backtest import strategies as strats  # noqa: E402
from tools.projectx_client import get_client, get_account_id  # noqa: E402
from tools.bar_fetcher import fetch_bars as _fetch_bars_impl  # noqa: E402
from tools.trader_utils import _tick_size  # noqa: E402
from tools.signal_queue import enqueue, make_signal  # noqa: E402
from tools.brain_logic import (  # noqa: E402
    load_live_cells,
    session_now_utc,
    current_regime,
    cell_passes_regime_filter,
    find_latest_signal,
)


# Scan cadence: faster than the trader's 5-min loop because the brain
# is what decides "now's the time". Trader will consume whatever is in
# the queue when it scans.
SCAN_INTERVAL_SEC = 60
SIGNAL_TTL_SEC = 180  # signals expire if trader doesn't pick them up in 3 min


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts} UTC] {msg}", flush=True)


def _fetch_bars(client, symbol: str, minutes: int = 5, lookback: int = 200):
    return _fetch_bars_impl(client, symbol, minutes, lookback, log_fn=_log)


def scan_once(*, dry_run: bool = False) -> dict:
    """One brain pass: read cells, filter by session+regime, run
    strategies, emit signals. Returns summary stats."""
    summary = {
        "cells": 0, "session_skipped": 0, "regime_skipped": 0,
        "scanned": 0, "signals_emitted": 0, "errors": 0,
    }
    cells = load_live_cells()
    if not cells:
        _log("brain: no live cells configured; nothing to scan")
        return summary

    session = session_now_utc(datetime.now(timezone.utc))
    _log(f"brain: session={session}, cells_total={len(cells)}")

    client = get_client()
    # Bar cache: fetch once per symbol per scan (multiple cells per symbol)
    bar_cache: dict[str, pd.DataFrame] = {}
    regime_cache: dict[str, dict] = {}

    for cell in cells:
        summary["cells"] += 1
        cell_session = cell.get("session", "")
        if cell_session != session:
            summary["session_skipped"] += 1
            continue

        symbol = cell.get("symbol", "")
        strat_name = cell.get("strategy", "")
        side = cell.get("side", "")
        if not (symbol and strat_name and side):
            continue

        if symbol not in bar_cache:
            try:
                bars = _fetch_bars(client, symbol, minutes=5, lookback=200)
                if bars is not None and len(bars) >= 30:
                    bar_cache[symbol] = bars
                else:
                    bar_cache[symbol] = None
            except Exception as e:
                _log(f"brain: fetch_bars failed for {symbol}: "
                      f"{type(e).__name__}: {e}")
                summary["errors"] += 1
                bar_cache[symbol] = None
        bars = bar_cache.get(symbol)
        if bars is None:
            continue

        if symbol not in regime_cache:
            regime_cache[symbol] = current_regime(bars, symbol=symbol)
        regime = regime_cache[symbol]

        ok, reason = cell_passes_regime_filter(cell, regime)
        if not ok:
            summary["regime_skipped"] += 1
            continue

        strat_fn = getattr(strats, strat_name, None)
        if strat_fn is None:
            continue

        summary["scanned"] += 1
        sig = find_latest_signal(bars, strat_fn, symbol=symbol,
                                  tick_size_lookup=_tick_size)
        if sig is None:
            continue
        if sig.get("stop") is None:
            continue
        if str(sig.get("side", "")).lower() != side:
            continue

        cell_key = (f"{strat_name}|{symbol}|{cell.get('session')}|"
                     f"{cell.get('side')}")
        notes = f"reason={sig.get('reason', '')}"
        if cell.get("experimental"):
            notes = f"experimental; {notes}"

        signal = make_signal(
            symbol=symbol,
            side=str(sig["side"]).lower(),
            entry_price=float(sig["price"]),
            stop_price=float(sig["stop"]),
            target_price=(float(sig["target"])
                            if sig.get("target") is not None else None),
            strategy=strat_name,
            session=cell.get("session", session),
            cell_key=cell_key,
            qty=1,
            shadow_only=bool(cell.get("experimental")),
            notes=notes,
            ttl_sec=SIGNAL_TTL_SEC,
        )

        if dry_run:
            _log(f"brain: DRY would-emit {cell_key} @ {sig['price']} "
                  f"stop={sig['stop']} target={sig.get('target')}")
        else:
            try:
                enqueue(signal)
                _log(f"brain: emitted {cell_key} @ {sig['price']} "
                      f"stop={sig['stop']} target={sig.get('target')} "
                      f"id={signal['id'][:8]}")
                summary["signals_emitted"] += 1
            except Exception as e:
                _log(f"brain: enqueue failed for {cell_key}: "
                      f"{type(e).__name__}: {e}")
                summary["errors"] += 1

    _log(f"brain: summary {summary}")
    return summary


def main() -> int:
    p = argparse.ArgumentParser(prog="brain_signaler")
    p.add_argument("--once", action="store_true", help="single scan + exit")
    p.add_argument("--dry-run", action="store_true",
                   help="compute signals but don't enqueue")
    p.add_argument("--interval", type=int, default=SCAN_INTERVAL_SEC)
    args = p.parse_args()

    if args.once:
        scan_once(dry_run=args.dry_run)
        return 0

    _log(f"=== brain_signaler started: interval={args.interval}s, "
          f"dry_run={args.dry_run} ===")
    while True:
        try:
            scan_once(dry_run=args.dry_run)
        except KeyboardInterrupt:
            _log("interrupted; exiting")
            return 0
        except Exception as e:
            _log(f"brain scan error (will retry): "
                  f"{type(e).__name__}: {e}")
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
