# Scoutbot – Next Steps Spec (full system)

Date: 2026-09-26 (hackathon day)
Builds on: the working brain in this repo (commit `b297ea4`), `disaster-response-robot-v1-spec.md`, and the research notes in the Claude project (`robot/research-notes-2026-09-26.md`).
Target: the "scoutbot system architecture" diagram — every box on it, built for real.

---

## 0. How to read this

Sections 1–3 are the rules and the big picture. Section 4 is how to run and test everything on your Mac with no robot. Sections 5–13 are one section per box on the diagram: what it does, its interface, its fake version, its real version, and how you know it is done. Section 14 is the build order for today. Sections 15–17 are risks, open questions for the hardware team, and the demo script.

Wherever this spec and the older `docs/` folder disagree, **the code and this spec win**. The `docs/` set describes a heavier design (a `WorldState` class, a formal state machine) that the working code does not follow, and there is no time to reconcile them today.

---

## 1. Goal and "done"

The system matches the diagram:

- **On the robot (Raspberry Pi 4):** camera, distance sensors, a FastAPI server, YOLOv8n person detection, a survivor log and map, an online/offline router, a dead-man motor stop, and an L298N driver running 4 TT motors.
- **Base-station laptop:** the responder dashboard (live video, drive controls, map, triage reports, survivor chat) and Ollama running `qwen2.5:3b` as the offline brain.
- **Cloud, when online:** Gemini (sees snapshots, writes triage, replies to survivors), Tiger Data and MongoDB (survivor sync), and ElevenLabs (survivor voice).
- All devices are on one Wi-Fi network. "Offline" means **no internet**, not no Wi-Fi.

**Demo is done when:**

1. The robot explores on its own and never hits anything. The existing brain does this.
2. When a person appears, YOLO spots them, the robot stops, a survivor pin appears on the map, and a snapshot is saved.
3. Gemini writes a preliminary triage report, and the robot talks to the survivor through ElevenLabs.
4. Cut the internet: the dashboard shows "offline", chat keeps working through Ollama, survivor records queue up locally, and driving is unaffected.
5. Restore the internet: queued survivor records sync to Tiger Data and MongoDB.
6. A responder can take over and drive from the dashboard. Letting go of the controls or losing the link stops the motors within half a second.
7. **All of 1–6 can also be run on the Mac with no robot,** using the laptop webcam and fake sensors.

---

## 2. Ground rules

1. **Do not break what works.** `robot/brain.py`, `robot/controller.py`, `robot/vlm.py`, `robot/types.py`, `robot/config.py`, `web_demo.py` and `dashboard.html` stay as they are. All 52 existing tests must keep passing. New work goes in new files, and existing code is called, not rewritten.
2. **The AI never drives.** Gemini, YOLO, Ollama and ElevenLabs only produce *descriptions* and *words*. Only the controller or a responder command can produce an action, and every action goes through the safety gate (section 6).
3. **Anything that talks cannot move.** The talk, voice and sync code must never import the motor code. A test enforces this (section 18).
4. **Every box has a fake and a real version,** chosen in one config file. You can always run the whole system on the Mac.
5. **Everything is timestamped and expires.** No part of the system acts on stale data.
6. **Local first.** Survivor records are written to disk before anything tries the network.
7. **All numbers go in config,** never hard-coded.

---

## 3. Architecture

### 3.1 One codebase, one program, different profiles

Everything lives in this repo. The Pi and the Mac run **the same program** with a different profile:

```bash
python -m scoutbot --profile mac     # everything on your Mac: webcam + fake sensors + fake motors
python -m scoutbot --profile sim     # Mac, simulated room: fake sensors that react to fake driving
python -m scoutbot --profile pi      # the real robot
```

The Pi runs the robot server. The responder opens the dashboard in a browser on the laptop at `http://<pi-ip>:8000`. Ollama runs on the laptop, and the Pi reaches it over Wi-Fi at `http://<laptop-ip>:11434`. On the Mac profiles, all of this is `localhost`.

This is simpler than splitting the Pi and laptop code into separate folders. There is one thing to install, one config format, and the same tests in both places.

### 3.2 Folder layout (new files marked NEW)

```text
heheheheha/
  robot/                      # EXISTING brain – unchanged
    brain.py controller.py config.py types.py vlm.py sensing.py
    scene_filter.py camera_health.py metrics.py sim.py
  scoutbot/                   # NEW – the full system
    __main__.py               # python -m scoutbot --profile X
    settings.py               # loads config/profiles/*.yaml + .env
    types.py                  # new shared shapes (section 3.4)
    runtime.py                # starts every worker thread, owns the shared state
    state.py                  # thread-safe latest-value store + event bus
    hw/                       # hardware interfaces (section 5)
      base.py                 # Camera, DistanceSensors, Motors protocols
      camera_opencv.py        # webcam / USB camera / GoPro-as-webcam
      camera_folder.py        # replay a folder of images or a video file
      distance_fake.py        # sliders, random (reuses robot/sim.py), scripted
      distance_hcsr04.py      # real ultrasonic (Pi)
      distance_tof.py         # real VL53L0X/VL53L1X over I2C (Pi), if hardware uses ToF
      motors_fake.py          # prints + moves the sim world
      motors_l298n.py         # real L298N via gpiozero (Pi)
      simworld.py             # 2D room: walls, obstacles, survivors, robot pose
    safety/
      gate.py                 # final check before motors (section 6)
      deadman.py              # motor watchdog
      modes.py                # STOPPED / AUTO / MANUAL
    perception/
      yolo.py                 # person detection (section 8)
      fusion.py               # YOLO + Gemini people -> one answer
      worker_remote.py        # run YOLO on the laptop against the Pi's video
    survivors/
      pose.py                 # dead-reckoning pose estimate
      registry.py             # survivor log: create / merge / update
      mapping.py              # breadcrumb trail + survivor pins + obstacle points
    talk/
      router.py               # online/offline router + circuit breaker (section 10)
      gemini_talk.py          # triage + replies (online)
      ollama_talk.py          # triage + replies (offline)
      triage.py               # rule-based category from extracted facts
      prompts/                # triage_v1.txt, reply_v1.txt
    voice/
      base.py                 # Speaker protocol
      elevenlabs.py           # online voice
      local_tts.py            # offline voice (espeak-ng on Pi, `say` on Mac)
      fake.py                 # prints
    sync/
      outbox.py               # local-first store + background sender
      mongo.py                # MongoDB sink
      tiger.py                # Tiger Data (Postgres/TimescaleDB) sink
    server/
      app.py                  # FastAPI: REST + WebSocket + MJPEG
      static/responder.html   # the responder dashboard (section 12)
  config/profiles/            # NEW: mac.yaml, sim.yaml, pi.yaml, base.yaml
  tests/                      # existing 52 tests + new ones (section 18)
  data/                       # NEW (git-ignored): survivors.jsonl, snapshots/, outbox/
  run_scoutbot_mac.command    # NEW double-click launchers
  run_scoutbot_sim.command
  run_ollama_check.command
```

