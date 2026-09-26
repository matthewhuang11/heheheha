# Contracts between the three areas

These are the seams where one agent's code calls another's. **Adding** things (a new optional field with a default, a new optional argument, a new message type) is fine: note it in STATUS. **Changing or removing** anything below needs a STATUS note *before* you push, and you must update every caller in the same commit. The owner is in brackets.

## 1. Hardware interfaces [A] (`scoutbot/hw/base.py`)

```python
class Camera(Protocol):
    def read(self) -> np.ndarray | None   # newest BGR frame, or None; may block up to ~1/fps
    def close(self) -> None
    ok: bool                              # True if the device opened (used by build() to fall back)

class DistanceSensors(Protocol):
    def read(self) -> robot.types.Sensors # RAW cm (not filtered); invalid reading => valid[i]=False (value ignored);
                                          # updated_at = time.monotonic() of the measurement; takes ~60-200 ms
    def close(self) -> None

class Motors(Protocol):
    def apply(self, action: Action) -> None       # called at 10 Hz by the control loop ONLY; ramps toward target
    def stop(self) -> None                        # immediate, idempotent, any thread (watchdog, E-stop, exit)
    def current(self) -> tuple[float, float]      # wheel fractions being output now (after ramp), -1..1
    def close(self) -> None

def build(cfg, shared, world=None) -> (Camera, DistanceSensors, Motors)
def wheel_speeds(action, cfg) -> (left, right)   # from cfg["speeds"] x trim
```

Rules:
- A missing echo is `valid=False`. It is **never** a large number.
- Real drivers import their Pi libraries inside `__init__`, so importing the module on a laptop never fails.
- `current()` is what the pose estimate integrates. If A adds wheel encoders later, add a new optional method (`odometry()`) rather than changing `current()`.
- Optional additions A may make: `read_cliff() -> float | None` on `DistanceSensors` (the downward sensor, cm; None = no sensor; 999 = no floor), and `hw.sensor_angles` in config (default `[30, 0, -30]`, left/center/right degrees, CCW positive).

## 2. Perception [A] → runtime [C]

```python
class PersonDetection(BaseModel):          # scoutbot/types.py (C owns the file, A owns the meaning)
    source: Literal["yolo", "gemini", "sim"]
    where: Literal["left", "center", "right"]     # which third of the image
    distance: Literal["near", "mid", "far"]       # near < ~1 m, mid ~1-2.5 m, far beyond (A tunes the cut-offs)
    confidence: float                              # 0..1
    bbox: tuple[float, float, float, float] | None # normalized x1, y1, x2, y2, or None
    track_id: str | None                           # optional stable detector identity; registry prefers it over spatial merging
    at: float                                      # time.monotonic() on the ROBOT
```
- `PerceptionWorker` writes **confirmed** detections only: `shared.detections` (list), `shared.det_at` (monotonic), `shared.det_fps`, and `shared.det_status`.
- **`det_status` values have meaning:** `"running"`, `"sim"` and anything starting with `"remote"` = a live detector. The runtime's survivor loop only falls back to Gemini's people report when the status is none of these (`"off"`, `"loading model"`, `"unavailable: ..."`, `"error: ..."`). Keep those prefixes.
- `POST /api/detections` body: `{"detections": [PersonDetection...], "fps": float}`. The server rewrites `at` to the robot's clock.
- `Fuser.fuse(scene, person) -> SceneReport | None` must return **the same object** while its inputs are unchanged (the SceneFilter cache rule).

## 3. Safety [A] → runtime [C]

```python
Gate(policy, backup_max_s).check(action, mode, L, C, R, sensors_fresh, now, yolo_person_near=False) -> GateResult(action, veto: str|None)
manual_action(cmd: DriveCommand|None, now, valid_s) -> Action
link_check(mode, link_at, now, safety_cfg) -> str|None     # reason string when the link is lost
MotorWatchdog(motors, timeout_s).fed(); .check(); .trips
ModeController(shared, bus).request(mode, reason); .estop(reason); .mode
```

