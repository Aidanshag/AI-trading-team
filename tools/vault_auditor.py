"""Recurring vault audit: detect contradictions, broken wikilinks,
stale strategy references, and orphan files. Posts a structured report
to `vault/_meta/vault_audit_YYYY-MM-DD.md` and Discord-alerts on any
HIGH severity findings.

Purpose: keep the brain "well-oiled" — autonomous detection of drift
between docs and live state. Pairs with `tools/vault_archive.py` (which
rotates stale auto-generated files).

Runs daily as FundVaultMaintenance scheduled task.

Checks:
  1. Stale strategy references — files mention strategies/cells that
     are NOT in live_strategies_filter or live_allowlist.
  2. Broken wikilinks — `[[name]]` style references where the target
     file doesn't exist anywhere in the vault.
  3. Orphan analysis files — files in `_meta/analysis/` and
     `research/analysis/` with zero inbound links.
  4. Auto-gen accumulation — files matching sentinel_*/macro_brief_*
     patterns older than archive thresholds still in `_meta/` (means
     vault_archive isn't running).
  5. Live-allowlist size sanity — sudden 2x change in cell count
     since last audit (would catch a bulk-stage accident).

Usage:
    .venv/Scripts/python.exe -m tools.vault_auditor [--dry]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VAULT = PROJECT_ROOT / "vault"
META_DIR = VAULT / "_meta"
VALIDATION_FILE = PROJECT_ROOT / "state" / "strategy_validation.json"


def _load_dotenv() -> None:
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        return
    try:
        for raw in env_file.read_text(encoding="utf-8",
                                         errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
    except Exception:
        pass


# Collect all vault md files once for cross-reference
def _scan_vault_files() -> dict[str, Path]:
    """Map basename-without-extension → full path for every md in vault/."""
    result: dict[str, Path] = {}
    for path in VAULT.rglob("*.md"):
        stem = path.stem
        # Keep the first occurrence in case of dupes (orphan check uses this)
        if stem not in result:
            result[stem] = path
    return result


def _file_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def check_stale_strategy_references() -> list[dict]:
    """Find files that name a strategy NOT in live_strategies_filter.

    The audit isn't strict — many docs legitimately reference strategies
    that aren't live (history, comparison, retirement notes). The check
    flags only files whose timestamp says "current state" or "active"
    when the named strategy isn't actually live.
    """
    findings = []
    if not VALIDATION_FILE.exists():
        return findings
    try:
        with VALIDATION_FILE.open("r", encoding="utf-8") as f:
            val = json.load(f)
    except Exception:
        return findings
    live_strats = {f.get("strategy") for f in
                    val.get("live_strategies_filter", []) if f.get("strategy")}

    # Patterns that suggest the doc is claiming current state
    current_state_phrases = re.compile(
        r"(?i)\b(active strategy|currently active|currently using|"
        r"live strategy|live cells include|now firing|primary edge)\b"
    )
    # Strategy name vocabulary — keep small; we want false-negative bias
    known_strategies = {
        "gap_fill", "gap_fill_wide", "vwap_reversion",
        "narrow_range_break", "fair_value_gap", "fair_value_gap_tuned",
        "inside_bar_break", "order_block", "order_block_d1",
        "liquidity_sweep", "liquidity_sweep_tuned", "keltner_breakout",
        "pivot_reversal", "vol_spike_fade", "cross_asset_divergence_zn",
        "rsi2_extreme_reversion",
    }
    retired = {"gap_fill", "gap_fill_wide", "vwap_reversion"}

    for md in VAULT.rglob("*.md"):
        # Skip explicit history/retirement docs
        if "retirement" in md.name or "archive/" in str(md):
            continue
        if "memory_backup" in str(md):
            continue  # memory backups are historical snapshots
        text = _file_text(md)
        if not text:
            continue
        if not current_state_phrases.search(text):
            continue
        # File asserts current-state claims; check if any retired strategy is named
        for strat in retired:
            # Word-boundary match to avoid 'gap_fill' matching 'gap_fill_wide'
            if re.search(rf"\b{re.escape(strat)}\b", text):
                # Verify the named strategy isn't in live_strats
                if strat not in live_strats:
                    findings.append({
                        "check": "stale_strategy_reference",
                        "severity": "med",
                        "file": str(md.relative_to(PROJECT_ROOT)),
                        "detail": f"file uses current-state language but names retired '{strat}'",
                    })
                    break  # one finding per file
    return findings


def check_broken_wikilinks(vault_files: dict[str, Path]) -> list[dict]:
    """Find [[X]] references where X doesn't resolve to any vault file."""
    findings = []
    wikilink = re.compile(r"\[\[([^\]\|#]+?)(?:\|[^\]]*)?\]\]")
    # Aggregate broken refs (which target -> which files cite it)
    broken: dict[str, list[str]] = defaultdict(list)
    for md in VAULT.rglob("*.md"):
        if "archive/" in str(md):
            continue
        text = _file_text(md)
        if not text:
            continue
        for match in wikilink.finditer(text):
            target = match.group(1).strip()
            # Strip subpath if any (e.g., "folder/name")
            target_stem = Path(target).stem if "/" in target else target
            if target_stem in vault_files:
                continue
            broken[target_stem].append(str(md.relative_to(PROJECT_ROOT)))
    for target, sources in sorted(broken.items())[:30]:
        # Only flag if cited by 2+ files OR cited by a hub file
        if len(sources) >= 2 or any("_MAP" in s or "README" in s for s in sources):
            findings.append({
                "check": "broken_wikilink",
                "severity": "low",
                "file": sources[0] if len(sources) == 1 else f"{len(sources)} files",
                "detail": f"wikilink target [[{target}]] doesn't resolve (cited by: {sources[:3]})",
            })
    return findings


