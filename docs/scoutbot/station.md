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
- **Dashboard** (checked in headless Chromium, desktop 1400x900 and phone 390x844, no JS errors):
  separate "Gemini scene" / "Gemini talk" chips (KI-44), offline banner with queued counts, round-trip time on the link chip,
  STOP always in the sticky header, 72x64 px touch pad (`touch-action: none`), map fit-all / follow-robot, 1 m scale bar,
  clickable survivor pins, survivors sorted red-first, JSON / CSV export (CSV opened and checked).
- **Command safety (KI-07):** `sim` and `sensor` commands are refused unless `server.test_controls` (off on the Pi).
- **Fast state (KI-08):** `Registry.summaries()` + 0.5 s cache, refreshed at once on survivor/chat/triage events.
  `state()` stays under 5 ms with 20 survivors x 50 messages (test).
- **`sim.fake_people: false`** makes the sim camera see nobody (KI-21).

## Survivor records vs people seen (sim, 300 s AUTO, fast-forwarded clock, 5 seeds x 3 worlds)

People "seen" = came within 2.5 m in view. Records = entries the registry created.

After KI-22 (the pose and the sim use per-action speeds: forward 30, slow 18, back-up 18 cm/s, turns 90 deg/s,
interpolated during ramps), sweep of `survivors.merge_cm`:

| merge_cm | runs exact (of 15) | extra (duplicate) records | missing (merged) records |
| --- | --- | --- | --- |
| 60 | 7 | 8 | 0 |
| 75 | 10 | 3 | 2 |
| **85 (new default)** | **13** | **0** | **2** |
| 100 (old default) | 12 | 0 | 3 |

Before KI-22, 100 gave 13/15 with 1 duplicate and 1 merge. The only misses left at 85 are demo seeds 2 and 4: the demo
world's two people stand 155 cm apart and are seen in separate frames, so drift merges them. Headless 20 s demo now
finds both (S-0001 and S-0002). Regression test: `test_one_survivor_record_per_person` (3 seeds, ~1.7 s).

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
| 11:35 | 58c8c11 | agent/station -> main (0f4ea19, ★ C1-C7) | 121 passed | 1 survivor, 0 contacts, 0 trips | clean |
| 10:37 | c73ec55 (B milestone) | origin/main into agent/station | 121 passed (3.5 s) | 1 survivor, 0 contacts, 0 watchdog trips | Removed `sync.sinks: []` from laptop/sim as B requested. |

## Known limits

- Windows `start.bat` not yet run on a real Windows machine.
- `--share` shows every LAN address it finds. Venue Wi-Fi sometimes blocks devices from seeing each other: use a phone hotspot.
- Setup needs Python 3.10+ already installed (the launchers say where to get it).
