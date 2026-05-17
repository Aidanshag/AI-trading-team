"""ib_historical_backfill — pull historical bars from IB Gateway and stage
them under vault/ib/data/ for multi-regime backtest research.

Phase 2 priority (per vault/_meta/weekly_calendar.md, originally 2026-05-23,
moved forward when IB connectivity confirmed 2026-05-17).

Target universe (broad ETFs + sector SPDRs + a few high-volume single names):
  Broad: SPY, QQQ, IWM, DIA
  Sector SPDRs: XLK, XLF, XLE, XLV, XLY, XLP, XLI, XLU, XLB, XLRE
  Mega caps: AAPL, MSFT, GOOG, NVDA, AMZN
  Vol product: VXX

For each symbol pull:
  - 1 day bars, 15 years (multi-regime: 2010-now spans 2018, 2020, 2022 stress)
  - 1 hour bars, 2 years
  - 15 min bars, 30 days (recent intraday for hi-res testing)

Output: vault/ib/data/<symbol>/<bar_size>/<YYYY>.csv
Index:  vault/ib/data/index.md (manifest of what's been pulled and when)

This is read-only data work. It does NOT touch the trader, risk gates, or
allowlist. Failure during a pull skips that symbol and continues.
"""
from __future__ import annotations

import csv
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "vault" / "ib" / "data"
INDEX_PATH = DATA_DIR / "index.md"
LOG_PATH = ROOT / "vault" / "ib" / "data" / "backfill_log.txt"

UNIVERSE = {
    # broad market
    "SPY": "Stock", "QQQ": "Stock", "IWM": "Stock", "DIA": "Stock",
    # sector SPDRs
    "XLK": "Stock", "XLF": "Stock", "XLE": "Stock", "XLV": "Stock",
    "XLY": "Stock", "XLP": "Stock", "XLI": "Stock", "XLU": "Stock",
    "XLB": "Stock", "XLRE": "Stock",
    # mega caps
    "AAPL": "Stock", "MSFT": "Stock", "GOOG": "Stock",
    "NVDA": "Stock", "AMZN": "Stock",
    # vol product
    "VXX": "Stock",
}

PULL_PLAN = [
    # (duration, bar_size, subdir)
    ("15 Y", "1 day",  "1d"),
    ("2 Y",  "1 hour", "1h"),
    ("30 D", "15 mins", "15min"),
]


def log(msg: str) -> None:
    line = f"[{datetime.now(tz=timezone.utc).isoformat()}] {msg}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def pull_one(client, symbol: str, sec_type: str, duration: str,
             bar_size: str, subdir: str) -> int:
    """Pull a single symbol/bar_size combination. Returns bar count."""
    out_dir = DATA_DIR / symbol / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    # Pull bars
    bars = client.get_historical_bars(
        symbol=symbol, sec_type=sec_type, exchange="SMART",
        currency="USD", duration=duration, bar_size=bar_size,
        what_to_show="TRADES", use_rth=True,
    )
    if not bars:
        log(f"  {symbol} {bar_size}: NO DATA")
        return 0
    # Bucket by year and write CSV files
    buckets: dict[str, list[dict]] = {}
    for b in bars:
        ts = b.get("t", "")
        year = ts[:4] if ts else "unknown"
        buckets.setdefault(year, []).append(b)
    for year, rows in buckets.items():
        out_file = out_dir / f"{year}.csv"
        with out_file.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["t", "o", "h", "l", "c", "v"])
            w.writeheader()
            for r in rows:
                w.writerow(r)
    log(f"  {symbol} {bar_size}: {len(bars)} bars -> {len(buckets)} years")
    return len(bars)


def main() -> int:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    log("=== IB historical backfill — start ===")
    try:
        from tools.ib_client import IBClient
    except ImportError as e:
        log(f"ABORT: cannot import IBClient: {e}")
        return 2

    client = IBClient()
    try:
        log(f"Connecting to IB Gateway {client.host}:{client.port} (clientId={client.client_id})")
        client.connect()
    except Exception as e:
        log(f"ABORT: IB connect failed: {type(e).__name__}: {e}")
        return 2

    log(f"Connected. Account(s): {client.get_accounts()}")

    summary: dict[str, dict[str, int]] = {}
    total_pulls = len(UNIVERSE) * len(PULL_PLAN)
    pull_n = 0
    for symbol, sec_type in UNIVERSE.items():
        summary[symbol] = {}
        for duration, bar_size, subdir in PULL_PLAN:
            pull_n += 1
            log(f"[{pull_n}/{total_pulls}] {symbol} {bar_size} ({duration})")
            try:
                n = pull_one(client, symbol, sec_type, duration, bar_size, subdir)
                summary[symbol][bar_size] = n
            except Exception as e:
                log(f"  ERROR {symbol} {bar_size}: {type(e).__name__}: {e}")
                summary[symbol][bar_size] = -1
            # IB has pacing limits — be polite
            time.sleep(2)

    client.disconnect()
    log("=== IB historical backfill — done ===")

    # Write index manifest
    lines = [
        "---",
        "type: manifest",
        f"updated: {datetime.now(tz=timezone.utc).isoformat()}",
        "---",
        "",
        "# IB historical data — manifest",
        "",
        "Generated by `scripts/ib_historical_backfill.py`. One row per (symbol, bar_size).",
        "Bar counts are post-fetch. `-1` = error during pull (see backfill_log.txt).",
        "",
        "| Symbol | 1d | 1h | 15min |",
        "|---|---|---|---|",
    ]
    for sym, counts in sorted(summary.items()):
        d = counts.get("1 day", 0)
        h = counts.get("1 hour", 0)
        m15 = counts.get("15 mins", 0)
        lines.append(f"| {sym} | {d} | {h} | {m15} |")

    INDEX_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"Manifest written: {INDEX_PATH}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("INTERRUPTED")
        sys.exit(130)
    except Exception as e:
        log(f"FATAL: {type(e).__name__}: {e}\n{traceback.format_exc()}")
        sys.exit(1)
