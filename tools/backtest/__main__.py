"""CLI entry for the backtest harness.

Usage:
    python -m tools.backtest run --strategy donchian_breakout \
        --symbol CL=F --start 2020-01-01 --end 2025-01-01

    python -m tools.backtest list      # show available strategies + sources
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .data import available_sources, load_bars
from .engine import backtest_strategy
from .metrics import format_summary, summary_stats
from .strategies import STRATEGY_REGISTRY, get_strategy


def _parse_params(s: str) -> dict:
    """Parse 'key1=val1,key2=val2' into a dict with numeric coercion."""
    if not s:
        return {}
    out = {}
    for pair in s.split(","):
        k, _, v = pair.strip().partition("=")
        if not v:
            continue
        try:
            v_num = int(v)
        except ValueError:
            try:
                v_num = float(v)
            except ValueError:
                v_num = v
        out[k.strip()] = v_num
    return out


def cmd_run(args: argparse.Namespace) -> int:
    strategy = get_strategy(args.strategy)
    params = _parse_params(args.params or "")

    print(f"Loading {args.symbol} from {args.source} ({args.start} → {args.end})...")
    bars = load_bars(args.symbol, args.start, args.end, source=args.source)
    print(f"Loaded {len(bars)} bars.")

    result = backtest_strategy(strategy, bars, symbol=args.symbol, params=params)
    print()
    print(format_summary(result))

    if args.output:
        out = Path(args.output)
        out.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        md_path = out / f"{ts}_{args.strategy}_{args.symbol.replace('=', '_')}.md"
        md_path.write_text(_as_markdown(result, args), encoding="utf-8")
        print(f"\nReport: {md_path}")

    return 0


def cmd_list(args: argparse.Namespace) -> int:
    print("Strategies:")
    for name in sorted(STRATEGY_REGISTRY):
        print(f"  - {name}")
    print("\nData sources:")
    for name in sorted(available_sources()):
        print(f"  - {name}")
    return 0


def _as_markdown(result, args) -> str:
    stats = summary_stats(result)
    trades_table = [
        "| # | Entry | Exit | Side | Entry $ | Exit $ | R | Reason |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, t in enumerate(result.trades, 1):
        trades_table.append(
            f"| {i} | {t.entry_date.date()} | {t.exit_date.date()} | {t.side} "
            f"| {t.entry_price:.2f} | {t.exit_price:.2f} | "
            f"{t.r_multiple:+.2f} | {t.exit_reason} |"
        )
    return (
        f"---\n"
        f"type: backtest\n"
        f"strategy: {args.strategy}\n"
        f"symbol: {args.symbol}\n"
        f"start: {args.start}\n"
        f"end: {args.end}\n"
        f"source: {args.source}\n"
        f"---\n\n"
        f"# Backtest: {args.strategy} on {args.symbol}\n\n"
        f"## Summary\n\n"
        f"```\n{format_summary(result)}\n```\n\n"
        f"## Trades\n\n"
        + "\n".join(trades_table) +
        f"\n\n## Raw stats (JSON)\n\n```json\n{json.dumps(stats, default=str, indent=2)}\n```\n"
    )


def main() -> int:
    p = argparse.ArgumentParser(prog="backtest")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("run", help="Run a strategy backtest")
    r.add_argument("--strategy", required=True, choices=list(STRATEGY_REGISTRY))
    r.add_argument("--symbol", required=True, help="e.g. CL=F, ES=F, GC=F")
    r.add_argument("--start", required=True, help="YYYY-MM-DD")
    r.add_argument("--end", required=True, help="YYYY-MM-DD (exclusive)")
    r.add_argument("--source", default="yfinance", choices=available_sources())
    r.add_argument("--params", default="", help="k1=v1,k2=v2")
    r.add_argument("--output", default="vault/research/backtests",
                   help="Directory for the markdown report; blank to skip")
    r.set_defaults(func=cmd_run)

    ls = sub.add_parser("list", help="List available strategies and sources")
    ls.set_defaults(func=cmd_list)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
