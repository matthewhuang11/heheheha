# Scoutbot

## Quick start (any computer)

1. Get the code: `git clone git@github.com:matthewhuang11/heheheha.git scoutbot && cd scoutbot`
2. **Mac:** double-click `start.command`. **Windows:** double-click `start.bat`. **Linux / Raspberry Pi:** run `./start.sh`.
3. The first time, it installs everything (a few minutes). Then pick **1** for the simulated room.
4. The dashboard opens at <http://localhost:8000>. Press **Start auto**.

Only Python 3.10 or newer is needed beforehand (<https://www.python.org/downloads/>; on Windows tick "Add python.exe to PATH").
Something wrong? Pick **5) Check my setup** in the menu, or run `python -m scoutbot.tools.doctor`.

## What Scoutbot is

Scoutbot is a small disaster-response robot. It drives itself with a Raspberry Pi 4, a camera and distance sensors,
finds people, and lets a responder see, drive and talk to survivors from a laptop dashboard (a web page, so phones work too).
The AI never drives: Gemini, YOLO and Ollama only describe what they see, and plain rules decide, through a safety gate.
Gemini, ElevenLabs and the survivor databases are used when there is internet. Ollama on the laptop takes over when there isn't.

## The start menu

`./start.sh` / `start.command` / `start.bat` (or `python -m scoutbot.start`) shows:

| # | Choice | Name to skip the menu | What it runs |
| --- | --- | --- | --- |
| 1 | Simulated room demo (no camera or robot needed) | `sim` | `python -m scoutbot --profile sim --set sim.world=demo` |
| 2 | This computer's webcam (fake distance sliders, no motors) | `laptop` | `python -m scoutbot --profile laptop` |
| 3 | Webcam, pretend there is no internet | `offline` | `... --profile laptop --set net.force_offline=true` |
| 4 | The real robot (run this ON the Pi) | `robot` | `python -m scoutbot --profile pi` |
| 5 | Check my setup | `doctor` | `python -m scoutbot.tools.doctor` |
| 6 | Run the tests | `test` | `python -m pytest -q tests` |

Example: `./start.sh sim --share` (Windows: `start.bat sim --share`).

## Keys (all optional)

Put them in `.env` in this folder (setup creates it from `.env.example`). Never commit `.env`.

| Key | Turns on | Without it | Get one |
| --- | --- | --- | --- |
| `GEMINI_API_KEY` | Gemini scene descriptions, replies and triage | driving uses the sensors only; replies from Ollama or canned text | <https://aistudio.google.com/apikey> |
| `ELEVENLABS_API_KEY` (+ `ELEVENLABS_VOICE_ID`) | natural voice | the computer's built-in voice | <https://elevenlabs.io/> |
| `MONGODB_URI` | survivor records synced to MongoDB | saved on this computer only (`data/`) | <https://www.mongodb.com/atlas> |
| `TIGER_DATABASE_URL` | sightings time series in Tiger Data | saved on this computer only | <https://www.tigerdata.com/> |
| `CAMERA_INDEX` | picks a camera (0, 1, 2...) | auto / profile default | |
| `SCOUTBOT_TOKEN` | a password for the dashboard (`/?token=...`) | no login (fine on your own Wi-Fi) | any long random text |

## Profiles

| Profile | Camera | Distance sensors | Motors | Notes |
| --- | --- | --- | --- | --- |
| `sim` | webcam if any (else drawn view) | simulated room | fake (move the sim robot) | no keys needed; worlds: `--set sim.world=demo` / `room_basic` / `rubble` |
| `laptop` (alias `mac`) | this computer's webcam | dashboard sliders | fake | Gemini if the key is set |
| `pi` | Pi camera / USB | HC-SR04 (or ToF) | L298N | listens on the network, test controls off |

Any setting can be changed for one run: `python -m scoutbot --profile laptop --set server.port=8001`.
Settings live in `config/profiles/*.yaml`.

## Open the dashboard on a phone or another laptop

Start with `--share` (or answer **y** in the menu). It prints something like:

