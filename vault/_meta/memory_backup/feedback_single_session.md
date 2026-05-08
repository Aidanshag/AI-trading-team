---
name: Single-session policy (Claude Desktop retired)
description: User retired the Claude Desktop app on 2026-04-29 — only Claude Code CLI sessions touch the working tree
type: feedback
originSessionId: 157e699b-ca68-4228-86ce-c8b6de221da2
---
As of 2026-04-29, the user has closed the Claude Desktop app and will only use Claude Code CLI sessions going forward.

**Why:** Earlier in 2026-04-29, the user noticed code in the running app appeared different from what was in the editing session. Investigation found multiple causes — broken git worktrees, an orphaned `.claude/worktrees/great-hofstadter-ff387f/` checkout, and the strong possibility that Claude Desktop was concurrently editing files in the same tree (e.g., risk_limits.yaml was modified mid-session by an unknown writer). User decided the simplest fix was to retire the second app.

**How to apply:**
- Treat the working tree as single-writer for Claude. Anything modifying files concurrently is either (a) the orchestrator process itself, (b) a script the user is running, or (c) a code formatter / IDE auto-save — not another LLM session.
- If a "file modified externally" reminder fires, suspect a linter/formatter rather than a parallel Claude session.
- The `.claude/worktrees/` directory was cleaned up 2026-04-29; if it reappears, it was probably created by an Agent invocation with `isolation: "worktree"` in this session — clean up after by pruning or removing.
- The user is the ONLY other writer to assume.
