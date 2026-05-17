"""ib_topstep_futures_backfill — pull HISTORICAL bars for Topstep-tradeable
CME futures from IB Gateway. This is the multi-regime bridge between the
two workstreams: IB has 10+ years of continuous-future history on the
same products Topstep trades, so we can validate Topstep strategies
across 2010-now (covering 2018 vol spike, 2020 COVID, 2022 tightening).

Output: vault/ib/data/futures/<SYMBOL>/<bar_size>/<YYYY>.csv
Index:  vault/ib/data/futures/index.md

Reconnect-on-disconnect logic added — IB Gateway often closes idle
sessions; we retry up to 3 times per pull with backoff.

The Topstep futures we want longer history on:
  Equity index: ES (S&P 500 e-mini), NQ (Nasdaq e-mini), RTY (Russell)
                MES/MNQ (micros — IB doesn't always have full history)
  Energy:       CL (WTI crude), NG (natural gas)
  Metals:       GC (gold), SI (silver), HG (copper)
  Treasuries:   ZN (10Y), ZB (30Y), ZF (5Y)
  FX:           6E, 6B, 6J, 6C (euro, sterling, yen, loonie)
  Grains:       ZC (corn), ZS (soy), ZW (wheat)
"""
from __future__ import annotations

import csv
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "vault" / "ib" / "data" / "futures"
INDEX_PATH = DATA_DIR / "index.md"
LOG_PATH = DATA_DIR / "backfill_log.txt"

# Topstep-tradeable CME futures (continuous-future series via IB CONTFUT)
# Source of truth: config/symbols.yaml (verified by Topstep 2026-04-28).
# Exchange hints help IB qualify the contract.
FUTURES_UNIVERSE = {
    # ── Equity index ──
    "ES": "CME",   "MES": "CME",
    "NQ": "CME",   "MNQ": "CME",
    "RTY": "CME",  "M2K": "CME",
    "YM": "CBOT",  "MYM": "CBOT",
    "NKD": "CME",
    # ── Energies ──
    "CL": "NYMEX", "MCL": "NYMEX",
    "NG": "NYMEX", "MNG": "NYMEX", "QG": "NYMEX",
    "RB": "NYMEX", "HO": "NYMEX", "QM": "NYMEX",
    # ── Metals ──
    "GC": "COMEX", "MGC": "COMEX",
    "SI": "COMEX", "SIL": "COMEX",
    "HG": "COMEX", "MHG": "COMEX",
    "PL": "NYMEX",
    # ── Rates ──
    "ZT": "CBOT", "ZF": "CBOT", "ZN": "CBOT",
    "ZB": "CBOT", "UB": "CBOT",
    # ── FX ──
    "6E": "CME", "6B": "CME", "6J": "CME",
    "6A": "CME", "6C": "CME", "6S": "CME",
    "M6E": "CME", "M6B": "CME", "E7": "CME",
    # ── Grains / Ag ──
    "ZC": "CBOT", "ZS": "CBOT", "ZW": "CBOT",
    "ZL": "CBOT", "ZM": "CBOT",
    # ── Livestock ──
    "LE": "CME", "HE": "CME",
    # ── Crypto ──
    "METK": "CME",
}

PULL_PLAN = [
    # Daily bars: maximum history IB allows on most futures
    ("20 Y", "1 day",  "1d"),
    # 1-hour bars: 2 years (~5,000 bars)
    ("2 Y",  "1 hour", "1h"),
    # 15-min bars: 60 days (recent intraday for hi-res testing)
    ("60 D", "15 mins", "15min"),
    # 5-min bars: 30 days (the cadence the trader actually fires on)
    ("30 D", "5 mins", "5min"),
]

MAX_RETRY_PER_PULL = 3


def log(msg: str) -> None:
    line = f"[{datetime.now(tz=timezone.utc).isoformat()}] {msg}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def ensure_connected(client, log_fn=log) -> bool:
    """Try to reconnect if the client lost its session."""
    if client.is_connected():
        return True
    log_fn("  reconnecting...")
    try:
        client.connect()
        return client.is_connected()
    except Exception as e:
        log_fn(f"  reconnect failed: {type(e).__name__}: {e}")
        return False


def pull_one(client, symbol: str, exchange: str, duration: str,
             bar_size: str, subdir: str) -> int:
    """Pull a single (symbol, bar_size) with retry. Returns bar count."""
    out_dir = DATA_DIR / symbol / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    last_err = None
    for attempt in range(1, MAX_RETRY_PER_PULL + 1):
        if not ensure_connected(client):
            time.sleep(3 * attempt)
            continue
        try:
            bars = client.get_historical_bars(
                symbol=symbol, sec_type="CONTFUT",
                exchange=exchange, currency="USD",
                duration=duration, bar_size=bar_size,
                what_to_show="TRADES", use_rth=True,
            )
            if not bars:
                log(f"  {symbol} {bar_size}: NO DATA")
                return 0
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
        except Exception as e:
            last_err = e
            log(f"  {symbol} {bar_size} attempt {attempt}: {type(e).__name__}: {e}")
            time.sleep(3 * attempt)
    log(f"  {symbol} {bar_size}: FAILED after {MAX_RETRY_PER_PULL} attempts ({last_err})")
    return -1


def main() -> int:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    log("=== IB Topstep-futures backfill — start ===")
    try:
        from tools.ib_client import IBClient
    except ImportError as e:
        log(f"ABORT: cannot import IBClient: {e}")
        return 2

    # Use clientId=9 so we run in parallel with the comprehensive
    # pull_everything (clientId=7) without collision.
    client = IBClient(client_id=9)
    try:
        log(f"Connecting to IB Gateway {client.host}:{client.port} (clientId={client.client_id})")
        client.connect()
    except Exception as e:
        log(f"ABORT: IB connect failed: {type(e).__name__}: {e}")
        return 2

    log(f"Connected. Account(s): {client.get_accounts()}")

    summary: dict[str, dict[str, int]] = {}
    total_pulls = len(FUTURES_UNIVERSE) * len(PULL_PLAN)
    pull_n = 0
    for symbol, exchange in FUTURES_UNIVERSE.items():
        summary[symbol] = {}
        for duration, bar_size, subdir in PULL_PLAN:
            pull_n += 1
            log(f"[{pull_n}/{total_pulls}] {symbol} ({exchange}) {bar_size} ({duration})")
            n = pull_one(client, symbol, exchange, duration, bar_size, subdir)
            summary[symbol][bar_size] = n
            time.sleep(2)

    client.disconnect()
    log("=== IB Topstep-futures backfill — done ===")

    lines = [
        "---",
        "type: manifest",
        f"updated: {datetime.now(tz=timezone.utc).isoformat()}",
        "---",
        "",
        "# IB Topstep-futures historical data — manifest",
        "",
        "Generated by `scripts/ib_topstep_futures_backfill.py`. CONTFUT bars",
        "(continuous-future back-adjusted series). Bar counts are post-fetch.",
        "`-1` = error during pull. See backfill_log.txt.",
        "",
        "These are the SAME products Topstep trades — but with 10+ years",
        "of history for multi-regime walk-forward analysis.",
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
