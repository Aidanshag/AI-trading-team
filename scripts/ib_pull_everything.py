"""ib_pull_everything — comprehensive IB data harvest.

User direction 2026-05-17: "comb everything you have access to on IB, take
anything and everything you can from there, theres no downside to having
more data to analyze."

Pulls EVERY asset class IB exposes for free historical bars:
  - All major US ETFs (broad, sector, factor, country, commodity, bond)
  - S&P 500 + Russell 1000 mega/large-cap names
  - Every Topstep-tradeable CME future (continuous-future series)
  - Major CME futures Topstep doesn't trade (lumber, hogs, cattle, etc.)
  - Major FX pairs (USD majors + crosses)
  - Major crypto (BTC, ETH CME futures)
  - VIX-family products

Per (symbol, asset-class) we pull:
  - 1 day bars: 20 years (caps at IB's max history)
  - 1 hour bars: 2 years
  - 15 min bars: 30 days

Output layout:
  vault/ib/data/<asset_class>/<symbol>/<bar_size>/<YYYY>.csv
  vault/ib/data/<asset_class>/index.md

Reconnect-on-disconnect with backoff. Designed to be re-run safely —
overwrites existing CSVs (which is fine since IB data doesn't change
historically). Persists progress to a JSON state file so a resumed run
can skip already-pulled cells.
"""
from __future__ import annotations

import csv
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "vault" / "ib" / "data"
PROGRESS_PATH = DATA_DIR / "_progress.json"
LOG_PATH = DATA_DIR / "pull_everything_log.txt"

# ────────────────────────────────────────────────────────────────
# UNIVERSE — broken into asset classes for organized output
# ────────────────────────────────────────────────────────────────

ETFS_BROAD = {
    "SPY": "STK", "QQQ": "STK", "IWM": "STK", "DIA": "STK", "VTI": "STK",
    "EFA": "STK", "EEM": "STK", "VEA": "STK", "VWO": "STK",
}
ETFS_SECTOR = {
    "XLK": "STK", "XLF": "STK", "XLE": "STK", "XLV": "STK", "XLY": "STK",
    "XLP": "STK", "XLI": "STK", "XLU": "STK", "XLB": "STK", "XLRE": "STK",
    "XLC": "STK",
    "SOXX": "STK", "SMH": "STK",  # semiconductors
    "KBE": "STK", "KRE": "STK",   # banks
    "ITB": "STK", "XHB": "STK",   # homebuilders
    "OIH": "STK", "XOP": "STK",   # oil & gas
    "GDX": "STK", "GDXJ": "STK",  # gold miners
}
ETFS_FACTOR = {
    "MTUM": "STK", "QUAL": "STK", "VLUE": "STK", "USMV": "STK",
    "SIZE": "STK", "SPLV": "STK", "SPHB": "STK",
}
ETFS_COUNTRY = {
    "EWJ": "STK", "EWG": "STK", "EWU": "STK", "FXI": "STK", "INDA": "STK",
    "EWZ": "STK", "EWC": "STK", "EWA": "STK", "MCHI": "STK",
}
ETFS_BOND = {
    "AGG": "STK", "BND": "STK", "TLT": "STK", "IEF": "STK", "SHY": "STK",
    "TIP": "STK", "LQD": "STK", "HYG": "STK", "JNK": "STK", "MUB": "STK",
    "EMB": "STK",
}
ETFS_COMMODITY = {
    "GLD": "STK", "SLV": "STK", "USO": "STK", "UNG": "STK", "DBC": "STK",
    "PALL": "STK", "PPLT": "STK", "DBA": "STK", "CORN": "STK", "WEAT": "STK",
}
ETFS_VOL = {
    "VXX": "STK", "UVXY": "STK", "SVXY": "STK", "VIXY": "STK",
}