### 3.3 Threads inside the program

Each worker is a thread that only reads from or writes to the shared state (`scoutbot/state.py`). Workers never call each other directly. This matches the existing `web_demo.py` pattern: a lock plus latest values.

| Worker | Rate | Reads | Writes |
| --- | --- | --- | --- |
| camera | as fast as the camera gives | camera | latest frame + JPEG, camera health |
| distance | ~16 Hz (3 sensors × 60 ms gap) | sensors | latest `Sensors` |
| scene (Gemini, existing `describe`) | every ~2 s | latest frame | latest `SceneReport`, VLM health |
| yolo | as fast as it can (target ≥ 3 FPS) | latest frame | latest `PersonDetections` |
| control | 10 Hz | sensors, scene, detections, mode, drive command | decision, gated action → motors |
| deadman | 20 Hz | time of the last motor command | forces stop if stale |
| pose | 10 Hz | executed actions | robot pose estimate |
| survivors | on every detection | detections, pose, frame | survivor records, snapshots |
| talk | on events | survivor records, chat input | triage, replies, chat log |
| voice | on events | replies | audio out |
| sync | every 2–5 s | outbox | remote databases |
| net | every 3 s | — | internet online/offline |
| server | on request | everything | commands in, state out |

The control loop is the only writer to the motors, always through the safety gate.

### 3.4 New shared data shapes (`scoutbot/types.py`)

These are Pydantic models, the same style as `robot/types.py`. Existing shapes (`Sensors`, `SceneReport`, `Action`) are reused unchanged.

```python
class Mode(str, Enum): STOPPED="STOPPED"; AUTO="AUTO"; MANUAL="MANUAL"

class DriveCommand(BaseModel):          # from the dashboard
    action: Action; seq: int; sent_at: float        # client clock, for latency display only

class PersonDetection(BaseModel):
    source: Literal["yolo","gemini"]
    where: Literal["left","center","right"]
    distance: Literal["near","mid","far"]
    confidence: float
    bbox: tuple[float,float,float,float] | None      # normalized x1,y1,x2,y2 (YOLO only)
    at: float                                        # monotonic time

class Pose(BaseModel):
    x_cm: float; y_cm: float; heading_deg: float
    uncertainty_cm: float                            # grows with distance travelled
    source: Literal["dead_reckoning","sim","imu"]

class TriageFacts(BaseModel):                       # what the model extracts; every field allows "unknown"
    responsive: Literal["yes","no","unknown"]
    can_walk: Literal["yes","no","unknown"]
    trapped: Literal["yes","no","unknown"]
    visible_bleeding: Literal["yes","no","unknown"]
    breathing_trouble: Literal["yes","no","unknown"]
    hazards_nearby: list[str]                         # from SceneReport hazards, not invented
    injuries_reported: list[str]                      # only what the survivor said
    summary: str                                       # <= 240 chars

class Triage(BaseModel):
    category: Literal["IMMEDIATE","DELAYED","MINOR","UNKNOWN"]    # START colors: red / yellow / green / grey
    rule: str                                          # which triage rule fired
    facts: TriageFacts
    model: str                                         # "gemini-…" or "ollama:qwen2.5:3b"
    preliminary: Literal[True] = True
    at: float

class ChatMessage(BaseModel):
    survivor_id: str
    role: Literal["survivor","robot","responder"]
    text: str
    source: Literal["typed","speech","gemini","ollama","responder","canned"]
    at: str                                            # UTC ISO time

class Survivor(BaseModel):
    id: str                                            # "S-0001"
    first_seen: str; last_seen: str
    pose: Pose                                         # estimated position of the person, not the robot
    sightings: int
    best_snapshot: str | None                          # data/snapshots/S-0001_0003.jpg
    triage: Triage | None
    chat: list[ChatMessage]
    version: int                                       # increments on every change (for sync)
```

---

## 4. Local testing on the Mac (no robot needed)

This is the most important section for today. Everything below works with only the Mac.

### 4.1 Profiles

| Setting | `mac` | `sim` | `pi` |
| --- | --- | --- | --- |
| camera | laptop webcam (`CAMERA_INDEX=1`) | webcam, or `folder:dataset/` replay | USB webcam or GoPro |
| distance sensors | `sliders` (dashboard) or `random` | `simworld` (raycast in a fake room) | `hcsr04` or `tof` |
| motors | `fake` (prints) | `fake` (moves the fake robot in the room) | `l298n` |
| YOLO | on the Mac (`device: mps`) | on the Mac | on the Pi (`ncnn`, 320 px), or `remote` |
| Gemini scene + talk | real (key in `.env`), or `fake` | real or `fake` | real |
| Ollama | `http://localhost:11434` | localhost | `http://<laptop-ip>:11434` |
| voice | Mac speakers (`elevenlabs`, falls back to `say`) | `fake` (prints) | Pi speaker (`elevenlabs`, falls back to `espeak-ng`) |
| database sync | `local` only, or real sinks | `local` | real sinks |
| server bind | `127.0.0.1:8000` | `127.0.0.1:8000` | `0.0.0.0:8000` |

