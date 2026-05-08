"""Unrealized P&L computation — pure broker-state observer.

Extracted from scripts/live_trader.py 2026-05-08 (continuous trim).
Sums unrealized P&L across positions using latest 1-min bar close per
contract. No DB writes; pure read + math.
"""
from __future__ import annotations

from datetime import timedelta

from tools.trader_utils import _load_yaml, _now_utc


def compute_unrealized(client, positions: list[dict]) -> float:
    """Sum unrealized P&L across positions using latest 1-min bar close."""
    if not positions:
        return 0.0
    syms = _load_yaml("config/symbols.yaml").get("symbols", {}) or {}
    total = 0.0
    now = _now_utc()
    for p in positions:
        size = int(p.get("size") or 0)
        if size == 0:
            continue
        contract = p.get("contractId") or p.get("contract") or ""
        avg_price = float(p.get("avgPrice") or p.get("averagePrice") or 0)
        if avg_price <= 0 or not contract:
            continue
        type_code = int(p.get("type") or 0)
        sign = 1 if type_code == 1 else -1 if type_code == 2 else (1 if size > 0 else -1)
        size = abs(size)
        # Resolve symbol root for tick economics
        root = None
        for tok in str(contract).split("."):
            if tok in ("CON", "F", "US", ""):
                continue
            if len(tok) <= 3 and tok and tok[0].isalpha() and tok[1:].isdigit():
                continue
            root = tok
            break
        meta = syms.get(root or "", {}) if root else {}
        tick_size = float(meta.get("tick_size") or 0)
        tick_value = float(meta.get("tick_value") or 0)
        if tick_size <= 0 or tick_value <= 0:
            continue
        try:
            bars = client.get_bars(
                contract_id=contract,
                start_time=(now - timedelta(minutes=10)).isoformat(),
                end_time=now.isoformat(),
                unit=2, unit_number=1, limit=10, live=False,
            )
            mark = float(bars[-1].get("c") or 0) if bars else 0
        except Exception:
            mark = 0
        if mark <= 0:
            continue
        points = mark - avg_price
        total += sign * size * (points / tick_size) * tick_value
    return total
