# Initialize a git repo for the fund.
# Version control is critical — prompt edits, risk config tweaks, and
# playbook updates should all be committed so you can revert bad changes.
# Run from project root:  .\scripts\git-init.ps1

if (Test-Path ".\.git") {
    Write-Host "Git already initialized." -ForegroundColor Yellow
    exit 0
}

git init
if ($LASTEXITCODE -ne 0) {
    Write-Host "git not on PATH — install Git for Windows." -ForegroundColor Red
    exit 1
}

# .gitattributes — normalize line endings so OneDrive + different editors don't churn
@"
* text=auto eol=lf
*.ps1 text eol=crlf
*.bat text eol=crlf
*.db binary
*.jsonl text eol=lf
*.md text eol=lf
"@ | Out-File -FilePath ".\.gitattributes" -Encoding utf8

git add .gitignore .gitattributes
git add pyproject.toml .env.example README.md
git add agents/ config/ hooks/ runtime/ state/ tools/ vault/ deploy/ scripts/
git commit -m "Initial fund scaffold"

Write-Host ""
Write-Host "Git initialized. Day-to-day:" -ForegroundColor Green
Write-Host "  git status"
Write-Host "  git add <files>"
Write-Host "  git commit -m 'what changed'"
Write-Host "  git log --oneline"
Write-Host "  git revert <hash>   # undo a bad commit"
Write-Host ""
Write-Host "For a remote backup, create a private repo on GitHub and run:" -ForegroundColor Cyan
Write-Host "  git remote add origin https://github.com/YOU/ai-trading-fund.git"
Write-Host "  git push -u origin main"
