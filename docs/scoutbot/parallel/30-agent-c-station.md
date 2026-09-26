# Agent C – Station (runtime, dashboard, survivors, simulator, setup on any computer, integration)

> **Brief (paste this as the agent's first message):**
> You are Agent C on a 3-agent team finishing Scoutbot, a disaster-response robot for a hackathon happening today. The repo is `heheheheha` (GitHub `origin`). Read, in order: `docs/scoutbot/parallel/00-START-HERE.md`, `01-shared-rules.md` (required: ownership and git rules), `02-codebase-map.md`, `03-contracts.md`, `04-known-issues.md`, then this file (`30-agent-c-station.md`) fully. You own the base station and the glue: the runtime, shared state and types, settings and profiles, the FastAPI server and the responder dashboard, the survivor registry, pose and map, the simulator, one-step setup on ANY computer (Mac, Windows, Linux), the README, and keeping `main` green as the three branches merge. Work only on branch `agent/station`. Commit every working step (at least every 30 minutes), push after every commit, merge `origin/main` into your branch at least hourly, merge to `main` at every ★ milestone (only when all tests and the 20 s headless sim pass), and keep your section of `docs/scoutbot/STATUS.md` current. You're also the integrator: after A or B merges to main, pull it and check that everything still works together. Handle requests addressed to you in STATUS before starting new P1/P2 work.

## Context you need

- **Matthew's top priority for you:** "it should work from ANY computer, very easily and seamlessly." A teammate with a fresh laptop should get from `git clone` to a working dashboard with **one double-click or one command**, without reading code.
- **The dashboard is a web page**, so any device on the same Wi-Fi can use it once the server is shared.
- **Your known issues:** KI-02, 07, 08, 09, 21, 22 (with A), 30, 31, 32, 34 (your files), 37, 38 (with A), 42, 44.

## Your files

`scoutbot/runtime.py`, `state.py`, `types.py`, `settings.py`, `__main__.py`, `__init__.py`, new `start.py`; `scoutbot/server/*` (including `static/responder.html`); `scoutbot/survivors/*`; `scoutbot/hw/simworld.py`, `distance_fake.py`, `motors_fake.py`; `config/profiles/base.yaml` layout plus sections `control`, `survivors`, `sim`, `server`; `mac.yaml`/`laptop.yaml`, `sim.yaml`; `config/worlds/*`; `requirements.txt`; `README.md`; `run_*.command`, new `start.command`, `start.sh`, `start.bat`; new `scripts/setup.py`; new `scoutbot/tools/doctor.py`; `.gitignore`, `.gitattributes`; the legacy `web_demo.py`, `dashboard.html`, `demo.py`, `simulate.py` (keep them working only); tests `test_server.py`, `test_registry.py`, `test_simworld.py`, `test_tools_smoke.py`, new `test_station_*.py`; `docs/scoutbot/station.md`; the layout of `docs/scoutbot/STATUS.md`.

## Setup

```bash
git fetch origin && git checkout -b agent/station origin/main && git push -u origin agent/station
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python -m pytest -q tests
python -m scoutbot --profile sim --set sim.world=demo       # open http://localhost:8000, press Start auto
```

Create `docs/scoutbot/station.md` with the headings "What works", "How to run", "Fresh-machine test log", "Integration log", "Known limits". `docs/scoutbot/STATUS.md` already exists: fill in your section first.

---

## P0: "any computer, one step" (start now; highest priority)

### C1. Profiles and settings (KI-32, KI-34)
- **Rename** `config/profiles/mac.yaml` → `laptop.yaml` with `git mv`. Header comment: "Any laptop (Mac, Windows, Linux): its webcam + fake distance sliders + fake motors."
- **In `settings.py`:**
  - `ALIASES = {"mac": "laptop"}`, applied before loading, so `--profile mac` and Codex's launchers still work.
  - Every `read_text()`/`open()` uses `encoding="utf-8"`.
  - `CAMERA_INDEX` that isn't a number is ignored.
  - A clear error for an unknown profile that lists the available profiles.
- Remove `sync.sinks: []` from `laptop.yaml` and `sim.yaml` once B's `resolve_sinks`/`auto` is in (coordinate via STATUS).
- **Tests:** the alias works; the unknown-profile message lists the choices; utf-8 content loads.

### C2. One-step setup: `scripts/setup.py` (KI-30, KI-37)
Uses **only the Python standard library** (it runs before anything is installed). Works on Mac, Windows, Linux and the Pi.
1. If Python < 3.10: exit with a plain message and the download link.
2. Create `.venv` with `venv.EnvBuilder(with_pip=True)` if it's missing (the venv python is `.venv/bin/python`, or `.venv\Scripts\python.exe` on Windows).
3. `pip install --upgrade pip`, then `pip install -r requirements.txt` (or `requirements-pi.txt` with `--pi`).
4. Unless `--no-yolo`: `pip install -r requirements-yolo.txt` (A creates it; if it's missing, install `ultralytics`). **A failure here is a warning**, "YOLO didn't install; Gemini will spot people instead; retry later with ...", not a stop.
5. If `.env` is missing, copy `.env.example` → `.env` and say "open .env and paste the keys you have (all optional)".
6. Run `scoutbot.tools.doctor --quiet` and print how to start.
- Show each step as `==> Installing packages (a few minutes the first time)`, echo the commands being run, and on failure say "that step failed, scroll up, fix, run setup again". **It must be safe to run again** at any time.
- **Move `ultralytics` out of `requirements.txt`** (KI-37). Keep `requirements.txt` to core packages, with a header comment on what it is and the easiest way to install.

### C3. Launchers (KI-02)
- `start.command` (Mac double-click):
  - `cd` to the script's folder.
  - If `.venv/bin/python` is missing: check `python3` exists (otherwise print the download link and wait for a key press), then run `python3 scripts/setup.py`.
  - Then `.venv/bin/python -m scoutbot.start "$@"`, and wait for a key press at the end so the window doesn't vanish.
- `start.sh` (Linux/Pi/Mac terminal): the same, without the waits. It ends with `exec .venv/bin/python -m scoutbot.start "$@"`.
- `start.bat` (Windows, **CRLF line endings**):
  - `cd /d "%~dp0"`.
  - Prefer `py -3`, else `python`.
  - If `.venv\Scripts\python.exe` is missing, run setup; on failure, print "install Python 3.10+ from python.org and tick 'Add python.exe to PATH'" and `pause`.
  - Then `.venv\Scripts\python.exe -m scoutbot.start %*` and `pause`.
- `.gitattributes`: `*.bat text eol=crlf`, `*.sh text eol=lf`, `*.command text eol=lf`. Run `chmod +x` on `start.command`, `start.sh` and `scripts/setup.py` (git keeps the executable bit).
- **Fix the Codex launchers** (`run_*.command`): `PY=python3; [ -x .venv/bin/python ] && PY=.venv/bin/python`, then `"$PY" -m ...`. Make `run_scoutbot_mac.command` use `--profile laptop`.

### C4. The start menu: `scoutbot/start.py`
`python -m scoutbot.start` shows:
```
Scoutbot
  1) Simulated room demo (no camera or robot needed)
  2) Use this computer's webcam (fake distance sliders, no motors)
  3) Webcam, but pretend there is no internet (tests Ollama + queued sync)
  4) The real robot (run this ON the Raspberry Pi)
  5) Check my setup
  6) Run the tests
Pick a number [1]:
```
- After choices 1–4 it asks: "Let phones / other laptops on this Wi-Fi open the dashboard too? [y/N]". Yes adds `--share`.
- It runs the chosen command with `sys.executable` from the repo root.
- `python -m scoutbot.start sim --share` skips the menu. The choice names are `sim`, `laptop`, `offline`, `robot`, `doctor` and `test`.
- Ctrl-C returns cleanly. An unknown choice prints the options.
- **Test:** `tests/test_station_start.py` calls `main(["doctor"])` with `subprocess.call` monkeypatched, and asserts the command built for each choice.

### C5. Doctor: `scoutbot/tools/doctor.py`
Prints `[ OK ]`, `[ -- ]` (optional, missing) or `[FAIL]` (a blocker) lines in plain words:
- Python version and OS.
- Core packages. If any are missing, `[FAIL]` "run setup again", and stop here.
- Optional packages, each with what it unlocks: google-genai (Gemini), ultralytics (YOLO; without it Gemini spots people), pymongo, psycopg, pytest.
- `.env` exists.
- Each key: set, or not set plus what turns off without it (Gemini: sensors only plus Ollama/canned replies; ElevenLabs: built-in voice; Mongo/Tiger: saved locally only).
- The sync sinks that will run.
- Internet reachable (use B's `NetWorker(cfg, Shared()).check()`).
- LAN address(es), with a tip to use `--share`.
- Ollama: running at the profile URL, and the model pulled. Otherwise, the exact `ollama pull` command.
- A built-in voice is available (B's `LocalVoice().cmd`).
- Camera: use A's `open_best_camera`. If A's work hasn't merged yet, open `hw.camera_index` directly and note it. Report "camera N works", or "no camera (Mac: allow Camera for Terminal in System Settings > Privacy & Security > Camera)".
- Ends with "Ready." or "N problem(s) to fix", then "Start with: python -m scoutbot.start (or double-click start.command / start.bat)".
- Exit code 1 only for real blockers (Python < 3.10, missing core packages). `--quiet` hides the OK lines; `--no-camera` skips the camera check.
- Add `doctor` to `test_tools_smoke.py`.

### C6. `--share`, and Windows console safety (KI-31, KI-34)
- **`python -m scoutbot --share`** sets `server.host=0.0.0.0` and prints:
  - `[scoutbot] dashboard: http://localhost:8000`
  - `[scoutbot] other devices on this Wi-Fi: http://192.168.x.y:8000` (plus `/?token=...` if `SCOUTBOT_TOKEN` is set).
- The LAN IP helper goes in `scoutbot/net.py` (B's file: a wiring edit), or in your `runtime.py`/`start.py`. Use the UDP-socket trick with a hostname fallback, and exclude `127.*`.
- **In `__main__`:** `sys.stdout.reconfigure(errors="replace")` (and stderr), so odd characters never crash a Windows console.
- **Replace `±`** in your prints with `+/-`. Make every file your code reads or writes utf-8.
- If the port is busy, print "port 8000 is in use; try --set server.port=8001" instead of a traceback.
- ★ Merge (C1–C6).

### C7. Fresh-machine test (the real proof)
- **In a new folder:** `git clone <repo> scoutbot-fresh && cd scoutbot-fresh`, then double-click `start.command` (or run `./start.sh`), pick 1 (sim), and confirm the dashboard works and Start auto drives. Time it and note every snag in `station.md`'s "Fresh-machine test log". Fix every snag.
- Repeat on Linux (any Linux box, Docker `python:3.11`, or WSL) with `./start.sh sim`.
- If a teammate has Windows, have them double-click `start.bat` and send you the screen output.
- **Python 3.10 check:** run the tests under 3.10 if you can (`uv python install 3.10`, or pyenv), since the Mac's system Python may be 3.10.
- ★ Merge.

---

## P1: dashboard and runtime quality

### C8. A real run on the laptop profile + the demo script
- Run `python -m scoutbot --profile laptop` with Matthew's keys and walk through the demo script in [40-integration-and-demo.md](40-integration-and-demo.md) step by step. Log what fails. Fix your parts; file STATUS requests for A and B.
- **Checks:**
  - The chips match reality (see C10).
  - The veto shows when driving into the slider-made wall (center slider 10 cm + hold W).
  - The drive pad works with a mouse, keys and touch.
  - The survivor card updates live (chat and triage).
  - The map draws the trail.
  - The event log is readable.

### C9. Safety of the commands (KI-07) and performance (KI-08)
- `sim` and `sensor` commands are refused unless `server.test_controls` is true (`pi.yaml` sets it false). Test it.
- `Registry.summaries()` gives light survivor rows without copying chats. Cache the state's survivor list for 0.5 s (invalidate it on the `survivor`/`chat`/`triage` bus events). `state()` must stay under about 5 ms with 20 survivors × 50 messages each: add a quick test that times it.

### C10. Dashboard polish (`responder.html`)
- **Chips (KI-44):** "Gemini scene" (from `vlm.failures`/`vlm.error` and `online`) and "Gemini talk" (from `services.gemini`), as separate chips or one with two dots. Hovering any chip shows the full status text.
- **Offline banner:** "No internet: replies from Ollama, survivors queued for sync", showing the queued counts.
- **Phone layout:**
  - Single column at < 800 px, with the STOP button always visible in the sticky header.
  - The drive pad has 64 px+ touch targets, and uses `touch-action: none` on the pad so the page doesn't scroll while driving.
  - Test with Chrome devtools phone emulation.
- **Map:** a "fit all / follow robot" toggle, a scale bar, survivor pins clickable to select, and the drift circle labeled.
- **Survivors:**
  - Sort by triage (red first), then by last seen.
  - **Export** button → download JSON and CSV of all survivors (id, category, position, sightings, last seen, summary, last 5 chat lines). This can be client-side from `/api/survivors`.
- **Connection:** a clear full-screen "Robot link lost – motors stopped – reconnecting…" (it exists). Also show the round-trip time.
- **Accessibility:** buttons have labels; colors aren't the only signal (the triage tag has text).
- **No framework, no build step.** Keep it one HTML file with inline JS/CSS, and escape all user text (chat is user-typed).

### C11. Survivors, pose and map
- **KI-22 (with A's numbers):** `DeadReckoning` uses a per-action speed (`motion.forward_cm_s`, `slow_cm_s`, `backup_cm_s`, `turn_deg_s`), interpolated by wheel fraction during ramps. Keep the sim consistent: `simworld` uses the same calibration.
- **KI-09:** use `shared.det_frame` if A provides it (the frame YOLO actually saw) for snapshots.
- **KI-21:** make `sim.fake_people: false` actually hide the sim survivors.
- **Survivor counts:** in the sim, over 5 seeds each of `room_basic`, `rubble` and `demo`, the number of survivor records should equal the number of people seen. Tune `survivors.merge_cm`/slack if not, and put a table in `station.md`. Add the check to `test_simworld.py` at a fast-forwarded clock (reuse the `run()` helper there).
- If A adds `hw.sensor_angles`/`sensor_beam_deg` (KI-39), `simworld.sensors()` and `MapBuilder` must read them.

### C12. Integration duty (every time A or B merges to main)
```bash
git fetch origin && git merge origin/main
python -m pytest -q tests
python -m scoutbot --profile sim --set sim.world=demo --headless 60      # check: explores, 0 contacts, survivors found
python -m scoutbot --profile laptop       # quick look at the dashboard: chips, video, a survivor chat
```
- Record the result in `station.md`'s "Integration log" (time, commits, pass/fail, problems).
- **If `main` is broken:** say so at the top of STATUS immediately and ping the agent in their Requests. If it's a one-line fix, fix it on your branch with a clear message and merge it.
- ★ Merge after each integration pass that needed fixes.

---

## P2

### C13. "Continue search" (KI-38, with A)
- **Dashboard:** a button on the survivor card, "Continue search (handled)", sends `{"type":"handled","survivor_id":"S-0001"}`.
- **Runtime:** stores handled survivors with a 60 s expiry, and passes their positions to A's `Fuser.suppress(...)`/gate hold each tick.
- **Survivor record:** a new field `handled_at` (with a default None, per the contract rule).
- A implements the fusion/gate side. Agree the function signature in STATUS first.

### C14. README rewrite (KI-42)
1. **Top:** a 5-line quick start: "Double-click `start.command` (Mac) or `start.bat` (Windows), or run `./start.sh` (Linux). Pick 1 for the simulator."
2. **Then:**
   - What Scoutbot is (3 sentences + the diagram image, if Matthew adds it to the repo).
   - Keys (a table: key, what it turns on, where to get it).
   - Profiles.
   - Sharing the dashboard with phones.
   - The Raspberry Pi (link to A's `robot.md`).
   - The cloud (link to B's `cloud.md`).
   - The demo script.
   - Troubleshooting: camera permission on Mac; port in use; Ollama not running; Windows "python not found"; YOLO slow; offline.
3. Keep the old "Robot Brain Laptop Harness" section at the bottom under "Legacy debug tools".

### C15. Recording and replay
- `--record` saves frames (2 fps) plus sensor readings to `data/recordings/<time>/`.
- `--set hw.camera=folder --set hw.camera_folder=data/recordings/<time>` replays them (the camera already exists). Add a matching `distance: replay` driver that reads the recorded sensor lines.

---

## Pitfalls

- **macOS camera capture must stay on the main thread.** uvicorn runs in a background thread (it already does this). Don't move the camera loop.
- **`Runtime(..., start_workers=False)`** is how tests build a runtime without threads. Keep that working.
- **When you change `state()` or the WebSocket messages,** update `03-contracts.md §8` in the same commit and note it in STATUS.
- **`responder.html` must escape** every user-typed string (chat and survivor text): use `textContent`, not `innerHTML`, for user text.
- **`.bat` files need CRLF** (`.gitattributes` handles it). Test the bat logic mentally for paths with spaces (quote everything).
- **Never make `setup.py` import any third-party package.** It runs before they exist.

## C is done when

- [ ] A fresh clone starts with one double-click on Mac (and one command on Linux), and Windows `start.bat` is written and reviewed (tested if a Windows machine is available).
- [ ] The doctor explains any missing piece in plain words.
- [ ] `--share` works from a phone on the same Wi-Fi.
- [ ] The demo script runs cleanly in the sim and on the laptop webcam, with any remaining failures logged as requests.
- [ ] KI-02, 07, 08, 21, 30, 31, 32, 34, 37, 42, 44 fixed; KI-22 done with A's numbers.
- [ ] Every A/B merge has been integration-checked and logged. `main` is green, tagged `demo-ready` at the end.
