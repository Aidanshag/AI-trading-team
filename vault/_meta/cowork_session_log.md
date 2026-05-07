---
type: meta
status: active
purpose: |
  Append-only log of Cowork (Claude desktop) sessions. Cowork operates on
  the same codebase as Claude Code (PowerShell terminal) but runs in a
  separate desktop environment. This file is the breadcrumb trail so
  Claude Code (or future Cowork sessions) can see what changed and why
  without having to re-derive it from git diffs.
applies_to: [Claude Code sessions, Cowork sessions, user]
read_on_first_wake: ALL
updated: 2026-05-06
---

# Cowork ↔ Claude Code session log

Cowork commits use the `[cowork]` prefix in commit messages so they're
visually distinguishable from Claude Code's `session: auto-commit` lines.
Filter with `git log --grep='\[cowork\]' --oneline` to see only Cowork's
contributions.

If Claude Code's auto-commit picks up Cowork's uncommitted edits, those
will land under a `session: auto-commit` message. The notes below name
which files Cowork wrote so you can find them in either commit style.

---

## 2026-05-06 — Session 1 (orientation, theses, two safety-floor fixes)

**Context.** First Cowork session on this project. User wanted Cowork to
catch up on the codebase, vault, recent activity, and contribute alongside
Claude Code without conflict.

**Catch-up performed.** Cowork read `CLAUDE.md`, the full `vault/_meta/`
foundation, the `vault/theses/` and `vault/playbooks/` libraries, the
`vault/futures/product_deep_dives/`, all `agents/*.md` and `vault/agents/`
briefs, the four `vault/lessons/` files (4/29 ZN ORB failure, 4/29 GC NRB
winner, 5/5 profit-lock disable, 5/5 strategy validation lockdown), the
6 daily journals (4/23–4/29), `runtime/orchestrator.py`,
`hooks/risk_gate.py`, `scripts/auto_trader.py`, `scripts/eod.py`, and
the relevant config files. Then queried `state/fund.db` for current
balance ($49,416.75), today's trades (5 fills on MCL/NG/GC before the
22:24 UTC lockdown), recent `risk_events`, and the `live_allowlist`
in `state/strategy_validation.json`.

**Live universe state confirmed.** As of 2026-05-06 22:24 UTC the user
locked the live allowlist via `live_strategies_filter` to **only**
`gap_fill` on ZN/ZT/ZB/ZF (16 cells). Everything else — including
strategies promoted earlier today like `narrow_range_break` and
`fair_value_gap_tuned` — is shadow-only.

### Commits this session

1. `2c7333e [cowork] vault: standing theses for ZN/ZT/ZB/ZF gap_fill universe`
   - Added `vault/theses/{ZN,ZT,ZB,ZF}.md`. One standing thesis per
     locked Treasury symbol. Each documents the gap_fill mechanic,
     walk-forward evidence (OOS E, t-stat, n), active live cells,
     kill conditions, duration-basket correlation notes, and sizing
     against the $250 per-trade cap.
   - Note: theses don't affect runtime decisions. The auto_trader
     reads numbers (state.db, validation.json), not text. They serve
     as agent context on wake and human-readable canon.

2. `75bf692 [cowork] scripts: backfill_daily_pl.py for stale daily_pl table`
   - Added `scripts/backfill_daily_pl.py`. The daily_pl table hasn't
     been populated since 2026-05-01 because the orchestrator's
     `session_close_workflow` and `_backfill_missing_daily_pl` are
     both dormant (per CLAUDE.md). Both upsert call sites in
     `runtime/orchestrator.py` also omit `trade_count`, which is why
     existing rows have it as NULL.
   - Dry-run shows 5 missing days (4/29–5/5). Idempotent on day.
   - **NOT YET RUN** — user opted to defer running until later.
     To execute: `python -m scripts.backfill_daily_pl` from PowerShell.

