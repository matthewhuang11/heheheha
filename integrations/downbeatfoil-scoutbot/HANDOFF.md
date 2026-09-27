# scoutbot handoff #3 (HackGT 13, hardware track), Sun Sep 27 ~1 AM

Hacking ends **Sun Sep 27 8 AM**; the expo runs 9–11:15 AM. This replaces handoff #2.

## Project
scoutbot is a search-and-rescue scout rover built around "store-and-forward blackout mode":
1. Press "send it in". The robot goes dark and explores on its own, using sonar to avoid obstacles and YOLO to spot people.
2. When it finds someone, it approaches, beeps, speaks through espeak-ng, and records their answer.
3. It retraces its path back to the entry.
4. Press "back in range". It syncs: Gemini transcribes the audio and writes a START triage report. Ollama and a plain template are the fallbacks.

Driving is a plain state machine, not an LLM.

## Where things are
- **Robot code:** `C:\Users\Aksha\Downloads\Random Stuff\scoutbot\` (not a git repo).
  - `pi/app.py` is the FastAPI server on :8000 (systemd `scoutbot`).
  - `pi/autonomy.py`, `motors.py`, `sensors.py`, `senses.py`, `camera.py`, `detector.py`, `victims.py`, `brain.py`, `voice.py`, `config.py`.
  - `dashboard/index.html` is the single-file dashboard.
- **Deploy the Pi (from `scoutbot/`):** `bash deploy.sh`. It never overwrites `pi/.env` or `pi/data`.
- **Deploy the cloud:** `bash cloud/deploy.sh` (details below).
- **Sim tests (from `scoutbot/pi`):** `../tools/.venv/Scripts/python ../tools/sim_autonomy.py`. All 16 checks pass.
- **Tools:**
  - `tools/sonar_scan.py`: stop the service, then run it on the Pi with `python3`. It pulses every free GPIO and reports which pin echoes.
  - `tools/buzz_say.py`: never run.
  - `tools/motor_test.sh`.
- **Team repo:** `Random Stuff/heheheha` (github.com/matthewhuang11/heheheha).
  - This is Matthew's separate, bigger scoutbot codebase ("scoutbot" package with a 3-sonar brain, safety gate, and Gemini/Ollama/ElevenLabs), with 165 tests.
  - It is **not** what runs on the Pi. Our code runs there.
  - Its `origin/agent/robot` branch has a Vultr MongoDB ingest service (`scoutbot/ingest/`, `deploy/vultr/`) for their own runtime. It isn't deployed.
  - Its docs, `docs/scoutbot/parallel/*` and `cloud.md`, explain their design.

## Access
- **Pi 4 (2 GB, Pi OS trixie):**
  - `ssh razzpi` = `akshaj@172.20.10.11`, key auth, passwordless sudo.
  - On the **iPhone hotspot**; the laptop is 172.20.10.10.
  - Local dashboard: http://172.20.10.11:8000.
- **Vultr (Ubuntu 22.04, 8 GB):**
  - `ssh scoutcloud` = `linuxuser@45.76.60.159`, key `~/.ssh/vultr_ed25519`, passwordless sudo.
  - Never use or ask for the password; the key is already installed.
- **Cloud dashboard:** https://downbeatfoil6588.duckdns.org/?token=... The full link is in `scoutbot/cloud/dashboard-link.txt`. Don't paste it in chat.
- **Secrets:**
  - The Pi's `pi/.env` holds `GEMINI_API_KEY`, `CLOUD_TOKEN`, and more.
  - `scoutbot/cloud/.tokens` holds `ROBOT_TOKEN` and `SITE_TOKEN`.
  - The server's `/etc/scoutcloud.env` holds the same tokens.
  - Never print any of these.

## Cloud system (built and deployed this session, working)
- **`pi/cloudlink.py`** (Pi systemd service `scoutbot-cloud`):
  - Dials **out** to `wss://downbeatfoil6588.duckdns.org/robot` with an `x-robot-token` header. It has to: the hotspot's NAT blocks any inbound connection.
  - Pushes `/api/state` at `CLOUD_STATE_HZ` and JPEGs from the local `/stream?fps=` at `CLOUD_FPS`.
  - Receives `{"type":"req"}` messages, replays them against `http://127.0.0.1:8000`, and answers `{"type":"resp", body base64}`. It only allows paths under `/api/`.
  - Reconnects with backoff.
- **`cloud/server.py`** (server systemd `scoutcloud`, uvicorn at 127.0.0.1:8090, behind Caddy with automatic HTTPS):
  - `/robot` is the Pi's websocket.
  - `/api/state` and `/stream` are served from the latest push. When the robot has sent nothing for 5 s, `/api/state` returns plain text with a 503, which the dashboard shows as "offline".
  - Every other `/api/*` call is tunnelled to the Pi.
  - `/api/history?minutes=` shows the stored data.
  - `/healthz` needs no auth.
  - Site auth: `?token=` is swapped for an httponly cookie `sb`.
- **Ingest:** SQLite at `~/scoutcloud/data/scout.db` on the server.
  - `telemetry` table: one row per second, with key columns plus the raw JSON.
  - `events` and `survivors` (upserted on change).
  - `frames`: a JPEG every 5 s under `data/frames/YYYYMMDD/`.
- **Verified end to end over the internet:**
  - 401 without the token.
  - State, video and the stop command all work; stop takes about 305 ms round trip.
  - Ingest rows appear.
- **Deploy script `cloud/deploy.sh`:**
  - Tars `cloud/` (with a copy of `dashboard/`) to `~/scoutcloud`.
  - Installs the venv, the systemd unit, Caddy (from Caddy's apt repo), and ufw rules for 80/443.
  - Writes `CLOUD_URL` and `CLOUD_TOKEN` into the Pi's `.env` and installs `scoutbot-cloud` there.
  - Run `bash deploy.sh` (Pi code) first whenever `pi/` changes.

## Other code changes this session (all deployed)
- **Dashboard senses tile** now shows each sonar by name, air, sound, camera fps, people in view, heading, and pi (CPU °C plus low power).
- **`/api/state`** has a new `pi` field (`cpu_c`, `low_power`), cached for 5 s from vcgencmd.
- **`detector.py`** caps YOLO at `DETECT_FPS`.
- **`app.py`:** `/stream` takes `?fps=`.
- **`senses.py`:**
  - sound has no debounce (that was the bug)
  - the DHT keeps looking for its iio node
  - the Buzzer class supports passive tones via `lgpio.tx_pwm`
  - `BUZZER_PASSIVE=1`, and the pin idles LOW
- **Sonar layout:** `SONARS` defaults to `left:17:27,right:22:10`, both angled about 30° off forward. `FRONT_SONARS` is the min of the forward sonars, and the robot goes blind only if all of them are dead.
- **Camera:** **Camera Module 3 (imx708 wide)** via `rpicam-vid` (`CAMERA_SRC=picam`, 640×360). There's **no GoPro any more**.

## Heat (a Pi 4 with no working fan was hitting 84 °C)
- **Mitigations live on the Pi:**
  - `cpu-cap.service` caps the clock at 1.2 GHz, applied on every boot.
  - In the Pi's `.env`: `CAMERA_FPS=8`, `DETECT_FPS=1.5`, `CLOUD_FPS=2`, `CLOUD_STATE_HZ=2`.
- **Result:** 80 °C dropped to about 66 °C.
- **Raise these once the fan works.**
- **Fan:** a 3-wire Vilros fan. Red is on pin 4, black on pin 6, and blue (the control wire) on pin 8 (GPIO14).
  - GPIO14 is driven HIGH by hand, and the fan still didn't spin.
  - `dtoverlay=gpio-fan,gpiopin=14,temp=55000` was added to `/boot/firmware/config.txt` (backup: `config.txt.bak-fan`). **It takes effect after the next reboot.**
  - Suggested checks: flick the blades, confirm the outer row is used, and try blue on pin 1 (3.3 V).

## Hardware status
| part | status |
|---|---|
| left sonar (17/27) | answers (reads 23–51 cm); a hand-tracking check is still unconfirmed |
| right sonar (22/10) | **stuck at exactly 6 cm**. Suspect VCC on 3.3 V instead of 5 V (pin 2 is the free 5 V pin), a blocked face, or a dead sensor. Swap the two sensors' plugs to tell which. |
| DHT11 (GPIO4 kernel overlay) | ✅ |
| sound sensor (GPIO25) | ✅ after the debounce fix |
| camera (Camera Module 3) | ✅ |
| speaker | ❌ **no sound**. It's an analog speaker spliced to cut airline-headphone wires in the 3.5 mm jack, and the Pi plays fine (`AUDIO_OUT=plughw:0,0`, espeak with `-a 200`). Likely the enamel coating on the splices is still on, plus it needs an amp (PAM8403 or similar). A continuity test via GPIO16 (pin 36, pull-up) against GND (pin 34) was never done. |
| GPIO8 buzzer | it was a passive buzzer wired straight from the pin to GND. The team may have put a speaker on it instead. **`victims.py` beeps GPIO8 twice whenever a survivor is found:** make sure nothing low-impedance sits directly on GPIO8. |
| motors (L298N 5/6/12, 23/24/13) | the pins are verified correct. **One side spins backward, and which side is still unknown.** Set `LEFT_INVERT=1` or `RIGHT_INVERT=1` in the Pi's `.env`. Not floor-calibrated. |
| mic | none |
| power | wall adapter (rating unknown). `throttled=0x50000`: under-voltage happened since boot but isn't happening now. |

## Known problems and risks
- **The iPhone hotspot keeps disappearing.** That's the "Pi crash" from earlier: the Pi never actually rebooted.
  - When it happens, the laptop falls back to eduroam and nothing can reach the Pi.
  - To rejoin: `netsh wlan connect name="iPhone"` once the network is visible again.
  - For the demo: phone on a charger, Auto-Lock set to Never, and the Personal Hotspot screen left open.
  - Or move the Pi to GTother or a travel router.
- **13 old test survivors** are in the robot's log and in the cloud DB. Clear them with `POST /api/reset` on the Pi before the demo (ask first).
- An **SD-card mask edit** (`systemd.mask=scoutbot.service`) was attempted but never stuck. The Pi's `cmdline.txt` is clean, so nothing needs undoing.

## How Akshaj likes to work
- Short and direct. He's impatient with waiting loops, so troubleshoot actively.
- Build ideas skip /roast.
- Ask before downloads, messages, or paid API calls.
- Never type passwords into anything; set up key auth instead.
- UI copy is lowercase and plain. Keep the dashboard simple.