def check_orphan_analyses() -> list[dict]:
    """Find files in _meta/analysis/ and research/analysis/ with zero
    inbound wikilinks AND not auto-generated."""
    findings = []
    candidate_dirs = [META_DIR / "analysis", VAULT / "research" / "analysis"]
    # Index of who-cites-what across the vault
    wikilink = re.compile(r"\[\[([^\]\|#]+?)(?:\|[^\]]*)?\]\]")
    md_link = re.compile(r"\]\(([^)]+\.md)\)")
    cited: set[str] = set()
    for md in VAULT.rglob("*.md"):
        text = _file_text(md)
        for m in wikilink.finditer(text):
            cited.add(m.group(1).strip().split("/")[-1])
        for m in md_link.finditer(text):
            cited.add(Path(m.group(1)).stem)
    for analysis_dir in candidate_dirs:
        if not analysis_dir.exists():
            continue
        for md in analysis_dir.iterdir():
            if not md.is_file() or md.suffix != ".md":
                continue
            if md.stem in ("README", "INDEX"):
                continue
            if md.stem in cited:
                continue
            findings.append({
                "check": "orphan_analysis_file",
                "severity": "low",
                "file": str(md.relative_to(PROJECT_ROOT)),
                "detail": "no inbound wikilinks — write-once research artifact?",
            })
    return findings


