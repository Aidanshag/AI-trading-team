"""Slippage tracker — measure actual fill slippage per cell.

Reads filled orders from state/fund.db, compares intent prices (limit_price,
stop_price) to actual fill prices, computes signed slippage, aggregates per
strategy × symbol × session × side cell, writes report to vault.

Adverse slippage = positive number.
Favorable slippage = negative number.
"""
from __future__ import annotations

import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Symbol tick economics for converting price slip → tick count
TICK_BY_SYMBOL = {
    "ZN": 0.015625, "ZB": 0.03125, "ZT": 0.0078125, "ZF": 0.0078125,
    "NG": 0.001, "GC": 0.10, "6E": 0.00005, "MES": 0.25, "MNQ": 0.25, "MCL": 0.01,
    "ES": 0.25, "NQ": 0.25, "CL": 0.01,
}


def session_for_hour(h: int) -> str:
    if 18 <= h or h < 4: return "Asian"
    if 4 <= h < 9: return "London"
    if 9 <= h < 16: return "RTH"
    return "PostClose"


def main() -> int:
    db_path = PROJECT_ROOT / "state" / "fund.db"
    if not db_path.exists():
        print(f"ERROR: {db_path} not found")
        return 1

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT client_order_id, symbol, side, order_type, limit_price, stop_price,
                  ts_proposed, ts_filled, avg_fill_price, qty, status, agent
           FROM orders
           WHERE agent = 'live_trader'
             AND avg_fill_price IS NOT NULL
             AND avg_fill_price > 0
           ORDER BY ts_proposed DESC""",
    ).fetchall()

    if not rows:
        print("No filled live_trader orders found yet.")
        print("(This is expected before the first live fills land.)")
        print(f"Run again after Sunday's session to see per-cell slippage.")
        return 0

    print("=" * 78)
    print(f"SLIPPAGE TRACKER — {len(rows)} filled live_trader orders")
    print("=" * 78)

    by_cell: dict[tuple, list[dict]] = defaultdict(list)

    for r in rows:
        sym = r["symbol"]
        tick = TICK_BY_SYMBOL.get(sym)
        if not tick:
            continue
        # Pick intent price: stop legs use stop_price; entries/targets use limit_price
        cid = r["client_order_id"] or ""
        if cid.endswith("_stop"):
            leg = "stop"
            intent = r["stop_price"]
        elif cid.endswith("_target"):
            leg = "target"
            intent = r["limit_price"]
        else:
            leg = "entry"
            intent = r["limit_price"]
        if intent is None or intent <= 0:
            continue
        actual = r["avg_fill_price"]
        side = (r["side"] or "").lower()

        # Adverse direction depends on side and leg:
        # - Buy entry: adverse = actual > intent (paid higher)
        # - Sell entry: adverse = actual < intent
        # - Stop sell (long pos): adverse = actual < intent
        # - Stop buy (short pos): adverse = actual > intent
        # - Target sell (long pos): adverse = actual < intent (rare for limit)
        # - Target buy (short pos): adverse = actual > intent (rare for limit)
        if side == "buy":
            slip_price = actual - intent  # +ve = paid higher = adverse
        else:
            slip_price = intent - actual
        slip_ticks = slip_price / tick

        # Determine session from ts_proposed
        sess = "?"
        try:
            ts = datetime.fromisoformat((r["ts_proposed"] or "").replace("Z", "+00:00"))
            ts_et_hour = (ts.astimezone(timezone.utc).hour - 4) % 24  # rough ET
            sess = session_for_hour(ts_et_hour)
        except Exception:
            pass

        cell_key = (sym, side, sess, leg)
        by_cell[cell_key].append({
            "cid": cid, "intent": intent, "actual": actual,
            "slip_price": slip_price, "slip_ticks": slip_ticks,
            "qty": r["qty"], "ts": r["ts_proposed"],
        })

    print(f"\nBy (symbol × side × session × leg):")
    print(f"{'cell':<32} {'n':>4} {'mean_ticks':>11} {'med_ticks':>10} {'worst':>8}")
    for cell_key in sorted(by_cell):
        rows_c = by_cell[cell_key]
        mean_t = mean(r["slip_ticks"] for r in rows_c)
        med_t = median(r["slip_ticks"] for r in rows_c)
        worst = max(r["slip_ticks"] for r in rows_c)
        cell_str = "|".join(str(x) for x in cell_key)
        print(f"{cell_str:<32} {len(rows_c):>4} {mean_t:>+10.2f} {med_t:>+9.2f} {worst:>+7.2f}")

    print(f"\nOverall:")
    all_slip = [r["slip_ticks"] for cell_rows in by_cell.values() for r in cell_rows]
    if all_slip:
        print(f"  N fills:           {len(all_slip)}")
        print(f"  Mean slippage:     {mean(all_slip):+.2f} ticks")
        print(f"  Median slippage:   {median(all_slip):+.2f} ticks")
        print(f"  Worst adverse:     {max(all_slip):+.2f} ticks")
        print(f"  Best (favorable):  {min(all_slip):+.2f} ticks")
        adverse = [s for s in all_slip if s > 0]
        print(f"  Adverse fraction:  {len(adverse)/len(all_slip)*100:.0f}%")

    # Write report to vault
    out = PROJECT_ROOT / "vault" / "research" / "live_slippage" / f"{datetime.now().strftime('%Y-%m-%d')}_per_cell.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        f.write(f"---\ndate: {datetime.now().strftime('%Y-%m-%d')}\n")
        f.write(f"kind: slippage_report\nsource: state/fund.db:orders (agent='live_trader')\n")
        f.write(f"n_fills: {len(rows)}\n---\n\n")
        f.write(f"# Slippage report — {datetime.now().strftime('%Y-%m-%d')}\n\n")
        f.write(f"**Total filled orders**: {len(rows)}\n\n")
        f.write(f"| cell | n | mean_ticks | median_ticks | worst |\n|---|---|---|---|---|\n")
        for cell_key in sorted(by_cell):
            rows_c = by_cell[cell_key]
            mean_t = mean(r["slip_ticks"] for r in rows_c)
            med_t = median(r["slip_ticks"] for r in rows_c)
            worst = max(r["slip_ticks"] for r in rows_c)
            cell_str = " \\| ".join(str(x) for x in cell_key)
            f.write(f"| {cell_str} | {len(rows_c)} | {mean_t:+.2f} | {med_t:+.2f} | {worst:+.2f} |\n")
        if all_slip:
            f.write(f"\n## Overall\n- N fills: {len(all_slip)}\n")
            f.write(f"- Mean: {mean(all_slip):+.2f} ticks\n")
            f.write(f"- Median: {median(all_slip):+.2f} ticks\n")
            f.write(f"- Adverse fraction: {len([s for s in all_slip if s > 0])/len(all_slip)*100:.0f}%\n")
    print(f"\nReport written to: {out.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
