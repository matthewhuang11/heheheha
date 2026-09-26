# Scoutbot robot notes

## What works

- A1 / KI-01: `motor_check` feeds each action every 0.1 seconds for one second, prints the ramped wheel output halfway through, then stops before the next action.
- The bench tool skips its physical-wheels confirmation when the configured motor driver is `fake`, so it is safe to exercise on the sim profile.
- A2 / KI-33: OpenCV camera selection tries the configured camera first, skips black or unavailable video feeds, and falls back across indexes 0 through 3. Windows uses OpenCV's DirectShow backend.
- A3/A5: YOLO webcam benchmark supports 320/640 pixels, optional box-height logging, NCNN export, and exported-folder loading. `requirements-yolo.txt` makes the large detector optional.
- KI-04: `sensor_check` now reports an all-missing sensor as a wiring/voltage-divider warning instead of crashing.
- KI-06: `scripts/pi_setup.sh` installs the Bookworm/OpenCV dependencies, enables I2C when available, adds GPIO/I2C group membership, creates the virtual environment and optional `.env`, and continues with remote YOLO guidance if the optional detector install fails.
- Safety proof includes a regression check that only the control loop and the explicit wheels-off-ground bench tool call `Motors.apply()`.

## How to run

```bash
.venv/bin/python -m scoutbot.tools.motor_check --profile sim
.venv/bin/python -m scoutbot.tools.camcheck --profile mac
.venv/bin/python -m scoutbot.tools.sensor_check --profile pi
bash scripts/pi_setup.sh
```

For real hardware, keep the wheels off the ground and confirm the prompt before running:

```bash
.venv/bin/python -m scoutbot.tools.motor_check --profile pi
```

## Measurements

- Sim motor bench, 2026-09-26: FORWARD reached left/right `+0.60/+0.60`; FORWARD_SLOW `+0.35/+0.35`; turns `-/+0.45`; BACK_UP `-0.35/-0.35` at the halfway check.
- Laptop camera check, 2026-09-26: selected index 1 at 1280x720, 37.3 FPS, frames not black. The configured `.env` index remains honored.
- YOLO laptop benchmark, 2026-09-26: 6.88 FPS at 320 px and 7.75 FPS at 640 px on Apple M1 CPU. NCNN 320 export completed in 12.4 seconds; exported NCNN ran at 16.46 FPS on the laptop. The folder is `yolov8n_ncnn_model` (12.1 MB, ignored and must be copied or exported on the Pi).

## Phase 2 live checks (R1-R4, 2026-09-26, Matthew's M1 Mac, webcam index 1)

### R1 near/mid/far (A4): tool ready, measurement needs a person at set distances
- Tool: `python -m scoutbot.tools.distance_tune` (stands at 0.7 / 1.0 / 1.5 / 2.5 / 4.0 m, then lying and half hidden at 1.5 m;
  prints a median/min/max table and suggests `near_frac` = midpoint of the 1.0 m and 1.5 m medians, `mid_frac` = midpoint of
  2.5 m and 4.0 m). Results are saved to `data/distance_tune.json`.
- Smoke readings so far: a person seated at the desk (~0.6-0.8 m) = box height 0.75-0.99 of the frame (always "near" with the
  current 0.5 cut-off). Table and tuned cut-offs: pending Matthew's 4-minute session (STATUS "Needs Matthew").
- NCNN on the laptop, live webcam, 50 frames each with a person in view: `yolov8n.pt` 13.9 FPS, `yolov8n_ncnn_model` 11.5 FPS,
  same boxes (height 0.79 vs 0.75-0.83, conf 0.91-0.93). On the M1 the PyTorch model is as fast or faster, so **the laptop default
  stays `yolov8n.pt`**; NCNN is for the Pi. Ultralytics auto-installs the `ncnn` package on first NCNN use (it is in requirements-pi.txt).

### R2 live person -> STOP (center slider 200 cm, Start auto, person at the desk ~0.7 m)
| path | how | result |
| --- | --- | --- |
| Gemini on | `--profile laptop` (online) | YOLO box ~0.9-2 s after start; survivor created at once; the brain fires **rule 5 "person near" -> STOP** when Gemini's report or YOLO (fused) has a near person. With a seated person partly out of frame the brain sometimes crept at FORWARD_SLOW (rule 7) between reports; see note. |
| Gemini off | `--set net.force_offline=true` | brain runs on sensors only (rule 8), and the gate adds **veto "person ahead (YOLO)" -> STOP** within 0.6 s of AUTO. |
Note: in the Gemini-on clean run, YOLO's first confirmed box came 11.7 s in (the person was mostly outside the frame at the desk);
the gate's YOLO hold only applies when the camera rules are not usable (by design, contracts section 3), so when Gemini says clear and
YOLO sees a near person, fusion adds the person and rule 5 fires on the next tick. A standing person walking into view (Matthew's
session) will be logged here.