# Mega/large caps — what serious factor/multi-name research needs
EQUITIES_MEGACAPS = {
    "AAPL": "STK", "MSFT": "STK", "GOOG": "STK", "GOOGL": "STK", "AMZN": "STK",
    "META": "STK", "NVDA": "STK", "TSLA": "STK", "BRK B": "STK",
    "AVGO": "STK", "ORCL": "STK", "ADBE": "STK", "CRM": "STK", "AMD": "STK",
    "NFLX": "STK", "INTC": "STK", "CSCO": "STK", "QCOM": "STK", "IBM": "STK",
    "JPM": "STK", "V": "STK", "MA": "STK", "BAC": "STK", "WFC": "STK",
    "GS": "STK", "MS": "STK", "C": "STK", "AXP": "STK", "BLK": "STK",
    "JNJ": "STK", "PFE": "STK", "UNH": "STK", "LLY": "STK", "ABBV": "STK",
    "MRK": "STK", "TMO": "STK", "DHR": "STK", "ABT": "STK",
    "WMT": "STK", "PG": "STK", "KO": "STK", "PEP": "STK", "COST": "STK",
    "MCD": "STK", "NKE": "STK", "SBUX": "STK", "HD": "STK", "LOW": "STK",
    "XOM": "STK", "CVX": "STK", "COP": "STK", "SLB": "STK", "EOG": "STK",
    "BA": "STK", "CAT": "STK", "GE": "STK", "HON": "STK", "RTX": "STK",
    "T": "STK", "VZ": "STK", "TMUS": "STK", "DIS": "STK", "CMCSA": "STK",
}

# Topstep-tradeable + adjacent CME futures via continuous-future
FUTURES = {
    # Equity index — Topstep
    "ES":  ("CONTFUT", "CME"),   "NQ":  ("CONTFUT", "CME"),
    "RTY": ("CONTFUT", "CME"),   "MES": ("CONTFUT", "CME"),
    "MNQ": ("CONTFUT", "CME"),   "M2K": ("CONTFUT", "CME"),
    "YM":  ("CONTFUT", "CBOT"),  "MYM": ("CONTFUT", "CBOT"),
    # Energy
    "CL": ("CONTFUT", "NYMEX"),  "NG": ("CONTFUT", "NYMEX"),
    "RB": ("CONTFUT", "NYMEX"),  "HO": ("CONTFUT", "NYMEX"),
    "MCL": ("CONTFUT", "NYMEX"), "BZ": ("CONTFUT", "NYMEX"),
    # Metals
    "GC": ("CONTFUT", "COMEX"),  "SI": ("CONTFUT", "COMEX"),
    "HG": ("CONTFUT", "COMEX"),  "PL": ("CONTFUT", "NYMEX"),
    "PA": ("CONTFUT", "NYMEX"),  "MGC": ("CONTFUT", "COMEX"),
    "SIL": ("CONTFUT", "COMEX"),
    # Treasuries
    "ZN": ("CONTFUT", "CBOT"),   "ZB": ("CONTFUT", "CBOT"),
    "ZF": ("CONTFUT", "CBOT"),   "ZT": ("CONTFUT", "CBOT"),
    "TN": ("CONTFUT", "CBOT"),   "UB": ("CONTFUT", "CBOT"),
    # FX
    "6E": ("CONTFUT", "CME"),    "6B": ("CONTFUT", "CME"),
    "6J": ("CONTFUT", "CME"),    "6C": ("CONTFUT", "CME"),
    "6A": ("CONTFUT", "CME"),    "6S": ("CONTFUT", "CME"),
    "6N": ("CONTFUT", "CME"),    "M6E": ("CONTFUT", "CME"),
    "M6B": ("CONTFUT", "CME"),
    # Grains
    "ZC": ("CONTFUT", "CBOT"),   "ZS": ("CONTFUT", "CBOT"),
    "ZW": ("CONTFUT", "CBOT"),   "ZM": ("CONTFUT", "CBOT"),
    "ZL": ("CONTFUT", "CBOT"),   "KE": ("CONTFUT", "KCBT"),
    # Softs
    "CC": ("CONTFUT", "NYBOT"),  "KC": ("CONTFUT", "NYBOT"),
    "SB": ("CONTFUT", "NYBOT"),  "CT": ("CONTFUT", "NYBOT"),
    "OJ": ("CONTFUT", "NYBOT"),
    # Livestock
    "LE": ("CONTFUT", "CME"),    "HE": ("CONTFUT", "CME"),
    "GF": ("CONTFUT", "CME"),
    # Crypto futures
    "BTC": ("CONTFUT", "CME"),   "MBT": ("CONTFUT", "CME"),
    "ETH": ("CONTFUT", "CME"),   "MET": ("CONTFUT", "CME"),
}

# Bucket name -> {sym: sec_type or (sec_type, exchange)}
UNIVERSE = {
    "etfs_broad": ETFS_BROAD,
    "etfs_sector": ETFS_SECTOR,
    "etfs_factor": ETFS_FACTOR,
    "etfs_country": ETFS_COUNTRY,
    "etfs_bond": ETFS_BOND,
    "etfs_commodity": ETFS_COMMODITY,
    "etfs_vol": ETFS_VOL,
    "equities_megacaps": EQUITIES_MEGACAPS,
    "futures": FUTURES,
}