A profile is a YAML file. `base.yaml` holds the defaults, and the others only override. Any value can also be overridden on the command line, for example `python -m scoutbot --profile mac --set hw.distance=random`.

### 4.2 The sim world (`hw/simworld.py`)

The simulator makes the fake sensors react to the fake motors. Without it, the map and survivor positions can't be tested.

- A 2D room of about 6 × 6 m, made of line-segment walls and box obstacles, loaded from `config/worlds/*.yaml`. Ship two: `room_basic.yaml` and `rubble.yaml`.
- The robot has a pose `(x, y, heading)`. `motors_fake` moves it using the same action → speed table as the real robot (section 5.3), plus a little random noise, so the dead-reckoning map drifts the way a real one would.
- The three distance sensors are raycasts at −30°, 0° and +30°, with the 15° beam, noise and occasional no-echo from `robot/sim.py`.
- Survivors are points in the room. When one is inside the camera's 60° field of view and within 4 m, the sim can inject a fake `PersonDetection` (`sim.fake_people: true`). This way the full survivor → triage → chat → sync path works with no real person in front of the camera.
- The camera stays real (webcam) or a folder replay. The camera is not simulated.
- The dashboard map shows the *true* sim pose as a faint ghost next to the *estimated* pose, so you can see the drift.

### 4.3 Launchers (double-click, like the existing ones)

| File | Runs |
| --- | --- |
| `run_scoutbot_mac.command` | `--profile mac`, opens `http://localhost:8000` |
| `run_scoutbot_sim.command` | `--profile sim --set sim.world=room_basic` |
| `run_scoutbot_offline.command` | `--profile mac --set net.force_offline=true` (tests the Ollama path) |
| `run_ollama_check.command` | checks that Ollama is running, pulls `qwen2.5:3b` if missing, times one reply |
| `run_yolo_bench.command` | times YOLO on 50 frames and prints FPS (run on the Pi too) |

The existing `run_web.command` and `run_web_sim.command` keep working unchanged as your brain debug tool.

### 4.4 Local test checklist

- [ ] Webcam + slider sensors: drag center to 10 cm → robot `BACK_UP`/turn; hold a person photo up → survivor pin appears.
- [ ] Sim world: robot explores `room_basic` for 5 minutes with zero collisions (the sim counts wall contacts).
- [ ] Sim world with `fake_people`: 3 survivors in the room → 3 survivor records, not 30 (merging works).
- [ ] Offline toggle: chat keeps answering (source shows `ollama`); records go to the outbox; toggle back → records sync.
- [ ] Manual drive: hold forward → moves; release → stops within 0.5 s; close the browser tab → stops within 0.5 s.
- [ ] Kill the Python process mid-drive (sim): no motion on restart until you press Start.

---

## 5. Hardware interfaces (`scoutbot/hw/`)

This is the handoff contract with the hardware team. If their code implements these three interfaces, it plugs in with no other changes.

### 5.1 Camera

```python
class Camera(Protocol):
    def read(self) -> np.ndarray | None: ...   # newest BGR frame, or None if nothing new / failed
    def close(self) -> None: ...
```

- `camera_opencv`: `cv2.VideoCapture(index)`, discards the first 30 frames (macOS starts black, as in `web_demo.py`), and keeps only the newest frame.
- `camera_folder`: loops over images or a video file at a set FPS, for repeatable tests.
- GoPro: try it as a USB webcam first. If that fails within an hour, use any cheap USB webcam. Nothing else cares where frames come from.
- Existing `robot/camera_health.py` runs on every frame, unchanged.

### 5.2 Distance sensors

```python
class DistanceSensors(Protocol):
    def read(self) -> Sensors: ...   # existing robot.types.Sensors: left/center/right cm, valid flags, updated_at
```

- The existing `robot/sensing.py` filter (median of 5, no-echo rules, time-to-collision) runs **inside the controller**, as now. Drivers return raw readings.
- `distance_hcsr04`: triggers the three sensors one at a time with a 60 ms gap (`sensing.PING_GAP_S`), 30 ms echo timeout, and uses `sensing.echo_to_cm` for the temperature-corrected distance. Echo pins **must** go through a voltage divider (5 V → 3.3 V).
- `distance_tof`: the diagram says "ToF · I²C". If the hardware team uses VL53L0X/VL53L1X sensors instead of HC-SR04s, each needs its own I²C address (set with XSHUT pins at boot). Same `Sensors` output. VL53L0X only reaches about 1.2–2 m, so readings beyond that count as "far", not "no echo".
- Missing echo = `valid=False`, never a big number. This is already a policy rule.

### 5.3 Motors

```python
class Motors(Protocol):
    def apply(self, action: Action) -> None: ...   # called ≥10 Hz by the control loop; each call refreshes the dead-man
    def stop(self) -> None: ...                    # immediate, idempotent, safe to call from any thread
```

- The 4 TT motors are wired as two sides (left pair on L298N channel A, right pair on channel B).
- Action → wheel speed table (fractions of full PWM), in config:

| Action | left | right |
| --- | --- | --- |
| STOP | 0 | 0 |
| FORWARD | 0.6 | 0.6 |
| FORWARD_SLOW | 0.35 | 0.35 |
| TURN_LEFT | −0.45 | 0.45 |
| TURN_RIGHT | 0.45 | −0.45 |
| BACK_UP | −0.35 | −0.35 |

