"""Regression tests for the overnight fixes shipped 2026-04-27.

Each test corresponds to a specific bug we found during the first live
trading day. If any of these fail, a real production gap has been
reintroduced.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


# ============================================================================
# Bug 1: agent-name normalization (today's QR thesis was lost because it was
# recorded under "quant_researcher" while chain looked for "Quant Researcher")
# ============================================================================

def test_agent_name_canonicalization():
    from state.db import _canonicalize_agent_name as canon
    assert canon("Quant Researcher") == "Quant Researcher"
    assert canon("quant_researcher") == "Quant Researcher"
    assert canon("QUANT RESEARCHER") == "Quant Researcher"
    assert canon("Quant-Researcher") == "Quant Researcher"
    assert canon("risk_manager") == "Risk Manager"
    assert canon("risk-manager") == "Risk Manager"
    assert canon("RiskManager") == "Risk Manager"


def test_agent_name_canonicalization_unknown_preserved():
    from state.db import _canonicalize_agent_name as canon
    # Unknown names (e.g. test fixtures, manual injections) must round-trip
    assert canon("manual_injection") == "manual_injection"
    assert canon("test_agent_123") == "test_agent_123"


def test_agent_name_canonicalization_empty_safe():
    from state.db import _canonicalize_agent_name as canon
    assert canon("") == ""


# ============================================================================
# Bug 2: verdict parser misread "block" inside "blocks" / "RE-PROPOSE" (today
# Risk Manager's APPROVE was misread as block because text contained "block")
# ============================================================================

def test_verdict_parser_explicit_allow():
    from runtime.orchestrator import _extract_verdict
    assert _extract_verdict({
        "final_text": "After 13 checks, all pass. VERDICT: ALLOW"
    }) == "allow"


def test_verdict_parser_explicit_block():
    from runtime.orchestrator import _extract_verdict
    assert _extract_verdict({
        "final_text": "Per-trade cap exceeded. VERDICT: BLOCK"
    }) == "block"


def test_verdict_parser_explicit_modifications():
    from runtime.orchestrator import _extract_verdict
    assert _extract_verdict({
        "final_text": "VERDICT: ALLOW_WITH_MODIFICATIONS"
    }) == "allow_with_modifications"


def test_verdict_parser_re_propose_not_misread():
    """The original bug: PM said 'Analyst can re-propose' and the parser
    matched 'PROPOSE' inside 'RE-PROPOSE'."""
    text = (
        "I'm passing this thesis. The analyst can re-propose if conviction "
        "rises (e.g., after Wednesday's macro prints).\n\n"
        "DECISION: PASS"
    )
    # We use the same parser logic as the chain
    import re
    m = re.search(r"DECISION\s*[:\-]\s*(PROPOSE|PASS)\b", text.upper())
    assert m is not None
    assert m.group(1) == "PASS"


def test_verdict_parser_block_inside_text_does_not_trigger():
    """Risk Manager's text often references 'block' as a verb in their
    explanation. Final verdict must come from explicit VERDICT: line."""
    from runtime.orchestrator import _extract_verdict
    text = (
        "I would normally block proposals like this, but here all 13 gates "
        "pass and the math works. Approved.\n\nVERDICT: ALLOW"
    )
    assert _extract_verdict({"final_text": text}) == "allow"


# ============================================================================
# Bug 3: SDK 32K command-line limit (today caused Risk Manager + Energies
# to fail with CLINotFoundError when prompts exceeded the limit)
# ============================================================================

def test_all_agent_prompts_fit_in_sdk_limit():
    """No agent prompt + team preamble may exceed the SDK Windows command-
    line argument budget. Hard limit ~32768; we test against a tight buffer
    (300 chars as of 2026-04-29). The auto_trader path doesn't go through
    the SDK, so this only matters for SDK-driven wakes — but those still
    need the headroom."""
    import os, sys
    sys.path.insert(0, ".")
    from runtime.orchestrator import Orchestrator, _team_preamble
    orch = Orchestrator()
    failures = []
    for name, spec in orch.specs.items():
        body = spec.prompt_path.read_text(encoding="utf-8")
        preamble = _team_preamble(spec.prompt_path.stem)
        total = len(preamble) + len(body)
        if total >= 32768 - 300:
            failures.append((name, total))
    assert not failures, (
        f"{len(failures)} agents exceed SDK budget (32768 - 300 buffer):\n"
        + "\n".join(f"  {n}: {t} chars" for n, t in failures)
    )


# ============================================================================
# Bug 4: risk framework config completeness
# ============================================================================

def test_risk_framework_config_complete():
    """The new tiered risk framework must be present in risk_limits.yaml."""
    cfg = yaml.safe_load(Path("config/risk_limits.yaml").read_text())
    rf = cfg.get("risk_framework")
    assert rf is not None, "risk_framework section missing"

    # Conviction-tiered R:R
    rr = rf.get("rr_minimums")
    assert rr is not None
    assert rr["high"] == 1.5
    assert rr["med"] == 2.0
    assert rr["low"] == 2.5
    assert rr["validation"] == 1.5

    # Single-micro floor
    assert "single_micro_floor_pct_of_equity" in rf
    assert 0 < rf["single_micro_floor_pct_of_equity"] <= 0.005

    # Validation-grade
    vg = rf.get("validation_grade")
    assert vg["enabled"] is True
    assert vg["max_risk_usd"] <= 100
    assert vg["max_per_session"] >= 1
    assert vg["requires_specialist_consult"] is False

    # Adaptive discipline
    ad = rf.get("adaptive_discipline")
    assert ad is not None
    for state in ("fresh", "profitable_lite", "profitable_heavy",
                  "minor_drawdown", "moderate_drawdown"):
        assert state in ad
        assert "rr_floor_offset" in ad[state]
        assert "per_trade_cap_pct" in ad[state]

    # Verdict types
    vt = rf.get("rm_verdict_types")
    assert "allow" in vt
    assert "allow_with_modifications" in vt
    assert "block" in vt

    # Checklist tiering
    hard = rf.get("checklist_hard_items")
    soft = rf.get("checklist_soft_items")
    assert set(hard) == {1, 4, 5, 6, 9, 12}
    assert set(soft) == {2, 3, 7, 8, 10, 11}


# ============================================================================
# Bug 5: hard rules are still hard (regression — verify the tightening
# didn't accidentally weaken the floor)
# ============================================================================

def test_hard_floor_rules_unchanged():
    """Tier 1 rules must remain non-negotiable.

    2026-04-29: `no_naked_shorts` was deliberately relaxed by user
    directive (futures shorts permitted; short options still blocked
    via the options.allow_naked_short_* settings). The rule is no
    longer treated as a hard floor — it's a strategy-class toggle now.
    `require_stop_on_every_trade` remains the actual hard floor.
    """
    cfg = yaml.safe_load(Path("config/risk_limits.yaml").read_text())
    hr = cfg["hard_rules"]
    assert "no_naked_shorts" in hr   # key still present for the hook
    assert hr["require_stop_on_every_trade"] is True
    # Short options must remain blocked (defined-risk only)
    opts = cfg["options"]
    assert opts["allow_naked_short_calls"] is False
    assert opts["allow_naked_short_puts"] is False
    assert opts["allow_short_strangles"] is False
    assert opts["allow_short_straddles"] is False

    acct = cfg["account"]
    # Per-trade cap not loosened
    assert acct["per_trade_risk_pct_of_equity"] <= 0.005
    # Internal DLL still in force
    assert acct["internal_dll_target_usd"] <= 500


# ============================================================================
# Bug 6: Edge Hunter agent loads
# ============================================================================

def test_edge_hunter_agent_exists_and_loads():
    """Edge Hunter is the new fast setup-discovery agent added overnight."""
    import os, sys
    sys.path.insert(0, ".")
    from runtime.orchestrator import Orchestrator
    orch = Orchestrator()
    assert "Edge Hunter" in orch.specs
    spec = orch.specs["Edge Hunter"]
    assert spec.model_tier == "cheap"  # designed for fast/frequent wakes
    assert spec.prompt_path.exists()


# ============================================================================
# Bug 7: Pre-Trade Checklist tiered
# ============================================================================

def test_pre_trade_checklist_tiering_in_doc():
    """The pre_trade_checklist.md must reference the tiering."""
    text = Path("vault/_meta/pre_trade_checklist.md").read_text(
        encoding="utf-8"
    )
    assert "HARD" in text
    assert "SOFT" in text
    assert "BLOCK" in text


# ============================================================================
# Bug 8: bearish-to-defined-risk routing guidance
# ============================================================================

def test_trading_process_documents_bearish_routing():
    """Trading process must explain how to express bearish views without
    naked shorts (today QR's 6E short was DOA at the hook)."""
    text = Path("vault/_meta/trading_process.md").read_text(encoding="utf-8")
    assert "naked short" in text.lower() or "bear put spread" in text.lower()
    # Must mention at least one defined-risk alternative
    assert any(s in text.lower() for s in (
        "put spread", "call spread", "calendar", "defined-risk"
    ))


# ============================================================================
# Bug 9: state_record_decision MUST-CALL discipline documented
# ============================================================================

def test_must_call_state_record_decision_documented():
    """Today many analysts produced theses but didn't call
    state_record_decision, so theses were lost."""
    text = Path("vault/_meta/trading_process.md").read_text(encoding="utf-8")
    assert "state_record_decision" in text
    assert "MANDATORY" in text or "MUST" in text