PULL_PLAN = [
    ("20 Y", "1 day",  "1d"),
    ("2 Y",  "1 hour", "1h"),
    ("30 D", "15 mins", "15min"),
]
MAX_RETRY = 3


def log(msg: str) -> None:
    line = f"[{datetime.now(tz=timezone.utc).isoformat()}] {msg}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_progress() -> dict:
    if PROGRESS_PATH.exists():
        try:
            return json.loads(PROGRESS_PATH.read_text())
        except Exception:
            return {}
    return {}


def save_progress(p: dict) -> None:
    PROGRESS_PATH.write_text(json.dumps(p, indent=2), encoding="utf-8")


def ensure_connected(client) -> bool:
    if client.is_connected():
        return True
    log("  reconnecting to IB Gateway...")
    try:
        client.connect()
        return client.is_connected()
    except Exception as e:
        log(f"  reconnect failed: {type(e).__name__}: {e}")
        return False


def pull(client, asset_class: str, symbol: str, sec_type: str, exchange: str,
         duration: str, bar_size: str, subdir: str) -> int:
    out_dir = DATA_DIR / asset_class / symbol / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, MAX_RETRY + 1):
        if not ensure_connected(client):
            time.sleep(3 * attempt)
            continue
        try:
            bars = client.get_historical_bars(
                symbol=symbol, sec_type=sec_type,
                exchange=exchange or "SMART", currency="USD",
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
            log(f"  {symbol} {bar_size} attempt {attempt}: {type(e).__name__}: {e}")
            time.sleep(3 * attempt)
    return -1


def main() -> int:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    log("=== IB PULL EVERYTHING — start ===")
    try:
        from tools.ib_client import IBClient
    except ImportError as e:
        log(f"ABORT: cannot import IBClient: {e}")
        return 2

    client = IBClient(client_id=7)
    try:
        log(f"Connecting to IB Gateway {client.host}:{client.port} (clientId={client.client_id})")
        client.connect()
    except Exception as e:
        log(f"ABORT: IB connect failed: {type(e).__name__}: {e}")
        log("HINT: IB Gateway may have lost its session. Re-authenticate via Gateway login window.")
        return 2

    log(f"Connected. Account(s): {client.get_accounts()}")

    progress = load_progress()
    total_pulls = 0
    for ac, syms in UNIVERSE.items():
        total_pulls += len(syms) * len(PULL_PLAN)
    log(f"Total planned pulls: {total_pulls}")

    summary: dict[str, dict[str, dict[str, int]]] = {}
    pull_n = 0
    for asset_class, syms in UNIVERSE.items():
        summary.setdefault(asset_class, {})
        for symbol, spec in syms.items():
            if isinstance(spec, tuple):
                sec_type, exchange = spec
            else:
                sec_type = spec
                exchange = "SMART"
            summary[asset_class][symbol] = {}
            for duration, bar_size, subdir in PULL_PLAN:
                pull_n += 1
                key = f"{asset_class}|{symbol}|{bar_size}"
                if progress.get(key, 0) > 0:
                    log(f"[{pull_n}/{total_pulls}] {asset_class}/{symbol} {bar_size} — already pulled, skip")
                    summary[asset_class][symbol][bar_size] = progress[key]
                    continue
                log(f"[{pull_n}/{total_pulls}] {asset_class}/{symbol} {bar_size} ({duration})")
                n = pull(client, asset_class, symbol, sec_type, exchange,
                         duration, bar_size, subdir)
                summary[asset_class][symbol][bar_size] = n
                progress[key] = n
                save_progress(progress)
                time.sleep(2)

    client.disconnect()
    log("=== IB PULL EVERYTHING — done ===")

    # Generate per-asset-class index files
    for asset_class, data in summary.items():
        path = DATA_DIR / asset_class / "index.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "---", "type: manifest",
            f"updated: {datetime.now(tz=timezone.utc).isoformat()}",
            f"asset_class: {asset_class}",
            "---", "",
            f"# {asset_class} — historical bars",
            "", "| Symbol | 1d | 1h | 15min |", "|---|---|---|---|",
        ]
        for sym, counts in sorted(data.items()):
            d = counts.get("1 day", 0)
            h = counts.get("1 hour", 0)
            m15 = counts.get("15 mins", 0)
            lines.append(f"| {sym} | {d} | {h} | {m15} |")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        log(f"Wrote {path}")

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