- Speed changes ramp over about 150 ms, so the robot doesn't jerk or tip. Stop is always instant.
- `motors_l298n`: `gpiozero.Motor(forward, backward, enable=pwm_pin)` per side, with pins from config. There are also per-side trim values, because TT motors never match.
- `motors_fake`: logs `LEFT 0.35 RIGHT 0.35` at most once a second, and moves the sim robot if the sim world is on.
- On program exit (including Ctrl-C and crashes caught by `atexit`/signal handlers), `stop()` is called.
- Calibration numbers (measured once on the floor): `motion.forward_cm_s`, `motion.slow_cm_s`, `motion.turn_deg_s`, `motion.backup_cm_s`. They feed both the pose estimate and `Policy.from_speed()`.

---

## 6. Safety gate, dead-man stop and modes (`scoutbot/safety/`)

This is the most important new code. Build and test it before anything else touches motors.

### 6.1 Modes

| Mode | Who picks the action | How you get there |
| --- | --- | --- |
| `STOPPED` | nobody – motors off | on boot, after an E-stop, after a link loss |
| `AUTO` | existing `Controller.step()` | responder presses **Start auto** |
| `MANUAL` | responder's held drive button | responder presses **Take control** |

- The program always boots in `STOPPED`. Leaving `STOPPED` needs an explicit button press.
- **E-stop** (big red button, or the space bar on the dashboard) → `STOPPED` from any mode, instantly.

### 6.2 Safety gate (`gate.py`)

`gate(action, mode, sensors_filtered, now) -> (final_action, veto_reason | None)`

It runs on every tick in both AUTO and MANUAL. It reuses the existing rules for close-range safety.

1. Sensor data stale (older than `sensor_stale_s`) or all three invalid → `STOP`. This is the existing rule 1.
2. Action moves forward and center < `stop_cm` → `STOP`.
3. Action moves forward and center < `slow_cm` → cap at `FORWARD_SLOW`.
4. Action is a turn toward a side < `side_near` → `STOP`.
5. `BACK_UP` is always allowed. The robot has no rear sensor, so it is time-limited to 1.5 s at a time.

In AUTO, the controller already follows these rules, so the gate should never fire. If it does, that is a bug, and it is logged. In MANUAL, the gate is what stops a responder from driving into a wall. The dashboard shows the veto reason ("blocked: something 12 cm ahead").

A YOLO person-near hold is also applied here (section 8.3).

### 6.3 Dead-man stop (`deadman.py`)

There are two independent timers. Either one stops the motors.

| Timer | Kept alive by | Timeout | On timeout |
| --- | --- | --- | --- |
| **Motor watchdog** (on the robot) | every `Motors.apply()` call | 0.5 s | `Motors.stop()`, repeated every 0.2 s until commands resume. This catches a crashed or frozen control loop. |
| **Link watchdog** | dashboard heartbeat over the WebSocket, sent every 100 ms | 0.5 s in MANUAL, 2 s in AUTO | MANUAL → `STOPPED`. AUTO → `STOPPED` by default (`safety.auto_on_link_loss: stop`), can be set to `continue` for a demo of robot autonomy out of Wi-Fi range. |

- In MANUAL, a drive command is only valid for 0.3 s. The dashboard repeats it every 100 ms while the button or key is held. Releasing = no more commands = stop within 0.3 s. Only real drive commands keep the robot moving. Heartbeats keep the link alive but never keep the wheels turning.
- Both timeouts are in config and shown live on the dashboard.

### 6.4 Done when

- Unit tests: every gate rule, both timers, E-stop from each mode, and boot in `STOPPED`.
- Mac manual test from section 4.4 passes.
- On the Pi with wheels off the ground: pull the Wi-Fi mid-drive → wheels stop within 0.5 s.

---

## 7. Robot server (`scoutbot/server/app.py`)

This is FastAPI served by uvicorn, as the diagram says. The existing `web_demo.py` stays as the debug tool.

| Endpoint | What |
| --- | --- |
| `GET /` | responder dashboard (`static/responder.html`) |
| `GET /video.mjpg` | live MJPEG stream, ~15 FPS, 640 px. The same technique as `web_demo.py` `/video`. |
| `GET /snapshot.jpg` | latest frame |
| `WS /ws` | two-way: state pushed at 10 Hz, commands received (below) |
| `GET /api/survivors` | all survivor records |
| `GET /api/survivors/{id}` | one record, including chat and triage |
| `GET /snapshots/{file}` | saved survivor photos |
| `GET /api/map` | pose trail, survivor pins, obstacle points |
| `POST /api/detections` | used by the remote YOLO worker (section 8.2) |
| `GET /api/health` | versions, uptime, every worker's last-tick age |

**WebSocket messages from the dashboard:**

```json
{"type":"heartbeat","t":1790400000.12}
{"type":"mode","mode":"AUTO"}                    // STOPPED | AUTO | MANUAL
{"type":"estop"}
{"type":"drive","action":"FORWARD","seq":1812}   // MANUAL only, repeated every 100 ms while held
{"type":"chat","survivor_id":"S-0001","role":"survivor","text":"my leg is stuck"}
{"type":"chat","survivor_id":"S-0001","role":"responder","text":"help is 5 minutes away"}
{"type":"retriage","survivor_id":"S-0001"}
{"type":"sim","offline":true}                    // test toggle: pretend the internet is down
```

**State pushed to the dashboard** (10 Hz, only fields that changed after the first message): mode; action, rule and reason; gate veto; sensors raw and filtered; scene report and age; YOLO detections with boxes; pose; link, internet, Gemini, Ollama and database status; dead-man timers; latest survivor summary; and new chat messages.

- Port 8000. Binds to `0.0.0.0` on the Pi and `127.0.0.1` on the Mac. There's no login for the hackathon, but an optional `SCOUTBOT_TOKEN` in `.env` makes the WebSocket require `?token=`.

---

## 8. Person detection (`scoutbot/perception/`)

### 8.1 Model and speed

