"""Fetch current macro levels from FRED (Federal Reserve Economic Data).

Pulls the series that drive Treasury futures behavior so the daily macro
brief and agent preambles see live regime context. FRED's CSV endpoint is
public and stable (no API key needed for the simple CSV form).

Series pulled:
  DGS10        — 10Y Treasury constant-maturity yield
  DGS2         — 2Y Treasury yield
  DGS30        — 30Y Treasury yield
  DFII10       — 10Y TIPS (real yield)
  T10Y2Y       — 10s2s curve slope
  T10YIE       — 10Y breakeven inflation
  DTWEXBGS     — Trade-weighted USD index (broad)
  VIXCLS       — CBOE VIX
  SOFR         — Secured Overnight Financing Rate (money-market stress signal)

Writes:
  vault/_meta/macro_levels.json   # last value + 5-day delta per series
  vault/_meta/macro_levels.md     # human-readable

USAGE:
  python -m scripts.fetch_fred_macro_levels
  python -m scripts.fetch_fred_macro_levels --print
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

_HERE = Path(__file__).resolve().parent.parent
os.chdir(_HERE)

FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"

SERIES = {
    "DGS10":   ("10Y Treasury yield",         "%"),
    "DGS2":    ("2Y Treasury yield",          "%"),
    "DGS30":   ("30Y Treasury yield",         "%"),
    "DFII10":  ("10Y real yield (TIPS)",      "%"),
    "T10Y2Y":  ("10s2s curve slope",          "%"),
    "T10YIE":  ("10Y breakeven inflation",    "%"),
    "DTWEXBGS":("Broad USD (trade-weighted)", "idx"),
    "VIXCLS":  ("VIX",                        ""),
    "SOFR":    ("Secured Overnight Funding",  "%"),
}


def fetch_series(sid: str) -> list[tuple[str, float]]:
    r = requests.get(FRED_CSV_URL.format(series=sid),
                     timeout=30,
                     headers={"User-Agent": "ai-trading-fund/1.0"})
    r.raise_for_status()
    rows: list[tuple[str, float]] = []
    text = r.text
    for line in text.splitlines()[1:]:  # skip header
        parts = line.split(",")
        if len(parts) < 2:
            continue
        date, val = parts[0], parts[1]
        try:
            rows.append((date, float(val)))
        except ValueError:
            continue   # FRED uses '.' for missing
    return rows


def summarize(sid: str, rows: list[tuple[str, float]]) -> dict:
    if not rows:
        return {"series": sid, "level": None, "as_of": None,
                "delta_5d": None, "delta_20d": None}
    as_of, level = rows[-1]
    def _delta(n: int) -> float | None:
        if len(rows) <= n:
            return None
        return level - rows[-1 - n][1]
    return {
        "series": sid,
        "level": level,
        "as_of": as_of,
        "delta_5d": _delta(5),
        "delta_20d": _delta(20),
        "label": SERIES[sid][0],
        "unit": SERIES[sid][1],
    }


def write_outputs(summaries: list[dict]) -> None:
    out_dir = _HERE / "vault" / "_meta"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "macro_levels.json"
    md_path = out_dir / "macro_levels.md"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "fred.stlouisfed.org",
        "series": summaries,
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    L = ["---", "type: macro_levels",
         f"generated_at: {payload['generated_at']}",
         "---", "",
         "# Macro levels — auto-fetched from FRED",
         "",
         "Live regime context for the agent preambles. Updated daily.",
         "",
         "| Series | Label | As of | Level | Δ 5d | Δ 20d |",
         "|---|---|---|---:|---:|---:|"]
    for s in summaries:
        if s["level"] is None:
            L.append(f"| {s['series']} | {s.get('label','')} | (no data) | — | — | — |")
            continue
        d5 = f"{s['delta_5d']:+.3f}" if s["delta_5d"] is not None else "—"
        d20 = f"{s['delta_20d']:+.3f}" if s["delta_20d"] is not None else "—"
        unit = s.get("unit", "")
        suf = f" {unit}" if unit else ""
        L.append(f"| {s['series']} | {s['label']} | {s['as_of']} | "
                 f"{s['level']:.3f}{suf} | {d5} | {d20} |")

    L += ["",
          "## Implications for `gap_fill` Treasury edge",
          "",
          "- **DGS10 trend (5d / 20d)**: rising trend = directional regime "
          "= overnight gaps more likely to extend, not fade. Recommend "
          "Risk Manager lean toward smaller size on long fades when 5d delta > +0.10%.",
          "- **DFII10 (real yield)**: aggressive moves in real yields "
          "shift Treasury demand sharply. >0.10% 5d delta = elevated risk "
          "for gap_fill across the curve.",
          "- **VIX**: elevated equity vol (>25) historically coincides with "
          "rates futures gap-extension regimes. Threshold for gap_fill caution: VIX > 20.",
          "- **SOFR vs IORB**: if SOFR drifting above IORB indicates "
          "money-market stress; ZT/ZF gap_fill especially exposed."]
    md_path.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"Wrote {json_path.relative_to(_HERE)}")
    print(f"Wrote {md_path.relative_to(_HERE)}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--print", dest="do_print", action="store_true")
    args = p.parse_args()

    summaries: list[dict] = []
    for sid in SERIES:
        try:
            rows = fetch_series(sid)
            summaries.append(summarize(sid, rows))
            level = summaries[-1]["level"]
            print(f"  {sid:10s}  level={level if level is not None else 'N/A'}")
        except Exception as e:
            print(f"  {sid:10s}  ERROR {type(e).__name__}: {e}", file=sys.stderr)
            summaries.append({"series": sid, "level": None, "as_of": None,
                              "delta_5d": None, "delta_20d": None,
                              "label": SERIES[sid][0],
                              "unit": SERIES[sid][1],
                              "error": str(e)[:200]})

    write_outputs(summaries)
    if args.do_print:
        for s in summaries:
            if s["level"] is None:
                continue
            print(f"  {s['series']:10s}  {s['as_of']}  {s['level']:.3f} "
                  f"({s['label']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
