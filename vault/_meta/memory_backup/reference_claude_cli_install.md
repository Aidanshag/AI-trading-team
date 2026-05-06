---
name: Claude CLI install path on this machine
description: User runs Claude Desktop MSIX; no traditional claude.exe on PATH. Use Node.js + npm for CLI.
type: reference
originSessionId: 0fb1ece1-0ed0-47f7-9c25-6b7ec073a6ec
---
User's machine:
- Claude Desktop installed via Microsoft Store / MSIX → `C:\Users\Owner\AppData\Local\Packages\Claude_pzs8sxrjxfjjc`.
- No `claude.exe` on PATH. `node` and `npm` not installed.

To enable `claude` in PowerShell:
1. Install Node.js LTS (winget: `winget install OpenJS.NodeJS.LTS`).
2. Open a fresh PowerShell (PATH refresh).
3. `npm install -g @anthropic-ai/claude-code`.
4. `npm config get prefix` → that's the bin path; normally already on user PATH.
5. Verify with `claude --version`.

Helper script: `scripts/install-claude-cli.ps1` in the project.

**Do not** suggest the user run the Claude Desktop app from PowerShell — MSIX execution aliases may not be exposed as `claude`. The npm CLI install is the clean answer.
