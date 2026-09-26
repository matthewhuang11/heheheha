# Known issues and gaps (as of main @ 705ccab)

Each item has an ID, an owner and a priority, and the agent briefs refer to these IDs. When you fix one, put its ID in the commit message (e.g. `[robot] fix KI-01: motor_check spins wheels`) and tick it in STATUS.

P0 = do today first. P1 = needed for a solid demo. P2 = nice to have.

## Bugs

| ID | Owner | Pri | Problem | Where | Fix direction |
| --- | --- | --- | --- | --- | --- |
| KI-01 | A | P0 | `motor_check` never spins the wheels. It calls `motors.apply(action)` once and sleeps, but `Ramp.set` starts from 0 with dt=0, so the output stays 0. | `scoutbot/tools/motor_check.py` | Call `apply` every 0.1 s for the whole step, then `stop()`. Add a test with `FakeMotors` checking `current()` is non-zero mid-step. |
| KI-02 | C | P0 | The Codex launchers call `python`, which doesn't exist on many Macs (only `python3`). | `run_*.command` | `PY=python3; [ -x .venv/bin/python ] && PY=.venv/bin/python`, then `"$PY" -m ...`. |
| KI-03 | B | P0 | `.env.example` fills optional keys with fake values (`replace_with_a_long_random_token`, `mongodb://user:password@host/...`). Copied to `.env`, they lock the dashboard behind a token nobody knows and cause fake database errors. | `.env.example` | Leave every optional key empty, with one comment line each. |
| KI-04 | A | P1 | `sensor_check` crashes (`min()` of an empty list) if a sensor never echoes. | `scoutbot/tools/sensor_check.py` | Print "no echo at all: check wiring and the voltage divider" instead. |
| KI-05 | A | P1 | `yolo_bench --export-ncnn` ignores `--imgsz` and doesn't tell you where the export went. | `scoutbot/tools/yolo_bench.py` | `model.export(format="ncnn", imgsz=a.imgsz)` and print the output folder plus the `pi.yaml` line to use. |
| KI-06 | A | P1 | `scripts/pi_setup.sh` fails on Pi OS Bookworm if `libatlas-base-dev` is missing, and doesn't install `libgl1` (needed by OpenCV) or `requirements-yolo`. | `scripts/pi_setup.sh` | Split essential and optional apt packages (`|| true` for optional), and make it safe to run twice. |
| KI-07 | C | P1 | The `sim` and `sensor` WebSocket commands are accepted even on the real robot (`server.test_controls: false`), so anyone on the Wi-Fi could fake "offline" or sensor values. | `scoutbot/runtime.py: command()` | Refuse `sim` and `sensor` unless `server.test_controls` is true. |
| KI-08 | C | P1 | `Runtime.state()` deep-copies every survivor with its whole chat, 10 times a second, for each connected dashboard. That gets slow with many survivors or long chats. | `runtime.py: state()`, `registry.all()` | Add `Registry.summaries()` (cheap: no chat copies) and cache it for 0.5 s. |
| KI-09 | C | P2 | A survivor snapshot is taken from the frame current when the survivor loop runs, not the exact frame YOLO saw. | `runtime.py: survivor_loop` | Save the frame with the detections in `PerceptionWorker` (A: add `shared.det_frame`) and use it. |
| KI-10 | B | P2 | `robot/vlm.describe()` creates a new Gemini client on every call (slower, more connections). | `robot/vlm.py` | Cache the client at module level, keyed by the API key. |
| KI-11 | A+C | P2 | When YOLO's person changes mid-report, the rebuilt fused copy is pushed into `SceneFilter` as an extra report with the same timestamp, which can double-count hazards in its "2 of last 3" rule. | `perception/fusion.py`, `robot/scene_filter.py` (frozen) | Only rebuild the fused copy when the Gemini report changes, and apply a YOLO-only person change through the gate hold instead. Discuss in STATUS first. |
| KI-12 | B | P2 | The `Speaker.recent` de-dup dict grows forever. | `voice/speaker.py` | Prune entries older than `dedupe_s`. |

## Config keys that exist but do nothing yet

