# Station (Agent C): runtime, dashboard, survivors, simulator, setup on any computer

## What works

- **One step from `git clone` to a dashboard** on Mac, Linux and (written, reviewed) Windows:
  - Mac: double-click `start.command`. Linux / Pi / Mac terminal: `./start.sh`. Windows: double-click `start.bat`.
  - The first run creates `.venv`, installs `requirements.txt`, tries YOLO (a failure is only a warning), creates `.env`
    from `.env.example` (placeholder values blanked), runs the doctor, then shows the start menu.
  - Later runs start at once. If `requirements.txt` changes (e.g. after `git pull`), setup re-runs by itself
    (`.venv/scoutbot-setup-ok` holds a hash of the requirements).
- **Start menu** `python -m scoutbot.start` (or `start sim --share` to skip it): sim, laptop, offline, robot, doctor, test.
- **Doctor** `python -m scoutbot.tools.doctor [--quiet] [--no-camera]`: Python, core and optional packages, .env keys and
  what each unlocks, sync sinks, internet, LAN address, Ollama + model, built-in voice, camera.
- **`--share`**: listens on 0.0.0.0 and prints `http://<LAN IP>:8000` (with `?token=` if `SCOUTBOT_TOKEN` is set).
- **Port in use** prints a one-line fix instead of a traceback.
- **Profiles**: `laptop` (any laptop; `mac` is an alias), `sim`, `pi`. Unknown profile lists the choices.
  Sync sinks come from B's `sinks: auto` (on when the URL is in `.env`).
- **Windows safety**: every file my code reads/writes is utf-8, consoles use `errors="replace"`, no `±` in prints,
  `start.bat` is CRLF via `.gitattributes`.
- Old `run_*.command` launchers use `.venv/bin/python` or `python3` (KI-02).

## How to run

```bash
./start.sh                  # menu (Mac: double-click start.command; Windows: start.bat)
./start.sh sim --share      # simulator, open from a phone on the same Wi-Fi
python -m scoutbot --profile laptop --share
python -m scoutbot.tools.doctor
python -m pytest -q tests
python -m scoutbot --profile sim --set sim.world=demo --headless 20
```

## Fresh-machine test log

| When | Machine | How | Result | Time | Snags (fixed?) |
| --- | --- | --- | --- | --- | --- |
| 10:33 | Mac (arm64, Python 3.13) | fresh `git clone -b agent/station`, `./start.sh`, pick 1 | dashboard served, but **401** | ~60 s | `.env.example` (old) had `SCOUTBOT_TOKEN=replace_with_...`, copied into `.env` => dashboard locked. **Fixed** in a8386b7: setup blanks placeholders; settings ignores placeholder values in an existing `.env`. |
| 10:35 | Mac (arm64, Python 3.13) | fresh clone, `./start.command` (menu 1, share y) | **pass**: localhost 200, LAN URL 200, Start auto over WebSocket drives (pose moved 60,200 -> 174,252; 0 contacts) | 58 s clone -> dashboard (pip cache warm, YOLO included) | none |
| 10:36 | Linux Docker `python:3.10-slim` | fresh clone, `scripts/setup.py --no-yolo`, tests, headless 20, `./start.sh sim --share` | **pass**: 117 tests, headless 0 contacts / 1 survivor, dashboard 200 | setup 29 s | the slim image needs `libgl1 libglib2.0-0` for OpenCV (normal desktops have them). Doctor now explains this if OpenCV won't load. |
| - | Windows | `start.bat` | written and reviewed, **not run** (no Windows machine yet) | | Ask a teammate with Windows to double-click it and send the screen output. |

## Integration log

| Time | main before | Merged in | Tests | Headless 20 s (demo) | Notes |
| --- | --- | --- | --- | --- | --- |
| 10:37 | c73ec55 (B milestone) | origin/main into agent/station | 121 passed (3.5 s) | 1 survivor, 0 contacts, 0 watchdog trips | Removed `sync.sinks: []` from laptop/sim as B requested. |

## Known limits

- Windows `start.bat` not yet run on a real Windows machine.
- `--share` shows every LAN address it finds. Venue Wi-Fi sometimes blocks devices from seeing each other: use a phone hotspot.
- Setup needs Python 3.10+ already installed (the launchers say where to get it).
