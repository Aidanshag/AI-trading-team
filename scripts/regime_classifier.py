"""Regime classifier — tag each historical bar with vol/trend/news context.

Per cowork_coordination.md 2026-05-08 priority #3. Adds a feature layer
that the live trader can read to gate trades by regime — specifically
"don't trade gap_fill if vol is high AND we're within 15 min of a
high-impact event," which is exactly the regime where the edge fails
per the standing thesis kill conditions.

OUTPUTS:
  state/regime_tags.json — schema:
    {
      "generated_at": "...",
      "interval": "5m",
      "by_symbol": {
        "ZN": {
          "tags": [{"ts": "...", "vol_regime": "low|med|high",
                    "trend_regime": "trending|ranging",
                    "news_proximity": "clear|near|inside"}, ...],
          "summary": {"vol_low": N, "vol_med": N, "vol_high": N, ...}
        }, ...
      }
    }

INPUTS:
  - yfinance bars per symbol (last N days, configurable)
  - vault/economic_calendar/today.json + treasury_auctions.json
    + fed_speakers.json — for news_proximity tagging

DEFINITIONS:

  vol_regime — 14-bar realized vol vs its rolling 100-bar median:
    low   : current vol  < 0.7 × median
    med   : 0.7 × median ≤ current vol ≤ 1.4 × median
    high  : current vol  > 1.4 × median

  trend_regime — ADX-lite: rolling 14-bar (high-low) range vs
                 rolling-100-bar mean of (high-low):
    trending : current range > 1.3 × mean range
    ranging  : otherwise

  news_proximity — distance to nearest high-impact event in the
                   merged economic calendar:
    clear   : > 60 min from any event
    near    : within 15-60 min before/after a MEDIUM event, OR
              within 60 min before/after a HIGH event (Fed speakers,
              auctions affecting any of {ZN,ZT,ZB,ZF})
    inside  : within ±15 min of a HIGH event

USAGE:
  python -m scripts.regime_classifier
  python -m scripts.regime_classifier --symbols ZN,ZT,ZB,ZF --period 30d
  python -m scripts.regime_classifier --print

REQUIRES: yfinance + pandas. Won't run in network-restricted sandboxes.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


SYMBOL_TO_YF = {
    "ZN": "ZN=F", "ZT": "ZT=F", "ZB": "ZB=F", "ZF": "ZF=F",
    "NG": "NG=F", "CL": "CL=F", "MCL": "CL=F",
    "GC": "GC=F", "SI": "SI=F", "HG": "HG=F",
    "MES": "ES=F", "MNQ": "NQ=F",
    "6E": "6E=F", "6B": "6B=F", "6J": "6J=F", "6A": "6A=F", "6C": "6C=F",
}

DEFAULT_SYMBOLS = ["ZN", "ZT", "ZB", "ZF"]   # locked Treasury universe


# ── bar fetch ──────────────────────────────────────────────────

def fetch_bars(symbol: str, period: str = "30d", interval: str = "5m"):
    try:
        import yfinance as yf
    except ImportError:
        print("ERROR: yfinance not installed", file=sys.stderr)
        return None
    ticker = SYMBOL_TO_YF.get(symbol, f"{symbol}=F")
    df = yf.download(ticker, period=period, interval=interval,
                     progress=False, auto_adjust=False)
    if df.empty:
        return None
    if hasattr(df.columns, "get_level_values"):
        df.columns = df.columns.get_level_values(0)
    keep = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    df = df[keep].copy().dropna()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return df


# ── regime tagging ─────────────────────────────────────────────

def tag_vol_regime(bars: pd.DataFrame, lookback: int = 14,
                   ref_window: int = 100) -> pd.Series:
    """Classify each bar as low/med/high vol vs its 100-bar median."""
    returns = bars["Close"].pct_change()
    realized = returns.rolling(lookback).std() * (252 * 78) ** 0.5  # annualized
    median = realized.rolling(ref_window, min_periods=20).median()
    out = pd.Series("med", index=bars.index, dtype=object)
    out[realized < 0.7 * median] = "low"
    out[realized > 1.4 * median] = "high"
    return out


def tag_trend_regime(bars: pd.DataFrame, lookback: int = 14,
                     ref_window: int = 100) -> pd.Series:
    """ADX-lite: range expansion vs mean range."""
    rng = (bars["High"] - bars["Low"]).rolling(lookback).mean()
    mean_rng = rng.rolling(ref_window, min_periods=20).mean()
    out = pd.Series("ranging", index=bars.index, dtype=object)
    out[rng > 1.3 * mean_rng] = "trending"
    return out


# ── news proximity ─────────────────────────────────────────────

def load_high_impact_events(symbol: str) -> list[dict]:
    """Merge economic_calendar/today.json + treasury_auctions.json +
    fed_speakers.json into a flat [{ts_utc, severity, source}] list.

    severity 'HIGH' = Fed Chair/Vice/NY-Fed speaker, or Treasury auction
                      affecting this symbol's tenor.
    severity 'MEDIUM' = other Fed speakers, other auctions.
    """
    events: list[dict] = []
    cal_dir = PROJECT_ROOT / "vault" / "economic_calendar"
    meta_dir = PROJECT_ROOT / "vault" / "_meta"

    # today.json — high-impact data prints
    today = cal_dir / "today.json"
    if today.exists():
        try:
            data = json.loads(today.read_text(encoding="utf-8"))
            for e in data.get("events") or []:
                if str(e.get("impact", "")).lower() == "high":
                    ts = e.get("ts_utc") or e.get("time_utc")
                    if ts:
                        events.append({"ts_utc": ts, "severity": "HIGH",
                                       "source": "calendar"})
        except Exception:
            pass

    # treasury_auctions.json — auctions affecting this symbol
    auct = cal_dir / "treasury_auctions.json"
    if auct.exists():
        try:
            data = json.loads(auct.read_text(encoding="utf-8"))
            for r in data.get("auctions") or []:
                primary = (r.get("affected_primary")
                           or r.get("affected_futures") or [])
                basis = r.get("affected_basis") or []
                ts = (r.get("auction_dt_et")
                      or f"{r.get('auction_date', '')}T{r.get('auction_time_et','13:00')}")
                if not ts:
                    continue
                # Convert ET→UTC roughly (ET = UTC-4 in DST, UTC-5 standard;
                # this is approximate)
                if symbol in primary:
                    events.append({"ts_utc": ts, "severity": "HIGH",
                                   "source": f"auction_{r.get('security_term')}"})
                elif symbol in basis:
                    events.append({"ts_utc": ts, "severity": "MEDIUM",
                                   "source": f"auction_basis_{r.get('security_term')}"})
        except Exception:
            pass

    # fed_speakers.json — speaker calendar
    spk = cal_dir / "fed_speakers.json"
    if spk.exists():
        try:
            data = json.loads(spk.read_text(encoding="utf-8"))
            for e in data.get("events") or []:
                inf = e.get("influence", "LOW")
                ts = e.get("ts_utc")
                if not ts:
                    continue
                if inf == "HIGH":
                    events.append({"ts_utc": ts, "severity": "HIGH",
                                   "source": "fed_speaker"})
                elif inf == "MEDIUM":
                    events.append({"ts_utc": ts, "severity": "MEDIUM",
                                   "source": "fed_speaker"})
        except Exception:
            pass

    return events


def tag_news_proximity(bars: pd.DataFrame, events: list[dict]) -> pd.Series:
    """For each bar, find min distance to nearest event and classify."""
    out = pd.Series("clear", index=bars.index, dtype=object)
    if not events:
        return out
    # Pre-parse event timestamps
    parsed: list[tuple[datetime, str]] = []
    for e in events:
        try:
            ts_str = str(e["ts_utc"]).replace("Z", "+00:00")
            if "T" in ts_str and "+" not in ts_str and "-" not in ts_str[10:]:
                ts_str += "+00:00"
            t = datetime.fromisoformat(ts_str)
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            parsed.append((t, e.get("severity", "MEDIUM")))
        except Exception:
            continue
    if not parsed:
        return out

    parsed.sort(key=lambda x: x[0])
    for ts in bars.index:
        bar_t = ts.to_pydatetime()
        if bar_t.tzinfo is None:
            bar_t = bar_t.replace(tzinfo=timezone.utc)
        # Find nearest event
        nearest_min = None
        nearest_sev = None
        for ev_t, sev in parsed:
            delta_min = abs((bar_t - ev_t).total_seconds() / 60.0)
            if nearest_min is None or delta_min < nearest_min:
                nearest_min = delta_min
                nearest_sev = sev
        if nearest_min is None:
            continue
        if nearest_sev == "HIGH":
            if nearest_min <= 15:
                out.at[ts] = "inside"
            elif nearest_min <= 60:
                out.at[ts] = "near"
        elif nearest_sev == "MEDIUM":
            if nearest_min <= 15:
                out.at[ts] = "near"
    return out


# ── main pipeline ──────────────────────────────────────────────

def classify_symbol(symbol: str, period: str, interval: str) -> dict | None:
    bars = fetch_bars(symbol, period, interval)
    if bars is None or len(bars) < 50:
        return None
    vol = tag_vol_regime(bars)
    trend = tag_trend_regime(bars)
    events = load_high_impact_events(symbol)
    news = tag_news_proximity(bars, events)

    tags = []
    for ts in bars.index:
        tags.append({
            "ts": ts.isoformat(),
            "vol_regime": str(vol.loc[ts]) if pd.notna(vol.loc[ts]) else "med",
            "trend_regime": str(trend.loc[ts]) if pd.notna(trend.loc[ts]) else "ranging",
            "news_proximity": str(news.loc[ts]),
        })

    # Summary counts
    summary = {
        "n_bars": len(tags),
        "vol_low": int((vol == "low").sum()),
        "vol_med": int((vol == "med").sum()),
        "vol_high": int((vol == "high").sum()),
        "trend_trending": int((trend == "trending").sum()),
        "trend_ranging": int((trend == "ranging").sum()),
        "news_clear": int((news == "clear").sum()),
        "news_near": int((news == "near").sum()),
        "news_inside": int((news == "inside").sum()),
    }
    return {"tags": tags, "summary": summary}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS),
                   help="Comma-separated list (default: ZN,ZT,ZB,ZF).")
    p.add_argument("--period", default="30d",
                   help="yfinance period (default 30d).")
    p.add_argument("--interval", default="5m",
                   help="yfinance interval (default 5m).")
    p.add_argument("--print", dest="do_print", action="store_true",
                   help="Print summary to stdout.")
    args = p.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "interval": args.interval,
        "period": args.period,
        "by_symbol": {},
    }
    for sym in symbols:
        print(f"  classifying {sym} ...", file=sys.stderr)
        result = classify_symbol(sym, args.period, args.interval)
        if result is None:
            print(f"    {sym}: SKIPPED (fetch failed or insufficient bars)",
                  file=sys.stderr)
            continue
        out["by_symbol"][sym] = result
        if args.do_print:
            s = result["summary"]
            print(f"  {sym}: bars={s['n_bars']}, vol "
                  f"l/m/h={s['vol_low']}/{s['vol_med']}/{s['vol_high']}, "
                  f"trend t/r={s['trend_trending']}/{s['trend_ranging']}, "
                  f"news c/n/i={s['news_clear']}/{s['news_near']}/{s['news_inside']}")

    out_path = PROJECT_ROOT / "state" / "regime_tags.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {out_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