def check_autogen_accumulation() -> list[dict]:
    """Detect failure of vault_archive to rotate stale auto-gen files."""
    findings = []
    now = datetime.now(tz=timezone.utc)
    patterns = [
        (re.compile(r"^sentinel_(\d{4}-\d{2}-\d{2})\.md$"), 14),  # warn beyond 14d
        (re.compile(r"^macro_brief_(\d{4}-\d{2}-\d{2})\.md$"), 30),  # warn beyond 30d
    ]
    for filepath in META_DIR.iterdir():
        if not filepath.is_file():
            continue
        for pattern, warn_days in patterns:
            m = pattern.match(filepath.name)
            if not m:
                continue
            try:
                file_date = datetime.strptime(m.group(1),
                                                "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            age_days = (now - file_date).days
            if age_days > warn_days:
                findings.append({
                    "check": "autogen_accumulation",
                    "severity": "low",
                    "file": str(filepath.relative_to(PROJECT_ROOT)),
                    "detail": (f"file is {age_days}d old, beyond {warn_days}d rotation "
                                f"threshold — vault_archive may not be running"),
                })
    return findings


def check_live_allowlist_sanity() -> list[dict]:
    """Sudden 2x+ change in live_allowlist size since the last audit.

    Reads the previous vault_audit_*.md to find prior count; flags
    unusual jumps (catches bulk-stage accidents or auto-promote runaway).
    """
    findings = []
    if not VALIDATION_FILE.exists():
        return findings
    try:
        with VALIDATION_FILE.open("r", encoding="utf-8") as f:
            val = json.load(f)
    except Exception:
        return findings
    current_count = len(val.get("live_allowlist", []))

    # Look for the most recent prior audit
    prior_audits = sorted(META_DIR.glob("vault_audit_*.md"), reverse=True)
    prior_count = None
    for audit in prior_audits[:1]:  # most recent
        text = _file_text(audit)
        m = re.search(r"live_allowlist size: (\d+)", text)
        if m:
            prior_count = int(m.group(1))
    if prior_count is None:
        return findings  # no prior baseline
    if current_count >= prior_count * 2 and current_count > prior_count + 10:
        findings.append({
            "check": "live_allowlist_sanity",
            "severity": "high",
            "file": "state/strategy_validation.json",
            "detail": (f"live_allowlist grew from {prior_count} to {current_count} "
                        f"({current_count - prior_count:+d}) since last audit — "
                        f"possible bulk-stage accident or auto-promote runaway"),
        })
    return findings


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry", action="store_true",
                     help="print findings, skip the Discord alert + report write")
    args = p.parse_args()

    _load_dotenv()
    print("=== vault_auditor ===")
    vault_files = _scan_vault_files()
    print(f"vault md files indexed: {len(vault_files)}")

    findings: list[dict] = []
    findings.extend(check_stale_strategy_references())
    findings.extend(check_broken_wikilinks(vault_files))
    findings.extend(check_orphan_analyses())
    findings.extend(check_autogen_accumulation())
    findings.extend(check_live_allowlist_sanity())

    print(f"\nfindings: {len(findings)}")
    by_sev = defaultdict(list)
    for f in findings:
        by_sev[f["severity"]].append(f)
    for sev in ("high", "med", "low"):
        if sev not in by_sev:
            continue
        print(f"\n--- {sev.upper()} ({len(by_sev[sev])}) ---")
        for f in by_sev[sev][:30]:
            print(f"  [{f['check']:30}] {f['file']}: {f['detail']}")

    if args.dry:
        return 0

    # Write the report
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    report_path = META_DIR / f"vault_audit_{today}.md"
    val_count = 0
    if VALIDATION_FILE.exists():
        try:
            with VALIDATION_FILE.open("r", encoding="utf-8") as f:
                val_count = len(json.load(f).get("live_allowlist", []))
        except Exception:
            pass
    write_report(report_path, findings, val_count, len(vault_files))
    print(f"\nReport: {report_path}")

    # Discord alert on any HIGH findings
    high = by_sev.get("high", [])
    if high:
        try:
            from tools.alert import send_alert
            summary = " | ".join(f"{f['check']}: {f['detail'][:60]}"
                                  for f in high[:3])
            send_alert(
                f"vault_auditor HIGH severity ({len(high)}): {summary}",
                level="warn",
            )
        except Exception:
            pass

    return 0


def write_report(path: Path, findings: list[dict], allowlist_count: int,
                  files_indexed: int):
    by_sev = defaultdict(list)
    for f in findings:
        by_sev[f["severity"]].append(f)
    lines = ["---", "type: vault_audit", f"date: {path.stem.replace('vault_audit_', '')}",
              f"findings_total: {len(findings)}",
              f"high: {len(by_sev.get('high', []))}",
              f"med: {len(by_sev.get('med', []))}",
              f"low: {len(by_sev.get('low', []))}",
              f"live_allowlist size: {allowlist_count}",
              f"vault md files indexed: {files_indexed}",
              "---", "",
              "# Vault audit", "",
              f"**Total findings:** {len(findings)}",
              f"**By severity:** HIGH={len(by_sev.get('high', []))}, "
              f"MED={len(by_sev.get('med', []))}, LOW={len(by_sev.get('low', []))}",
              f"**live_allowlist size:** {allowlist_count}", ""]
    for sev in ("high", "med", "low"):
        items = by_sev.get(sev, [])
        if not items:
            continue
        lines.append(f"## {sev.upper()} severity ({len(items)})")
        lines.append("")
        for f in items:
            lines.append(f"- **[{f['check']}]** `{f['file']}`")
            lines.append(f"  - {f['detail']}")
        lines.append("")
    if not findings:
        lines.append("All checks passed. Brain is well-oiled.")
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
