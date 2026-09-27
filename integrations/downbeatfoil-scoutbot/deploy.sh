#!/usr/bin/env bash
# Push code to the pi and restart the service. Usage: ./deploy.sh [host]   (default: razzpi from ~/.ssh/config)
set -euo pipefail
HOST="${1:-razzpi}"
cd "$(dirname "$0")"

tar --exclude='pi/data' --exclude='pi/.env' --exclude='__pycache__' -czf - pi dashboard \
  | ssh "$HOST" 'mkdir -p ~/scoutbot && tar -xzf - -C ~/scoutbot'

ssh "$HOST" 'bash -s' <<'EOF'
set -e
cd ~/scoutbot/pi
command -v espeak-ng >/dev/null || sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq espeak-ng >/dev/null
[ -d .venv ] || python3 -m venv --system-site-packages .venv
.venv/bin/pip install -q -r requirements.txt
[ -f .env ] || cp .env.example .env

sudo tee /etc/systemd/system/scoutbot.service >/dev/null <<UNIT
[Unit]
Description=scoutbot
After=network-online.target

[Service]
User=$USER
WorkingDirectory=$HOME/scoutbot/pi
ExecStart=$HOME/scoutbot/pi/.venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 2
Restart=always
RestartSec=2
# the dashboard's mjpeg stream never ends, so without these a restart hangs for 90 s
TimeoutStopSec=8

[Install]
WantedBy=multi-user.target
UNIT
sudo usermod -aG video,gpio "$USER" 2>/dev/null || true
sudo systemctl daemon-reload
sudo systemctl enable --now scoutbot >/dev/null 2>&1
sudo systemctl restart scoutbot
sleep 3
systemctl is-active scoutbot && echo "dashboard: http://$(hostname -I | awk '{print $1}'):8000"
EOF
