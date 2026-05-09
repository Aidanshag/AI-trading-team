"""Compare yfinance bars vs Topstep bars for ZN over last 7 days.

If they match closely → yfinance backtest results are trustworthy.
If they diverge → we need to redo the backtest on Topstep bars.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.projectx_client import get_client  # noqa: E402


def fetch_topstep(symbol: str, days: int) -> pd.DataFrame:
    c = get_client()
    cid = c.front_month_contract_id(symbol)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    bars = c.get_bars(
        contract_id=cid,
        start_time=start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        end_time=end.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        unit=2, unit_number=5, limit=1000, live=False,
    )
    if not bars:
        return pd.DataFrame()
    df = pd.DataFrame(bars)
    df["t"] = pd.to_datetime(df["t"])
    df = df.set_index("t").rename(columns={
        "o": "Open", "h": "High", "l": "Low", "c": "Close", "v": "Volume"
    })
    df = df.sort_index()
    return df


def fetch_yfinance(symbol: str, days: int) -> pd.DataFrame:
    yf_map = {"ZN": "ZN=F", "ZB": "ZB=F", "ZT": "ZT=F", "ZF": "ZF=F"}
    df = yf.download(yf_map[symbol], period=f"{days}d", interval="5m",
                     progress=False, auto_adjust=False)
    if hasattr(df.columns, "get_level_values"):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return df


def main():
    print("=" * 72)
    print("YFINANCE vs TOPSTEP bar comparison — ZN, last 7 days, 5m bars")
    print("=" * 72)

    yf_df = fetch_yfinance("ZN", 7)
    ts_df = fetch_topstep("ZN", 7)

    print(f"\nyfinance: {len(yf_df)} bars, range {yf_df.index.min()} → {yf_df.index.max()}")
    print(f"topstep:  {len(ts_df)} bars, range {ts_df.index.min()} → {ts_df.index.max()}")

    # Align on common timestamps
    yf_df.index = yf_df.index.tz_convert("UTC").floor("min")
    ts_df.index = ts_df.index.tz_convert("UTC").floor("min")
    common_idx = yf_df.index.intersection(ts_df.index)
    print(f"\nCommon 5m timestamps: {len(common_idx)}")

    if len(common_idx) == 0:
        print("No overlap — cannot compare directly.")
        return

    yf_aligned = yf_df.loc[common_idx]
    ts_aligned = ts_df.loc[common_idx]

    # Per-bar diff
    diffs = pd.DataFrame({
        "yf_O": yf_aligned["Open"], "ts_O": ts_aligned["Open"],
        "yf_H": yf_aligned["High"], "ts_H": ts_aligned["High"],
        "yf_L": yf_aligned["Low"],  "ts_L": ts_aligned["Low"],
        "yf_C": yf_aligned["Close"],"ts_C": ts_aligned["Close"],
        "yf_V": yf_aligned["Volume"],"ts_V": ts_aligned["Volume"],
    })
    for col in ["O", "H", "L", "C"]:
        diffs[f"d{col}"] = (diffs[f"ts_{col}"] - diffs[f"yf_{col}"]).abs()

    print("\n=== Price agreement (absolute price difference per bar) ===")
    for col in ["O", "H", "L", "C"]:
        d = diffs[f"d{col}"]
        print(f"  {col}: mean={d.mean():.5f}  median={d.median():.5f}  "
              f"max={d.max():.5f}  exact_match={(d==0).sum()}/{len(d)}")

    # Tick-level comparison (ZN tick = 0.015625)
    tick = 0.015625
    print(f"\n=== Tick-level agreement (1 tick = {tick} = $15.625) ===")
    for col in ["O", "H", "L", "C"]:
        d = diffs[f"d{col}"] / tick
        print(f"  {col}: avg ticks off={d.mean():.2f}  max ticks off={d.max():.2f}  "
              f"within 1 tick={(d<=1).sum()}/{len(d)}  "
              f"within 0.5 tick={(d<=0.5).sum()}/{len(d)}")

    # Volume divergence
    vol_diff_pct = ((diffs["ts_V"] - diffs["yf_V"]).abs() / diffs["yf_V"].replace(0, 1)).clip(0, 5)
    print(f"\n=== Volume comparison ===")
    print(f"  yf median volume:  {diffs['yf_V'].median():.0f}")
    print(f"  ts median volume:  {diffs['ts_V'].median():.0f}")
    print(f"  volume divergence: median={vol_diff_pct.median()*100:.0f}%  "
          f"mean={vol_diff_pct.mean()*100:.0f}%")

    # Show a sample of the worst price disagreements
    print("\n=== 5 worst Close-price disagreements ===")
    worst = diffs.sort_values("dC", ascending=False).head(5)
    for ts, r in worst.iterrows():
        print(f"  {ts}  yf={r['yf_C']:.5f}  ts={r['ts_C']:.5f}  "
              f"diff={r['dC']*1/tick:+.1f} ticks")

    # Verdict
    print("\n" + "=" * 72)
    high_close_match = (diffs["dC"] / tick <= 0.5).sum() / len(diffs)
    if high_close_match >= 0.95:
        print(f"VERDICT: bars agree closely ({high_close_match*100:.0f}% of closes within 0.5 tick).")
        print("yfinance backtest results are trustworthy for live extrapolation.")
    elif high_close_match >= 0.80:
        print(f"VERDICT: bars mostly agree ({high_close_match*100:.0f}% within 0.5 tick) "
              f"but some divergence — flag for tracking.")
    else:
        print(f"VERDICT: bars disagree substantially ({high_close_match*100:.0f}% within 0.5 tick).")
        print("Consider redoing backtest on Topstep bars before deploy.")
    print("=" * 72)


if __name__ == "__main__":
    main()
