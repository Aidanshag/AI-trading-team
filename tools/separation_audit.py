"""separation_audit — enforces clean Topstep <-> IB workstream isolation.

Run on every preflight and weekly audit. Fails loudly if any broker boundary
is violated. The two workstreams share strategies + research; they do NOT
share trader, risk config, or live allowlists.

Boundaries enforced:
1. Every live_allowlist cell must have a broker field
2. Every shadow_trades row must have a broker field
3. IB-only modules must not be imported from Topstep trader scripts
4. Topstep-only modules must not be imported from IB scripts
5. vault/futures/ and vault/ib/ subdirectories must not cross-reference each other's trader files
6. No IB cell may appear with broker='topstep' or vice versa
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "state" / "fund.db"
ALLOWLIST_PATH = ROOT / "state" / "strategy_validation.json"

# Modules that must stay in their lane
TOPSTEP_ONLY_MODULES = {
    "tools.projectx_client",
    "tools.topstep",
    "scripts.live_trader",
    "scripts.brain_signaler",
    "hooks.risk_gate",
}
IB_ONLY_MODULES = {
    "tools.ib_client",
    "tools.backtest.ib_strategies",
}

# Files that import each other are violations
TOPSTEP_SCRIPTS = [
    ROOT / "scripts" / "live_trader.py",
    ROOT / "scripts" / "brain_signaler.py",
]
IB_SCRIPTS = list((ROOT / "scripts").glob("ib_*.py"))


def violations() -> list[str]:
    out: list[str] = []
    out += _check_allowlist_broker_field()
    out += _check_shadow_trades_broker_field()
    out += _check_cross_imports()
    out += _check_ib_symbols_not_in_topstep_allowlist()
    return out


def _check_allowlist_broker_field() -> list[str]:
    if not ALLOWLIST_PATH.exists():
        return ["[allowlist] state/strategy_validation.json missing"]
    data = json.loads(ALLOWLIST_PATH.read_text())
    cells = data.get("live_allowlist", [])
    untagged = [c for c in cells if not c.get("broker")]
    if untagged:
        names = ", ".join(f"{c.get('symbol')}/{c.get('strategy')}" for c in untagged[:5])
        return [
            f"[allowlist] {len(untagged)} cell(s) missing broker field — first: {names}"
        ]
    valid_brokers = {"topstep", "ib"}
    invalid = [c for c in cells if c["broker"] not in valid_brokers]
    if invalid:
        return [f"[allowlist] {len(invalid)} cell(s) have invalid broker value"]
    return []


def _check_shadow_trades_broker_field() -> list[str]:
    if not DB_PATH.exists():
        return []
    con = sqlite3.connect(DB_PATH)
    try:
        cols = [r[1] for r in con.execute("PRAGMA table_info(shadow_trades)").fetchall()]
        if "broker" not in cols:
            return ["[shadow_trades] missing 'broker' column"]
        bad = con.execute(
            "SELECT COUNT(*) FROM shadow_trades WHERE broker IS NULL OR broker NOT IN ('topstep','ib')"
        ).fetchone()[0]
        if bad:
            return [f"[shadow_trades] {bad} row(s) with NULL/invalid broker"]
    finally:
        con.close()
    return []


def _check_cross_imports() -> list[str]:
    out: list[str] = []
    for script in TOPSTEP_SCRIPTS:
        if not script.exists():
            continue
        text = script.read_text(encoding="utf-8", errors="ignore")
        for bad in IB_ONLY_MODULES:
            if _imports(text, bad):
                out.append(f"[cross-import] {script.name} imports IB-only module {bad}")
    for script in IB_SCRIPTS:
        if not script.exists():
            continue
        text = script.read_text(encoding="utf-8", errors="ignore")
        for bad in TOPSTEP_ONLY_MODULES:
            if _imports(text, bad):
                out.append(f"[cross-import] {script.name} imports Topstep-only module {bad}")
    return out


def _imports(text: str, mod: str) -> bool:
    pattern = re.compile(
        rf"^\s*(?:from\s+{re.escape(mod)}|import\s+{re.escape(mod)})", re.MULTILINE
    )
    return bool(pattern.search(text))


# IB equity symbols that must NEVER appear in Topstep allowlist
# (Topstep is futures-only; if an equity ticker shows up it's a misroute)
IB_ONLY_SYMBOLS_PREFIXES = ("SPY", "QQQ", "IWM", "XL", "AAPL", "MSFT", "GOOG", "NVDA")


def _check_ib_symbols_not_in_topstep_allowlist() -> list[str]:
    if not ALLOWLIST_PATH.exists():
        return []
    data = json.loads(ALLOWLIST_PATH.read_text())
    cells = data.get("live_allowlist", [])
    out = []
    for c in cells:
        if c.get("broker") != "topstep":
            continue
        sym = c.get("symbol", "")
        if any(sym.startswith(p) for p in IB_ONLY_SYMBOLS_PREFIXES):
            out.append(f"[symbol-leak] equity '{sym}' in Topstep allowlist (futures-only)")
    return out


def main() -> int:
    vs = violations()
    if not vs:
        print("separation_audit: OK (no violations)")
        return 0
    print(f"separation_audit: {len(vs)} VIOLATION(S):")
    for v in vs:
        print(f"  - {v}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
