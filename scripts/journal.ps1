# Open today's journal note in the default markdown editor (Obsidian).
# Run from project root:  .\scripts\journal.ps1
$today = (Get-Date -Format "yyyy-MM-dd")
$path = ".\vault\journal\$today.md"
if (-not (Test-Path $path)) {
    New-Item -Path $path -ItemType File -Force | Out-Null
    "---`ndate: $today`ntype: journal`n---`n`n# Journal — $today`n`n" | Out-File -FilePath $path -Encoding utf8 -Append
}
Invoke-Item $path
