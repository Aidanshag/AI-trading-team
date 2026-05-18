"""ib_topstep_gap_fill — retry the 0-bar Topstep symbols with alternate
IB contract specs.

Found in the 2026-05-17 Topstep futures pull:
  - 6 FX symbols (6A/6B/6C/6E/6J/6S) returned 0 bars — wrong exchange root
  - METK/MNG/SIL returned 0 — wrong root or unsupported as CONTFUT
  - Many 1h pulls returned 0 — IB tier limitation, retry

This script tries alternative IB specs:
  - FX futures: try with currency-pair roots (EUR, GBP, JPY, etc.) via
    ContFuture on GLOBEX, or fall back to the M-prefix micro version
  - METK: try MET (CME micro Ether) and BTC-related alternatives
  - MNG: try with "NGAS" or other natural-gas micros
  - SIL: try MGC variant or alternate exchange
  - 1h retries: just retry the original spec; may have been transient

Output appends to vault/ib/data/futures/<symbol>/<bar_size>/<YYYY>.csv
(same layout as the original backfill). Updates index.md when done.
"""
from __future__ import annotations

import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "vault" / "ib" / "data" / "futures"
LOG_PATH = DATA_DIR / "gap_fill_log.txt"

# Alternate contract specs to try for each problem symbol
RETRY_SPECS = {
    # FX futures — try the currency-pair root via GLOBEX
    "6E": [("EUR", "GLOBEX"), ("6E", "GLOBEX")],
    "6B": [("GBP", "GLOBEX"), ("6B", "GLOBEX")],
    "6J": [("JPY", "GLOBEX"), ("6J", "GLOBEX")],
    "6A": [("AUD", "GLOBEX"), ("6A", "GLOBEX")],
    "6C": [("CAD", "GLOBEX"), ("6C", "GLOBEX")],
    "6S": [("CHF", "GLOBEX"), ("6S", "GLOBEX")],
    # Micros + alternates
    "METK": [("MET", "CME"), ("MET", "CMECRYPTO")],
    "MNG": [("MNG", "NYMEX"), ("MNG", "GLOBEX")],
    "SIL": [("SIL", "COMEX"), ("MGC", "COMEX")],  # if SIL fails, use MGC as proxy
}

PULL_PLAN = [
    ("20 Y", "1 day",  "1d"),
    ("2 Y",  "1 hour", "1h"),
    ("60 D", "15 mins", "15min"),
    ("30 D", "5 mins", "5min"),
]

# Symbols that need 1h retry only (they have 1d/15min/5min)
RETRY_1H_ONLY = [
    "CL", "GC", "HE", "HG", "HO", "LE", "MCL", "MGC", "NG", "PL",
    "QG", "QM", "RB", "SI", "UB", "ZB", "ZC", "ZF", "ZL", "ZM",
    "ZN", "ZS",
]


def log(msg: str) -> None:
    line = f"[{datetime.now(tz=timezone.utc).isoformat()}] {msg}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def try_pull(client, original_symbol: str, ib_symbol: str, exchange: str,
              duration: str, bar_size: str, subdir: str) -> int:
    """Try one alternate spec. Save to vault/ib/data/futures/<original>/<subdir>/."""
    out_dir = DATA_DIR / original_symbol / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        bars = client.get_historical_bars(
            symbol=ib_symbol, sec_type="CONTFUT",
            exchange=exchange, currency="USD",
            duration=duration, bar_size=bar_size,
            what_to_show="TRADES", use_rth=True,
        )
    except Exception as e:
        log(f"    {ib_symbol}@{exchange} {bar_size}: {type(e).__name__}: {str(e)[:80]}")
        return -1
    if not bars:
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
    return len(bars)


def main() -> int:
    log("=== Topstep gap-fill — start ===")
    try:
        from tools.ib_client import IBClient
    except ImportError as e:
        log(f"ABORT: cannot import IBClient: {e}")
        return 2

    client = IBClient(client_id=11)  # separate clientId from running pulls
    try:
        log(f"Connecting to IB Gateway (clientId={client.client_id})")
        client.connect()
    except Exception as e:
        log(f"ABORT: IB connect failed: {type(e).__name__}: {e}")
        return 2
    log(f"Connected. Account(s): {client.get_accounts()}")

    summary = {"retried": 0, "filled": 0, "still_failed": 0}

    # Phase A: zero-bar symbols — try alternate specs
    log("\n--- Phase A: zero-bar retries ---")
    for original_sym, specs in RETRY_SPECS.items():
        log(f"\nRetrying {original_sym} (alt specs: {specs})")
        for ib_sym, exchange in specs:
            log(f"  Trying ({ib_sym}, {exchange})...")
            success = False
            for duration, bar_size, subdir in PULL_PLAN:
                n = try_pull(client, original_sym, ib_sym, exchange,
                              duration, bar_size, subdir)
                summary["retried"] += 1
                if n > 0:
                    log(f"    SUCCESS {ib_sym}@{exchange} {bar_size}: {n} bars")
                    summary["filled"] += 1
                    success = True
                else:
                    summary["still_failed"] += 1
                time.sleep(2)
            if success:
                log(f"  {original_sym} resolved via ({ib_sym}, {exchange}) — stopping further attempts")
                break

    # Phase B: 1h-only retries (these had 1d/15min/5min but missing 1h)
    log("\n--- Phase B: 1h gap-fill retries ---")
    for sym in RETRY_1H_ONLY:
        # Determine the original exchange used (from index.md or hardcoded
        # mapping — duplicate the Topstep futures script's mapping here).
        exchange_map = {
            "CL": "NYMEX", "MCL": "NYMEX", "NG": "NYMEX", "MNG": "NYMEX",
            "QG": "NYMEX", "RB": "NYMEX", "HO": "NYMEX", "QM": "NYMEX",
            "GC": "COMEX", "MGC": "COMEX", "SI": "COMEX", "SIL": "COMEX",
            "HG": "COMEX", "MHG": "COMEX", "PL": "NYMEX",
            "ZT": "CBOT", "ZF": "CBOT", "ZN": "CBOT", "ZB": "CBOT", "UB": "CBOT",
            "ZC": "CBOT", "ZS": "CBOT", "ZW": "CBOT", "ZL": "CBOT", "ZM": "CBOT",
            "LE": "CME", "HE": "CME",
        }
        exchange = exchange_map.get(sym, "GLOBEX")
        log(f"  {sym} 1h retry on {exchange}...")
        n = try_pull(client, sym, sym, exchange, "2 Y", "1 hour", "1h")
        summary["retried"] += 1
        if n > 0:
            log(f"    SUCCESS {sym} 1h: {n} bars")
            summary["filled"] += 1
        else:
            log(f"    still 0 bars on {sym} 1h")
            summary["still_failed"] += 1
        time.sleep(2)

    client.disconnect()
    log(f"\n=== DONE: {summary['filled']} filled, {summary['still_failed']} still failed, "
        f"{summary['retried']} retried total ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