**Safety invariants (tests must keep proving these):**
1. The robot boots in STOPPED, and leaving STOPPED needs an explicit command.
2. E-stop → STOPPED from any mode, and `motors.stop()` is called immediately.
3. Every motor command goes `control_tick → Gate.check → Motors.apply`. Nothing else in the running program calls `apply` (the separate `motor_check` bench tool is the only exception).
4. The motor watchdog stops the motors if `apply` hasn't been called for 0.5 s.
5. A MANUAL drive command expires 0.3 s after it arrives. Heartbeats never keep the wheels moving.
6. A lost link (no WebSocket message for 0.5 s in MANUAL, 2 s in AUTO) → STOPPED, unless `auto_on_link_loss: continue`.
7. Forward is refused when center < `stop_cm`, and capped to SLOW when center < `slow_cm` or has no echo.

## 4. Shared state fields [C] (`scoutbot/state.py`)

Read and write under `shared.lock`. **Writer** means the only code allowed to write that field.

| Field | Type | Writer |
| --- | --- | --- |
| `frame`, `jpeg`, `frame_at`, `frame_seq`, `cam_health` | ndarray (≤640 px wide), bytes, float, int, dict | camera_loop (C) |
| `raw_sensors` | `Sensors` | distance_loop (C, via A's driver) |
| `slider_values`, `slider_valid` | lists of 3 | server command `sensor` (C) |
| `scene`, `scene_at`, `vlm_failures`, `vlm_latency`, `vlm_error`, `vlm_calls` | | scene_loop (C, calling B's `describe`) |
| `detections`, `det_at`, `det_fps`, `det_status` | | PerceptionWorker / `/api/detections` (A) |
| `mode`, `mode_reason`, `drive_cmd` | | ModeController (A) / server command (C) |
| `link_at` | float | server: any WebSocket message (C) |
| `decision`, `final_action`, `veto`, `filtered`, `pose`, `true_pose`, `sim_contacts`, `last_motor_apply`, `watchdog_trips` | | control_tick (C) |
| `internet` | bool | NetWorker (B) |
| `force_offline` | bool | server command `sim` / `net.force_offline` (C/B) |
| `services["gemini"]`, `["ollama"]` | str | TalkWorker / TalkRouter (B) |
| `services["voice"]` | str | Speaker (B) |
| `services["yolo"]` | str | PerceptionWorker (A) |
| `sync_status[sink]` | `{state, queued, last_ok, error, retry_in_s}` | SyncWorker (B) |

**Service status strings:** the dashboard colors a chip green if the string starts with `ok`/`ready`, is `running`/`sim`, or contains ` ok`; red if it contains `error`, `unreach`, `unavailable` or `failed`; amber if it contains `disabled` or `off`; otherwise blue. Keep to that vocabulary. `sync_status.state` ∈ `starting`, `ok`, `offline`, `offline (queued)`, `error`, `not configured`.

## 5. Events on the Bus [C owns the Bus]

`bus.publish(topic, payload)`. The dashboard receives them as `{"type": "event", "seq", "topic", "payload", "t"}`.

| Topic | Payload | Publisher |
| --- | --- | --- |
| `survivor` | full `Survivor.model_dump()` | Registry (C) |
| `chat` | `ChatMessage.model_dump()` | TalkWorker (B) |
| `triage` | `{"survivor_id", **Triage.model_dump()}` | TalkWorker (B) |
| `mode` | `{"mode", "reason"}` | ModeController (A) |
| `net` | `{"online"}` | NetWorker (B), server (C) |

New topics are fine. Tell C in STATUS if the dashboard should show them.

## 6. Talk / voice / sync APIs [B], called by C's code

```python
TalkWorker(cfg, shared, bus, registry, voice, router=None)
TalkWorker.submit(kind, sid, text="", source="typed")   # kind: new_survivor | survivor_says | responder_says | retriage
TalkRouter(online_fn, gemini, ollama, canned=None, breaker=None, status_fn=None).reply(chat, context) -> (text, source)
                                                                                .triage(chat, context, snapshot_bytes) -> Triage
Speaker(cfg, shared).say(text, priority=0, key=None)   # non-blocking; higher priority first; dedupe on key or text
Outbox(data_dir, sinks).put_survivor(survivor); .add_rows(kind, rows)   # kind: sightings | telemetry
SyncWorker(cfg, shared, outbox).start()
NetWorker(cfg, shared, bus).start()
```

- **Row shapes.** `sightings`: `{time (ISO UTC), survivor_id, x_cm, y_cm, uncertainty_cm, source, confidence}`. `telemetry`: `{time, mode, action, rule, left_cm, center_cm, right_cm, internet, x_cm, y_cm}`.
- The Registry calls `outbox.put_survivor` and `add_rows("sightings")`. The runtime calls `add_rows("telemetry")` at `sync.telemetry_hz` (only when there are sinks).
- Planned (B.P1): `scoutbot.sync.resolve_sinks(cfg) -> list[str]`, which turns `"auto"` into the sinks whose URL is set. C (or a B wiring edit) calls it where `Outbox` is created.

## 7. Data models [C owns `scoutbot/types.py`]

`Survivor{id "S-0001", first_seen, last_seen (ISO UTC), pose: Pose (x_cm, y_cm, uncertainty_cm, source), sightings, best_snapshot, snapshots[], best_box_frac, triage: Triage|None, chat: [ChatMessage], version}`.
`Triage{category IMMEDIATE|DELAYED|MINOR|UNKNOWN, rule, facts: TriageFacts, model (e.g. "gemini-flash-lite-latest", "ollama:qwen2.5:3b", "canned"), preliminary: True, at}`.
`TriageFacts{responsive, can_walk, trapped, visible_bleeding, breathing_trouble: yes|no|unknown; hazards_nearby[], injuries_reported[], summary ≤240}`.
`ChatMessage{survivor_id, role survivor|robot|responder, text, source typed|speech|gemini|ollama|responder|canned, at}`.

Add fields with defaults only. Old `survivors.jsonl` lines must still load.

## 8. Dashboard protocol [C]

**WebSocket `/ws`** (`?token=` if `SCOUTBOT_TOKEN` is set). The server sends `hello` once, then `state` at `server.state_hz`, then `event`s, plus `reply` for commands that answer.

Browser → robot (any message also counts as a heartbeat; the page sends `heartbeat` every 100 ms):
```json
{"type":"heartbeat","t":<float>}
{"type":"mode","mode":"STOPPED|AUTO|MANUAL"}
{"type":"estop"}
{"type":"drive","action":"FORWARD|FORWARD_SLOW|TURN_LEFT|TURN_RIGHT|BACK_UP|STOP","seq":<int>}   // MANUAL only, repeat every 100 ms
{"type":"chat","survivor_id":"S-0001","role":"survivor|responder","text":"..."}
{"type":"retriage","survivor_id":"S-0001"}
{"type":"sim","offline":true|false}
{"type":"sensor","i":0|1|2,"value":<cm>,"valid":<bool>}    // sliders profile only
{"type":"handled","survivor_id":"S-0001"}                  // "Continue search": ignore this survivor for survivors.handled_s (60 s); event topic "handled"
{"type":"ping","t":<float>}                                // reply {"type":"reply","for":"ping","ok":true,"t":<same>} (round-trip time)
```
`sim` and `sensor` are refused (`reply ok:false`) unless `server.test_controls` is true (KI-07).

**`state` keys:** `mode, mode_reason, decision{action, rule, reason, notes, stuck}, trace[], final_action, veto, sensors{raw, valid, filtered, age}, scene, scene_age, vlm{failures, latency, error, calls}, detections[], yolo{status, fps}, pose, true_pose, sim_contacts, internet, force_offline, online, services{}, sync{}, camera{healthy, reasons...}, deadman{motor_age, trips, link_age, link_timeout}, sliders{values, valid}, survivors[{id, category, sightings, last_seen, x, y, u, snapshot, messages}]`.

**`hello` keys:** `profile, test_controls, distance, world (sim layout or null), policy{stop_cm, slow_cm, side_near}`.

**REST:** `GET /api/survivors`, `/api/survivors/{id}`, `/api/map` (`{trail, obstacles, true_trail, world}`), `/api/health`, `/api/state`, `/snapshots/{name}`, `/video.mjpg`, `/snapshot.jpg`; `POST /api/detections`.

## 9. Config and environment

- `.env` keys: `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_TALK_MODEL`, `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, `MONGODB_URI`, `TIGER_DATABASE_URL`, `CAMERA_INDEX`, `SCOUTBOT_TOKEN`. B owns `.env.example`.
- Config sections by owner: see [01-shared-rules.md §2](01-shared-rules.md#shared-config-configprofilesbaseyaml).
- `settings.load()` returns a plain dict with `cfg["profile"]` set. Code reads config at startup; there's no live reload.