3. `3271237 [cowork] scripts: walk-forward param sweep for Treasury gap_fill`
   - Added `scripts/walk_forward_treasury_param_sweep.py`. Mirrors
     `walk_forward_extensions.py` (which only ran on ZN) but extends
     the parameter sweep to ZT/ZB/ZF — the other three Treasuries
     that got promoted at DEFAULT params and have never been tuned.
   - Sweeps `min_gap_atr ∈ {0.5, 0.75, 1.0, 1.25} × rr_target ∈ {1.0,
     1.5, 2.0}` with a 75/25 walk-forward split.
   - Cannot run from Cowork sandbox (no network for yfinance).
     Run from PowerShell: `python -m scripts.walk_forward_treasury_param_sweep`.
   - Background: ZN sweep on 2026-05-04 showed `rr=2.0` raised OOS E
     from +1.20R to +1.51R (~+26% per-trade expectancy). If ZT/ZB/ZF
     show the same pattern, tuning kwargs in `STRATEGY_ROSTER` could
     raise live edge meaningfully.

### Uncommitted Cowork work in working tree

- **`scripts/auto_trader.py`** — dedupe added to the
  `per_symbol_burn_warn` emission block (lines ~2313-2333). Without
  this, the warn fires on every 5-minute scan after a symbol crosses
  the threshold. 2026-05-06 logged 325 warn rows on MCL alone before
  the fix. Dedupe keys on (symbol, count) per UTC day, mirroring
  `_audit_risk_config_drift`'s pattern.
  - **The OneDrive bash mount in the Cowork sandbox has a stale,
    truncated copy of this file** — committing from bash would
    corrupt the file in git. The Windows-side file is correct
    (verified via Read tool); Claude Code's next auto-commit will
    pick up the edit cleanly.
  - If you want to commit this manually with the [cowork] prefix
    instead, from PowerShell:
    `git add scripts/auto_trader.py && git commit -m "[cowork] auto_trader: dedupe per_symbol_burn_warn"`

### Deletions

- Six empty placeholder files at the vault root were removed:
  `2026-05-04.md`, `VIX.md`, `Untitled.base`, `Untitled 1.base`,
  `Untitled 1.canvas`, `Untitled 2.canvas`. These were untracked
  Obsidian default-new-file artifacts (Ctrl+N without choosing a
  folder lands at the vault root). Future thesis creation: navigate
  into `vault/theses/` in Obsidian's file pane first, or include the
  path prefix when creating (`theses/SYMBOL.md`).

### Findings worth remembering

- **`per_symbol_burn_warn` flood was log noise, not a trading issue.**
  The actual block is `per_symbol_burn_block` at 5 trades; the warn at
  3 trades is informational. Dedupe makes EOD reports cleaner; doesn't
  change a single trading decision.

- **`daily_pl` table has been stale since 5/1.** Snapshots are fine
  (auto_trader writes them every 5 min). The finalization step that
  rolls snapshots into daily_pl rows is in the dormant orchestrator.
  Either wake `session_close_workflow`, or move that responsibility
  into `auto_trader.scan_once` as a "first-scan-of-new-day" check.
  Not done in this session — proposed for review.

- **The 5/5 NG -$702 trade was `inside_bar_break`, not gap_fill.**
  My initial summary had this wrong. Verified via the live-vs-OOS
  tracker at `vault/research/live_vs_oos/2026-05-06_live_r_comparison.md`.

- **The 4/29 daily_pl row shows realized=$0** even though that day was
  a -$1,013 disaster. Reason: snapshots were broken on 4/29 (empty
  pipeline — exactly the failure the post-incident hardening fixed).
  Cannot recover what was never recorded; backfill will leave 4/29 at
  $0 and the lesson `2026-04-29_*.md` files capture the actual loss.

### Sync mechanism for future sessions

Cowork will run a catch-up at the start of every session: `git log`,
`git status`, query state.db for recent activity, scan recent vault
writes. Reports back to user before doing anything else. Anyone reading
this log can do the same in reverse: `git log --grep='\[cowork\]'`
shows exactly what Cowork has done.

If Claude Code wants to know what's safe to assume Cowork built:
- Anything committed under `[cowork]` is Cowork's work
- Anything under `session: auto-commit` could be either Claude Code's
  own changes or Claude Code picking up Cowork's uncommitted edits
- This file is the disambiguator
