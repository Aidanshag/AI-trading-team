"""Real-time fund dashboard. Single-pane view of the desk's state.

Usage:  python scripts/dashboard.py        # one-shot snapshot
        python scripts/dashboard.py --live # auto-refresh every 5 sec
"""

from __future__ import annotations

import argparse
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.text import Text


DB_PATH = Path("state/fund.db")


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _account_panel() -> Panel:
    c = _conn()
    snap = c.execute(
        "SELECT * FROM account_snapshots ORDER BY ts DESC LIMIT 1"
    ).fetchone()

    table = Table.grid(padding=(0, 2))
    table.add_column(style="dim")
    table.add_column(style="bold")

    if snap:
        bal = float(snap["balance_usd"])
        day_pl = float(snap["realized_pl_day_usd"]) + float(snap["unrealized_pl_usd"])
        tdd = float(snap["trailing_dd_usd"])
        color = "green" if day_pl >= 0 else "red"
        table.add_row("Balance",       f"${bal:,.2f}")
        table.add_row("Day P&L",       f"[{color}]${day_pl:+,.2f}[/]")
        table.add_row("Trailing DD",   f"${tdd:,.2f} / $2,000 limit")
        table.add_row("Snapshot age",  snap["ts"])
    else:
        table.add_row("Account", "[dim]no snapshot yet[/]")

    return Panel(table, title="Account", border_style="cyan")


def _positions_panel() -> Panel:
    c = _conn()
    rows = c.execute(
        "SELECT symbol, side, contracts, avg_price, stop_price, target_price "
        "FROM positions"
    ).fetchall()

    if not rows:
        return Panel("[dim]No open positions[/]", title="Positions", border_style="cyan")

    t = Table(show_header=True, header_style="bold")
    t.add_column("Symbol")
    t.add_column("Side")
    t.add_column("Qty", justify="right")
    t.add_column("Entry", justify="right")
    t.add_column("Stop", justify="right")
    t.add_column("Target", justify="right")
    for r in rows:
        side_color = "green" if r["side"] == "long" else "red"
        t.add_row(
            r["symbol"],
            f"[{side_color}]{r['side']}[/]",
            str(r["contracts"]),
            f"{r['avg_price']:.2f}",
            f"{r['stop_price']:.2f}" if r["stop_price"] else "-",
            f"{r['target_price']:.2f}" if r["target_price"] else "-",
        )
    return Panel(t, title=f"Positions ({len(rows)})", border_style="cyan")


def _activity_panel() -> Panel:
    c = _conn()
    rows = c.execute(
        "SELECT ts, agent, kind, summary FROM decisions "
        "ORDER BY id DESC LIMIT 10"
    ).fetchall()

    t = Table(show_header=True, header_style="bold")
    t.add_column("Time", style="dim")
    t.add_column("Agent")
    t.add_column("Kind")
    t.add_column("Summary")

    for r in rows:
        ts_short = (r["ts"] or "")[11:19]
        t.add_row(
            ts_short,
            (r["agent"] or "")[:22],
            (r["kind"] or "")[:18],
            (r["summary"] or "")[:60],
        )
    return Panel(t, title="Recent Activity (last 10)", border_style="cyan")


def _risk_panel() -> Panel:
    c = _conn()
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    rows = c.execute(
        "SELECT severity, COUNT(*) AS n FROM risk_events "
        "WHERE ts LIKE ? GROUP BY severity",
        (f"{today}%",),
    ).fetchall()

    counts = {r["severity"]: r["n"] for r in rows}
    t = Table.grid(padding=(0, 2))
    t.add_column(style="dim")
    t.add_column()
    t.add_row("Today's risk events:", "")
    for sev, color in (("info", "cyan"), ("warn", "yellow"), ("block", "red"), ("breach", "red bold")):
        t.add_row(f"  {sev}", f"[{color}]{counts.get(sev, 0)}[/]")
    return Panel(t, title="Risk", border_style="cyan")


def _cost_panel() -> Panel:
    c = _conn()
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    month = today[:7]

    today_total = c.execute(
        "SELECT COALESCE(SUM(usd_est), 0) FROM costs WHERE day = ?", (today,),
    ).fetchone()[0]
    month_total = c.execute(
        "SELECT COALESCE(SUM(usd_est), 0) FROM costs WHERE day LIKE ?", (f"{month}%",),
    ).fetchone()[0]
    all_total = c.execute(
        "SELECT COALESCE(SUM(usd_est), 0) FROM costs",
    ).fetchone()[0]

    t = Table.grid(padding=(0, 2))
    t.add_column(style="dim")
    t.add_column(style="bold")
    t.add_row("Today",           f"${today_total:.4f}")
    t.add_row("Month-to-date",   f"${month_total:.4f}")
    t.add_row("All time",        f"${all_total:.4f}")
    return Panel(t, title="API Cost", border_style="cyan")


def _build_layout() -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
    )
    layout["body"].split_row(
        Layout(name="left"),
        Layout(name="right"),
    )
    layout["left"].split_column(
        Layout(_account_panel(), size=8),
        Layout(_positions_panel()),
    )
    layout["right"].split_column(
        Layout(_risk_panel(), size=10),
        Layout(_cost_panel(), size=8),
        Layout(_activity_panel()),
    )
    layout["header"].update(
        Panel(
            f"[bold cyan]AI Trading Fund[/] — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            border_style="cyan",
        )
    )
    return layout


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--live", action="store_true", help="Auto-refresh every 5 sec")
    args = p.parse_args()

    if not DB_PATH.exists():
        Console().print("[red]No state DB found. Run: python -m state.db init[/]")
        return 1

    if args.live:
        with Live(_build_layout(), refresh_per_second=0.2, screen=True) as live:
            try:
                while True:
                    time.sleep(5)
                    live.update(_build_layout())
            except KeyboardInterrupt:
                pass
    else:
        Console().print(_build_layout())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
