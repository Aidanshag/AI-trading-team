# Install the Claude Code CLI so `claude` works from any PowerShell window.
#
# Background: you have Claude Desktop installed (Microsoft Store / MSIX)
# but no command-line `claude` on PATH. The CLI is a separate npm package.
# This script installs Node.js (if missing) and then the Claude Code CLI.
#
# Run in an ELEVATED PowerShell (right-click → Run as Administrator).

# ── 1. Node.js ────────────────────────────────────────────────
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "Node.js not found. Installing via winget..." -ForegroundColor Cyan
    $wg = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $wg) {
        Write-Host "winget not available. Install Node.js LTS manually from https://nodejs.org" -ForegroundColor Red
        Write-Host "Then re-run this script." -ForegroundColor Red
        exit 1
    }
    winget install --id OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
    Write-Host ""
    Write-Host "Node installed. CLOSE this PowerShell and open a new one, then re-run this script." -ForegroundColor Yellow
    Write-Host "(The PATH refresh requires a new session.)" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "Node.js: $(node --version)" -ForegroundColor Green
}

# ── 2. npm check ──────────────────────────────────────────────
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "npm missing even though Node is present. Reinstall Node from nodejs.org." -ForegroundColor Red
    exit 1
}

# ── 3. Claude Code CLI ────────────────────────────────────────
Write-Host "Installing @anthropic-ai/claude-code globally..." -ForegroundColor Cyan
npm install -g @anthropic-ai/claude-code

if ($LASTEXITCODE -ne 0) {
    Write-Host "npm install failed. Try running this script as Administrator." -ForegroundColor Red
    exit 1
}

# ── 4. Verify PATH ────────────────────────────────────────────
$npmBin = & npm config get prefix
Write-Host ""
Write-Host "npm global bin: $npmBin" -ForegroundColor Cyan

# Ensure npm's global bin is on PATH permanently (user scope)
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$npmBin*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$npmBin", "User")
    Write-Host "Added $npmBin to user PATH." -ForegroundColor Green
}

# ── 5. Verify ──────────────────────────────────────────────────
$env:Path += ";$npmBin"
if (Get-Command claude -ErrorAction SilentlyContinue) {
    Write-Host ""
    Write-Host "claude is now available:" -ForegroundColor Green
    claude --version
    Write-Host ""
    Write-Host "In any NEW PowerShell window, just type: claude" -ForegroundColor Cyan
} else {
    Write-Host "claude still not on PATH. Try: claude.cmd --version" -ForegroundColor Yellow
    Write-Host "Or open a fresh PowerShell and retry." -ForegroundColor Yellow
}
