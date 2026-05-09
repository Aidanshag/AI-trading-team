# Deployment

Two target environments, in order of maturity:

1. **Windows (local laptop / mini-PC)** — where you'll start. Run as a Windows Service via NSSM so it auto-starts on boot, restarts on crash, and survives logoff.
2. **Linux VPS** — where you'll graduate to once the fund is proven in paper. `systemd` unit file included. Cheapest path to 24/5 uptime.

## Recommended progression

1. **Phase 1 — your laptop, foreground terminal.** Run `fund` by hand in a PowerShell window. Watch it. Read the journal. This is how you learn where it misbehaves. (Requires your laptop stay awake — see power-settings notes in the main README.)
2. **Phase 2 — your laptop as a Windows Service.** Use NSSM (`deploy/windows/install_nssm.md`). The fund survives lid-close, logoff, reboot. Auto-restarts on crash.
3. **Phase 3 — dedicated mini-PC at home.** Same NSSM setup on a Beelink/NUC/similar. Wired ethernet, UPS. Laptop can now be a laptop again.
4. **Phase 4 — Linux VPS ($5–20/mo).** `deploy/systemd/fund.service` installed. Git pull, venv, systemd restart loop. Most robust; paper-validate here before live.

Do not skip phase 1. The watch-and-learn loop on a real laptop is where most real bugs and miscalibrations surface.

## Secrets

`.env` holds Anthropic and ProjectX credentials. Never commit it. On the VPS, either:
- Place `.env` directly in the deploy directory (simple; `chmod 600`), or
- Use the VPS provider's secrets manager and render `.env` at boot.

## Observability

- `logs/audit.jsonl` — every tool call (firehose). Grep this to replay a session.
- `state/fund.db` — SQLite. Open with any client. The decisions, risk_events, and orders tables are the audit trail.
- `vault/journal/YYYY-MM-DD.md` — human-readable daily log.
- `vault/reviews/YYYY-MM-DD.md` — post-trade reviews + compliance summary.
