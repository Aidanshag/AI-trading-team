"""calibrate_regime_filters — verify each live_allowlist cell's regime_filter
matches the actual majority regime in its historical session bars.

Output:
  - vault/research/analysis/YYYY-MM-DD_regime_calibration.md (human-readable
    report with a row per cell: configured filter vs observed distribution)
  - state/regime_calibration_proposals.json (machine-readable proposed
    regime_filter changes — REVIEW BEFORE APPLYING, no auto-apply)

Method:
  1. Load every cell from state/strategy_validation.json:live_allowlist
  2. For each (symbol, session): load the recent 1-min bars from
     state/bars/<sym>_1m_*.parquet, filter to that session window
  3. Run current_regime() on rolling 60-bar windows; record trending vs
     ranging percentages
  4. Compare to the cell's regime_filter.trend_regime — flag mismatches

Mismatch cases:
  - Cell expects 'trending', observed <30% trending → over-restrictive
  - Cell expects 'ranging', observed <30% ranging → over-restrictive
  - Cell has no filter but observed >70% of one regime → could tighten

This is a DIAGNOSTIC script. It writes proposed changes but never modifies
state/strategy_validation.json. User reviews the proposals doc + decides.
"""
from __future__ import annotations

import glob
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

ALLOWLIST_PATH = ROOT / "state" / "strategy_validation.json"
BARS_DIR = ROOT / "state" / "bars"
REPORT_DIR = ROOT / "vault" / "research" / "analysis"
PROPOSALS_PATH = ROOT / "state" / "regime_calibration_proposals.json"


# Session window definitions (UTC hours)
SESSION_WINDOWS = {
    "Asian":     (22, 6),    # 22:00-06:00 UTC = 17:00 ET prev day - 01:00 ET (Tokyo open)
    "London":    (6, 13),    # 06:00-13:00 UTC = 02:00-09:00 ET (London open)
    "RTH":       (13, 20),   # 13:00-20:00 UTC = 08:00-15:00 ET (US RTH)
    "PostClose": (20, 22),   # 20:00-22:00 UTC = 15:00-17:00 ET (US post-close)
}


def load_symbol_bars(symbol: str, max_files: int = 30) -> pd.DataFrame | None:
    """Load all available 1-min bars for `symbol`, concat, return DataFrame
    with UTC index. Returns None if no files."""
    pattern = str(BARS_DIR / f"{symbol}_1m_*.parquet")
    files = sorted(glob.glob(pattern))[-max_files:]
    if not files:
        return None
    frames = []
    for f in files:
        try:
            df = pd.read_parquet(f)
            frames.append(df)
        except Exception:
            continue
    if not frames:
        return None
    out = pd.concat(frames, ignore_index=False)
    # Ensure UTC index
    if hasattr(out.index, "tz_localize"):
        try:
            if out.index.tz is None:
                out.index = out.index.tz_localize("UTC")
            else:
                out.index = out.index.tz_convert("UTC")
        except Exception:
            pass
    out = out.sort_index()
    return out


def filter_to_session(df: pd.DataFrame, session: str) -> pd.DataFrame:
    """Slice df to rows whose UTC hour is inside the session window."""
    if session not in SESSION_WINDOWS:
        return df
    start, end = SESSION_WINDOWS[session]
    if not hasattr(df.index, "hour"):
        return df
    hours = df.index.hour
    if start < end:
        mask = (hours >= start) & (hours < end)
    else:  # wraps midnight
        mask = (hours >= start) | (hours < end)
    return df[mask]


def classify_regime_distribution(df: pd.DataFrame,
                                   window_bars: int = 60,
                                   step_bars: int = 10) -> dict:
    """Walk through bars in rolling windows; classify each window's regime;
    return {'trending': n, 'ranging': n, 'unclear': n, 'total': n}.

    Returns empty if not enough data.
    """
    from tools.brain_logic import current_regime
    counts = {"trending": 0, "ranging": 0, "unclear": 0, "total": 0}
    if df is None or len(df) < window_bars + 10:
        return counts
    for i in range(window_bars, len(df) - 1, step_bars):
        window = df.iloc[i - window_bars:i]
        try:
            reg = current_regime(window)
            trend_reg = reg.get("trend_regime", "unclear") if isinstance(reg, dict) else "unclear"
        except Exception:
            trend_reg = "unclear"
        if trend_reg not in counts:
            counts[trend_reg] = 0
        counts[trend_reg] += 1
        counts["total"] += 1
    return counts


