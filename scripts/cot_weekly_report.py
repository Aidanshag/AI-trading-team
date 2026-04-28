"""Weekly COT positioning report generator.

Runs after CFTC's Friday 3:30 PM ET release. Pulls 2 years of COT data
for every authorized symbol, computes the 52-week percentile of net
speculator positioning, writes a single Markdown summary into
vault/flow/cot_{date}.md for the Flow Analyst to read on next wake.

Usage (manual):  python -m scripts.cot_weekly_report
Usage (cron):    Friday 22:00 UTC (16:00 CT, 60 min after release)
"""
from __future__ import annotations

import os
import sys
import warnings
from datetime import date, timedelta
from pathlib import Path

warnings.filterwarnings("ignore")

# Load .env so cache dir + any future keys resolve
_env = Path(".env")
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

from tools.fundamentals.cftc import (
    SYMBOL_TO_COT,
    MARKET_PATTERNS,
    commitments_for_symbol,
    speculator_net,
)


def _percentile_of_last(series, lookback: int = 104) -> float | None:
    """Where does the most recent value sit in the trailing window?
    Returns 0.0 (window low) to 1.0 (window high), or None if insufficient.
    """
    s = series.dropna()
    if len(s) < 20:
        return None
    window = s.iloc[-lookback:] if len(s) >= lookback else s
    rng = window.max() - window.min()
    if rng == 0:
        return 0.5
    return float((window.iloc[-1] - window.min()) / rng)


def _classify(pct: float | None) -> tuple[str, str]:
    """Return (label, emoji-like marker) for the percentile."""
    if pct is None:
        return ("(insufficient history)", " ")
    if pct >= 0.90:
        return ("CROWDED LONG — fade rallies", "[LL]")
    if pct >= 0.75:
        return ("Net long — elevated", "[ L]")
    if pct >= 0.55:
        return ("Mild long bias", "[ +]")
    if pct >= 0.45:
        return ("Neutral / range", "[ ~]")
    if pct >= 0.25:
        return ("Mild short bias", "[ -]")
    if pct >= 0.10:
        return ("Net short — elevated", "[ S]")
    return ("CROWDED SHORT — fade declines", "[SS]")


def _build_report(start: str, end: str) -> tuple[str, dict]:
    """Run all symbols, return (markdown_body, stats_dict)."""
    rows: list[dict] = []
    extremes_long: list[dict] = []
    extremes_short: list[dict] = []
    misses: list[str] = []

    for sym in sorted(SYMBOL_TO_COT):
        market_key, report = SYMBOL_TO_COT[sym]
        try:
            df = commitments_for_symbol(sym, start, end)
        except Exception as e:
            misses.append(f"{sym}: {type(e).__name__}: {str(e)[:60]}")
            continue
        if df.empty:
            misses.append(f"{sym}: empty response")
            continue
        net = speculator_net(df, report)
        if net.empty:
            misses.append(f"{sym}: no speculator columns")
            continue
        pct = _percentile_of_last(net, lookback=104)
        latest_net = int(net.iloc[-1]) if not net.empty else 0
        as_of = df.index[-1].date().isoformat() if len(df) else "?"
        label, marker = _classify(pct)
        row = {
            "symbol": sym,
            "market": MARKET_PATTERNS.get(market_key, market_key),
            "report": report,
            "as_of": as_of,
            "net": latest_net,
            "pct_52w": pct,
            "label": label,
            "marker": marker,
        }
        rows.append(row)
        if pct is not None and pct >= 0.90:
            extremes_long.append(row)
        if pct is not None and pct <= 0.10:
            extremes_short.append(row)

    # Build markdown
    today = date.today().isoformat()
    lines: list[str] = []
    lines.append("---")
    lines.append(f"date: {today}")
    lines.append("type: cot_positioning_report")
    lines.append("source: CFTC Commitments of Traders (free public feed)")
    lines.append("---")
    lines.append("")
    lines.append(f"# COT Positioning Report — {today}")
    lines.append("")
    lines.append(
        "Speculator (Managed Money / Leveraged Funds) net positioning per "
        "authorized symbol. Percentile is over the trailing 104-week window. "
        "Above 0.90 = crowded long (mean-revert risk); below 0.10 = crowded "
        "short. The Flow Analyst should weight extremes heavily in setup "
        "filtering."
    )
    lines.append("")

    if extremes_long or extremes_short:
        lines.append("## Positioning Extremes")
        lines.append("")
        if extremes_long:
            lines.append("### Crowded LONG (≥ 90th percentile, 2-yr) — fade-rally candidates")
            lines.append("")
            lines.append("| Sym | As of | Net | Pct | Market |")
            lines.append("|---|---|---:|---:|---|")
            for r in sorted(extremes_long, key=lambda x: -x["pct_52w"]):
                lines.append(
                    f"| {r['symbol']} | {r['as_of']} | {r['net']:+,} "
                    f"| {r['pct_52w']*100:.0f} | {r['market'][:50]} |"
                )
            lines.append("")
        if extremes_short:
            lines.append("### Crowded SHORT (≤ 10th percentile, 2-yr) — fade-decline candidates")
            lines.append("")
            lines.append("| Sym | As of | Net | Pct | Market |")
            lines.append("|---|---|---:|---:|---|")
            for r in sorted(extremes_short, key=lambda x: x["pct_52w"]):
                lines.append(
                    f"| {r['symbol']} | {r['as_of']} | {r['net']:+,} "
                    f"| {r['pct_52w']*100:.0f} | {r['market'][:50]} |"
                )
            lines.append("")
    else:
        lines.append("## Positioning Extremes")
        lines.append("")
        lines.append("_None this week — no symbol above 0.90 or below 0.10 percentile._")
        lines.append("")

    lines.append("## Full positioning table")
    lines.append("")
    lines.append("| Sym | Pct | Net | As of | Read |")
    lines.append("|---|---:|---:|---|---|")
    for r in sorted(rows, key=lambda x: -(x["pct_52w"] or 0)):
        pct_str = f"{r['pct_52w']*100:.0f}" if r["pct_52w"] is not None else "—"
        lines.append(
            f"| {r['symbol']} | {pct_str} | {r['net']:+,} "
            f"| {r['as_of']} | {r['marker']} {r['label']} |"
        )
    lines.append("")

    if misses:
        lines.append("## Symbols with no COT data this week")
        lines.append("")
        for m in misses:
            lines.append(f"- {m}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "_Auto-generated by `scripts/cot_weekly_report.py`. CFTC publishes "
        "weekly Friday 3:30 PM ET; positions reflect the prior Tuesday's close._"
    )

    stats = {
        "n_symbols": len(rows),
        "n_extremes_long": len(extremes_long),
        "n_extremes_short": len(extremes_short),
        "n_misses": len(misses),
    }
    return ("\n".join(lines), stats)


def main() -> int:
    today = date.today()
    # Pull 2.5 years to ensure rolling 104-week percentile is well-populated
    start = (today - timedelta(days=int(365 * 2.5))).isoformat()
    end = today.isoformat()

    print(f"Pulling COT for {len(SYMBOL_TO_COT)} symbols, {start} -> {end}...")
    body, stats = _build_report(start, end)

    out_dir = Path("vault/flow")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"cot_{today.isoformat()}.md"
    out_path.write_text(body, encoding="utf-8")

    print()
    print(f"Symbols processed:  {stats['n_symbols']}")
    print(f"Crowded LONG  (>= 90th pct): {stats['n_extremes_long']}")
    print(f"Crowded SHORT (<= 10th pct): {stats['n_extremes_short']}")
    print(f"Misses (no data):           {stats['n_misses']}")
    print()
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
