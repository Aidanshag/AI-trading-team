"""Auto-promote RULE-tier lessons into the strategy_blacklist.

When a `vault/lessons/*.md` reaches `confidence: RULE` (n>=3 confirmations)
or `confidence: HARD` (n>=5), and it has both `applies_to_symbol` and
`applies_to_strategy`, this script ensures a matching entry exists in
`config/risk_limits.yaml:strategy_blacklist`.

Runs nightly. Idempotent — won't add duplicates. Reports adds in stdout
for the daily journal.

Lesson front-matter schema:
  ---
  confidence: RULE | HARD | PATTERN | ADVISORY
  applies_to_symbol: ZN
  applies_to_strategy: opening_range_breakout
  reason: short rationale
  ---

Usage:
  python -m scripts.auto_promote_lessons [--dry-run]
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import yaml


LESSONS = Path("vault/lessons")
RISK_LIMITS = Path("config/risk_limits.yaml")


def _parse_front_matter(text: str) -> dict[str, Any]:
    """Pull the YAML front matter from a markdown file. Returns {} on
    malformed input."""
    if not text.startswith("---"):
        return {}
    m = re.match(r"^---\s*\n(.*?\n)---\s*\n", text, re.DOTALL)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}


def _eligible_lesson(meta: dict) -> bool:
    """RULE or HARD tier with both symbol + strategy."""
    tier = str(meta.get("confidence", "")).upper()
    return (tier in ("RULE", "HARD")
            and bool(meta.get("applies_to_symbol"))
            and bool(meta.get("applies_to_strategy")))


def _scan_lessons() -> list[dict]:
    """Return list of {symbol, strategy, reason, source} for all eligible
    lessons."""
    if not LESSONS.exists():
        return []
    out: list[dict] = []
    for f in sorted(LESSONS.glob("*.md")):
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        meta = _parse_front_matter(text)
        if not _eligible_lesson(meta):
            continue
        out.append({
            "symbol": str(meta["applies_to_symbol"]).upper(),
            "strategy": str(meta["applies_to_strategy"]).lower(),
            "reason": str(meta.get("reason", f"auto-promoted from {f.name}"))[:200],
            "source": f.name,
        })
    return out


def _existing_blacklist(cfg: dict) -> list[dict]:
    return list(cfg.get("strategy_blacklist") or [])


def _has_entry(existing: list[dict], symbol: str, strategy: str) -> bool:
    """Case-insensitive presence check. Symbol is uppercased, strategy
    lowercased, on both sides of the comparison so the caller doesn't
    have to remember the convention."""
    sym = str(symbol).upper()
    strat = str(strategy).lower()
    for e in existing:
        if (str(e.get("symbol", "")).upper() == sym
                and str(e.get("strategy", "")).lower() == strat):
            return True
    return False


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()

    if not RISK_LIMITS.exists():
        print(f"ERROR: {RISK_LIMITS} not found")
        return 2

    cfg = yaml.safe_load(RISK_LIMITS.read_text(encoding="utf-8")) or {}
    existing = _existing_blacklist(cfg)

    candidates = _scan_lessons()
    if not args.quiet:
        print(f"[auto_promote] scanned {len(candidates)} eligible lesson(s)")

    new_entries: list[dict] = []
    for c in candidates:
        if _has_entry(existing, c["symbol"], c["strategy"]):
            continue
        entry = {
            "symbol": c["symbol"],
            "strategy": c["strategy"],
            "reason": f"{c['reason']} (auto-promoted from {c['source']})",
        }
        new_entries.append(entry)

    if not new_entries:
        if not args.quiet:
            print("[auto_promote] no new blacklist entries needed")
        return 0

    if not args.quiet:
        print(f"[auto_promote] adding {len(new_entries)} blacklist entry/entries:")
        for e in new_entries:
            print(f"  {e['symbol']} + {e['strategy']}: {e['reason']}")

    if args.dry_run:
        print("(dry-run; not writing)")
        return 0

    cfg.setdefault("strategy_blacklist", []).extend(new_entries)
    RISK_LIMITS.write_text(yaml.safe_dump(cfg, sort_keys=False),
                           encoding="utf-8")
    if not args.quiet:
        print(f"[auto_promote] wrote {RISK_LIMITS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