def evaluate_cell(cell: dict) -> dict:
    """For one cell: load bars, slice to session, classify, compare to filter."""
    symbol = cell.get("symbol", "")
    session = cell.get("session", "")
    rf = cell.get("regime_filter") or {}
    configured = rf.get("trend_regime")  # list of allowed regimes, or None
    bars = load_symbol_bars(symbol)
    if bars is None:
        return {"cell": cell, "status": "no_bars", "observed": {}}
    sess_bars = filter_to_session(bars, session)
    dist = classify_regime_distribution(sess_bars)
    if dist["total"] == 0:
        return {"cell": cell, "status": "insufficient_session_bars",
                "observed": dist}
    pct_trending = dist["trending"] / dist["total"] if dist["total"] else 0
    pct_ranging = dist["ranging"] / dist["total"] if dist["total"] else 0
    verdict = "ok"
    rec = None
    if configured is None:
        # No filter — recommend one if heavily skewed
        if pct_trending > 0.70:
            verdict = "could_tighten"
            rec = {"trend_regime": ["trending"]}
        elif pct_ranging > 0.70:
            verdict = "could_tighten"
            rec = {"trend_regime": ["ranging"]}
    else:
        # Check if configured filter sees enough relevant bars
        configured_pct = sum(
            dist.get(r, 0) / dist["total"] for r in configured
        )
        if configured_pct < 0.15:
            verdict = "over_restrictive"
            # Suggest the OBSERVED majority
            if pct_trending > pct_ranging:
                rec = {"trend_regime": ["trending"]}
            else:
                rec = {"trend_regime": ["ranging"]}
    return {
        "cell": cell, "status": verdict,
        "observed": {
            "trending_pct": round(pct_trending, 2),
            "ranging_pct": round(pct_ranging, 2),
            "total_windows": dist["total"],
        },
        "configured": configured,
        "recommendation": rec,
    }


def main() -> int:
    if not ALLOWLIST_PATH.exists():
        print(f"ABORT: {ALLOWLIST_PATH} missing")
        return 2
    with ALLOWLIST_PATH.open() as f:
        data = json.load(f)
    cells = data.get("live_allowlist", [])
    print(f"Calibrating {len(cells)} cells against historical bars...")
    results = []
    for c in cells:
        r = evaluate_cell(c)
        results.append(r)
        sym = c.get("symbol")
        strat = c.get("strategy")
        sess = c.get("session")
        side = c.get("side")
        print(f"  {sym}/{strat}/{sess}/{side}: {r['status']}")

    # Write proposals (machine-readable)
    proposals = [r for r in results if r.get("recommendation")]
    PROPOSALS_PATH.write_text(
        json.dumps({
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "total_cells": len(cells),
            "proposals": [
                {"cell_id": f"{r['cell'].get('symbol')}/{r['cell'].get('strategy')}/"
                            f"{r['cell'].get('session')}/{r['cell'].get('side')}",
                 "current": r.get("configured"),
                 "recommend": r["recommendation"],
                 "reason": r["status"],
                 "observed": r["observed"]}
                for r in proposals
            ],
        }, indent=2),
        encoding="utf-8",
    )

    # Write human-readable report
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    report_path = REPORT_DIR / f"{today}_regime_calibration.md"
    lines = [
        "---", "type: analysis", f"date: {today}",
        "purpose: Per-cell regime_filter calibration — round 1", "---", "",
        "# Per-cell regime calibration — round 1",
        "",
        f"Generated by `scripts/calibrate_regime_filters.py` against "
        f"`state/bars/*_1m_*.parquet`.",
        f"Cells analyzed: **{len(cells)}**. Proposals: **{len(proposals)}**.",
        "",
        "Status meanings:",
        "- `ok` — configured filter matches observed regime distribution",
        "- `over_restrictive` — configured regime represents <15% of session windows",
        "- `could_tighten` — no filter, but observed >70% one regime",
        "- `no_bars` — no historical bars for this symbol",
        "- `insufficient_session_bars` — bars exist but not enough in session window",
        "",
        "| Symbol | Strategy | Session | Side | Configured | Observed | Status | Recommend |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        c = r["cell"]
        obs = r["observed"]
        rec = r.get("recommendation") or "—"
        if obs.get("total_windows", 0) > 0:
            obs_str = (f"trend={obs.get('trending_pct',0)*100:.0f}% "
                        f"range={obs.get('ranging_pct',0)*100:.0f}% "
                        f"n={obs.get('total_windows',0)}")
        else:
            obs_str = "no data"
        configured = r.get("configured") or "—"
        lines.append(
            f"| {c.get('symbol','')} | {c.get('strategy','')} | "
            f"{c.get('session','')} | {c.get('side','')} | {configured} | "
            f"{obs_str} | {r['status']} | {rec} |"
        )
    lines += [
        "",
        "## How to apply",
        "",
        "1. Review `state/regime_calibration_proposals.json` for the machine-readable diffs.",
        "2. Apply proposed regime_filter changes manually to `state/strategy_validation.json:live_allowlist` after manual review.",
        "3. Re-run this script in 1-2 weeks to verify calibration holds.",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nReport: {report_path}")
    print(f"Proposals: {PROPOSALS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