- Ultralytics **YOLOv8n**, as the diagram says. Only the `person` class (`classes=[0]`).
- On the Pi 4: export to **NCNN** at **320 px** (`yolo export model=yolov8n.pt format=ncnn imgsz=320`) on the Mac, then copy the folder to the Pi. There are no published Pi 4 numbers, and Pi 5 numbers range from 67 to 290 ms per image at 640 px, so **measure it with `run_yolo_bench.command` on day one**. The target is ≥ 3 FPS at 320 px.
- On the Mac: the PyTorch model with `device="mps"`.
- `YOLO11n` or `YOLO26n` are one config line away (`perception.yolo.model`) if they turn out faster.
- Box → categories: `where` = which third of the image the box center is in; `distance` = box height as a fraction of the image: > 0.5 → near, > 0.2 → mid, else far. These cutoffs go in config and get tuned on real frames.
- Minimum confidence 0.45. A detection must appear in 2 of the last 3 frames before it counts, which cuts flicker and false alarms.

### 8.2 Where YOLO runs (`perception.yolo.where`)

| Value | Meaning |
| --- | --- |
| `robot` (default) | runs as a thread in the robot program |
| `remote` | `python -m scoutbot.perception.worker_remote --video http://<pi>:8000/video.mjpg --robot http://<pi>:8000` runs on the laptop and posts detections to `/api/detections`. Use this if the Pi 4 is too slow. |
| `off` | people come from Gemini only |

The code is the same in all three cases. Only where it runs changes.

### 8.3 Fusing YOLO with Gemini (`fusion.py`)

The brain is **not changed**. Fusion happens around it.

1. **Gemini report present and fresh:** if YOLO has a confirmed person that Gemini missed, a copy of the `SceneReport` is made with `people` set from YOLO (`visible=true`, YOLO's where and distance), and that copy is what goes into `Controller.step()`. If both see a person, the **nearer** distance is kept. YOLO can add a person but can never remove one Gemini saw. This follows the existing policy that the camera side can only add caution.
2. **Gemini offline or stale:** the brain skips its camera rules, as today. The safety gate adds one rule: a confirmed YOLO person at `near` + a forward action → `STOP` ("person ahead (YOLO)"). The robot still turns and backs up normally.
3. Every tick logs which source said what, and disagreements are counted in the existing `robot/metrics.py` style (YOLO-only person, Gemini-only person).

### 8.4 Done when

- `run_yolo_bench.command` prints an FPS on the Mac, and later on the Pi.
- Standing in front of the webcam → confirmed detection within 1 s → robot stops in AUTO.
- Unit tests for box → where/distance, the 2-of-3 confirmation, and both fusion cases.

---

## 9. Survivor log and map (`scoutbot/survivors/`)

### 9.1 Pose estimate (`pose.py`)

- **Dead reckoning:** integrate the *executed* action over time using the calibration speeds from section 5.3. In the sim, the true pose is also available for comparison.
- `uncertainty_cm = 30 + 0.3 × distance travelled since start`. The research found about 30% drift without wheel encoders, so the dashboard draws this as a circle, not a false exact point.
- A `PoseEstimator` interface lets an IMU- or encoder-based version replace this later (on hold until the hardware team confirms). The rest of the code does not change.

### 9.2 Survivor registry (`registry.py`)

- **New sighting:** a confirmed person detection (YOLO or Gemini). Its estimated position = robot pose + bearing (left −25°, center 0°, right +25°) × distance (near 0.7 m, mid 2 m, far 4 m).
- **Merge rule:** if a sighting is within `max(100 cm, 1.5 × uncertainty)` of an existing survivor, it updates that survivor (`sightings+1`, `last_seen`, and the position averages in). Otherwise a new survivor `S-000N` is created.
- **Snapshot:** saved on the first sighting and again when a later sighting has a bigger YOLO box (a better view). Keep at most 5 per survivor.
- A new survivor triggers the talk lane (section 10): triage + greeting.
- Every change writes the full record to `data/survivors.jsonl` **first**, then drops a copy in the sync outbox.

### 9.3 Map (`mapping.py`)

- Breadcrumb trail of poses (one every 20 cm travelled).
- Survivor pins with uncertainty circles, colored by triage category.
- Obstacle dots: each valid distance reading turned into a point from the current pose. Only the last 2,000 are kept. This is a rough sketch, not a real map, and it is labeled "approximate" on the dashboard.

### 9.4 Done when

- Sim world with 3 fake survivors → exactly 3 records, pins within their uncertainty circles of the true positions.
- Restarting the program reloads `survivors.jsonl`, so survivors persist.

---

## 10. Talk lane: triage and survivor chat (`scoutbot/talk/`)

This lane only writes words. It never imports motor code.

### 10.1 Online/offline router (`router.py`)

- A **net checker** makes a small HTTPS request to the Gemini endpoint every 3 s and sets `internet: online|offline`. The dashboard's "simulate offline" toggle forces offline for testing.
- A **circuit breaker** around Gemini calls works like this. A call gets 1 quick retry (on 503 or a timeout). After 3 failures in a row, the circuit **opens**: all talk goes to Ollama for 30 s, then one test call is tried. If it works, the circuit closes and Gemini is used again. This matches the existing rule of 3 failures meaning offline.
- If Ollama is also unreachable, the robot uses canned replies ("Help is on the way. Stay where you are if you can. Can you tell me if you are hurt?") and triage stays `UNKNOWN`.
- Every triage and reply records which model made it. The dashboard shows it.
- Timeouts: Gemini talk 8 s, Ollama 20 s. These are longer than the scene VLM's timeouts because nothing about driving waits on them.

### 10.2 Triage (`triage.py` + the model)

The model **extracts facts**, and plain rules **pick the category**. This is the same idea as the driving brain. It is loosely based on START adult triage, simplified because the robot can't measure breathing rate or pulse.

| Order | Condition (from `TriageFacts`) | Category |
| --- | --- | --- |
| 1 | `can_walk == yes` | MINOR (green) |
| 2 | `responsive == no` | IMMEDIATE (red) |
| 3 | `breathing_trouble == yes` or `visible_bleeding == yes` | IMMEDIATE |
| 4 | `trapped == yes` | IMMEDIATE |
| 5 | `responsive == yes` | DELAYED (yellow) |
| 6 | anything else | UNKNOWN (grey) |

- **Online (Gemini):** input = best snapshot + the survivor's chat so far + the latest `SceneReport` hazards. Output = `TriageFacts` as JSON (schema embedded in the prompt, like `robot/vlm.py`, since Gemini's `response_schema` failed before). It is validated with Pydantic, and anything invalid falls back to `UNKNOWN`.
- **Offline (Ollama, text only):** input = chat so far + the last scene report and YOLO results *as text* (for example "person visible, center, near; hazards: water left near"). It uses Ollama's `format` field with the JSON schema so replies are valid JSON.
- Triage re-runs when the survivor says something new or the responder presses **Re-triage**. Categories can go up or down, and every change is logged.
- It is always labeled **"Preliminary – for responder review"**, both on the dashboard and in the database.

