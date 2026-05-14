"""Walk-forward validation for the 4 MGC cells added 2026-05-13 evening.

CELLS UNDER TEST (live_allowlist, experimental=True):
  - narrow_range_break MGC Asian long
  - narrow_range_break MGC Asian short
  - fair_value_gap_tuned MGC Asian short
  - inside_bar_break MGC PostClose long

BAR SOURCE: GC=F via yfinance (full-size Gold futures). Per the existing
walk_forward_firing_strategies pattern: "Micros use the full-size
underlying; strategies are price-pattern-based so signals transfer."
The microstructure differences between MGC and GC (lower volume on
MGC, slightly wider spreads) are real but should NOT change the
direction-of-edge of price-pattern strategies. Shadow-mode fills via
brain_signaler + shadow_trade_resolver will accumulate MGC-specific
microstructure data over time; this walk-forward is the cold-start
prior so the cells have OOS stats from day one.

OUTPUT:
  - Updates state/strategy_validation.json:cells under the keys
      narrow_range_break|MGC|Asian|long
      narrow_range_break|MGC|Asian|short
      fair_value_gap_tuned|MGC|Asian|short
      inside_bar_break|MGC|PostClose|long
    with `last_oos: {n, hit, e, t}` populated.
  - Writes a per-run markdown report to vault/research/backtests/.

PROMOTION RULE (from CLAUDE.md):
  Cells with n>=25 AND t>=1.5 AND E>0 OOS qualify. Anything below stays
  experimental: true in the allowlist.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, stdev

import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.backtest import strategies as strats  # noqa: E402
from tools.backtest.engine import backtest_strategy  # noqa: E402


VALIDATION_PATH = PROJECT_ROOT / "state" / "strategy_validation.json"

CELLS = [
    {"strategy": "narrow_range_break", "session": "Asian", "side": "long"},
    {"strategy": "narrow_range_break", "session": "Asian", "side": "short"},
    {"strategy": "fair_value_gap_tuned", "session": "Asian", "side": "short"},
    {"strategy": "inside_bar_break", "session": "PostClose", "side": "long"},
]

STRATEGY_FNS = {
    "narrow_range_break": strats.narrow_range_break,
    "fair_value_gap_tuned": strats.fair_value_gap_tuned,
    "inside_bar_break": strats.inside_bar_break,
}


def fetch_bars():
    """Fetch 60 days of 5m GC=F bars (proxy for MGC)."""
    df = yf.download("GC=F", period="60d", interval="5m",
                       progress=False, auto_adjust=False)
    if df.empty:
        return None
    if hasattr(df.columns, "get_level_values"):
        df.columns = df.columns.get_level_values(0)
    keep = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    df = df[keep].copy().dropna()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert("America/New_York")
    return df


def session_of(ts):
    """ET datetime → session bucket. Mirrors tools/brain_logic.session_now_utc."""
    h = ts.hour + ts.minute / 60.0
    if 9.5 <= h < 16:    return "RTH"
    if 4 <= h < 9.5:     return "London"
    if 16 <= h < 20:     return "PostClose"
    return "Asian"


def collect_cell_trades(strat_fn, bars, session: str, side: str):
    """Run strategy on bars, filter to (session, side) cell."""
    try:
        result = backtest_strategy(strat_fn, bars, symbol="MGC", params={})
    except Exception as exc:
        return [], str(exc)
    rows = []
    for t in result.trades:
        if t.is_open:
            continue
        et = t.entry_date
        if et.tz is None:
            et = et.tz_localize("UTC").tz_convert("America/New_York")
        else:
            et = et.tz_convert("America/New_York")
        if session_of(et) != session:
            continue
        if t.side != side:
            continue
        rows.append({"entry_et": et, "r": t.r_multiple})
    return rows, None


def stats(rows):
    n = len(rows)
    if n == 0:
        return None
    rs = [r["r"] for r in rows]
    hit = sum(1 for r in rs if r > 0) / n
    e = mean(rs)
    sd = stdev(rs) if n > 1 else 0
    t = (e / (sd / (n ** 0.5))) if (sd > 0 and n > 1) else 0
    return {"n": n, "hit": round(hit, 3), "e": round(e, 3), "t": round(t, 3)}


def split_at(rows, cutoff):
    return ([r for r in rows if r["entry_et"] < cutoff],
            [r for r in rows if r["entry_et"] >= cutoff])


def fmt(s):
    if s is None:
        return "(empty)"
    return f"n={s['n']:>4} hit={s['hit']*100:>5.1f}% E={s['e']:>+5.2f}R t={s['t']:>+5.2f}"


def passes_promotion(s_oos):
    """CLAUDE.md rule: n>=25 AND t>=1.5 AND E>0."""
    if s_oos is None:
        return False
    return s_oos["n"] >= 25 and s_oos["t"] >= 1.5 and s_oos["e"] > 0


def main():
    ts = datetime.now(timezone.utc)
    print(f"=== MGC WALK-FORWARD VALIDATION — {ts:%Y-%m-%d %H:%M UTC} ===\n")
    print("Bar source: GC=F via yfinance (60d, 5m). MGC microstructure")
    print("differences are acknowledged; this is a cold-start prior.\n")

    bars = fetch_bars()
    if bars is None or len(bars) < 100:
        print("BARS FETCH FAILED — aborting")
        return 1
    print(f"Bars: {len(bars)} [{bars.index[0]:%Y-%m-%d} → {bars.index[-1]:%Y-%m-%d}]")

    # 75/25 train/OOS split
    span = bars.index[-1] - bars.index[0]
    cutoff = bars.index[-1] - span * 0.25
    print(f"OOS cutoff: {cutoff:%Y-%m-%d %H:%M}\n")

    L = ["---", "type: walk_forward_mgc_cells",
         f"date: {ts.isoformat()}",
         f"bar_source: GC=F yfinance proxy",
         f"cutoff: {cutoff}", "---", "",
         "# MGC walk-forward validation",
         "",
         "4 MGC cells added 2026-05-13 evening as shadow mirrors of GC parents.",
         "Walk-forward uses GC=F bars as proxy (microstructure differences",
         "acknowledged).",
         "",
         f"Bars: {len(bars)} | OOS cutoff: {cutoff:%Y-%m-%d %H:%M ET}",
         "",
         "| Strategy | Session | Side | Train | OOS | Pass | Action |",
         "|---|---|---|---|---|---|---|"]

    # Read current validation file
    sv = json.loads(VALIDATION_PATH.read_text(encoding="utf-8"))
    cells_dict = sv.setdefault("cells", {})

    promoted: list[str] = []
    held_shadow: list[str] = []

    for cell in CELLS:
        strat = cell["strategy"]
        session = cell["session"]
        side = cell["side"]
        key = f"{strat}|MGC|{session}|{side}"

        fn = STRATEGY_FNS[strat]
        rows, err = collect_cell_trades(fn, bars, session, side)
        if err:
            print(f"  {key}: ERR — {err}")
            L.append(f"| {strat} | {session} | {side} | err | err | ✗ | err: {err[:50]} |")
            continue

        train, test = split_at(rows, cutoff)
        s_tr, s_te = stats(train), stats(test)
        passes = passes_promotion(s_te)
        action = "PROMOTE → experimental=false" if passes else "hold shadow"
        if passes:
            promoted.append(key)
        else:
            held_shadow.append(key)

        print(f"  {key}:")
        print(f"    TRAIN: {fmt(s_tr)}")
        print(f"    OOS:   {fmt(s_te)}  → {action}")

        # Write OOS stats to cells dict
        cells_dict[key] = {
            "status": "live" if passes else "shadow",
            "consecutive_passes": 1 if passes else 0,
            "consecutive_fails": 0 if passes else 1,
            "last_seen": ts.strftime("%Y-%m-%d"),
            "last_oos": s_te or {"n": 0, "hit": 0.0, "e": 0.0, "t": 0.0},
            "bar_source": "GC=F_yfinance_proxy",
            "validated_at": ts.isoformat(timespec="seconds"),
        }

        L.append(f"| {strat} | {session} | {side} | {fmt(s_tr)} | {fmt(s_te)} | "
                 f"{'✓' if passes else '✗'} | {action} |")

    # Persist updated validation file
    sv["cells"] = cells_dict
    VALIDATION_PATH.write_text(json.dumps(sv, indent=2), encoding="utf-8")
    print(f"\nUpdated {VALIDATION_PATH.relative_to(PROJECT_ROOT)}")

    # Summary
    L += ["", "## Promotion summary", ""]
    if promoted:
        L.append("**Promoted to live (experimental=false candidates):**")
        for k in promoted:
            L.append(f"- `{k}`")
    else:
        L.append("**No cells passed promotion gate** (n≥25 AND t≥1.5 AND E>0).")
    if held_shadow:
        L += ["", "**Held in shadow:**"]
        for k in held_shadow:
            L.append(f"- `{k}`")

    L += ["", "## Note on bar source", "",
          "GC=F was used as the bar proxy because yfinance does not surface",
          "an MGC-specific micro-contract series with sufficient history.",
          "This is a known limitation. Live shadow_trade fills will provide",
          "the MGC-specific microstructure validation over the next 2-5",
          "sessions; this walk-forward serves only as the cold-start prior."]

    out = PROJECT_ROOT / "vault" / "research" / "backtests"
    out.mkdir(parents=True, exist_ok=True)
    md_path = out / f"{ts:%Y-%m-%d_%H%M}_mgc_cells_walk_forward.md"
    md_path.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"Report: {md_path.relative_to(PROJECT_ROOT)}")

    # If any promoted, also flip experimental flag in live_allowlist
    if promoted:
        allowlist = sv.get("live_allowlist", [])
        flipped = []
        for entry in allowlist:
            if entry.get("symbol") != "MGC":
                continue
            key = (f"{entry.get('strategy')}|MGC|"
                     f"{entry.get('session')}|{entry.get('side')}")
            if key in promoted and entry.get("experimental"):
                entry["experimental"] = False
                entry["promoted_at"] = ts.isoformat(timespec="seconds")
                flipped.append(key)
        if flipped:
            sv["live_allowlist"] = allowlist
            VALIDATION_PATH.write_text(json.dumps(sv, indent=2), encoding="utf-8")
            print(f"\nFlipped experimental=false on {len(flipped)} MGC cell(s):")
            for k in flipped:
                print(f"  {k}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
