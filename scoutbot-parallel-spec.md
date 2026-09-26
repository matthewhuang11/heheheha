# Scoutbot – Three-Agent Parallel Build Spec

Date: 2026-09-26. Repo: `heheheheha` (GitHub `origin`). Base commit: `main` at `7709cef` or later.
Read first: `scoutbot-next-steps-spec.md` (the full design) and the architecture diagram (robot → base-station laptop → cloud).

This spec splits the remaining work into three jobs that can run **at the same time** without stepping on each other:

| Agent | Job | Branch | Commit prefix |
| --- | --- | --- | --- |
| **A – Robot** | Hardware drivers, YOLO person detection, safety, Raspberry Pi bring-up | `agent/robot` | `[robot]` |
| **B – Cloud & Talk** | Gemini, Ollama, the online/offline router, ElevenLabs voice, MongoDB and Tiger Data sync | `agent/cloud` | `[cloud]` |
| **C – Station** | Dashboard, server, runtime wiring, simulator, survivors/map, setup on any computer, README, integration | `agent/station` | `[station]` |

---

## 0. Before the agents start (Matthew, 2 minutes)

1. Push the current work so all agents start from the same place. Right now GitHub is far behind your Mac:
   ```bash
   cd heheheheha && git checkout main && git push origin main
   ```
2. Make sure `.env` on the machine(s) the agents use has the keys you have: `GEMINI_API_KEY`, `ELEVENLABS_API_KEY`, `MONGODB_URI`, `TIGER_DATABASE_URL`. **Never commit `.env`.**
3. Install Ollama (ollama.com) on the laptop Agent B uses, and open it once.
4. Give each agent: this file, its own section below, and section 1 (rules). Paste the "Brief" box at the top of its section as the first message.

---

## 1. Rules for all three agents (read fully)

### 1.1 What already exists (do not rebuild it)
Everything on the diagram has first-version code, and 99 tests pass. The job now is to **make each piece work for real, fix what breaks, and polish**. It is not a rewrite.

| Folder | What it is |
| --- | --- |
| `robot/` | The original driving brain (8 rules, filters, controller). **Nobody changes it** unless all three agree in `STATUS.md`. |
| `scoutbot/runtime.py` | Starts all workers; the control loop is the only thing that drives motors |
| `scoutbot/hw/` | Camera / distance sensors / motors interfaces + fake and real versions + simulator |
| `scoutbot/safety/` | Safety gate, dead-man stop, STOPPED/AUTO/MANUAL modes |
| `scoutbot/perception/` | YOLO, fusion with Gemini, remote YOLO worker |
| `scoutbot/survivors/` | Survivor registry, dead-reckoning pose, rough map |
| `scoutbot/talk/` | Gemini / Ollama / canned replies, circuit breaker, rule-based triage |
| `scoutbot/voice/` | ElevenLabs, local voice, fake voice |
| `scoutbot/sync/` | Local-first outbox, MongoDB and Tiger Data sinks |
| `scoutbot/server/` | FastAPI server + `static/responder.html` dashboard |
| `scoutbot/tools/` | camcheck, yolo_bench, ollama_check, sensor_check, motor_check |
| `config/profiles/` | `base.yaml` defaults + `mac`, `sim`, `pi` profiles; `config/worlds/` sim rooms |

Run things with: `python -m scoutbot --profile sim --set sim.world=demo` (no hardware needed), `--profile mac` (webcam), `--headless 30` (no server, quick check). Tests: `python -m pytest -q tests`.

### 1.2 File ownership (the most important rule)
Each file has ONE owner. You may freely edit files you own. For files you don't own:
- **Tiny wiring edits (10 lines or fewer)** are allowed. Commit them **alone** with a message like `[cloud] wiring: runtime calls resolve_sinks()`, push at once, and note it in `STATUS.md`.
- **Anything bigger:** write a request in the owner's "Requests" list in `STATUS.md`, and keep working around it.