### 10.3 Survivor chat

- **How survivor words get in (v1):** the dashboard has a "survivor says" box, which a teammate types into during the demo. Microphone + speech-to-text is a later swap behind the same `SurvivorInput` interface (open question 5).
- **Robot replies:** Gemini online or Ollama offline. The system prompt (`prompts/reply_v1.txt`) says to keep replies to at most 2 short sentences, be calm, ask one question at a time, never promise times or rescues, never give medical treatment beyond "keep pressure on bleeding" and "don't move if your neck or back hurts", and always say that a human responder is coming.
- **Responder messages:** the responder can type directly. These are spoken as-is by the voice lane, marked `role=responder`, and skip the model.
- **Greeting:** a new survivor automatically gets "Hello, I'm a rescue robot. Help is being called. Can you hear me?"
- Each conversation is capped at the last 12 messages sent to the model, to keep Ollama fast.

### 10.4 Ollama setup (laptop)

```bash
brew install ollama && ollama serve        # on the laptop
ollama pull qwen2.5:3b                     # the diagram's model
OLLAMA_HOST=0.0.0.0 ollama serve           # so the Pi can reach it over Wi-Fi
```

- The model name is in config (`talk.ollama.model`). If there's time, compare `llama3.2:3b` or a newer 3–4B model with `run_ollama_check.command`. Pick on speed and JSON reliability, measured on your laptop.
- Set `keep_alive: 30m` on requests so the model stays loaded and the first offline reply isn't slow.

### 10.5 Done when

- Online: a new survivor gets a triage card within 10 s and a spoken greeting.
- Offline toggle: the next reply comes from `ollama`, the triage card shows `ollama:qwen2.5:3b`, and nothing about driving changes.
- Unit tests: every triage rule, invalid model JSON → `UNKNOWN`, circuit breaker open/close timing, and the canned fallback.

---

## 11. Voice (`scoutbot/voice/`)

```python
class Speaker(Protocol):
    def say(self, text: str, priority: int = 0) -> None: ...   # non-blocking, queued
```

- **Online:** ElevenLabs `eleven_flash_v2_5`, **streamed**, so speech starts before the whole clip is made. The voice ID is in `.env` (`ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`). The router's online/offline state decides whether to use it.
- **Offline fallback:** `espeak-ng` on the Pi (tiny and robotic but works), and `say` on the Mac. Research found Piper needs too much memory for a Pi 4.
- **Queue:** one clip at a time. Responder messages and the greeting jump the queue. The same sentence is never repeated within 10 s.
- **Where audio plays:** out of the robot's speaker (the Pi's 3.5 mm jack or a USB speaker). On the Mac, out of the laptop speakers. `fake` prints `[SAY] …`.
- **Done when:** a new survivor's greeting is heard in under 2 s online, and the fallback voice speaks when offline.

---

## 12. Sync: Tiger Data and MongoDB (`scoutbot/sync/`)

### 12.1 Outbox (local first)

- Every survivor change is already in `data/survivors.jsonl` (section 9.2). The outbox is `data/outbox/<survivor_id>.json`, holding the newest version only, so repeated edits collapse into one upload.
- The sync worker runs only when `internet == online`. Each sink sends every outbox record, and a file is deleted only after **both** enabled sinks confirm. Failures back off: 2 s, 4 s, 8 s, up to 60 s.
- Writes are **upserts by `survivor.id` and `version`**, so sending the same record twice is harmless.

### 12.2 Sinks

| Sink | What is stored |
| --- | --- |
| **MongoDB** (Atlas free tier, `pymongo`) | Collection `survivors`: one document per survivor, including chat and triage history. Collection `runs`: one document per program run. `MONGODB_URI` goes in `.env`. |
| **Tiger Data** (Tiger Cloud free tier, Postgres + TimescaleDB, `psycopg`) | Table `survivors` (latest record, JSONB) + a **hypertable** `sightings(time, survivor_id, x_cm, y_cm, uncertainty_cm, source, confidence)` + a hypertable `telemetry(time, action, rule, left_cm, center_cm, right_cm, internet)` sampled at 1 Hz. Time-series data is Tiger's strength, and a good story for their prize. `TIGER_DATABASE_URL` goes in `.env`. |

- Each sink is behind one interface: `upsert_survivor(s)`, `add_sightings(list)`, `add_telemetry(list)`. Turn them on or off in config (`sync.sinks: [mongo, tiger]`).
- The dashboard shows the per-sink status: queued count, last success time, last error.

### 12.3 Done when

- Offline for 2 minutes with 2 survivors found → outbox has 2 files. Online → both appear in Mongo and Tiger within 10 s, and the outbox empties.

---

## 13. Responder dashboard (`scoutbot/server/static/responder.html`)

This is a new single page served by the robot. It is separate from the existing `dashboard.html`, which stays your brain debug view. It's plain HTML/JS with no build step, in the same dark style as the existing dashboard.

