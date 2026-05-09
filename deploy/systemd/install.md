# Running the fund on a Linux VPS with systemd

Tested on Ubuntu 22.04+ / Debian 12+. Works the same on any systemd distro.

## One-time setup on the VPS

```bash
# 1. Create a dedicated user — never run services as root
sudo useradd --system --create-home --shell /bin/bash fund

# 2. Clone / upload the fund
sudo mkdir -p /opt/ai-trading-fund
sudo chown fund:fund /opt/ai-trading-fund
sudo -u fund git clone <your-private-repo-url> /opt/ai-trading-fund
#  or: sudo -u fund rsync ... from your laptop

# 3. Python venv
sudo -u fund python3 -m venv /opt/ai-trading-fund/.venv
sudo -u fund /opt/ai-trading-fund/.venv/bin/pip install -e "/opt/ai-trading-fund[dev]"

# 4. .env with secrets — chmod tight
sudo -u fund cp /opt/ai-trading-fund/.env.example /opt/ai-trading-fund/.env
sudo -u fund nano /opt/ai-trading-fund/.env
sudo chmod 600 /opt/ai-trading-fund/.env

# 5. Initialize state
sudo -u fund /opt/ai-trading-fund/.venv/bin/python -m state.db init

# 6. Install the systemd unit
sudo cp /opt/ai-trading-fund/deploy/systemd/fund.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable fund
sudo systemctl start fund
```

## Day-to-day

```bash
sudo systemctl status fund
sudo systemctl restart fund
sudo journalctl -u fund -f          # tail logs
sudo journalctl -u fund --since "1 hour ago"
```

## Updating

```bash
cd /opt/ai-trading-fund
sudo -u fund git pull
sudo -u fund /opt/ai-trading-fund/.venv/bin/pip install -e .
sudo systemctl restart fund
```

## Hardening checklist

- UFW / firewall: only allow outbound. Inbound only if you expose an ops dashboard.
- `fail2ban` on SSH.
- SSH key-only auth.
- Automatic security updates (`unattended-upgrades`).
- Daily `rsync` of `state/fund.db` and `logs/audit.jsonl` to an S3 bucket or another VPS.