| Owner | Files |
| --- | --- |
| **A – Robot** | `scoutbot/hw/` **except** `simworld.py`, `distance_fake.py`, `motors_fake.py`; `scoutbot/perception/`; `scoutbot/safety/`; `scoutbot/tools/{camcheck,yolo_bench,sensor_check,motor_check}.py`; `config/profiles/pi.yaml`; `scripts/pi_setup.sh`; `requirements-pi.txt`; new `requirements-yolo.txt`; tests `test_gate.py`, `test_deadman.py`, `test_fusion.py`; new `docs/scoutbot/robot.md` |
| **B – Cloud & Talk** | `scoutbot/talk/`; `scoutbot/voice/`; `scoutbot/sync/`; `scoutbot/net.py`; `robot/vlm.py` (the Gemini scene call – the only `robot/` file B may touch, and without changing the `SceneReport` fields); `check_gemini.py`; `scoutbot/tools/ollama_check.py` + new cloud tools; `.env.example`; tests `test_router.py`, `test_triage.py`, `test_outbox.py`, `test_talk_worker.py`, `test_isolation.py`; new `docs/scoutbot/cloud.md` |
| **C – Station** | `scoutbot/runtime.py`, `state.py`, `types.py`, `settings.py`, `__main__.py`, new `start.py`; `scoutbot/server/` (incl. the dashboard); `scoutbot/survivors/`; `scoutbot/hw/simworld.py`, `distance_fake.py`, `motors_fake.py`; `config/profiles/{base,mac,sim}.yaml` + `config/worlds/`; `requirements.txt`; `README.md`; all `*.command`, new `start.*` launchers, new `scripts/setup.py`, new `scoutbot/tools/doctor.py`; `.gitignore`, `.gitattributes`; tests `test_server.py`, `test_registry.py`, `test_simworld.py`; `docs/scoutbot/STATUS.md` layout |

**Shared config keys:** anyone may add keys to `base.yaml`, but only inside their own sections. A: `hw`, `motion`, `speeds`, `safety`, `perception`. B: `talk`, `voice`, `sync`, `net`, `scene`. C: `control`, `survivors`, `sim`, `server`. Add keys; never rename or remove someone else's.

**`requirements.txt`:** C owns it. A and B may **append** a line (for example `pymongo`) with a comment saying who needs it.

### 1.3 Contracts between the agents (don't break these)
Changing any of these needs a note in `STATUS.md` **before** you push, plus updating every caller in the same commit.
- `Camera.read() -> frame|None`, `DistanceSensors.read() -> robot.types.Sensors`, `Motors.apply(action) / stop() / current()` (`scoutbot/hw/base.py`)
- `PersonDetection` fields and `Pose` fields (`scoutbot/types.py`) – add fields with defaults only
- `TalkWorker.submit(kind, sid, text, source)` with kinds `new_survivor`, `survivor_says`, `responder_says`, `retriage`
- `Speaker.say(text, priority, key=None)`
- `Outbox.put_survivor(survivor)`, `Outbox.add_rows(kind, rows)` with kinds `sightings`, `telemetry`
- `shared.services[...]` keys: `gemini`, `ollama`, `yolo`, `voice` (the dashboard chips read them)
- `Runtime.state()` JSON keys and the WebSocket message types (`heartbeat`, `mode`, `estop`, `drive`, `chat`, `retriage`, `sim`, `sensor`) – C owns these, and A/B read them
- Safety invariants (spec section 6): boots STOPPED; E-stop from any mode; every motor command goes through the gate; the motor watchdog is 0.5 s; manual commands expire after 0.3 s; talk/voice/sync code never imports `scoutbot.hw`, `scoutbot.safety` or `scoutbot.runtime` (`tests/test_isolation.py`)