```
[scoutbot] dashboard: http://localhost:8000
[scoutbot] other devices on this Wi-Fi: http://192.168.1.23:8000
```

Open the second address on a phone on the **same Wi-Fi**. Venue Wi-Fi often blocks devices from seeing each other:
then use a phone hotspot for both.

## The Raspberry Pi and the cloud

- The robot, hardware and YOLO: [docs/scoutbot/robot.md](docs/scoutbot/robot.md). On the Pi: `bash scripts/pi_setup.sh`, then `./start.sh robot`.
- Gemini, Ollama, voice and sync: [docs/scoutbot/cloud.md](docs/scoutbot/cloud.md).
- The station (this laptop side, setup, dashboard): [docs/scoutbot/station.md](docs/scoutbot/station.md).
- Team plan and status: [docs/scoutbot/STATUS.md](docs/scoutbot/STATUS.md).

## Demo script (about 3 minutes)

1. Open the dashboard (projector, plus a phone via `--share`). The robot is STOPPED.
2. **Start auto**: it drives itself and avoids obstacles; "Robot is doing" shows the rule that fired.
3. A person comes into view: YOLO box, the robot stops, a survivor pin on the map, a spoken greeting.
4. Type (or say) "My leg is stuck, I can't move it": triage turns red, IMMEDIATE (trapped), preliminary; the reply is spoken.
5. Toggle **Simulate offline**: replies now come from Ollama in the local voice; survivors are queued for sync.
6. Toggle back online: MongoDB and Tiger chips go green.
7. **Take control**, drive at a wall: the safety gate blocks it; let go and it stops; **STOP** works from every mode.

Full checklist: [docs/scoutbot/parallel/40-integration-and-demo.md](docs/scoutbot/parallel/40-integration-and-demo.md).

## Troubleshooting

| Problem | Fix |
| --- | --- |
| Black video / "no camera" on a Mac | System Settings > Privacy & Security > Camera: allow Terminal. Or set `CAMERA_INDEX=0` (or 1, 2) in `.env`. |
| "port 8000 is in use" | Scoutbot is already running in another window: close it, or add `--set server.port=8001`. |
| Ollama chip red / "Ollama not running" | Install from <https://ollama.com>, open it once, then `ollama pull qwen2.5:3b`. |
| Windows: "python is not recognized" | Install Python 3.10+ from python.org and tick "Add python.exe to PATH", then double-click `start.bat` again. |
| Linux: `libGL.so.1` error | `sudo apt install libgl1 libglib2.0-0` |
| YOLO slow or didn't install | Optional. Without it Gemini spots people. Retry: `.venv/bin/python -m pip install -r requirements-yolo.txt`. |
| No internet | Fine: Scoutbot works offline (Ollama replies, built-in voice, sync waits and catches up). |
| Setup failed half-way | Fix what it says, then double-click start again. It is safe to run any number of times. |
| Anything else | `python -m scoutbot.tools.doctor` explains what's missing. |

## Developers

```bash
python3 scripts/setup.py          # or let start.* do it; creates .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
python -m pytest -q tests
python -m scoutbot --profile sim --set sim.world=demo --headless 20
```

Tools: `python -m scoutbot.tools.doctor`, `camcheck`, `yolo_bench`, `sensor_check`, `motor_check` (wheels off the ground),
`ollama_check`, `talk_check`, `voice_check`, `sync_check`.

## Legacy debug tools: Robot Brain Laptop Harness

The original brain debug tools (kept working, not extended):

```bash
python demo.py
python demo.py --fake-vlm
python demo.py --image path.jpg
python demo.py --once
python web_demo.py                # old debug dashboard
```

On macOS, grant **Camera** permission to the terminal or IDE running `demo.py`.

Keys: `1`/`2`/`3` select left/center/right, `=` and `-` change it by 10 cm, `0` toggles no echo, `r` resets, `v` toggles VLM offline, space forces a VLM call, `4`–`9` select canned reports in `--fake-vlm`, and `q` quits. Decisions append to `logs/run.jsonl`.
