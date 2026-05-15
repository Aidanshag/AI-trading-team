"""Pull 6-12 months of 1-min RTH bars for the focus universe and cache
as parquet. Phase 0 of the RTH expansion plan.

ProjectX history endpoint returns up to limit=1000 bars/call. For 6
months of 1-min RTH (~30k bars/symbol), that's ~30 paginated calls/sym.
Parallelize across symbols via threads since the bottleneck is API
latency, not local CPU.

Bars are filtered to RTH-only at the post-processing step (UTC time
range 13:30-20:00 = ET 9:30-16:00, weekdays only). The full intraday
range is pulled first so we can later carve out the Asian and London
slices without re-fetching.

Output: state/bars/<sym>_1m_2026-05-15.parquet, columns:
  ts (UTC), open, high, low, close, volume, session ('RTH'|'London'|'Asian'|'PostClose')

Usage:
    .venv/Scripts/python.exe -m scripts.pull_rth_bars --months 6
    .venv/Scripts/python.exe -m scripts.pull_rth_bars --symbols MGC,MNQ --months 12

Run-time: ~15-30 min sequential per symbol; ~1-1.5 hours total with
4-thread parallelism for the full 14-symbol universe.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for raw in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip(); v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v

sys.path.insert(0, str(PROJECT_ROOT))

from tools.projectx_client import ProjectXClient  # noqa: E402

# Focus universe — 14 symbols
FOCUS_UNIVERSE = [
    "MGC", "GC",      # micro/full gold
    "MNQ", "NQ",      # micro/full nasdaq
    "MES", "ES",      # micro/full S&P
    "6E",             # euro fx
    "ZN", "ZB", "ZF", # treasuries
    "CL", "MCL",      # crude oil
    "NG", "MNG",      # natural gas
]

OUTPUT_DIR = PROJECT_ROOT / "state" / "bars"


def session_for_utc(ts_utc: datetime) -> str:
    """Classify a UTC timestamp into trading session per our convention.

    ET window mapping (DST handling kept simple — May 15 is EDT, UTC-4):
      Asian:     17:00 ET prev day -> 03:00 ET   = 21:00-07:00 UTC
      London:    03:00 ET -> 08:00 ET             = 07:00-12:00 UTC
      RTH:       09:30 ET -> 16:00 ET             = 13:30-20:00 UTC
      PostClose: 16:00 ET -> 17:00 ET             = 20:00-21:00 UTC
      Gap (08:00-09:30 ET / 12:00-13:30 UTC): "PreOpen" — discarded
    """
    h = ts_utc.hour
    m = ts_utc.minute
    minutes_utc = h * 60 + m
    if minutes_utc >= 21 * 60 or minutes_utc < 7 * 60:  # 21:00 -> 07:00
        return "Asian"
    if minutes_utc < 12 * 60:  # 07:00 -> 12:00
        return "London"
    if minutes_utc < 13 * 60 + 30:  # 12:00 -> 13:30
        return "PreOpen"
    if minutes_utc < 20 * 60:  # 13:30 -> 20:00
        return "RTH"
    return "PostClose"  # 20:00 -> 21:00


def pull_symbol_bars(client: ProjectXClient, symbol: str,
                      start_dt: datetime, end_dt: datetime,
                      progress_lock: threading.Lock) -> Optional["pd.DataFrame"]:
    """Pull 1-min bars for `symbol` between `start_dt` and `end_dt`,
    paginating in 1000-bar chunks. Returns a pandas DataFrame or None
    on irrecoverable error."""
    import pandas as pd

    try:
        contract_id = client.front_month_contract_id(symbol)
    except Exception as e:
        with progress_lock:
            print(f"  [{symbol}] front-month resolve FAILED: {e}")
        return None

    all_rows = []
    cursor_end = end_dt
    page = 0
    last_t: Optional[str] = None

    while cursor_end > start_dt:
        page += 1
        s_iso = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        e_iso = cursor_end.strftime("%Y-%m-%dT%H:%M:%SZ")
        # Exponential backoff: 0s/5s/15s/30s/60s/120s. ProjectX 429s
        # take ~30-60s to clear at our rate-limit tier.
        bars = None
        for attempt, wait_s in enumerate([0, 5, 15, 30, 60, 120]):
            if wait_s > 0:
                time.sleep(wait_s)
            try:
                bars = client.get_bars(contract_id, s_iso, e_iso,
                                        unit=2, unit_number=1, limit=1000,
                                        live=False) or []
                break
            except Exception as e:
                is_429 = "429" in str(e)
                with progress_lock:
                    print(f"  [{symbol}] page {page} attempt {attempt+1}: "
                           f"{'429' if is_429 else type(e).__name__}")
                if not is_429 and attempt >= 1:
                    bars = None
                    break
        if bars is None:
            with progress_lock:
                print(f"  [{symbol}] page {page} EXHAUSTED retries - stopping")
            break
        if not bars:
            break
        # Bars come newest-first. Add them all; we'll dedupe + sort later.
        all_rows.extend(bars)
        # Move the cursor to just before the oldest bar in this page
        oldest_t = bars[-1].get("t")
        if oldest_t is None or oldest_t == last_t:
            break
        last_t = oldest_t
        cursor_end = datetime.fromisoformat(oldest_t.replace("Z", "+00:00"))
        # Small delay between pages to be polite to the API
        time.sleep(0.2)
        if page % 5 == 0:
            with progress_lock:
                print(f"  [{symbol}] {page} pages, {len(all_rows)} bars, "
                       f"cursor at {cursor_end.strftime('%Y-%m-%d %H:%M')}")

    if not all_rows:
        return None

    df = pd.DataFrame(all_rows)
    # Normalize column names
    rename_map = {"t": "ts", "o": "open", "h": "high", "l": "low",
                   "c": "close", "v": "volume"}
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df.drop_duplicates(subset=["ts"]).sort_values("ts").reset_index(drop=True)
    df["session"] = df["ts"].apply(session_for_utc)
    with progress_lock:
        print(f"  [{symbol}] DONE — {len(df)} unique bars, "
               f"range {df['ts'].min()} -> {df['ts'].max()}")
    return df


def worker(symbol: str, start_dt: datetime, end_dt: datetime,
            progress_lock: threading.Lock) -> None:
    """One-shot worker: pull, save parquet, report."""
    client = ProjectXClient()
    client.authenticate()
    df = pull_symbol_bars(client, symbol, start_dt, end_dt, progress_lock)
    if df is None:
        return
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    out_path = OUTPUT_DIR / f"{symbol}_1m_{today}.parquet"
    df.to_parquet(out_path, index=False)
    with progress_lock:
        rth_count = (df["session"] == "RTH").sum()
        print(f"  [{symbol}] saved {out_path.name} "
               f"({len(df)} bars, RTH={rth_count})")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--months", type=int, default=6,
                     help="how many months back to pull (default 6)")
    p.add_argument("--symbols", type=str, default=None,
                     help="comma-separated symbol override (default: full focus universe)")
    p.add_argument("--threads", type=int, default=4)
    args = p.parse_args()

    symbols = args.symbols.split(",") if args.symbols else FOCUS_UNIVERSE
    end_dt = datetime.now(tz=timezone.utc)
    start_dt = end_dt - timedelta(days=30 * args.months)

    print(f"=== RTH bar pull (Phase 0) ===")
    print(f"window: {start_dt.strftime('%Y-%m-%d')} -> "
           f"{end_dt.strftime('%Y-%m-%d')} ({args.months} months)")
    print(f"symbols: {symbols}")
    print(f"threads: {args.threads}")
    print()

    progress_lock = threading.Lock()

    # Run in batches of `threads` concurrent workers
    batches = [symbols[i:i + args.threads]
                for i in range(0, len(symbols), args.threads)]

    t0 = time.time()
    for batch_idx, batch in enumerate(batches):
        print(f"--- batch {batch_idx + 1}/{len(batches)}: {batch} ---")
        threads = []
        for sym in batch:
            t = threading.Thread(
                target=worker, args=(sym, start_dt, end_dt, progress_lock),
                name=f"pull-{sym}", daemon=True,
            )
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        print()

    elapsed = time.time() - t0
    print(f"=== DONE in {elapsed:.0f}s ({elapsed / 60:.1f}min) ===")
    print(f"Output: {OUTPUT_DIR}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