### 1.4 Git workflow – commit and push often so everyone keeps up
```bash
git fetch origin && git checkout -b agent/<name> origin/main        # once, at the start
```
- **Commit small and often:** every working step, at least every 30 minutes. Message = prefix + what + why, e.g. `[robot] yolo: load NCNN model folder so the Pi 4 runs ~3x faster`.
- **Push after every commit:** `git push -u origin agent/<name>`.
- **Pull the others' work in at least every hour**, and before merging to main: `git fetch origin && git merge origin/main`. Use merge, **not rebase**, because the branches are already pushed. **Never force-push.**
- **Merge to `main` when a milestone works (marked ★ below):**
  ```bash
  git fetch origin && git checkout main && git merge --ff-only origin/main
  git merge --no-ff agent/<name> -m "merge agent/<name>: <milestone>"
  python -m pytest -q tests          # MUST pass; if not, fix on your branch first
  git push origin main && git checkout agent/<name> && git merge main && git push
  ```
- `main` must always pass all tests. If a push to main is rejected (someone merged first), fetch, merge again, re-run tests, push.
- **Never commit:** `.env`, `data/`, `logs/`, model weights (`*.pt`, `*_ncnn_model/`), `.venv/`, `__pycache__/`. A adds the model patterns to `.gitignore` (tiny wiring edit to C's file).
- End every commit message with the attribution lines your tool normally adds.

### 1.5 STATUS.md – how the agents stay in sync
C creates `docs/scoutbot/STATUS.md` in its first commit, with one section per agent. **Only edit your own section**, so there are no merge conflicts. Update it with every push to main, and at least every hour:
```
## A – Robot            (updated 14:05)
Done: ...
Doing now: ...
Next: ...
Blocked on: ...
Requests for B: ...
Requests for C: ...
Changed a contract? ...
```
Read the other two sections every time you merge `origin/main`.

### 1.6 Definition of done for every task
- It works for real (not only in a test), you checked it yourself, and you wrote down how you checked it.
- New logic has a test. All tests pass. There is no new warning at startup.
- Plain-language notes live in your `docs/scoutbot/<area>.md` (what works, how to run it, the numbers you measured).
- Secrets never show up in logs, commits or the dashboard.

### 1.7 Test setup on any machine
```bash
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt                          # A also: pip install ultralytics
python -m pytest -q tests
```

---

## 2. Agent A – Robot (hardware, YOLO, safety, Pi)

> **Brief (paste this):** You are Agent A on a 3-agent team building Scoutbot, a disaster-response robot for a hackathon. Read `scoutbot-parallel-spec.md` sections 1 and 2, and `scoutbot-next-steps-spec.md` sections 5, 6, 8 and 14. You own the robot side: hardware drivers, YOLO person detection, the safety layer, and Raspberry Pi 4 bring-up. Work on branch `agent/robot`, commit and push after every working step, merge `origin/main` every hour, update your section of `docs/scoutbot/STATUS.md`, and only edit files you own (section 1.2). The Pi and sensors may not exist yet: do everything you can on a laptop first, and make the Pi steps one-command ready.

### A.P0 – do first (laptop only)
1. **Fix `motor_check`** (bug): it calls `motors.apply(action)` once and then sleeps, but the speed ramp starts from zero on the first call (`Ramp.set` with dt=0), so the wheels never move. Call `apply` at 10 Hz for the whole second, then `stop()`. Add a test using `FakeMotors` that checks `current()` is non-zero during the step.
2. **YOLO for real on the laptop webcam.** `pip install ultralytics`. Run `python -m scoutbot.tools.yolo_bench` (fix anything broken). Then run `python -m scoutbot --profile mac`. Standing in front of the webcam should give a person box on the dashboard, a survivor record, and the robot STOP in AUTO. Record FPS at 320 and 640 in `docs/scoutbot/robot.md`.
3. **Tune the near/mid/far cut-offs** (`perception.yolo.near_frac`, `mid_frac`): stand at 0.7 m, 1.5 m, 2.5 m and 4 m from the webcam and record the box height fraction. Set the cut-offs so near is under 1 m and mid is 1–2.5 m. Write the table in `robot.md`.
4. **NCNN for the Pi:** make `yolo_bench --export-ncnn` export at the chosen `imgsz`, and make `YoloDetector` load an exported folder (`perception.yolo.model: yolov8n_ncnn_model`). Add the weights and exports to `.gitignore`. ★ Merge.
5. **Remote YOLO end to end:** on one laptop, run the robot with `--set perception.yolo.where=remote`, and in a second terminal run `python -m scoutbot.perception.worker_remote --robot http://localhost:8000`. Detections must show on the dashboard, and the chip must say "remote". Fix anything broken. ★ Merge.
6. **Camera auto-detect:** add `open_best_camera(preferred, candidates=range(4))` to `hw/camera_opencv.py`. It tries the preferred index; if that's missing or black (mean < 8), it tries the others and prints which one it used. Use `cv2.CAP_DSHOW` on Windows. Use it in `hw/base.build` and `tools/camcheck.py`, so the wrong `CAMERA_INDEX` never means "no camera".

### A.P1 – Pi bring-up (as soon as hardware exists; prepare scripts before)
7. **Make `scripts/pi_setup.sh` robust.** Tolerate apt packages that don't exist on Bookworm (`libatlas-base-dev`): install the essentials (`python3-venv espeak-ng mpg123 libgl1 i2c-tools`) and the optional ones with `|| true`. Enable I2C. Make the venv and install `requirements-pi.txt` + `requirements-yolo.txt`. Print the IP. It must be safe to run twice.
8. **Bring-up checklist** (next-steps spec section 14): camcheck → yolo_bench on the Pi (NCNN, 320). If under 3 FPS, set `where: remote` in `pi.yaml`. Then sensor_check with a tape measure at 20/50/100 cm, and motor_check with the **wheels off the ground**. Calibrate: time 1 m forward, 1 m slow, and one 360° turn, and fill in `motion.*` in `pi.yaml`. Fix wheel directions in config, not wiring. Record everything in `robot.md`.
9. **Pins:** get the real GPIO numbers from the hardware team and put them in `pi.yaml` (base has placeholders). Confirm whether the distance sensors are HC-SR04 (ultrasonic) or VL53L0X/VL53L1X (ToF). If ToF, test `distance_tof.py` and fix it.
10. **Dead-man on real hardware:** with the wheels off the ground, drive in MANUAL from the dashboard on another laptop, then turn that laptop's Wi-Fi off. The wheels must stop within 0.5 s. Also kill the Python process: the wheels must stop (atexit + watchdog). ★ Merge.

### A.P2 – if time allows
11. **Sensor blind spot:** the sim showed the robot's side can clip a thin wall end at about 80° off heading, where no sensor sees. Add `hw.sensor_angles` (default `[30, 0, -30]`), recommend a layout to the hardware team (for example ±45°), and ask C (via STATUS) to make `simworld.py` and `mapping.py` read the same setting.
12. **Downward cliff sensor:** `robot/brain.py` already accepts `cliff` in `Context`. Add an optional 4th distance reading to the driver interface (`read_cliff()`, default None) and a request for C to pass it to `controller.step(..., cliff=)`.

**A is done when:** YOLO works on the webcam with measured cut-offs; NCNN and remote modes work; motor_check is fixed; the Pi scripts are ready (or the Pi checklist has passed); and `robot.md` has all the numbers.

---

## 3. Agent B – Cloud & Talk (Gemini, Ollama, router, voice, sync)

> **Brief (paste this):** You are Agent B on a 3-agent team building Scoutbot, a disaster-response robot for a hackathon. Read `scoutbot-parallel-spec.md` sections 1 and 3, and `scoutbot-next-steps-spec.md` sections 10–12. You own everything that talks to the cloud or makes words: the Gemini scene call and triage/replies, Ollama (offline brain), the online/offline router, the ElevenLabs voice and its local fallback, and MongoDB + Tiger Data survivor sync. The keys are in `.env` (never print or commit them). Work on branch `agent/cloud`, commit and push after every working step, merge `origin/main` every hour, update your section of `docs/scoutbot/STATUS.md`, and only edit files you own (section 1.2). Your code must never import motor, safety or runtime code.

### B.P0 – do first
1. **`.env.example` cleanup:** every optional key empty (a placeholder like `replace_with...` would turn on the dashboard token or fake database URLs), with one comment line each on what it does and where to get it. Add `GEMINI_TALK_MODEL=` (optional) and `CAMERA_INDEX=` (optional).
2. **Gemini scene, live.** Run `python -m scoutbot --profile mac` with the real key. The dashboard "Scene" row must update every ~2 s. Measure latency (p50 and p95) over 30 calls and the valid-JSON rate. If `GEMINI_MODEL` fails, choose the fastest model that works. Use `check_gemini.py`. Record the results in `docs/scoutbot/cloud.md`.
3. **Gemini triage and replies, live.** Get a survivor (stand in front of the webcam, or use `--profile sim --set sim.world=demo`), then type survivor lines. Check that replies are short, calm and safe, and that triage is valid JSON with sensible categories over 20 tries. Tune `talk/prompts/*.txt` (bump to `_v2` files and keep `_v1`). Add a tool `python -m scoutbot.tools.talk_check` that runs 5 fixed conversations through Gemini and Ollama and prints category, latency and reply text. ★ Merge.
4. **Ollama, real.** `ollama pull qwen2.5:3b`. `python -m scoutbot.tools.ollama_check` must pass (fix the tool if needed; the model-name matching should accept `qwen2.5:3b` and `qwen2.5:3b-instruct...`). Confirm Ollama's `format` JSON-schema mode gives valid triage. Measure the first reply (cold) and the next (warm). Document `OLLAMA_HOST=0.0.0.0` so the Pi can reach the laptop, and test from a second machine if you can.
5. **Router end to end:** on the dashboard, toggle "Simulate offline". The next reply must come from `ollama`, the triage model must show `ollama:qwen2.5:3b`, and driving must not change. Then break Gemini (bad key via `--set` or an env override): after 3 failures the breaker opens, Ollama answers, and after 30 s it probes Gemini again. Stop Ollama as well: canned replies, triage UNKNOWN, no crash. ★ Merge.
6. **ElevenLabs, live on each OS you can reach.** The Mac plays through `afplay`; Linux or the Pi streams through `mpg123`/`ffplay`; Windows has no mp3 player, so request `output_format=pcm_22050`, wrap it as `.wav` (stdlib `wave`) and play it with PowerShell `Media.SoundPlayer`. Measure time-to-first-audio.
7. **Local (offline) voice on each OS:** `say` (Mac), `espeak-ng` (Linux/Pi), and Windows built-in speech via PowerShell `System.Speech`. Offline and without an ElevenLabs key, the robot must still speak.

### B.P1
8. **Sync turns itself on:** add `resolve_sinks(cfg) -> list[str]` in `scoutbot/sync/`. When `sync.sinks` is `"auto"`, include `mongo` if `MONGODB_URI` is set and `tiger` if `TIGER_DATABASE_URL` is set. Ask C (STATUS) to call it in `runtime.py`, or make that ≤10-line wiring edit yourself and announce it. Set `sync.sinks: auto` in `base.yaml`.
9. **MongoDB Atlas, real:** survivors upsert (a newer version wins, an older one is ignored), and sightings and telemetry insert. Test offline for 2 minutes with 2 survivors: records queue. Go online: they appear within 10 s and the outbox empties. Dashboard chip states must be right.
10. **Tiger Data (Tiger Cloud), real:** same test, and confirm `sightings` and `telemetry` are hypertables. Write 3 demo queries in `cloud.md` (survivors by triage; sightings over time with `time_bucket`; robot path from telemetry) plus a matching MongoDB query. These are for the sponsor demo. ★ Merge.

### B.P2 – if time allows
11. **Survivor speech-to-text:** a `SurvivorInput` so survivors can talk instead of a teammate typing (for example ElevenLabs speech-to-text online, or a local model offline). Press-to-talk on the dashboard sends audio; ask C for a small endpoint.
12. A prompt-safety review: replies never promise times, never give medical advice beyond the two allowed lines, and never tell anyone to move toward a hazard. Add tests with canned bad model outputs, and a post-filter if needed.

**B is done when:** Gemini scene, triage and replies work live with measured numbers; offline chat works through Ollama, with canned replies as a last resort; voice works online and offline on Mac (plus any other OS reachable); and Mongo and Tiger sync end to end, with the demo queries written.

---

## 4. Agent C – Station (dashboard, server, runtime, sim, survivors, setup, integration)

> **Brief (paste this):** You are Agent C on a 3-agent team building Scoutbot, a disaster-response robot for a hackathon. Read `scoutbot-parallel-spec.md` sections 1 and 4, and `scoutbot-next-steps-spec.md` sections 3, 4, 7, 9, 13 and 17. You own the base station and the glue: the runtime, shared state and types, settings and profiles, the FastAPI server and responder dashboard, the survivor registry and map, the simulator, one-step setup on any computer (Mac, Windows, Linux), the README, and keeping `main` green when the three branches merge. Work on branch `agent/station`, commit and push after every working step, merge `origin/main` every hour, and only edit files you own (section 1.2). Create `docs/scoutbot/STATUS.md` in your very first commit.

### C.P0 – do first
1. **First commit, within 10 minutes:** `docs/scoutbot/STATUS.md` with the A, B and C sections (template in 1.5). Push, then ★ merge to main right away, so A and B can write their sections.
2. **Any computer, one step:**
   - Rename `config/profiles/mac.yaml` → `laptop.yaml` (it works on any laptop), and keep `mac` working as an alias in `settings.py`.
   - `settings.py`: read every file with `encoding="utf-8"`. Ignore a non-number `CAMERA_INDEX`.
   - `scripts/setup.py` (standard library only): check Python ≥ 3.10; create `.venv`; `pip install -r requirements.txt`; then `requirements-yolo.txt` unless `--no-yolo` (a YOLO failure is a warning, not a stop); `--pi` → `requirements-pi.txt`; copy `.env.example` → `.env` if missing; run the doctor.
   - Launchers: `start.command` (Mac double-click), `start.sh` (Linux/Pi), `start.bat` (Windows, CRLF line endings). If `.venv` is missing they run setup first, then `python -m scoutbot.start`. Add `.gitattributes` (`*.bat eol=crlf`, `*.sh eol=lf`, `*.command eol=lf`). Fix the existing `run_*.command` files: they call `python`, which doesn't exist on many Macs, so use `.venv/bin/python`, else `python3`.
   - `scoutbot/start.py`: a numbered menu. 1 sim demo, 2 laptop webcam, 3 webcam pretending offline, 4 real robot (Pi), 5 doctor, 6 tests. It asks "let other devices on this Wi-Fi open the dashboard?", and `python -m scoutbot.start sim --share` skips the menu.
   - `scoutbot/tools/doctor.py`: plain-language [OK]/[--]/[FAIL] lines for Python version, core packages, optional packages (what each unlocks), each `.env` key (what turns off without it), internet, LAN IP, Ollama (running and model pulled), built-in voice, and camera. Exit code 1 only for real blockers.
   - `requirements.txt`: the core only (no `ultralytics`; that moves to A's `requirements-yolo.txt`).
   - ★ Merge.
3. **`--share` mode:** `python -m scoutbot --share` binds `0.0.0.0` and prints `http://<LAN-IP>:8000` (plus `?token=` if `SCOUTBOT_TOKEN` is set) for phones and teammates. Test from a phone on the same Wi-Fi.
4. **Windows safety:** in `__main__`, `sys.stdout.reconfigure(errors="replace")`; no `±` or other non-ASCII in console prints; utf-8 for every file C owns (A and B do theirs; list any you spot in STATUS).
5. **Fresh-machine test:** clone into a new folder, run `start.command`/`start.sh` from nothing, pick sim, and confirm the dashboard works. Repeat on any teammate's Windows laptop if possible. Write down every snag and fix it. ★ Merge.

### C.P1
6. **Real run on the laptop profile** (webcam + Gemini + sliders), going through the demo script (next-steps spec section 17), step by step. Fix dashboard bugs. Check that the chips match reality (Gemini, Ollama, YOLO, voice, Mongo, Tiger), the veto message shows, the drive pad works with keys and touch, and the survivor card updates live.
7. **Dashboard polish:** it must work on a phone (touch drive pad, the layout stacks); the map has zoom-to-fit with a "follow robot" toggle; a banner shows when offline ("Offline: using Ollama, survivors queued"); and one-click survivor export (a JSON/CSV download of all survivors).
8. **Survivor registry and map:** check with the sim (`room_basic`, `rubble`, `demo`) that N survivors give N records. Tune `survivors.merge_cm` and the slack if not. When A adds `hw.sensor_angles`, make `simworld.py` and `mapping.py` read it.
9. **Integration duty:** every time A or B merges to main, pull it into your branch, run the full test suite and a 60 s `--headless` sim run, and report problems in STATUS. You're the last line of defense for "main always green". ★ Merge.

### C.P2 – if time allows
10. **Wiring requests from A and B** (cliff sensor into `controller.step`, `resolve_sinks`, a speech-to-text endpoint).
11. **README rewrite:** 5-line quick start at the top (double-click start, pick a number); then profiles, keys, Pi, the demo script and troubleshooting. Plain words.
12. A `--record` flag that saves frames + sensor readings to `data/recordings/<time>/` for replay with `hw.camera=folder`.

**C is done when:** a fresh clone on Mac (and Windows or Linux if available) starts with one double-click; the demo script runs cleanly in sim and on the laptop webcam; the dashboard works on a phone via `--share`; STATUS stays current; and `main` is green.

---

## 5. Timeline and merge checkpoints

| Time from start | A – Robot | B – Cloud | C – Station |
| --- | --- | --- | --- |
| 0:10 | branch made | branch made | STATUS.md on main ★ |
| ~1:00 | motor_check fix, YOLO on webcam | `.env.example`, Gemini live numbers | setup + launchers + start menu ★ |
| ~2:00 | cut-offs tuned, NCNN ★ | triage/replies tuned, talk_check ★ | `--share`, fresh-machine test ★ |
| ~3:00 | remote YOLO ★, Pi scripts | router + Ollama + voice ★ | laptop-profile demo run, dashboard fixes |
| ~4:00 | Pi bring-up (if hardware) ★ | Mongo + Tiger live, demo queries ★ | integration run of all merges ★ |
| After | blind spot, cliff sensor | speech-to-text, safety review | polish, README, recording |

**Final integration (all three, about 20 minutes):** everyone merges to main. C runs the full tests, a 60 s headless sim, and the full demo script on the laptop profile with real keys. A runs the same on the Pi if it exists. The last commit on main is tagged `demo-ready`.

## 6. Demo acceptance checklist (the whole team)
- [ ] The dashboard opens from a phone on the same Wi-Fi.
- [ ] Start auto: the robot explores (sim or real) with no contacts, and the rule that fired is shown.
- [ ] A person in view: YOLO box → robot stops → survivor pin → greeting spoken (ElevenLabs).
- [ ] Survivor says they're stuck → triage turns red (IMMEDIATE, preliminary) → a Gemini reply is spoken.
- [ ] Simulate offline → the reply comes from Ollama in the local voice → survivors show "queued".
- [ ] Back online → Mongo and Tiger chips go green → records visible in both, with the demo queries ready.
- [ ] Take control → driving toward a wall is blocked by the gate → letting go stops → STOP works.
- [ ] Closing the dashboard tab or killing the program stops the motors within 0.5 s.
