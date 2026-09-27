# scoutbot (the code running on the robot)

Search-and-rescue scout rover for HackGT 13. This is the code on the Raspberry Pi and the Vultr cloud dashboard.
It's separate from [matthewhuang11/heheheha](https://github.com/matthewhuang11/heheheha), and it runs on the real wiring.

- `pi/`: the robot. A FastAPI app on :8000 (systemd `scoutbot`) with camera + YOLO, sonar, DHT11, sound, motors, autonomy, survivor log, and Gemini triage.
  `cloudlink.py` (systemd `scoutbot-cloud`) dials out to the cloud and relays the dashboard.
- `dashboard/index.html`: the single-file dashboard, served by the Pi and by the cloud.
- `cloud/server.py`: runs on the Vultr box behind Caddy (HTTPS). It relays live state, video, and controls between the browser and the Pi,
  and ingests telemetry, events, survivors, and snapshots into SQLite.
- `tools/`: sim tests (`sim_autonomy.py`), `sonar_scan.py`, `motor_test.sh`, and more.

Deploy: `bash deploy.sh` (Pi), then `bash cloud/deploy.sh` (server, plus linking the Pi). Secrets live only in `pi/.env`,
`cloud/.tokens` and the server's `/etc/scoutcloud.env`, and none of them are committed.
Current state, access, and open issues: [HANDOFF.md](HANDOFF.md). Product and design notes: [PRODUCT.md](PRODUCT.md), [DESIGN.md](DESIGN.md).