| ID | Owner | Key | Fix |
| --- | --- | --- | --- |
| KI-20 | B | `talk.history_messages` | Pass it to `transcript(chat, limit)` in both models. |
| KI-21 | C | `sim.fake_people` | When false, `PerceptionWorker(where=sim)` and `simworld.scene_report()` should report no people (tests the "no person" paths). |
| KI-22 | A | `motion.slow_cm_s`, `motion.backup_cm_s` | The pose estimate scales everything from `forward_cm_s`. Use a per-action calibration: a measured speed for FORWARD, SLOW and BACK_UP, and `turn_deg_s` for turns, interpolated during the ramp. A owns the calibration numbers; C owns `pose.py`, so this is a joint task: A requests it, and C implements it with A's numbers. |

## Gaps: not built yet

| ID | Owner | Pri | Gap |
| --- | --- | --- | --- |
| KI-30 | C | P0 | No one-step setup on any computer: no `scripts/setup.py`, no `start.command`/`start.sh`/`start.bat`, no `python -m scoutbot.start` menu, no `doctor` tool. |
| KI-31 | C | P0 | The dashboard can't be opened from other devices without `--set server.host=0.0.0.0`, and nothing prints the LAN address. There is no `--share` flag. |
| KI-32 | C | P0 | The profile is called `mac` but works on any laptop. Rename it to `laptop` and keep `mac` as an alias. |
| KI-33 | A | P0 | Camera index: base default 1 (Matthew's Mac). Other computers need 0, and a wrong index means "no camera". There is no auto-detect. |
| KI-34 | C+A+B | P0 | Windows safety: file reads without `encoding="utf-8"`; `±` printed to the console (crashes some Windows consoles); no Windows camera backend hint (`CAP_DSHOW`). Each owner fixes their own files. |
| KI-35 | B | P0 | No Windows offline voice (LocalVoice only knows `say`/`espeak`), and ElevenLabs playback needs `afplay`, `mpg123` or `ffplay` (none of which Windows has). |
| KI-36 | B | P1 | Sync sinks don't turn themselves on: `mac` and `sim` have `sinks: []`, so Mongo and Tiger never run on a laptop even with URLs in `.env`. |
| KI-37 | C | P1 | `requirements.txt` includes `ultralytics` (PyTorch, hundreds of MB), which makes setup slow everywhere. Move it to `requirements-yolo.txt` (A) and install it as an optional step. |
| KI-38 | A+C | P1 | **AUTO holds forever at a nearby person** (brain rule 5 → STOP). Good for the v1 demo, but the robot can't carry on searching. Proposal: a dashboard button, "Continue search (S-0001 handled)", that makes fusion and the gate ignore that survivor's position for 60 s. A owns the fusion/gate side and C the button plus the survivor ↔ detection matching. Brain rules stay frozen. |
| KI-39 | A | P2 | **Sensor blind spot.** In the sim, the robot's side clipped the thin end of a wall at about 80° off heading, where no sensor sees (sensors at 0 and ±30°, 15° beams). Add a `hw.sensor_angles` config and recommend a layout to the hardware team. C makes `simworld.py` and `mapping.py` read it. |
| KI-40 | A | P2 | Downward cliff sensor: `Controller.step(..., cliff=)` exists but nothing feeds it. |
| KI-41 | B | P2 | Survivors can't talk: a teammate types for them. Add a speech-to-text input (press-to-talk on the dashboard). |
| KI-42 | C | P1 | The README has only 3 lines for Scoutbot. It needs a real quick start, troubleshooting and the demo script. |
| KI-43 | B | P1 | Nothing proves Gemini, Ollama, ElevenLabs, Mongo or Tiger work for real. There are no live-check tools apart from `ollama_check`. Add `talk_check`, `voice_check` and `sync_check`. |
| KI-44 | C | P1 | The dashboard's "Gemini" chip shows the talk status only. Scene (driving camera) errors are hidden in a tooltip. Show both, e.g. "Gemini scene ✓ / talk ✓". |

## Not problems (decided, don't "fix")

- **Far sightings (over about 2.5 m) never create a survivor.** This is on purpose: the position guess is too rough.
- **The gate's "turn toward a close side" veto only applies in MANUAL.** In AUTO the brain already turns away from close sides, and turning in place is safe.
- **BACK_UP is limited to 1.5 s bursts with 0.5 s pauses.** There is no rear sensor.
- **Survivors can be recorded while the robot is STOPPED.** The camera keeps watching, which is useful.
- **`sync.telemetry` rows are only queued when at least one sink is on.** The local log `logs/scoutbot_run.jsonl` always has everything.
