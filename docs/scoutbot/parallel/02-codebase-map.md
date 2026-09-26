# Codebase map: what exists today (main @ 705ccab)

About 2,200 lines of new Python in `scoutbot/`, on top of the original brain in `robot/`, with 99 tests in `tests/`. This file tells you where everything is, how data flows, and who owns what (ownership: [01-shared-rules.md](01-shared-rules.md#2-file-ownership)).

## 1. How to run it

| Command | What happens |
| --- | --- |
| `python -m scoutbot --profile sim --set sim.world=demo` | Simulated room: fake sensors react to fake driving, fake survivors. Dashboard at http://localhost:8000. No keys or hardware needed. |
| `python -m scoutbot --profile mac` | Laptop webcam, dashboard sliders as distance sensors, fake motors. Uses Gemini if `GEMINI_API_KEY` is set. |
| `python -m scoutbot --profile pi` | The real robot: HC-SR04 sensors, L298N motors, binds 0.0.0.0. |
| `... --set a.b=c` | Override any config value, e.g. `--set hw.distance=random --set sim.world=rubble`. |
| `... --headless 30` | No server: runs 30 s in AUTO (link check off), prints progress and a survivor summary. A quick smoke test. |
| `python -m pytest -q tests` | All tests (about 4 s). |
| `python web_demo.py` / `run_web.command` | The OLD brain debug dashboard (kept working, not extended). |

Double-click launchers from Codex: `run_scoutbot_mac.command`, `run_scoutbot_sim.command`, `run_scoutbot_offline.command`, `run_camcheck.command`, `run_ollama_check.command`, `run_yolo_bench.command`. Known bug: they call `python`, which is missing on many Macs (see [04-known-issues.md](04-known-issues.md)).

## 2. The big picture (threads inside one process)

```
             ┌──────────── scoutbot/runtime.py : Runtime ─────────────────────────────────────────────┐
 camera ───► │ camera_loop (MAIN thread) ─► shared.frame / jpeg / cam_health                           │
 sensors ──► │ distance_loop ────────────► shared.raw_sensors                                          │
             │ scene_loop (every ~2 s) ──► robot.vlm.describe(frame) ─► shared.scene (+ failures)      │
             │ PerceptionWorker (YOLO) ──► shared.detections (confirmed 2-of-3)                        │
             │ control_loop 10 Hz  = control_tick():                                                   │
             │     fuse YOLO+Gemini ─► robot Controller.step() ─► mode (AUTO/MANUAL/STOPPED)           │
             │     ─► safety Gate.check() ─► Motors.apply() ─► MotorWatchdog.fed()                      │
             │     ─► DeadReckoning pose ─► MapBuilder ─► logs/scoutbot_run.jsonl + telemetry outbox    │
             │ survivor_loop ─► Registry.sighting() ─► data/survivors.jsonl + outbox + bus "survivor"  │
             │                       └─ new survivor ─► TalkWorker.submit("new_survivor")              │
             │ TalkWorker ─► TalkRouter (Gemini ▸ Ollama ▸ canned) ─► chat + triage ─► Speaker.say()   │
             │ Speaker (voice thread)   NetWorker (internet check)   SyncWorker (outbox ─► Mongo/Tiger)│
             │ MotorWatchdog thread (stops motors if control loop goes quiet 0.5 s)                    │
             └─────────────────────────────────────────────────────────────────────────────────────────┘
                     ▲ commands (WebSocket)                         │ state 10 Hz + events (WebSocket)
             scoutbot/server/app.py (FastAPI, uvicorn thread) ◄─────┘   + /video.mjpg, REST
                     ▲
             responder.html (browser: laptop or phone)
```

**Rules of the house:** workers talk only through `Shared` (latest values, under `shared.lock`) and `Bus` (events). Workers don't call each other directly. The one deliberate exception is `TalkWorker.submit()` being called by the survivor loop and the server.

## 3. File by file

### `robot/` (the original brain, frozen except `vlm.py`)

| File | What it does |
| --- | --- |
| `types.py` | `Action` (STOP, FORWARD, FORWARD_SLOW, TURN_LEFT, TURN_RIGHT, BACK_UP), `SceneReport` (Gemini's answer: path_ahead, best_direction, terrain, hazards, people, objects, confidence, notes), `Sensors` (left/center/right cm, valid flags, updated_at, vlm_online) |
| `brain.py` | The 8 rules, first match wins. `evaluate()` returns the full trace and `decide()` returns the action. The camera can only add caution. |
| `controller.py` | `Controller.step(raw_sensors, scene, scene_at, cam_healthy, now, cliff=None)` → `Decision` (action, rule, reason, steps, filtered sensors, notes, stuck). Filters sensors, hysteresis, turn hold, stuck recovery. |
| `sensing.py` | Median-of-5 filter, no-echo rule, time-to-collision, `echo_to_cm`, `PING_GAP_S`. |
| `scene_filter.py` | Filters Gemini reports over time. Danger is believed fast; "clear" is believed slowly. **Treats each new report object as a new report.** |
| `camera_health.py` | Detects dark, washed out, low contrast or frozen frames. |
| `config.py` | `Policy` thresholds (`stop_cm` 25, `slow_cm` 60, `side_near` 15 ...). `DEFAULT = Policy.from_speed()`. |
| `vlm.py` (**B**) | `describe(frame) -> SceneReport` via Gemini. The schema is in the prompt, it retries on 503, temperature 0. |
| `sim.py`, `metrics.py` | Random mock data; metrics for the old dashboard. |

### `scoutbot/` core (**C**)

| File | What it does |
| --- | --- |
| `__main__.py` | CLI: `--profile`, `--set`, `--headless`. Starts uvicorn in a thread and runs the camera loop on the main thread. Ctrl-C stops the motors. |
| `settings.py` | `load(profile, overrides, load_env=True)`: base.yaml + profile + `--set`, loads `.env`, applies `CAMERA_INDEX`. `get(cfg, "a.b")`. |
| `types.py` | `Mode`, `DriveCommand`, `PersonDetection`, `Pose`, `TriageFacts`, `Triage`, `ChatMessage`, `Survivor`, `utc_now()`. |
| `state.py` | `Shared` (every live value, see [03-contracts.md §4](03-contracts.md)) and `Bus` (publish/subscribe with history). |
| `runtime.py` | `Runtime`: builds everything from config; loops `camera_loop`, `distance_loop`, `scene_loop`, `control_tick`/`control_loop`, `survivor_loop`; `command(msg)` for dashboard commands; `state()`/`hello()` for the dashboard. |
| `net.py` (**B**) | `NetWorker`: HEAD request every 3 s → `shared.internet`. `shared.online()` = internet and not force_offline. |

### `scoutbot/hw/` (A owns the real drivers and base; C owns the simulator and fakes)

| File | Owner | What it does |
| --- | --- | --- |
| `base.py` | A | `Camera`, `DistanceSensors`, `Motors` protocols; `Ramp` (smooth speed changes; stop is instant); `wheel_speeds(action, cfg)`; `build(cfg, shared, world)` picks the implementations. |
| `camera_opencv.py` | A | `OpenCVCamera(index)`, `FolderCamera(path, fps)`, `SyntheticCamera(world)` (a drawn view of the sim). |
| `distance_hcsr04.py` | A | Real HC-SR04 ×3 over `lgpio`, one at a time, 60 ms apart. |
| `distance_tof.py` | A | Real VL53L0X ×3 over I2C (XSHUT address setup). Untested. |
| `motors_l298n.py` | A | Real L298N via `gpiozero.Motor`, ramped. |
| `distance_fake.py` | C | `SliderDistance` (dashboard sliders), `RandomDistance`, `ScriptedDistance`. |
| `motors_fake.py` | C | Prints wheel outputs and moves the sim robot. |
| `simworld.py` | C | 2D room from `config/worlds/*.yaml`; walls, boxes, survivors; raycast sensors; `visible_survivors()`, `detections()`, `scene_report()`, true pose; counts wall `contacts`. |

### `scoutbot/safety/` (**A**)

| File | What it does |
| --- | --- |
| `gate.py` | `Gate.check(action, mode, L, C, R, sensors_fresh, now, yolo_person_near)` → `GateResult(action, veto)`. STOPPED → STOP; stale → STOP; forward into < stop_cm → STOP; FORWARD capped to SLOW under slow_cm; MANUAL turn into a close side → STOP; BACK_UP limited to 1.5 s bursts; YOLO person near + forward → STOP. |
| `deadman.py` | `manual_action(cmd, now, valid_s)`, `link_check(mode, link_at, now, safety_cfg)`, `MotorWatchdog` (0.5 s, re-sends stop every 0.2 s). |
| `modes.py` | `ModeController`: boots STOPPED; `request(mode)`, `estop()`. |

### `scoutbot/perception/` (**A**)

| File | What it does |
| --- | --- |
| `yolo.py` | `box_to_detection` (thirds of the image for where; box height for near/mid/far); `Confirmer` (k of n); `YoloDetector` (lazy ultralytics, person class only, mps on Mac); `PerceptionWorker` (`where`: robot, remote, sim or off). |
| `fusion.py` | `fresh_person()`, `Fuser.fuse(scene, person)`: YOLO can add a person to Gemini's report but never remove one; the nearer distance wins; the result is cached. |
| `worker_remote.py` | Runs YOLO on the laptop against `/video.mjpg` and posts to `/api/detections`. |

### `scoutbot/survivors/` (**C**)

| File | What it does |
| --- | --- |
| `pose.py` | `DeadReckoning.update(wheels, now)` integrates the wheel fractions × calibration. `uncertainty = 30 + 0.3 × odometer`. |
| `registry.py` | `Registry.sighting(det, pose, odometer, frame, exclude)` → `(Survivor or None, is_new)`. Far sightings never create a survivor. The merge radius is based on drift since last seen. Snapshots are capped at 5. Every change goes to `data/survivors.jsonl` first, then the outbox and the bus. `update(sid, fn)` for chat and triage. |
| `mapping.py` | `MapBuilder`: breadcrumb trail, obstacle dots (sensors at +30/0/-30°), true trail in sim. |

### `scoutbot/talk/`, `voice/`, `sync/` (**B**)

| File | What it does |
| --- | --- |
| `talk/triage.py` | START-like rules → IMMEDIATE / DELAYED / MINOR / UNKNOWN; `parse_facts()` is tolerant; `FACTS_SCHEMA`. |
| `talk/models.py` | `GeminiTalk`, `OllamaTalk` (`/api/chat`, `format` = JSON schema, keep_alive), `CannedTalk`; `GREETING`; `transcript()`. |
| `talk/router.py` | `CircuitBreaker(3, 30 s)`; `TalkRouter.reply()`/`triage()`: Gemini (if online and breaker allows, 1 retry) ▸ Ollama ▸ canned/UNKNOWN. |
| `talk/worker.py` | `TalkWorker`: a job queue for `new_survivor`, `survivor_says`, `responder_says`, `retriage`; writes chat and triage via `registry.update`; publishes `chat` and `triage` on the bus; speaks via `Speaker`. |
| `talk/prompts/*.txt` | `triage_v1.txt`, `reply_v1.txt`. |
| `voice/speaker.py` | `Speaker.say(text, priority, key)` priority queue with de-duplication. `ElevenLabsVoice` (streams to mpg123/ffplay if present, else a file played by afplay), `LocalVoice` (`say` or espeak), `FakeVoice`. |
| `sync/outbox.py` | `Outbox` (a folder per sink; the newest survivor version wins; rows as jsonl), `SyncWorker` (only online; per-sink backoff 2→60 s; status in `shared.sync_status`). |
| `sync/mongo.py`, `sync/tiger.py` | Real sinks (pymongo; psycopg with hypertables). Untested against real services. |

### `scoutbot/server/` (**C**)

| File | What it does |
| --- | --- |
| `app.py` | `create_app(runtime)`: `/`, `/video.mjpg`, `/snapshot.jpg`, `/snapshots/{name}`, `/api/survivors[/{id}]`, `/api/map`, `/api/detections` (POST), `/api/health`, `/api/state`, WebSocket `/ws`. Optional `SCOUTBOT_TOKEN`. |
| `static/responder.html` | The responder dashboard: mode + STOP + Start auto + Take control; status chips; video with YOLO boxes; action + reason + veto + sensor bars + rule trace; drive pad (W/A/S/D, arrow keys, Shift = slow, Space = STOP; repeats every 100 ms while held); map canvas; status table; test controls (simulate offline, sensor sliders); survivor list and card (snapshot, triage, facts, chat, two input boxes); event log. |

### `scoutbot/tools/` (Codex; A and B own theirs)

`camcheck`, `yolo_bench`, `sensor_check`, `motor_check` (A); `ollama_check` (B). Known bugs are in [04-known-issues.md](04-known-issues.md).

## 4. Config (`config/profiles/base.yaml`) at a glance

| Section | Main keys (default) | Owner |
| --- | --- | --- |
| `hw` | `camera` opencv, `camera_index` 1, `distance` sliders, `motors` fake, `pins` (placeholders), `tof_xshut` | A (C for the fake/sim values) |
| `motion` | forward_cm_s 30, slow_cm_s 18, backup_cm_s 18, turn_deg_s 90, ramp_s 0.15, trim_left/right 1.0 | A |
| `speeds` | [left, right] PWM fraction per action | A |
| `safety` | motor_watchdog_s 0.5, manual_cmd_valid_s 0.3, link_required true, link_timeout_manual_s 0.5, link_timeout_auto_s 2.0, auto_on_link_loss stop, backup_max_s 1.5 | A |
| `control` | hz 10, log_every_s 0.5 | C |
| `scene` | provider gemini / fake / sim, interval_s 2.0 | B |
| `perception.yolo` | where robot, model yolov8n.pt, imgsz 320, device auto, min_conf 0.45, confirm [2,3], near_frac 0.5, mid_frac 0.2, max_age_s 1.0 | A |
| `survivors` | merge_cm 100, bearing_deg 25, dist_cm near/mid/far 70/200/400, max_snapshots 5, data_dir data | C |
| `talk` | enabled, gemini.timeout_s 8, ollama url/model qwen2.5:3b/timeout_s 20/keep_alive 30m, breaker 3 / 30 s, history_messages 12 (**not wired yet**) | B |
| `voice` | provider elevenlabs, fallback local, model eleven_flash_v2_5, dedupe_s 10 | B |
| `sync` | sinks [mongo, tiger] (mac and sim override to []), interval_s 3, backoff_max_s 60, telemetry_hz 1 | B |
| `net` | check_interval_s 3, check_url, force_offline false | B |
| `sim` | world room_basic, noise 0.05, fake_people (**not read by the code**) | C |
| `server` | host 127.0.0.1, port 8000, test_controls true, state_hz 10, open_browser false | C |

Profiles: `mac` (webcam, sliders, fake motors, Gemini, YOLO on the robot, ElevenLabs → local, sinks [], opens the browser); `sim` (simworld sensors, sim scene, sim YOLO, fake voice, sinks []); `pi` (real hardware, NCNN model, Ollama at `LAPTOP_IP`, sinks [mongo, tiger], host 0.0.0.0, test_controls false). Worlds: `room_basic`, `rubble`, `demo`.

## 5. Files written at runtime (all git-ignored)

| Path | Written by | Format |
| --- | --- | --- |
| `data/survivors.jsonl` | Registry | one full `Survivor` JSON per change (append only; the last line per id wins on reload) |
| `data/snapshots/S-0001_0003.jpg` | Registry | survivor photos, at most 5 per survivor |
| `data/outbox/<sink>/survivors/<id>.json` | Outbox | the newest version to upload |
| `data/outbox/<sink>/{sightings,telemetry}.jsonl` | Outbox | rows to upload (renamed `.sending` while being sent) |
| `logs/scoutbot_run.jsonl` | Runtime | one line every 0.5 s: mode, raw and filtered sensors, person, brain action and rule, final action, veto, pose, online |
| `logs/run.jsonl`, `logs/web_run.jsonl` | old tools | (legacy) |

## 6. Tests (99)

| File | Covers | Owner |
| --- | --- | --- |
| `test_brain.py`, `test_policy.py`, `test_rules_table.py` | the original brain (52) | frozen |
| `test_gate.py`, `test_deadman.py`, `test_fusion.py` | safety gate, modes, watchdog, link loss, YOLO mapping and fusion | A |
| `test_router.py`, `test_triage.py`, `test_outbox.py`, `test_talk_worker.py`, `test_isolation.py` | breaker, routing, triage rules and parsing, outbox and backoff, talk end to end, talk never imports motors | B |
| `test_server.py`, `test_registry.py`, `test_simworld.py`, `test_tools_smoke.py` | REST and WebSocket commands, survivor merge/snapshots/reload, raycasts and 5-minute sim runs, tool `--help` | C |
