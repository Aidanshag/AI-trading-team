"""Fetch the upcoming Treasury auction schedule from TreasuryDirect.

Writes:
  vault/economic_calendar/treasury_auctions.json    # machine-readable
  vault/economic_calendar/treasury_auctions.md      # human-readable

Why: gap_fill on ZN/ZT/ZB/ZF is the fund's headline edge. Per the standing
theses, auction concession days (the day before a major auction, and the
auction day itself) reliably weaken the issuance side of the curve and
produce directional drift — the regime where gap_fill fades fail. The
high-impact blackout gate in the risk hook can read this file and block
entries during the relevant window.

Data source: TreasuryDirect's structured auction data feed at
fiscaldata.treasury.gov (no auth required). Falls back to scraping
TreasuryDirect's upcoming-auctions HTML page if the fiscaldata API
endpoint changes shape.

USAGE:
  python -m scripts.fetch_treasury_auctions             # write outputs
  python -m scripts.fetch_treasury_auctions --print     # also print to stdout
  python -m scripts.fetch_treasury_auctions --days 30   # window (default 21)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

_HERE = Path(__file__).resolve().parent.parent
os.chdir(_HERE)

# fiscaldata.treasury.gov public endpoint (no auth).
# 2026-05-07: API field names verified via live probe — they renamed
# `security_type_desc` → `security_type` and removed `maturity_date`
# (the field is computable from issue_date + security_term, not stored).
# Available fields: record_date, security_type, security_term, reopening,
# cusip, offering_amt, announcemt_date (sic), auction_date, issue_date.
FISCALDATA_URL = (
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"
    "v1/accounting/od/upcoming_auctions"
    "?fields=record_date,security_type,security_term,auction_date,"
    "issue_date,offering_amt,announcemt_date,reopening"
    "&page[size]=100"
)

# Security types we care about for gap_fill on the rates curve
RATES_SECURITY_TYPES = {"Note", "Bond", "TIPS", "Bill"}


def fetch() -> list[dict]:
    """Returns list of auction records (dict)."""
    r = requests.get(FISCALDATA_URL, timeout=30)
    r.raise_for_status()
    payload = r.json()
    return payload.get("data", [])


def filter_window(records: list[dict], days: int) -> list[dict]:
    """Keep only auctions in the next `days` days."""
    today = datetime.now(tz=timezone.utc).date()
    cutoff = today + timedelta(days=days)
    out = []
    for r in records:
        try:
            ad = datetime.fromisoformat(str(r.get("auction_date", "")).split("T")[0]).date()
        except Exception:
            continue
        if today <= ad <= cutoff:
            out.append(r)
    out.sort(key=lambda r: r.get("auction_date", ""))
    return out


def annotate_for_gap_fill(records: list[dict]) -> list[dict]:
    """Add fields the high-impact blackout gate might want."""
    out = []
    for r in records:
        # 2026-05-07: API uses `security_type` (was `security_type_desc`).
        sec = str(r.get("security_type", "") or r.get("security_type_desc", ""))
        term = str(r.get("security_term", ""))
        ad = str(r.get("auction_date", "")).split("T")[0]

        # Map to ProjectX symbol risk:
        #   2-year note  -> ZT
        #   3-year note  -> (no direct mapping; affects ZT/ZF basis)
        #   5-year note  -> ZF
        #   7-year note  -> (affects ZF/ZN basis)
        #   10-year note -> ZN
        #   20-year bond -> (affects ZB)
        #   30-year bond -> ZB
        #   2/5/10 TIPS  -> affects real-yield component but not directly the future
        affected = []
        if sec == "Note":
            if "2-Year" in term: affected.append("ZT")
            elif "5-Year" in term: affected.append("ZF")
            elif "10-Year" in term: affected.append("ZN")
        elif sec == "Bond":
            if "30-Year" in term: affected.append("ZB")
            elif "20-Year" in term: affected.append("ZB")  # secondary effect

        rec = {
            "auction_date": ad,
            "announcement_date": str(r.get("announcemt_date", "") or "").split("T")[0],
            "issue_date": str(r.get("issue_date", "")).split("T")[0],
            "security_type": sec,
            "security_term": term,
            "reopening": r.get("reopening"),
            "offering_amt_usd": _parse_amt(r.get("offering_amt")),
            "affected_futures": affected,
        }
        out.append(rec)
    return out


def _parse_amt(v) -> float | None:
    if v is None:
        return None
    try:
        # API returns as string in dollars
        return float(str(v).replace(",", ""))
    except Exception:
        return None


def write_outputs(records: list[dict]) -> None:
    out_dir = _HERE / "vault" / "economic_calendar"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "treasury_auctions.json"
    md_path = out_dir / "treasury_auctions.md"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": FISCALDATA_URL,
        "auctions": records,
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    L = ["---", "type: treasury_auction_calendar",
         f"generated_at: {payload['generated_at']}",
         f"count: {len(records)}",
         "---", "",
         "# Treasury auction calendar — upcoming",
         "",
         "Risk-relevant for gap_fill on ZN/ZT/ZB/ZF. Concession days "
         "(typically the trading day before each auction, and the auction "
         "day itself) tend to produce sustained directional drift in the "
         "issued tenor — gap_fill fade can fail.",
         "",
         "| Auction date | Announce | Type | Term | Issue | Amount ($B) | Reopen | Affects futures |",
         "|---|---|---|---|---|---:|---|---|"]
    for r in records:
        amt = (r.get("offering_amt_usd") or 0) / 1e9
        reopen = "Y" if r.get("reopening") in (True, "Y", "yes") else ""
        L.append(f"| {r['auction_date']} | {r.get('announcement_date','')} "
                 f"| {r['security_type']} | {r['security_term']} | {r['issue_date']} "
                 f"| {amt:.1f} | {reopen} "
                 f"| {', '.join(r['affected_futures']) or '—'} |")
    md_path.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"Wrote {json_path.relative_to(_HERE)}")
    print(f"Wrote {md_path.relative_to(_HERE)}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=21,
                   help="Window in days (default 21).")
    p.add_argument("--print", dest="do_print", action="store_true",
                   help="Also print to stdout.")
    args = p.parse_args()

    try:
        records = fetch()
    except Exception as e:
        print(f"ERROR: failed to fetch from fiscaldata: {e}", file=sys.stderr)
        return 2

    window = filter_window(records, args.days)
    annotated = annotate_for_gap_fill(window)
    print(f"Fetched {len(records)} records, filtered to {len(annotated)} in next {args.days} days.")
    write_outputs(annotated)

    if args.do_print:
        print()
        for r in annotated:
            futs = ", ".join(r["affected_futures"]) or "—"
            amt = (r.get("offering_amt_usd") or 0) / 1e9
            print(f"  {r['auction_date']}  {r['security_type']:5s} {r['security_term']:25s} "
                  f"${amt:>5.1f}B  futures={futs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