**Layout (desktop first, works on a phone):**

- **Top bar:** mode chip (STOPPED/AUTO/MANUAL), big red **STOP** (space bar), **Start auto**, **Take control**. Status chips: Robot link, Internet, Gemini, Ollama, Mongo, Tiger, and dead-man timers.
- **Left:** live video (`/video.mjpg`) with YOLO boxes drawn on a canvas overlay. Current action + rule + reason, and the safety-gate veto if any. The three distance readings as bars.
- **Drive pad (MANUAL only):** hold-to-drive buttons and keys (W/A/S/D, with Shift for slow). It sends `drive` every 100 ms while held. It shows "blocked: …" when the gate vetoes.
- **Middle:** map canvas with the breadcrumb trail, robot arrow, uncertainty circle, obstacle dots, and survivor pins colored by triage (plus the sim ghost when in sim).
- **Right:** survivor list (id, triage color, last seen, sightings). Click one to open its card: best snapshot, triage category + facts + model + "Preliminary", **Re-triage**, and the chat thread with two input boxes ("survivor says" and "responder says").
- **Test strip (only when `server.test_controls: true`):** simulate offline, and for `sliders` sensors, the three sliders.

**Behavior:**

- One WebSocket. It reconnects with backoff, and while disconnected the page greys out and shows "Robot link lost – motors stopped".
- The heartbeat is sent every 100 ms from the page, even when idle.
- Closing the tab or losing focus while driving stops sending drive commands, so the robot stops.

---

## 14. Build order for today

Each slice ends with something that runs end to end on the Mac. Hardware bring-up (slice H) runs in parallel whenever the team hands over parts. Times are rough guesses.

| # | Slice | Done when | Rough time |
| --- | --- | --- | --- |
| 0 | ✅ Commit current work | `b297ea4` | done |
| 1 | Skeleton: `scoutbot/` package, profiles, state, runtime, hardware interfaces with fakes, control loop calling the existing `Controller` | `python -m scoutbot --profile mac` prints decisions from webcam + random sensors; all 52 old tests pass | 1 h |
| 2 | Safety: modes, gate, dead-man + tests | gate/deadman tests pass | 45 min |
| 3 | Server + responder dashboard v1: video, state, STOP, Start auto, manual drive | Mac manual-drive checklist passes | 1.5 h |
| 4 | Sim world + pose + map | robot explores `room_basic` 5 min with 0 contacts; map drawn | 1 h |
| 5 | YOLO + fusion + survivor registry + snapshots | stand in front of webcam → stop + survivor pin | 1.5 h |
| 6 | Talk lane: Gemini triage/replies, router, Ollama, canned fallback | online and offline chat both work; triage cards show | 1.5 h |
| 7 | Voice: ElevenLabs + local fallback | greeting heard online and offline | 45 min |
| 8 | Sync: outbox + Mongo + Tiger | offline → online sync test passes | 1 h |
| 9 | Demo polish + rehearsal (section 17) | full demo run twice without touching code | 1 h |
| H | **Pi bring-up (parallel):** OS, venv, camera, `run_yolo_bench` → choose YOLO `robot` or `remote`, sensors, motors wheels-off, calibration speeds, full run at slow speed | section 16 checklist | whenever parts arrive |

**If time runs short, cut in this order** (every box still exists, just simpler): obstacle dots on the map → sim world ghost → Tiger telemetry hypertable (keep survivors) → re-triage button → voice queue priorities. Never cut the safety gate, dead-man, or offline fallback.

### Pi bring-up checklist (slice H)

- [ ] Raspberry Pi OS 64-bit, Python 3.11, `python -m venv .venv`, `pip install -r requirements-pi.txt`.
- [ ] Separate power for motors and Pi, with a common ground. Pi 4 needs a real 5 V 3 A supply. The L298N drops about 2 V, so motor battery ≥ 7.4 V.
- [ ] Physical power cutoff reachable by hand. **First motor tests with wheels off the ground.**
- [ ] Camera: `python -m scoutbot.tools.camcheck` saves 20 frames; look at them.
- [ ] YOLO: `run_yolo_bench` at 320 px NCNN. If < 3 FPS, set `perception.yolo.where: remote`.
- [ ] Distance: each sensor against a tape measure at 20 / 50 / 100 cm; all three on together with steady readings.
- [ ] Motors: each action spins the right wheels the right way; fix with config, not rewiring.
- [ ] Calibrate: time 1 m forward, 1 m slow, one 360° turn → fill in the `motion.*` numbers.
- [ ] Dead-man: pull Wi-Fi mid-drive → stop.
- [ ] Ollama reachable from the Pi: `curl http://<laptop-ip>:11434/api/tags`.

---

## 15. Config reference (`config/profiles/base.yaml`, main keys)

