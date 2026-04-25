# Tail the audit log live.
# Run from project root:  .\scripts\tail.ps1
Get-Content ".\logs\audit.jsonl" -Tail 20 -Wait
