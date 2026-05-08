"""Tests for scripts.auto_promote_lessons — verifies that auto-promoting
RULE-tier lessons into strategy_blacklist does NOT strip YAML comments.

The 2026-04-29 incident produced a similar bug in scripts/halt.py where
yaml.safe_dump destroyed all hand-curated comments. The fix in both
places: targeted text-only edits.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_auto_promote_preserves_comments(tmp_path, monkeypatch):
    """Run auto_promote_lessons against a fixture risk_limits + lesson;
    confirm comments survive."""
    project = tmp_path / "project"
    project.mkdir()
    (project / "vault" / "lessons").mkdir(parents=True)
    (project / "config").mkdir()

    # Fixture risk_limits with comments + an existing strategy_blacklist
    risk_yaml = """\
# This is a top-of-file comment that MUST survive.
hard_rules:
  no_naked_shorts: false       # inline comment about naked shorts
  require_stop_on_every_trade: true

# Comment block above strategy_blacklist
strategy_blacklist:
  - { symbol: ZN, strategy: opening_range_breakout, reason: "existing" }

# Comment block at end
sessions:
  block_first_n_seconds_after_open: 60
"""
    (project / "config" / "risk_limits.yaml").write_text(risk_yaml,
                                                          encoding="utf-8")

    # A RULE-tier lesson eligible for promotion
    lesson_md = """\
---
confidence: RULE
applies_to_symbol: NG
applies_to_strategy: vwap_reversion
reason: "test lesson"
---
# Lesson body
"""
    (project / "vault" / "lessons" / "test_lesson.md").write_text(
        lesson_md, encoding="utf-8")

    # Run the script with cwd=project
    proj_root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "scripts.auto_promote_lessons", "--quiet"],
        cwd=project, capture_output=True, text=True, timeout=15,
        env={**__import__("os").environ,
             "PYTHONPATH": str(proj_root)},
    )
    assert result.returncode == 0, (
        f"script failed: stdout={result.stdout} stderr={result.stderr}")

    out = (project / "config" / "risk_limits.yaml").read_text(encoding="utf-8")

    # Comments survive
    assert "# This is a top-of-file comment that MUST survive." in out
    assert "# inline comment about naked shorts" in out
    assert "# Comment block above strategy_blacklist" in out
    assert "# Comment block at end" in out

    # New blacklist entry added
    assert "NG" in out
    assert "vwap_reversion" in out
    # Existing entry preserved
    assert "ZN" in out
    assert "opening_range_breakout" in out


def test_auto_promote_idempotent(tmp_path, monkeypatch):
    """Running twice doesn't add duplicates."""
    project = tmp_path / "project"
    project.mkdir()
    (project / "vault" / "lessons").mkdir(parents=True)
    (project / "config").mkdir()

    (project / "config" / "risk_limits.yaml").write_text(
        "strategy_blacklist:\n"
        "  - { symbol: NG, strategy: vwap_reversion, reason: 'existing' }\n",
        encoding="utf-8")
    (project / "vault" / "lessons" / "test.md").write_text(
        "---\nconfidence: RULE\napplies_to_symbol: NG\napplies_to_strategy: vwap_reversion\nreason: test\n---\n",
        encoding="utf-8")

    proj_root = Path(__file__).resolve().parent.parent
    env = {**__import__("os").environ, "PYTHONPATH": str(proj_root)}
    for _ in range(2):
        r = subprocess.run(
            [sys.executable, "-m", "scripts.auto_promote_lessons", "--quiet"],
            cwd=project, capture_output=True, text=True, timeout=15, env=env,
        )
        assert r.returncode == 0

    out = (project / "config" / "risk_limits.yaml").read_text(encoding="utf-8")
    # Should still contain NG once (the existing entry)
    assert out.count("vwap_reversion") == 1