```yaml
hw:
  camera: opencv            # opencv | folder
  camera_index: 1
  camera_folder: dataset/
  distance: sliders         # sliders | random | scripted | simworld | hcsr04 | tof
  motors: fake              # fake | l298n
  pins: {trig: [23, 24, 25], echo: [17, 27, 22], left: {fwd: 5, back: 6, en: 12}, right: {fwd: 13, back: 19, en: 18}}   # placeholders – hardware team fills in
motion: {forward_cm_s: 30, slow_cm_s: 18, backup_cm_s: 18, turn_deg_s: 90, ramp_s: 0.15, trim_left: 1.0, trim_right: 1.0}
speeds: {FORWARD: [0.6, 0.6], FORWARD_SLOW: [0.35, 0.35], TURN_LEFT: [-0.45, 0.45], TURN_RIGHT: [0.45, -0.45], BACK_UP: [-0.35, -0.35]}
safety: {motor_watchdog_s: 0.5, manual_cmd_valid_s: 0.3, link_timeout_manual_s: 0.5, link_timeout_auto_s: 2.0, auto_on_link_loss: stop, backup_max_s: 1.5}
scene: {provider: gemini, interval_s: 2.0}        # gemini | fake  (uses existing robot/vlm.py)
perception:
  yolo: {where: robot, model: yolov8n.pt, format: pt, imgsz: 320, device: auto, min_conf: 0.45, confirm: [2, 3], near_frac: 0.5, mid_frac: 0.2}
survivors: {merge_cm: 100, bearing_deg: 25, dist_cm: {near: 70, mid: 200, far: 400}, max_snapshots: 5}
talk:
  gemini: {model_env: GEMINI_MODEL, timeout_s: 8}
  ollama: {url: http://localhost:11434, model: qwen2.5:3b, timeout_s: 20, keep_alive: 30m}
  breaker: {fail_threshold: 3, open_s: 30}
  history_messages: 12
voice: {provider: elevenlabs, fallback: local, model: eleven_flash_v2_5, dedupe_s: 10}
sync: {sinks: [mongo, tiger], interval_s: 3, backoff_max_s: 60, telemetry_hz: 1}
net: {check_interval_s: 3, force_offline: false}
sim: {world: room_basic, fake_people: true, noise: 0.05}
server: {host: 127.0.0.1, port: 8000, test_controls: true, state_hz: 10}
```

New `.env` keys (never committed, never printed): `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, `MONGODB_URI`, `TIGER_DATABASE_URL`, optional `SCOUTBOT_TOKEN`. Add them to `.env.example` with placeholder values.

New dependencies: `fastapi`, `uvicorn[standard]`, `pyyaml`, `httpx`, `ultralytics`, `pymongo`, `psycopg[binary]`. On the Pi also `gpiozero`, `lgpio`, `ncnn`, and `smbus2` if using ToF. Split them into `requirements.txt` (Mac) and `requirements-pi.txt`.

---

## 16. Risks and fallbacks

| Risk | Fallback that keeps the box on the diagram |
| --- | --- |
| YOLO too slow on the Pi 4 | `perception.yolo.where: remote` – same code runs on the laptop |
| GoPro won't stream to the Pi | any USB webcam; nothing else changes |
| Pi or motors not ready in time | demo on `--profile sim` with the real webcam, and show the hardware separately; every box still runs |
| Venue internet flaky | this *is* the offline demo – Ollama, local voice and the outbox are built for it |
| Venue Wi-Fi blocks device-to-device traffic | phone hotspot for the Pi + laptop |
| Gemini triage JSON invalid | falls back to `UNKNOWN` + canned reply; logged |
| Ollama slow on first reply | `keep_alive`, warm-up call at startup |
| Survivors duplicated on the map | raise `merge_cm`; tune in the sim first |
| Dead reckoning drifts badly | it's shown honestly as an uncertainty circle; the IMU/encoders can plug in later |
| Responder drives into something | safety gate vetoes in MANUAL, E-stop, dead-man |

---

## 17. Demo script (about 3 minutes)

1. The dashboard is up and the robot is `STOPPED`. Press **Start auto**. The robot explores and avoids a box, and the dashboard shows the rule that fired.
2. A teammate lies down partly behind an obstacle. YOLO box appears → robot stops → survivor pin on the map → the greeting is spoken by ElevenLabs.
3. The teammate types (as the survivor): "I can't feel my leg, it's stuck." A triage card turns **red – IMMEDIATE (trapped)**, marked preliminary, and Gemini's reply is spoken.
4. Toggle **simulate offline** (or unplug the hotspot's internet). The chips turn orange. The next reply comes from Ollama in a robotic local voice. Survivor records show "queued".
5. Toggle back online. Mongo and Tiger chips go green, and the records appear. Show the Tiger `sightings` table and the Mongo document.
6. Press **Take control**, drive toward a wall, and see "blocked" from the gate. Let go and it stops. Press **STOP**.

Close with the key design idea: *"The AI never drives. It describes, and plain rules decide."*

---

## 18. Tests to add

- `tests/test_gate.py`: every gate rule, in both AUTO and MANUAL.
- `tests/test_deadman.py`: motor watchdog, manual command expiry, link timeouts per mode, boot in `STOPPED`, E-stop from each mode.
- `tests/test_fusion.py`: YOLO adds a person, YOLO never removes one, nearer distance wins, the YOLO-only hold when Gemini is offline.
- `tests/test_yolo_mapping.py`: box → where/distance, 2-of-3 confirmation.
- `tests/test_registry.py`: merge vs new survivor, snapshots capped, reload from `survivors.jsonl`.
- `tests/test_triage.py`: every triage rule, invalid JSON → `UNKNOWN`.
- `tests/test_router.py`: breaker opens after 3 failures, closes after a good probe, canned fallback when both models are down (fake clients, no network).
- `tests/test_outbox.py`: newest version wins, deleted only after all sinks confirm, backoff.
- `tests/test_isolation.py`: importing `scoutbot.talk`, `scoutbot.voice` and `scoutbot.sync` never imports `scoutbot.hw.motors_*` or `scoutbot.safety`.
- `tests/test_simworld.py`: raycast distances against known walls; 5-minute auto run has 0 wall contacts (fast-forwarded clock).

Run them all with `python -m pytest -q tests`. The existing 52 must still pass.

---

## 19. Open questions for the hardware team

1. **Distance sensors:** 3 × HC-SR04 (ultrasonic), as in the code, or ToF over I²C, as on the diagram? Which model?
2. **Pins:** GPIO numbers for sensors and the L298N (the config has placeholders).
3. **Camera:** GoPro model, and does it show up as a webcam on the Pi? Is there a backup USB webcam?
4. **Encoders or IMU:** coming or not? (On hold. The map works without them, just less accurately.)
5. **Microphone and speaker on the robot?** A speaker is needed for voice. A microphone would let survivors talk instead of a teammate typing (later swap).
6. **Power:** motor battery voltage, and is there a physical kill switch?
7. **When** will each part be ready, so slice H can be scheduled?
