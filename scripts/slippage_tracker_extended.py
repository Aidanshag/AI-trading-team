"""Extended slippage tracker — per-symbol, per-time-of-day, per-regime.

Companion to scripts/slippage_tracker.py (which produces per-cell
breakdown). This script aggregates the same fill data along three
additional dimensions called out in cowork_coordination.md and the
slippage measurement infrastructure spec:

  1. PER-SYMBOL — collapse session × side × leg, answer "how much
     slippage does ZN typically eat per round-trip?"
  2. PER-TIME-OF-DAY — group fills by UTC hour, answer "which hours
     have systematically worse slippage?"
  3. PER-REGIME — cross-reference fills with `state/regime_tags.json`,
     answer "is high-vol or news-proximity regime materially worse?"

Output:
  vault/research/live_slippage/<date>_per_symbol.md
  vault/research/live_slippage/<date>_per_hour.md
  vault/research/live_slippage/<date>_per_regime.md
  vault/research/live_slippage/<date>_summary.md
  vault/research/live_slippage/<date>_extended.json (machine-readable)

Per the new coordination rule (cowork_coordination.md 2026-05-08
~23:30 UTC), this work item ships with explicit Prediction +
Measurement plan + Variance trigger. See PREDICTIONS section below.

USAGE:
  python -m scripts.slippage_tracker_extended
  python -m scripts.slippage_tracker_extended --since 2026-05-10
  python -m scripts.slippage_tracker_extended --print

REQUIRES: state/fund.db with `live_trader` filled orders. Empty
output until Sunday's first fills land.

═══════════════════════════════════════════════════════════════════
PREDICTIONS (recorded BEFORE first live fills, 2026-05-09 evening):
═══════════════════════════════════════════════════════════════════

PER-SYMBOL (mean adverse slippage per leg, ticks):
  ZN: 0.20  (10y, deepest book of the curve)
  ZT: 0.15  (2y, tightest spread)
  ZF: 0.20  (5y, similar to ZN)
  ZB: 0.30  (30y, widest natural spread of the four)

In dollars per round-trip (entry+exit slippage):
  ZN: 2 × 0.20 × $15.625 = $6.25
  ZT: 2 × 0.15 × $15.625 = $4.69
  ZF: 2 × 0.20 × $7.8125 = $3.13
  ZB: 2 × 0.30 × $31.25  = $18.75

PER-TIME-OF-DAY:
  RTH hours (UTC 13-20): 50% lower slippage than Asian
  Asian hours (UTC 0-7): 1.5-2× the RTH slippage (thinnest tape)
  London hours (UTC 8-12): RTH-comparable

PER-REGIME (using regime_tags.json):
  vol=low + news=clear: baseline (~0.15 ticks/side)
  vol=high OR news=inside: 2-3× baseline (~0.4-0.5 ticks)
  vol=high AND news=inside: 3-5× baseline (avoid this regime)

VARIANCE TRIGGERS (rollback / redesign thresholds):
  - ANY per-symbol mean > 0.5 ticks/side after 5+ fills:
    that cell is gap_fill_wide-unsafe; demote to shadow.
  - Asian-hour slippage > 2× RTH after 10+ fills per hour:
    add a thin-tape Asian filter to the live_allowlist.
  - Regime correlation absent (no clear pattern) after 30+ fills:
    regime_classifier.py either useless or miscalibrated; revisit.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, stdev

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "state" / "fund.db"
REGIME_TAGS = PROJECT_ROOT / "state" / "regime_tags.json"
OUT_DIR = PROJECT_ROOT / "vault" / "research" / "live_slippage"


# Per-symbol tick economics (matches scripts/slippage_tracker.py)
TICK_BY_SYMBOL = {
    "ZN": 0.015625, "ZB": 0.03125, "ZT": 0.0078125, "ZF": 0.0078125,
    "NG": 0.001, "GC": 0.10, "6E": 0.00005,
    "MES": 0.25, "MNQ": 0.25, "MCL": 0.01,
    "ES": 0.25, "NQ": 0.25, "CL": 0.01,
}
# Tick value in dollars (for $-conversion of slippage)
TICK_VALUE_USD = {
    "ZN": 15.625, "ZB": 31.25, "ZT": 15.625, "ZF": 7.8125,
    "NG": 10.0, "GC": 10.0, "6E": 6.25,
    "MES": 1.25, "MNQ": 0.50, "MCL": 1.00,
    "ES": 12.50, "NQ": 5.00, "CL": 10.00,
}


# ── Predictions baked in (for the variance comparison) ─────────
PREDICTED_PER_SYMBOL_TICKS = {
    "ZN": 0.20, "ZT": 0.15, "ZF": 0.20, "ZB": 0.30,
    # Other symbols default to 0.25 if absent from this map
}
VARIANCE_THRESHOLD_PER_SYMBOL = 0.20   # ±0.20 ticks deviation = warn
SYMBOL_CRITICAL_THRESHOLD = 0.50       # > 0.5 ticks/side = unsafe cell


# ── Data load helpers ──────────────────────────────────────────

def load_fills(since: str | None = None) -> list[dict]:
    """Read filled live_trader orders from state/fund.db. Optionally
    bound to fills with ts_proposed >= since (YYYY-MM-DD)."""
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    q = (
        "SELECT client_order_id, symbol, side, order_type, limit_price, "
        "stop_price, ts_proposed, ts_filled, avg_fill_price, qty, status "
        "FROM orders "
        "WHERE agent = 'live_trader' "
        "  AND avg_fill_price IS NOT NULL "
        "  AND avg_fill_price > 0"
    )
    args: tuple = ()
    if since:
        q += " AND ts_proposed >= ?"
        args = (since,)
    q += " ORDER BY ts_proposed"
    return [dict(r) for r in conn.execute(q, args).fetchall()]


def load_regime_tags() -> dict:
    """Returns the regime_tags.json payload, or empty dict if missing.

    Schema (per scripts/regime_classifier.py):
      {
        "by_symbol": {
          "ZN": {
            "tags": [{"ts": "...", "vol_regime": "low|med|high",
                      "trend_regime": "trending|ranging",
                      "news_proximity": "clear|near|inside"}, ...]
          }
        }
      }
    """
    if not REGIME_TAGS.exists():
        return {}
    try:
        return json.loads(REGIME_TAGS.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ── Slippage compute (mirrors slippage_tracker.py) ─────────────

def compute_slippage(row: dict) -> tuple[float, float, str] | None:
    """Returns (slip_ticks, slip_usd, leg) or None if computable.

    slip_ticks > 0 = adverse (paid worse than intent).
    slip_ticks < 0 = favorable (got better than intent).
    """
    sym = row["symbol"]
    tick = TICK_BY_SYMBOL.get(sym)
    tick_val = TICK_VALUE_USD.get(sym)
    if not tick or not tick_val:
        return None
    cid = row.get("client_order_id") or ""
    if cid.endswith("_stop"):
        leg, intent = "stop", row["stop_price"]
    elif cid.endswith("_target"):
        leg, intent = "target", row["limit_price"]
    else:
        leg, intent = "entry", row["limit_price"]
    if intent is None or intent <= 0:
        return None
    actual = float(row["avg_fill_price"])
    side = (row["side"] or "").lower()
    if side == "buy":
        slip_price = actual - float(intent)
    else:
        slip_price = float(intent) - actual
    slip_ticks = slip_price / tick
    slip_usd = slip_ticks * tick_val * int(row.get("qty") or 1)
    return slip_ticks, slip_usd, leg


def utc_hour(ts_iso: str) -> int | None:
    try:
        dt = datetime.fromisoformat((ts_iso or "").replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).hour
    except Exception:
        return None


def regime_at(ts_iso: str, symbol: str, regime_data: dict) -> dict | None:
    """Find the regime tag bar nearest to ts_iso for the given symbol."""
    by_sym = (regime_data.get("by_symbol") or {}).get(symbol)
    if not by_sym or not by_sym.get("tags"):
        return None
    target = ts_iso or ""
    # Tags are sorted by ts; binary search would be faster, but linear
    # scan is fine at <10k tags.
    nearest: dict | None = None
    for tag in by_sym["tags"]:
        if tag["ts"] <= target:
            nearest = tag
        else:
            break
    return nearest


# ── Aggregation ────────────────────────────────────────────────

def stats_block(slips: list[float], slips_usd: list[float],
                ticks_pred: float | None = None) -> dict:
    if not slips:
        return {"n": 0}
    n = len(slips)
    out = {
        "n": n,
        "mean_ticks": mean(slips),
        "median_ticks": median(slips),
        "worst_ticks": max(slips),
        "best_ticks": min(slips),
        "stdev_ticks": stdev(slips) if n > 1 else 0.0,
        "mean_usd": mean(slips_usd) if slips_usd else 0.0,
        "total_usd": sum(slips_usd) if slips_usd else 0.0,
        "adverse_fraction": sum(1 for s in slips if s > 0) / n,
    }
    if ticks_pred is not None:
        out["predicted_ticks"] = ticks_pred
        out["variance_ticks"] = out["mean_ticks"] - ticks_pred
        out["variance_flag"] = (
            "WARN" if abs(out["variance_ticks"]) > VARIANCE_THRESHOLD_PER_SYMBOL
            else "ok"
        )
        if out["mean_ticks"] > SYMBOL_CRITICAL_THRESHOLD:
            out["variance_flag"] = "CRITICAL"
    return out


def bucket_per_symbol(rows: list[dict]) -> dict[str, dict]:
    by_sym_ticks: dict[str, list[float]] = defaultdict(list)
    by_sym_usd: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        comp = compute_slippage(r)
        if comp is None:
            continue
        slip_ticks, slip_usd, leg = comp
        if leg != "entry":
            continue   # entries first; stop/target handled separately
        sym = r["symbol"]
        by_sym_ticks[sym].append(slip_ticks)
        by_sym_usd[sym].append(slip_usd)
    out = {}
    for sym in sorted(by_sym_ticks):
        pred = PREDICTED_PER_SYMBOL_TICKS.get(sym)
        out[sym] = stats_block(by_sym_ticks[sym], by_sym_usd[sym], pred)
    return out


def bucket_per_hour(rows: list[dict]) -> dict[int, dict]:
    by_hour_ticks: dict[int, list[float]] = defaultdict(list)
    by_hour_usd: dict[int, list[float]] = defaultdict(list)
    for r in rows:
        comp = compute_slippage(r)
        if comp is None:
            continue
        slip_ticks, slip_usd, leg = comp
        if leg != "entry":
            continue
        h = utc_hour(r.get("ts_filled") or r.get("ts_proposed", ""))
        if h is None:
            continue
        by_hour_ticks[h].append(slip_ticks)
        by_hour_usd[h].append(slip_usd)
    return {h: stats_block(by_hour_ticks[h], by_hour_usd[h])
            for h in sorted(by_hour_ticks)}


def bucket_per_regime(rows: list[dict], regime_data: dict) -> dict[str, dict]:
    """Bucket fills by (vol_regime × news_proximity) regime tags."""
    by_regime_ticks: dict[str, list[float]] = defaultdict(list)
    by_regime_usd: dict[str, list[float]] = defaultdict(list)
    if not regime_data:
        return {}
    for r in rows:
        comp = compute_slippage(r)
        if comp is None:
            continue
        slip_ticks, slip_usd, leg = comp
        if leg != "entry":
            continue
        sym = r["symbol"]
        ts = r.get("ts_filled") or r.get("ts_proposed") or ""
        tag = regime_at(ts, sym, regime_data)
        if tag is None:
            continue
        regime_key = f"{tag.get('vol_regime', '?')}|{tag.get('news_proximity', '?')}"
        by_regime_ticks[regime_key].append(slip_ticks)
        by_regime_usd[regime_key].append(slip_usd)
    return {k: stats_block(by_regime_ticks[k], by_regime_usd[k])
            for k in sorted(by_regime_ticks)}


# ── Output ─────────────────────────────────────────────────────

def write_per_symbol_md(date: str, results: dict[str, dict]) -> Path:
    p = OUT_DIR / f"{date}_per_symbol.md"
    L = ["---", "type: slippage_per_symbol",
         f"date: {date}",
         f"generated_at: {datetime.now(timezone.utc).isoformat()}",
         "---", "",
         "# Slippage by symbol",
         "",
         "Mean adverse slippage on entry orders, by symbol. Predictions",
         "are baked into `scripts/slippage_tracker_extended.py:PREDICTED_PER_SYMBOL_TICKS`.",
         "Variance > 0.20 ticks = WARN; > 0.50 ticks/side mean = CRITICAL",
         "(cell is gap_fill_wide-unsafe; demote).",
         "",
         "| Symbol | n | Mean ticks | Median | Predicted | Variance | $/RT | Adverse % | Flag |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    if not results:
        L.append("| _(no fills yet)_ |  |  |  |  |  |  |  |  |")
    for sym, s in results.items():
        if s.get("n", 0) == 0:
            continue
        pred = s.get("predicted_ticks")
        var = s.get("variance_ticks")
        flag = s.get("variance_flag", "—")
        rt_usd = s["mean_usd"] * 2  # round-trip = 2 × per-leg
        L.append(
            f"| {sym} | {s['n']} | {s['mean_ticks']:+.2f} | "
            f"{s['median_ticks']:+.2f} | "
            f"{pred:+.2f} | {var:+.2f}" if pred is not None
            else f"| {sym} | {s['n']} | {s['mean_ticks']:+.2f} | "
            f"{s['median_ticks']:+.2f} | — | —"
        )
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(L) + "\n", encoding="utf-8")
    return p


def write_per_hour_md(date: str, results: dict[int, dict]) -> Path:
    p = OUT_DIR / f"{date}_per_hour.md"
    L = ["---", "type: slippage_per_hour",
         f"date: {date}",
         f"generated_at: {datetime.now(timezone.utc).isoformat()}",
         "---", "",
         "# Slippage by hour-of-day (UTC)",
         "",
         "Hours where slippage spikes are likely thin-tape windows. The",
         "live trader's regime gate already blocks 21:00-04:00 ET",
         "(01:00-08:00 UTC). If non-blocked hours show systematically",
         "worse slippage than RTH (UTC 13:30-20:00), consider widening",
         "the gate.",
         "",
         "| UTC hour | n | Mean ticks | Median | Worst | Adverse % |",
         "|---:|---:|---:|---:|---:|---:|"]
    if not results:
        L.append("| _(no fills yet)_ |  |  |  |  |  |")
    for h in sorted(results):
        s = results[h]
        if s.get("n", 0) == 0:
            continue
        L.append(
            f"| {h:02d} | {s['n']} | {s['mean_ticks']:+.2f} | "
            f"{s['median_ticks']:+.2f} | {s['worst_ticks']:+.2f} | "
            f"{s['adverse_fraction']*100:.0f}% |"
        )
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(L) + "\n", encoding="utf-8")
    return p


def write_per_regime_md(date: str, results: dict[str, dict]) -> Path:
    p = OUT_DIR / f"{date}_per_regime.md"
    L = ["---", "type: slippage_per_regime",
         f"date: {date}",
         f"generated_at: {datetime.now(timezone.utc).isoformat()}",
         "---", "",
         "# Slippage by regime",
         "",
         "Cross-references each fill with the regime tag at fill time",
         "from `state/regime_tags.json` (vol_regime × news_proximity).",
         "Prediction: high-vol or news=inside cells should show 2-3×",
         "baseline slippage. If they don't, the regime classifier is",
         "miscalibrated.",
         "",
         "| vol×news regime | n | Mean ticks | Median | Worst | Adverse % |",
         "|---|---:|---:|---:|---:|---:|"]
    if not results:
        L.append("| _(no regime data or no fills)_ |  |  |  |  |  |")
    for regime in sorted(results):
        s = results[regime]
        if s.get("n", 0) == 0:
            continue
        L.append(
            f"| {regime} | {s['n']} | {s['mean_ticks']:+.2f} | "
            f"{s['median_ticks']:+.2f} | {s['worst_ticks']:+.2f} | "
            f"{s['adverse_fraction']*100:.0f}% |"
        )
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(L) + "\n", encoding="utf-8")
    return p


def write_summary_md(date: str, per_sym: dict, per_hour: dict,
                     per_regime: dict, n_fills: int) -> Path:
    p = OUT_DIR / f"{date}_summary.md"
    L = ["---", "type: slippage_summary",
         f"date: {date}",
         f"generated_at: {datetime.now(timezone.utc).isoformat()}",
         f"n_fills: {n_fills}",
         "---", "",
         "# Slippage summary — extended",
         "",
         f"**Total filled live_trader entries**: {n_fills}",
         "",
         "## Variance vs predictions (per symbol)", ""]
    if not per_sym:
        L.append("_(no fills yet — predictions await Sunday's data)_")
    else:
        critical = []
        warns = []
        oks = []
        for sym, s in per_sym.items():
            flag = s.get("variance_flag")
            if flag == "CRITICAL":
                critical.append((sym, s))
            elif flag == "WARN":
                warns.append((sym, s))
            elif flag == "ok":
                oks.append((sym, s))
        if critical:
            L.append("### ⚠ CRITICAL — cells flagged for demotion\n")
            for sym, s in critical:
                L.append(f"- **{sym}**: mean {s['mean_ticks']:+.2f} ticks/side "
                         f"> 0.50 critical threshold. n={s['n']}. "
                         f"Predicted {s.get('predicted_ticks', '—')}. "
                         f"Recommend demote to shadow.")
        if warns:
            L.append("\n### ⚠ WARN — variance > ±0.20 ticks\n")
            for sym, s in warns:
                L.append(f"- {sym}: mean {s['mean_ticks']:+.2f}, "
                         f"predicted {s['predicted_ticks']:+.2f}, "
                         f"variance {s['variance_ticks']:+.2f}.")
        if oks:
            L.append("\n### ✓ OK — within prediction band\n")
            for sym, s in oks:
                L.append(f"- {sym}: mean {s['mean_ticks']:+.2f} "
                         f"(predicted {s['predicted_ticks']:+.2f}, "
                         f"n={s['n']}).")

    L += ["",
          "## Hour-of-day pattern", ""]
    if per_hour:
        # Find best/worst hours by mean
        hours_by_mean = sorted(per_hour.items(),
                               key=lambda x: x[1].get("mean_ticks", 0))
        L.append(f"- Best hour: UTC {hours_by_mean[0][0]:02d} "
                 f"({hours_by_mean[0][1]['mean_ticks']:+.2f} ticks, "
                 f"n={hours_by_mean[0][1]['n']})")
        L.append(f"- Worst hour: UTC {hours_by_mean[-1][0]:02d} "
                 f"({hours_by_mean[-1][1]['mean_ticks']:+.2f} ticks, "
                 f"n={hours_by_mean[-1][1]['n']})")
    else:
        L.append("_(insufficient data)_")

    L += ["", "## Regime correlation", ""]
    if per_regime:
        # Compare clear vs inside news-proximity
        clear_high = [v for k, v in per_regime.items()
                      if "clear" in k and v.get("n", 0) > 0]
        inside_high = [v for k, v in per_regime.items()
                       if "inside" in k and v.get("n", 0) > 0]
        if clear_high and inside_high:
            avg_clear = mean(s["mean_ticks"] for s in clear_high)
            avg_inside = mean(s["mean_ticks"] for s in inside_high)
            ratio = avg_inside / avg_clear if avg_clear > 0 else 0
            L.append(f"- news=clear avg: {avg_clear:+.2f} ticks")
            L.append(f"- news=inside avg: {avg_inside:+.2f} ticks")
            L.append(f"- ratio: {ratio:.2f}× "
                     f"({'as predicted' if 1.5 < ratio < 5 else 'OUTSIDE prediction band'})")
        else:
            L.append("_(need both clear and inside fills to compare)_")
    else:
        L.append("_(no regime tags loaded — run scripts/regime_classifier.py first)_")

    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(L) + "\n", encoding="utf-8")
    return p


def write_json(date: str, per_sym: dict, per_hour: dict,
               per_regime: dict, n_fills: int) -> Path:
    p = OUT_DIR / f"{date}_extended.json"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_fills": n_fills,
        "per_symbol": per_sym,
        "per_hour": per_hour,
        "per_regime": per_regime,
        "predictions_baseline": PREDICTED_PER_SYMBOL_TICKS,
    }
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return p


# ── main ───────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--since", default=None,
                   help="Lower bound on ts_proposed (YYYY-MM-DD).")
    p.add_argument("--print", dest="do_print", action="store_true")
    args = p.parse_args()

    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} not found", file=sys.stderr)
        return 1

    rows = load_fills(args.since)
    n_fills = len(rows)
    if n_fills == 0:
        print("No filled live_trader orders found.")
        print("(Empty until Sunday 2026-05-10 17:00 ET kickstart.)")
        # Still write empty reports so downstream consumers see the file.
    print(f"Loaded {n_fills} filled live_trader orders.")

    regime = load_regime_tags()
    if not regime:
        print("(No regime_tags.json — per-regime breakdown will be empty. "
              "Run `python -m scripts.regime_classifier` to populate.)")

    per_sym = bucket_per_symbol(rows)
    per_hour = bucket_per_hour(rows)
    per_regime = bucket_per_regime(rows, regime)

    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sym_path = write_per_symbol_md(date, per_sym)
    hour_path = write_per_hour_md(date, per_hour)
    regime_path = write_per_regime_md(date, per_regime)
    summary_path = write_summary_md(date, per_sym, per_hour, per_regime, n_fills)
    json_path = write_json(date, per_sym, per_hour, per_regime, n_fills)

    print(f"Wrote {sym_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {hour_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {regime_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {summary_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {json_path.relative_to(PROJECT_ROOT)}")

    if args.do_print and per_sym:
        print()
        print("Per-symbol (mean entry slippage, ticks):")
        for sym, s in per_sym.items():
            if s.get("n", 0) == 0:
                continue
            flag = s.get("variance_flag", "")
            print(f"  {sym}: n={s['n']:>3d} mean={s['mean_ticks']:+.2f} "
                  f"median={s['median_ticks']:+.2f} {flag}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
