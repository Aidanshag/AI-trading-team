---
type: index
---

# Meta

Stable reference material read by every agent on wake.

**First-wake essentials (canon):**
- [[team]] — team culture and collaboration rules.
- [[trading_process]] — the formal front-office workflow.
- [[conventions]] — vault conventions, frontmatter, wikilinks.
- [[symbol_registry]] — every tradeable symbol's wikilink target.
- [[topstep_setup_window]] — current learning sprint directive.
- [[idle_protocol]] — rules when agents are autonomously expanding the brain.
- [[idle_backlog]] — queue of expansion tasks.

**Current goal + roadmap:**
- [[current_goal]] — current top-level KPI (Combine pass).
- [[strategic_roadmap]] — multi-phase plan (Combine → XFA → multi-account).
- [[improvement_backlog]] — work queue for autonomous improvement cycles.

**Authoritative references:**
- [[topstep_combine_rules]] — full Topstep Combine + XFA rule spec.
- [[economics]] — cost equation; ~$575/mo fixed.
- [[principles]] — distilled trading canon; `→ encoded:` markers.

**Subdirectories** (sub-readme/index where relevant):
- `analysis/` — internal cross-cutting analysis pieces (see `analysis/INDEX.md` for catalog).
- `memory_backup/` — frozen exports of `~/.claude/.../memory/` for vault-visible reference.
- `daily_summaries/` — auto-generated daily P&L + activity summaries (rolling).
- `archive/` — auto-archived sentinel + macro_brief files older than the rolling window (vault-archive script handles this).

**Sibling workstreams** (parallel broker paths):
- `vault/futures/` — Topstep workstream (futures, Combine path, current priority).
- `vault/ib/` — Interactive Brokers workstream (personal capital, data-collection phase). Read `vault/ib/README.md` for the architectural distinction. The two share strategy library + research but NOT the trader.

**Auto-generated files** (NEVER hand-edit; they get overwritten):
- `sentinel_YYYY-MM-DD.md` — daily sentinel report (rotated by vault_archive after 7 days).
- `macro_brief_YYYY-MM-DD.md` — daily macro brief (rotated by vault_archive after 14 days).
- `daily_summaries/YYYY-MM-DD.md` — daily summary (kept indefinitely).

## When to read which

- Every wake: `team.md`, `trading_process.md` (via orchestrator preamble).
- Session start: add `conventions.md`, `symbol_registry.md`, `topstep_setup_window.md`.
- When making strategy decisions: `current_goal.md`, `strategic_roadmap.md`, `improvement_backlog.md`.
- When idle and authorized: `idle_protocol.md` + `idle_backlog.md`.
