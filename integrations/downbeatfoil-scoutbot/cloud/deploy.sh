#!/usr/bin/env bash
# Put the cloud server on the vultr box and link the pi to it.
# Usage (from scoutbot/): bash cloud/deploy.sh            needs `ssh scoutcloud` and `ssh razzpi` to work
#   HOSTNAME=downbeatfoil6588.duckdns.org  https via caddy; blank = plain http on port 80
set -euo pipefail
cd "$(dirname "$0")/.."
HOST="${CLOUD_HOST:-scoutcloud}"
PI="${PI_HOST:-razzpi}"
NAME="${HOSTNAME_OVERRIDE:-downbeatfoil6588.duckdns.org}"

# tokens are made once and kept in cloud/.tokens (never printed, never deployed anywhere but the two boxes)
if [ ! -f cloud/.tokens ]; then
  python -c "import secrets; print('ROBOT_TOKEN=' + secrets.token_urlsafe(32)); print('SITE_TOKEN=' + secrets.token_urlsafe(12))" > cloud/.tokens
  chmod 600 cloud/.tokens
fi
. cloud/.tokens

rm -rf cloud/dashboard && cp -r dashboard cloud/dashboard
tar --exclude='cloud/data' --exclude='cloud/.tokens' --exclude='__pycache__' -czf - cloud \
  | ssh "$HOST" 'mkdir -p ~/scoutcloud && tar -xzf - -C ~/scoutcloud --strip-components=1'

ssh "$HOST" "ROBOT_TOKEN='$ROBOT_TOKEN' SITE_TOKEN='$SITE_TOKEN' NAME='$NAME' bash -s" <<'EOF'
set -e
cd ~/scoutcloud
python3 -c "import ensurepip" 2>/dev/null || { sudo apt-get update -qq; sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-venv >/dev/null; }
[ -x .venv/bin/pip ] || { rm -rf .venv; python3 -m venv .venv; }
.venv/bin/pip install -q fastapi 'uvicorn[standard]'
sudo install -m 600 /dev/null /etc/scoutcloud.env
printf 'ROBOT_TOKEN=%s\nSITE_TOKEN=%s\nDATA_DIR=%s/scoutcloud/data\n' "$ROBOT_TOKEN" "$SITE_TOKEN" "$HOME" | sudo tee /etc/scoutcloud.env >/dev/null
sudo tee /etc/systemd/system/scoutcloud.service >/dev/null <<UNIT
[Unit]
Description=scoutbot cloud (relay + ingest + dashboard)
After=network-online.target
[Service]
User=$USER
WorkingDirectory=$HOME/scoutcloud
EnvironmentFile=/etc/scoutcloud.env
ExecStart=$HOME/scoutcloud/.venv/bin/uvicorn server:app --host 127.0.0.1 --port 8090 --ws-ping-interval 10 --timeout-graceful-shutdown 2
Restart=always
RestartSec=2
TimeoutStopSec=8
[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now scoutcloud >/dev/null 2>&1
sudo systemctl restart scoutcloud

# caddy: https on the duckdns name (it gets the certificate itself), plus plain http on the bare ip
if ! command -v caddy >/dev/null; then  # ubuntu 22.04 doesn't package caddy: use caddy's own apt repo
  curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/gpg.key | sudo gpg --batch --yes --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt | sudo tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
  sudo apt-get update -qq && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq caddy >/dev/null
fi
sudo tee /etc/caddy/Caddyfile >/dev/null <<CADDY
$NAME {
    reverse_proxy 127.0.0.1:8090
}
http://45.76.60.159 {
    reverse_proxy 127.0.0.1:8090
}
CADDY
sudo systemctl enable --now caddy >/dev/null 2>&1
sudo systemctl reload caddy || sudo systemctl restart caddy
if command -v ufw >/dev/null && sudo ufw status | grep -q "Status: active"; then
  sudo ufw allow 80/tcp >/dev/null; sudo ufw allow 443/tcp >/dev/null
fi
sleep 2
systemctl is-active scoutcloud caddy
curl -fsS http://127.0.0.1:8090/healthz
EOF

# the pi: point cloudlink at the server and run it as its own service
ssh "$PI" "ROBOT_TOKEN='$ROBOT_TOKEN' NAME='$NAME' bash -s" <<'EOF'
set -e
cd ~/scoutbot/pi
sed -i '/^CLOUD_URL=/d;/^CLOUD_TOKEN=/d' .env
printf 'CLOUD_URL=wss://%s/robot\nCLOUD_TOKEN=%s\n' "$NAME" "$ROBOT_TOKEN" >> .env
.venv/bin/pip install -q 'websockets>=14'
sudo tee /etc/systemd/system/scoutbot-cloud.service >/dev/null <<UNIT
[Unit]
Description=scoutbot cloud link
After=network-online.target scoutbot.service
[Service]
User=$USER
WorkingDirectory=$HOME/scoutbot/pi
ExecStart=$HOME/scoutbot/pi/.venv/bin/python -u cloudlink.py
Restart=always
RestartSec=3
[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now scoutbot-cloud >/dev/null 2>&1
sudo systemctl restart scoutbot-cloud
sleep 4
journalctl -u scoutbot-cloud -n 3 --no-pager -o cat
EOF
echo "dashboard: https://$NAME/?token=<SITE_TOKEN in cloud/.tokens>"
