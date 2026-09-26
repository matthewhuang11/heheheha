# Cloud, talk, and Mongo ingest

Gemini and ElevenLabs remain independent optional services. This guide covers the only cloud database path: MongoDB Atlas behind the authenticated Vultr ingest service.

## Local-first behavior

`data/survivors.jsonl` remains the canonical local record. Per-sink outbox files hold survivor updates, sightings, and telemetry until the server acknowledges them. While offline, no upload is attempted; reconnect retries begin at 2 seconds and back off to `sync.backoff_max_s`. A failed acknowledgement leaves the row on disk. Each sighting and telemetry row has a durable `event_id`, so a retry after a successful write is harmless.

## Configuration and switching

All variable values are secrets or deployment-specific; only their names are listed here.

- Pi/base-station Vultr mode: `INGEST_URL`, `INGEST_TOKEN`; leave `MONGODB_URI` unset.
- Vultr service environment: `INGEST_HOSTNAME`, `INGEST_TOKEN`, `MONGODB_URI`.
- Direct local-development fallback only: set `sync.target: mongo` and `MONGODB_URI`; do not use this mode on a Pi or responder station that will leave your private network.
- Local-only mode: set `sync.target: none` or `sync.sinks: []`.
- `sync.target: ingest` is the default. `sync.target: auto` prefers ingest when both client variables exist, then direct Mongo. Tiger Data is not a configured target.

Check a configured client without writing data:

```sh
python -m scoutbot.tools.sync_check --sink ingest
python -m scoutbot.tools.sync_check --sink mongo  # direct development fallback only
```

## MongoDB Atlas setup

1. Create an Atlas project and a least-privilege database user for database `scoutbot`.
2. Create the cluster and obtain its application connection string for the Vultr server only.
3. Add the Vultr VM's static public IPv4 address to Atlas network access. Do not add broad public access or Pi/station addresses.
4. Set `MONGODB_URI` only in the Vultr service environment. The service creates survivor, event-id, time, and survivor/time indexes on startup.
5. Verify from the Vultr VM with `docker compose exec ingest python -c "from scoutbot.ingest.repository import MongoRepository; import os; MongoRepository(os.environ['MONGODB_URI']).health()"`.

Collections are `survivors` (version-gated `_id` upserts), `sightings`, and `telemetry`. Event collections use unique `event_id` indexes; the service also records server-side `received_at` metadata.

## Vultr deployment

Prerequisites needing user action: a Vultr account and approved paid VM, a DNS hostname, a MongoDB Atlas project/database user, a generated ingest bearer token, and the service-side Mongo URI. No resource is created by this repository.

1. Create a small supported Linux VM with a static IPv4 address. Open only TCP 80 and 443 in the Vultr firewall; use SSH administration controls appropriate to your team.
2. Point the chosen DNS hostname at that static address.
3. Install Docker Engine and Docker Compose on the VM, clone this repository, then enter `deploy/vultr/`.
4. Create a server-only `.env` beside `compose.yaml` with the variables `INGEST_HOSTNAME`, `INGEST_TOKEN`, and `MONGODB_URI`. Set restrictive file permissions and never copy it to the Pi/station or commit it.
5. Start and update with `docker compose up -d --build`. Caddy obtains and renews TLS certificates and proxies only to the internal ingest container.
6. Verify externally with `curl -fsS https://<hostname>/healthz`; use `docker compose logs --tail=100 ingest` for failures. A 503 means the service cannot reach Atlas.
7. Roll back by redeploying the previous image/revision, then check `/healthz`. The client outbox retains undelivered rows throughout an outage.

The service exposes only `GET /healthz` and authenticated `POST /v1/ingest`. It uses constant-time bearer comparison, strict Pydantic request models, a 1 MB request limit, maximum 500 items per request, no API docs endpoint, and no Mongo credential on the clients. Run it as the non-root image user; Caddy is the only public-facing container.

### No-Docker deployment

To run directly under `systemd` instead, log into the VM console as the limited sudo user and run the following. Enter secret values only in the server console; do not paste them into chat.

```sh
sudo apt-get update
sudo apt-get install -y git python3-venv caddy
git clone --branch agent/robot https://github.com/matthewhuang11/heheheha.git ~/scoutbot
cd ~/scoutbot
python3 -m venv .venv
.venv/bin/pip install fastapi 'uvicorn[standard]' pymongo pydantic
sudo install -m 600 /dev/null /etc/scoutbot-ingest.env
sudo nano /etc/scoutbot-ingest.env
```

The environment file contains the names `INGEST_TOKEN` and `MONGODB_URI`. Then install and start the non-root service:

```sh
DEPLOY_USER="$(whoami)"
sudo tee /etc/systemd/system/scoutbot-ingest.service >/dev/null <<EOF
[Unit]
Description=Scoutbot Mongo ingest API
After=network-online.target
Wants=network-online.target
[Service]
User=${DEPLOY_USER}
WorkingDirectory=/home/${DEPLOY_USER}/scoutbot
EnvironmentFile=/etc/scoutbot-ingest.env
ExecStart=/home/${DEPLOY_USER}/scoutbot/.venv/bin/uvicorn scoutbot.ingest.app:create_app --factory --host 127.0.0.1 --port 8080
Restart=always
RestartSec=3
[Install]
WantedBy=multi-user.target
EOF
sed 's/{\$INGEST_HOSTNAME}/downbeatfoil6588.duckdns.org/' deploy/vultr/Caddyfile.systemd | sudo tee /etc/caddy/Caddyfile >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now scoutbot-ingest caddy
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
```

Verify with `sudo systemctl status scoutbot-ingest caddy --no-pager` and `curl -fsS https://downbeatfoil6588.duckdns.org/healthz`.

## Test and acceptance commands

```sh
python -m pytest tests/test_outbox.py tests/test_ingest_client.py tests/test_ingest_api.py
python -m pytest -q tests
python -m scoutbot --profile sim --set sync.target=none --headless 20
```

For an authorized integration run, start the local ingest container with a test Atlas database, run the first command with `INGEST_URL` and `INGEST_TOKEN`, then verify:

1. Force offline and create a survivor plus telemetry; inspect that the ingest outbox has rows.
2. Restore connectivity and wait for sync status `ok`.
3. Query Atlas for one versioned survivor and the matching `event_id` documents.
4. Repeat delivery/restart the client; the event counts must not increase.

## Status and limits

No live Atlas, Vultr, Gemini, or ElevenLabs measurement has been performed here. This work does not make the robot demo-ready. Physical Pi bring-up, account creation, DNS, paid-resource approval, secret provisioning, and live queue-to-Atlas acceptance evidence remain required.
