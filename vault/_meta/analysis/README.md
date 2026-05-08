---
type: meta
status: active
applies_to: [CIO, Risk Manager, Quant Researcher, Edge Hunter, Cowork, all analysts]
read_on_first_wake: true
purpose: Home for ongoing internal analysis pieces. Distinct from vault/research/ (which is backtest + validation output) and vault/lessons/ (which is incident post-mortems). This is where reflective, cross-cutting analysis lives so the system can read it and accumulate insight.
updated: 2026-05-07
---

# Internal analysis library

This folder is where Cowork (primarily) and any agent that does
deliberative analytical work writes pieces that aren't backtest output
and aren't incident lessons — but DO contain insight the system should
pull into its decision-making.

The intent: **the auto_trader and the agent chain don't currently have a
"reflection" layer that reads cross-cutting analysis** — strategy
performance is encoded numerically in `state/strategy_validation.json`,
risk gates are encoded in `config/risk_limits.yaml` and `vault/lessons/`,
playbooks are static reference. There's no place for the kind of analysis
that says "across the last 30 days, here's the pattern in our losers" or
"these two cells look correlated under stress" or "the macro brief's
regime-read framing has been wrong N% of the time."

This folder fills that gap. Pieces here are **input to learning** —
findings that prove robust get promoted into lessons, config changes,
strategy demotions, or thesis revisions.

## What goes here

- **Cross-cell or cross-strategy pattern analysis** — e.g., "when ZN
  gap_fill underperforms, does ZT/ZB/ZF also?"
- **Live-vs-OOS deviation analysis** — interpretation layered on top of
  the raw `vault/research/live_vs_oos/*.md` data
- **Risk event taxonomy** — categorizing recurring risk events into
  patterns the lessons system can act on
- **Trade attribution** — when wins/losses happen, what factors
  predicted them
- **Macro brief retrospectives** — was the regime read right?
- **Process / workflow analysis** — where the trading workflow leaks
- **Meta-analysis of lessons** — common threads across multiple lessons

## What does NOT go here

- Raw backtest output → `vault/research/backtests/`
- Incident post-mortems → `vault/lessons/`
- Trade-by-trade reviews → `vault/reviews/`
- Standing strategy view → `vault/theses/`
- Live-vs-OOS raw data → `vault/research/live_vs_oos/`

If a piece naturally fits one of those folders, put it there. This
folder is the residual: analysis that is reflective, often
cross-domain, and intended to inform future decisions rather than
record past ones.

## Naming convention

```
vault/_meta/analysis/YYYY-MM-DD_<slug>.md
```

The slug should describe the topic, not the conclusion. Conclusions can
change in updates; topics stay stable.

Good: `2026-05-07_treasury_cell_correlation.md`
Bad:  `2026-05-07_zb_is_too_correlated.md`

## Frontmatter

Every analysis piece must include:

```yaml
---
type: analysis
date: YYYY-MM-DD
author: Cowork (Claude) | Claude Code | Quant Researcher | etc.
applies_to: [CIO, Risk Manager, Quant Researcher, Edge Hunter, ...]
sources: [list of files / DB tables / commits / dates this analysis reads from]
confidence: ADVISORY | PATTERN | RULE
status: open | superseded-by:<file> | promoted-to-lesson:<file>
---
```

## Lifecycle: from analysis to learning

```
analysis (here)  →  lesson (RULE tier)  →  hard gate in risk_gate.py
                 ↘
                  →  config change (e.g., tighter threshold)
                 ↘
                  →  thesis revision (vault/theses/)
                 ↘
                  →  validation gate (state/strategy_validation.json)
```

When an analysis piece reaches confidence **PATTERN** (n≥2 supporting
observations within ~30 days) or **RULE** (n≥3), it should be
**promoted** into one of the four downstream forms above. The piece
itself stays in this folder as the historical record; the new
lesson/config/thesis cites it via a `derived_from:` field.

## Surfacing protocol

Pieces in this folder get pulled into agent preambles when the agent
chain wakes. Specifically, the CIO's session brief should include the
**three most recent analysis pieces** from this folder by `date` field.
Cowork sessions use the catch-up pass to spot new pieces.

If a piece is `status: open` for >30 days without follow-up, archive it
to `vault/_meta/analysis/_archive/` to keep the active set small.

## See also

- [[INDEX]] — the running index of analysis pieces (newest first).
- [[../learning_system]] — the broader confidence-ladder framework these pieces feed into.
- [[../cowork_coordination]] — Cowork ↔ Claude Code coordination protocol.
