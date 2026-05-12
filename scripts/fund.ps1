# Fund - single-verb command launcher for the AI trading system.
#
# USAGE:
#   .\scripts\fund.ps1 <verb> [args]
#
# Or after installing the alias (run scripts/install-fund-shortcuts.ps1 once):
#   fund <verb> [args]   # works from any PowerShell window
#
# Verbs:
#   status          - show Topstep + DB + fees status
#   start           - start auto-trader (Ctrl+C to stop)
#   start-debug     - start auto-trader with cooldown=0 (first launch)
#   stop            - kill all running python processes (auto-trader + runtime)
#   flatten         - emergency: cancel all working orders + close all positions
#   nightly         - run all end-of-day reports
#
#   journal         - open today's journal in Notepad
#   journal-recent  - list 5 most recent journal entries
#   lessons         - list all lesson files
#   lesson <name>   - open a specific lesson (partial name match)
#   recap           - open latest nightly recap
#
#   config          - open risk_limits.yaml in Notepad
#   focus           - open focus_universe.yaml in Notepad
#   vault           - open vault folder in File Explorer (Obsidian sees it)
#   project         - open project root in File Explorer
#
#   pnl             - quick P&L attribution
#   shadow          - shadow-trade recap (which symbols would have worked)
#   scorecards      - agent scorecards
#
#   claude          - launch Claude Code in the project (sees code + vault)
#   obsidian        - launch Obsidian on the vault
#   help            - print this list

param(
    [Parameter(Position=0)]
    [string]$Verb = "help",

    [Parameter(Position=1, ValueFromRemainingArguments=$true)]
    [string[]]$RestArgs
)

$ErrorActionPreference = "Stop"
$ProjectRoot = "C:\Users\Owner\OneDrive\Personal AI\AI Trading"
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

# Force UTF-8 for Python file reads (matches start-autotrader-daily.ps1 fix
# from 2026-05-01). Without this, scripts that read_text() YAML configs crash
# on cp1252 default when the file contains em-dashes or arrows.
$env:PYTHONUTF8 = "1"

# Unbuffered Python stdout -- without this, `fund start` output sits in a 4KB
# block buffer and the trader appears dead even when scanning. Caught
# 2026-05-01 when the running trader produced no log output for 6+ minutes
# while CPU usage showed it was alive but mid-network-call.
$env:PYTHONUNBUFFERED = "1"

if (-not (Test-Path $Python)) {
    Write-Host "ERROR: Python venv not found at $Python" -ForegroundColor Red
    exit 1
}

# Always operate from the project root and load .env
Set-Location $ProjectRoot
$envFile = Join-Path $ProjectRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([A-Z_]+)\s*=\s*(.+)$') {
            $val = $Matches[2].Trim().Split('#')[0].Trim()
            [Environment]::SetEnvironmentVariable($Matches[1], $val, 'Process')
        }
    }
}

function Show-Help {
    Get-Content $PSCommandPath | Select-Object -First 38 | ForEach-Object {
        if ($_ -match "^#") {
            Write-Host ($_.Substring(1).TrimStart()) -ForegroundColor Cyan
        }
    }
}

