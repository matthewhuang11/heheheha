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
- **Simulator camera:** `sim` uses its drawn camera view, so a fresh simulator run needs no webcam or macOS camera permission.

## Survivor records vs people seen (sim, 300 s AUTO, fast-forwarded clock, 5 seeds x 3 worlds)

People "seen" = came within 2.5 m in view. Records = entries the registry created. Simulated
detections now include a stable per-person track ID; the registry prefers that identity over a
spatial merge, while real untracked detections retain the existing spatial fallback.

| Matching | runs exact (of 15) | extra (duplicate) records | missing (merged) records |
| --- | --- | --- | --- |
| Spatial merge only (`merge_cm: 85`) | 13 | 0 | 2 |
| **Stable sim track ID + spatial fallback** | **15** | **0** | **0** |

The affected demo people stand 155 cm apart and appear in separate frames, so spatial estimates alone
merged them in seeds 2 and 4. `test_one_survivor_record_per_person` now runs all 15 deterministic
cases at a fast-forwarded clock (about 13 seconds).

## Fresh-machine test log

| When | Machine | How | Result | Time | Snags (fixed?) |
| --- | --- | --- | --- | --- | --- |
| 10:33 | Mac (arm64, Python 3.13) | fresh `git clone -b agent/station`, `./start.sh`, pick 1 | dashboard served, but **401** | ~60 s | `.env.example` (old) had `SCOUTBOT_TOKEN=replace_with_...`, copied into `.env` => dashboard locked. **Fixed** in a8386b7: setup blanks placeholders; settings ignores placeholder values in an existing `.env`. |
| 10:35 | Mac (arm64, Python 3.13) | fresh clone, `./start.command` (menu 1, share y) | **pass**: localhost 200, LAN URL 200, Start auto over WebSocket drives (pose moved 60,200 -> 174,252; 0 contacts) | 58 s clone -> dashboard (pip cache warm, YOLO included) | none |
| 10:36 | Linux Docker `python:3.10-slim` | fresh clone, `scripts/setup.py --no-yolo`, tests, headless 20, `./start.sh sim --share` | **pass**: 117 tests, headless 0 contacts / 1 survivor, dashboard 200 | setup 29 s | the slim image needs `libgl1 libglib2.0-0` for OpenCV (normal desktops have them). Doctor now explains this if OpenCV won't load. |
| 12:14 | Mac (arm64, Python 3.13) | station branch, setup then full suite and 60 s demo sim | **pass**: 136 tests; 1 survivor, 0 contacts, 0 watchdog trips | 63 s demo | sim initially opened an unnecessary denied webcam. **Fixed**: `sim` now uses its drawn camera, verified by the regression test. |
| - | Windows | `start.bat` | written and reviewed, **not run** (no Windows machine yet) | | Ask a teammate with Windows to double-click it and send the screen output. |
| 12:57 | Mac (arm64, Python 3.13) | fresh local clone of final `main`, `scripts/setup.py --no-yolo`, then `./start.sh doctor` and a 20 s sim | **pass**: setup created `.venv` and blank `.env`; launcher worked; sim found 1 survivor with 0 contacts / 0 watchdog trips | ~60 s setup + sim | Camera permission was denied, as the doctor reported; the simulator needs no camera. Remote fresh-clone authentication was unavailable to this integration environment, so this was a local-clone check. |

## Laptop run with real keys (C8, 11:46)

`python -m scoutbot --profile laptop` with Matthew's `.env` (keys never printed):
- Camera healthy (auto index), YOLO running at ~67 fps on the M-series Mac, Gemini scene OK (1.5 s per call).
- **Bug found, fixed (1f673bb, wiring edit in B's `talk` section):** every Gemini talk call failed with
  `400 INVALID_ARGUMENT: Manually set deadline 8s is too short. Minimum allowed deadline is 10s`. `talk.gemini.timeout_s` 8 -> 12.
- After the fix: typed "My leg is stuck under a shelf, I can't move it." -> Gemini reply spoken ("I am here and help is on
  the way...") and triage **IMMEDIATE (trapped)** by `gemini-flash-lite-latest`, within ~5 s.
- **Bug found, fixed (193398f):** sim survivors were saved in `data/` and reloaded into laptop runs. The sim now uses `data/sim/`.
- Known: while YOLO is still loading (first ~5 s), Gemini's people report can create a survivor, and YOLO then creates a
  second one at the same spot. Both go through the same merge rule, so this is rare. Watching it.
- Ollama not installed on this Mac: the chip is red, as expected.

## Integration log

| Time | main before | Merged in | Tests | Headless 20 s (demo) | Notes |
| --- | --- | --- | --- | --- | --- |
| 11:35 | 58c8c11 | agent/station -> main (0f4ea19, ★ C1-C7) | 121 passed | 1 survivor, 0 contacts, 0 trips | clean |
| 10:37 | c73ec55 (B milestone) | origin/main into agent/station | 121 passed (3.5 s) | 1 survivor, 0 contacts, 0 watchdog trips | Removed `sync.sinks: []` from laptop/sim as B requested. |
| 12:14 | 8f208ea | C13/C15 station validation before merge | 136 passed (6.5 s) | 1 survivor, 0 contacts, 0 watchdog trips | Continue-search and record/replay regression tests pass. A has unmerged camera/YOLO work; B has an unmerged reply-filter fix, so neither was merged directly into Station. |
| 12:17 | f2f3fc6 | agent/station -> main (C13, C15, simulator camera) | 136 passed (6.3 s) | 1 survivor, 0 contacts, 0 watchdog trips | clean; pushed to `origin/main` |
| 12:27 | station survivor-track branch | stable simulated survivor identities | 137 passed (15.6 s) | 2 survivors, 0 contacts, 0 watchdog trips | full 5 seeds x 3 worlds sweep: 15/15 exact |
| 12:29 | 1d0110b | agent/station -> main (survivor identity matching) | 137 passed (15.3 s) | 2 survivors, 0 contacts, 0 watchdog trips | clean; pushed to `origin/main` |
| 12:37 | 219082b | agent/station -> main (C13 Fuser/gate suppression) | 137 passed (14.9 s) | 2 survivors, 0 contacts, 0 watchdog trips | handled, distinct, and 60 s expiry regressions pass |
| 12:53 | 6c112b3 | agent/robot -> main (`dc0bd68`) | 144 passed (13.4 s) | 1 survivor, 0 contacts, 0 watchdog trips | camera auto-detection, YOLO/Pi tooling, and Robot regressions integrated; pushed to `origin/main`. |
| 12:55 | dc0bd68 | agent/cloud -> main (`3b61ce8`) | 144 passed (12.7 s) | 1 survivor, 0 contacts, 0 watchdog trips | safe survivor-reply filtering integrated; pushed to `origin/main`. |

## Known limits

- Windows `start.bat` not yet run on a real Windows machine.
- `--share` shows every LAN address it finds. Venue Wi-Fi sometimes blocks devices from seeing each other: use a phone hotspot.
- Setup needs Python 3.10+ already installed (the launchers say where to get it).
- Final integration environment had no usable LAN address, denied camera permission, and no running Ollama; therefore this pass did not repeat the phone dashboard, webcam, local-voice/Ollama, or live Mongo/Tiger checks.