### R3 remote YOLO end to end (A6): PASS
- Terminal 1: `python -m scoutbot --profile laptop --set perception.yolo.where=remote --set server.port=8001 --set voice.provider=fake`
- Terminal 2: `python -m scoutbot.perception.worker_remote --robot http://localhost:8001`
- Chip: `remote (laptop worker)` at 26-67 FPS (M1, worker FPS as reported). First confirmed box 6.5 s after the worker started
  (model load + stream open). Survivors created from remote detections.
- Kill the worker: the control loop's person input clears between 0.53 s and 1.17 s (`max_age_s` 1.0), the dashboard list at 1.4 s.
- Robot restarted while the worker runs: the worker printed exactly one "robot video failed ... retrying quietly" line and one
  "is back" line, then resumed detections by itself.
- Bad `POST /api/detections` bodies (not JSON, bad enum, wrong types) now return 400 (test_robot_remote.py).
- Pi use: `pi.yaml` `perception.yolo.where: remote`; on the laptop run the worker with `--robot http://<pi-ip>:8000 [--token T]`.

### R4 camera auto-detect live: PASS
- `--set hw.camera_index=3` (no such device): OpenCV reports "out device of bound", then
  `[camera] camera 3 has no picture; using camera 1 (set CAMERA_INDEX=1 in .env to skip this search)`; the dashboard camera is healthy.
  Startup with the search takes ~17 s (each missing index costs a few seconds on macOS).
- Found and fixed while testing: `--set perception.yolo.where=off` arrives as YAML `False` and was treated as "robot"; now "off".

### R5 safety live checks (A7), sim profile on port 8001: all PASS

Server: `python -m scoutbot --profile sim --set sim.world=demo --set server.port=8001 --set voice.provider=fake`.
Driven by a scripted WebSocket client that behaves like the dashboard (drive every 100 ms, heartbeats); timings are from the
client polling `/api/state`, so they include up to ~50 ms of polling delay.

| # | Check (manual steps for a person in brackets) | Expected | Observed |
| --- | --- | --- | --- |
| 1 | Take control, hold W, close the tab [open http://localhost:8001, Take control, hold W, close the tab] | STOPPED within 0.5 s of the last message | FORWARD -> STOPPED + STOP **0.04 s** after the socket closed (last drive was ~0.1 s earlier), reason "robot link lost (0.5s) - motors stopped" |
| 2 | Take control, hold W, release W (tab stays open) | wheels stop within 0.3 s | FORWARD -> STOP **0.24 s** after the last drive; mode stays MANUAL |
| 3 | E-stop from MANUAL while driving [press STOP or Space] | STOPPED + STOP immediately | **0.09 s** |
| 4 | E-stop from AUTO while moving | STOPPED + STOP immediately | FORWARD_SLOW -> STOP **0.06 s** |
| 5 | Kill the server (`kill -9`) while driving | no motion | the process (and with it the motors and the fake robot) is gone; dashboard socket closed in 0.01 s and shows "Robot link lost". **On a real Pi the L298N may keep its last PWM after the process dies: see hardware-handoff.md (pull-downs on ENA/ENB, or a relay/kill switch).** |
| 6 | Control loop hangs (in-process test: `control_tick` blocked) | watchdog stops wheels within 0.5 s | wheels 0.35/0.35 -> 0/0 after **0.49 s**, trips = 1 |

Invariants with automated tests: boot STOPPED, E-stop (test_server, test_deadman), only control_tick applies motors
(static test), watchdog 0.5 s (test_deadman), manual command expiry 0.3 s (test_deadman), link loss (test_deadman),
forward refused/capped (test_gate).

## Pi bring-up log

- Waiting for Pi hardware, actual GPIO pins, sensor type, camera model, and motor battery voltage.
- Do not connect an HC-SR04 echo output directly to a Pi GPIO pin. It needs a 5 V to 3.3 V voltage divider.

## Known limits

- The physical motor direction and speed calibration still require wheels-off-ground and floor tests on the actual robot.
- No Pi hardware measurements have been taken yet.
- Pi setup was syntax-checked locally, but not run on Raspberry Pi OS hardware.
- Remote YOLO, live dashboard link-loss, physical camera auto-detection, and Windows DirectShow have not been revalidated in this local-only pass.