switch ($Verb.ToLower()) {

    # ?? Trading control ????????????????????????????????????
    "status" {
        & $Python -m scripts.status
    }
    "old-status" {
        & $Python -m scripts.check_status
    }
    "start" {
        # 2026-05-11: switched from auto_trader to live_trader (the active trader).
        # auto_trader retained as legacy reference but not the production path anymore.
        Write-Host "Starting live_trader (5-min scans)..." -ForegroundColor Green
        Write-Host "Press Ctrl+C to stop. Open positions stay safe at Topstep." -ForegroundColor DarkGray
        Write-Host ""
        & $Python -u -m scripts.live_trader
    }
    "start-debug" {
        Write-Host "start-debug retired. Use `fund start-dry` for tight-loop testing." -ForegroundColor Yellow
        & $Python -u -m scripts.live_trader
    }
    "start-dry" {
        Write-Host "Starting live_trader DRY RUN (5-min scans, no broker writes)..." -ForegroundColor Cyan
        & $Python -m scripts.live_trader --dry-run
    }
    "start-legacy" {
        # Kept for archaeological purposes only — auto_trader hasn't been the
        # production path since 2026-05-11. Don't use unless deliberately
        # reverting.
        Write-Host "Starting LEGACY auto_trader (deprecated path, not recommended)..." -ForegroundColor Yellow
        & $Python -u -m scripts.auto_trader --interval-minutes 5
    }
    "stop" {
        Write-Host "Killing all python processes..." -ForegroundColor Yellow
        taskkill /F /IM python.exe 2>$null
        Start-Sleep -Seconds 1
        $remaining = Get-Process python -ErrorAction SilentlyContinue
        if ($remaining) {
            Write-Host "Some processes still running:" -ForegroundColor Red
            $remaining | Format-Table Id, StartTime
        } else {
            Write-Host "All clean." -ForegroundColor Green
        }
    }
    "flatten" {
        Write-Host "Cancelling all working orders + closing all positions..." -ForegroundColor Yellow
        & $Python -m scripts.flatten
    }
    "halt" {
        & $Python -m scripts.halt $Args
    }
    "resume" {
        & $Python -m scripts.halt clear
    }
    "stage" {
        # Show or set account stage (combine | xfa | live)
        # When stage transitions away from 'combine', the daily profit cap
        # auto-disables (config/account_stage.yaml controls it).
        if (-not $Args -or $Args.Count -eq 0) {
            # Use python -m to read the YAML cleanly without shell quoting issues
            $stageCfg = Get-Content (Join-Path $ProjectRoot "config\account_stage.yaml") -Raw
            if ($stageCfg -match '(?m)^stage:\s*(\S+)') { Write-Host "stage = $($Matches[1])" }
            if ($stageCfg -match '(?m)^combine_daily_profit_cap_usd:\s*(\S+)') { Write-Host "combine_daily_profit_cap_usd = $($Matches[1])" }
        } else {
            $newStage = $Args[0].ToString().ToLower()
            if ($newStage -notin @("combine", "xfa", "live")) {
                Write-Host "Invalid stage: $newStage. Must be combine | xfa | live." -ForegroundColor Red
                exit 1
            }
            $cfg = Join-Path $ProjectRoot "config\account_stage.yaml"
            $content = Get-Content $cfg -Raw
            $content = $content -replace '(?m)^stage:\s*\S+', "stage: $newStage"
            Set-Content -Path $cfg -Value $content -Encoding utf8
            Write-Host "Account stage set to: $newStage" -ForegroundColor Green
            if ($newStage -ne "combine") {
                Write-Host "Daily profit cap is now DISABLED (combine-only safety)." -ForegroundColor Yellow
            } else {
                Write-Host "Daily profit cap remains active." -ForegroundColor Yellow
            }
            Write-Host ""
            Write-Host "Restart the trader for changes to take effect:" -ForegroundColor Cyan
            Write-Host "  fund stop && fund start" -ForegroundColor Cyan
        }
    }

    # ?? Reports ????????????????????????????????????????????
    "eod" {
        & $Python -m scripts.eod $Args
    }
    "preflight" {
        & $Python -m scripts.preflight
    }
    "nightly" {
        & $Python -m scripts.nightly_reports
    }
    "pnl" {
        & $Python -m scripts.pnl_attribution
    }
    "shadow" {
        & $Python -m scripts.shadow_trade_recap
    }
    "scorecards" {
        & $Python -m scripts.agent_scorecards
    }

    # ?? Vault / journal access ?????????????????????????????
    "journal" {
        $today = Get-Date -Format "yyyy-MM-dd"
        $path = Join-Path $ProjectRoot "vault\journal\$today.md"
        if (-not (Test-Path $path)) {
            Write-Host "No journal entry for today yet ($path)." -ForegroundColor Yellow
            Write-Host "Creating one..." -ForegroundColor DarkGray
            New-Item -Path $path -ItemType File -Force | Out-Null
        }
        notepad $path
    }
    "journal-recent" {
        Get-ChildItem (Join-Path $ProjectRoot "vault\journal\*.md") |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 5 |
            ForEach-Object { Write-Host "  $($_.Name)  ($([int]((Get-Date) - $_.LastWriteTime).TotalHours)h ago)" }
    }
    "lessons" {
        Get-ChildItem (Join-Path $ProjectRoot "vault\lessons\*.md") |
            Sort-Object LastWriteTime -Descending |
            ForEach-Object { Write-Host "  $($_.Name)" }
    }
    "lesson" {
        if (-not $RestArgs) { Write-Host "Usage: fund lesson <name-fragment>" -ForegroundColor Red; exit 1 }
        $pattern = "*$($RestArgs[0])*"
        $match = Get-ChildItem (Join-Path $ProjectRoot "vault\lessons\$pattern.md") -ErrorAction SilentlyContinue |
                 Select-Object -First 1
        if ($match) { notepad $match.FullName }
        else { Write-Host "No lesson matched '$pattern'" -ForegroundColor Red }
    }
    "recap" {
        $latest = Get-ChildItem (Join-Path $ProjectRoot "vault\_meta\nightly_run_*.md") -ErrorAction SilentlyContinue |
                  Sort-Object LastWriteTime -Descending |
                  Select-Object -First 1
        if ($latest) { notepad $latest.FullName }
        else { Write-Host "No nightly recap yet. Run: fund nightly" -ForegroundColor Yellow }
    }

    # ?? Config files ???????????????????????????????????????
    "config" { notepad (Join-Path $ProjectRoot "config\risk_limits.yaml") }
    "focus"  { notepad (Join-Path $ProjectRoot "config\focus_universe.yaml") }
    "models" { notepad (Join-Path $ProjectRoot "config\models.yaml") }
    "fund-yaml" { notepad (Join-Path $ProjectRoot "config\fund.yaml") }

    # ?? File-system shortcuts ??????????????????????????????
    "vault"   { Start-Process explorer.exe (Join-Path $ProjectRoot "vault") }
    "project" { Start-Process explorer.exe $ProjectRoot }
    "logs"    { Start-Process explorer.exe (Join-Path $ProjectRoot "logs") }
    "scripts" { Start-Process explorer.exe (Join-Path $ProjectRoot "scripts") }

    # ?? Open Obsidian on the vault ?????????????????????????
    "obsidian" {
        $vault = Join-Path $ProjectRoot "vault"
        $obsidian = "$env:LOCALAPPDATA\Obsidian\Obsidian.exe"
        if (Test-Path $obsidian) {
            Start-Process $obsidian "obsidian://open?path=$([uri]::EscapeDataString($vault))"
        } else {
            Write-Host "Obsidian not found at $obsidian. Opening folder in Explorer instead." -ForegroundColor Yellow
            Start-Process explorer.exe $vault
        }
    }

    # ?? Launch Claude Code with full project + vault access ??????
    # Claude Code reads ALL files in the cwd tree, including vault/.
    # That's the simplest "Claude + Obsidian" integration: you're
    # always in the project root, so Claude sees the markdown.
    "claude" {
        Write-Host "Launching Claude Code in project root..." -ForegroundColor Green
        Write-Host "Claude can now read code (runtime/, hooks/, scripts/)" -ForegroundColor DarkGray
        Write-Host "AND vault contents (vault/journal/, vault/lessons/, etc)" -ForegroundColor DarkGray
        Write-Host ""
        Set-Location $ProjectRoot
        & claude
    }

    # ?? Help / default ?????????????????????????????????????
    "help"    { Show-Help }
    default   {
        Write-Host "Unknown verb: '$Verb'" -ForegroundColor Red
        Write-Host ""
        Show-Help
        exit 1
    }
}
