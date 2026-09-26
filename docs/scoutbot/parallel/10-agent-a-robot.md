# Agent A – Robot (hardware, YOLO, safety, Raspberry Pi)

> **Brief (paste this as the agent's first message):**
> You are Agent A on a 3-agent team finishing Scoutbot, a disaster-response robot for a hackathon happening today. The repo is `heheheheha` (GitHub `origin`). Read, in order: `docs/scoutbot/parallel/00-START-HERE.md`, `01-shared-rules.md` (required: ownership and git rules), `02-codebase-map.md`, `03-contracts.md`, `04-known-issues.md`, then this file (`10-agent-a-robot.md`) fully. You own the robot side: hardware drivers, YOLO person detection, the safety layer (gate, dead-man, modes), and Raspberry Pi 4 bring-up. Work only on branch `agent/robot`. Commit every working step (at least every 30 minutes), push after every commit, merge `origin/main` into your branch at least hourly, merge to `main` at every ★ milestone (only when all tests and the 20 s headless sim pass), and keep your section of `docs/scoutbot/STATUS.md` current. Edit only files you own; anything else goes through STATUS requests or ≤10-line wiring edits. The Pi and sensors may not be ready: do everything you can on a laptop first, and make every Pi step a single command. Safety comes before features: never weaken the safety invariants in `03-contracts.md §3`.

## Context you need

- **The hardware (from the team's diagram):** Raspberry Pi 4; a USB webcam or GoPro; distance sensors (either 3× HC-SR04 ultrasonic, as the code assumes, or ToF over I2C, as the diagram says; **confirm with the hardware team**); an L298N driver with 4 TT motors (left pair = channel A, right pair = channel B); an IMU is planned but **on hold** (Matthew is checking).
- **YOLO on a Pi 4 is the biggest unknown.** There are no published Pi 4 numbers. Pi 5 numbers at 640 px range from 67 to 290 ms per image depending on the export format. Measure it and decide `robot` vs `remote`.
- **Everything already exists** (see `02-codebase-map.md`). You're making it work for real, tuning it, and fixing the known issues assigned to you: KI-01, 04, 05, 06, 22 (joint with C), 33, 34 (your files), 38 (joint), 39, 40.

## Your files

`scoutbot/hw/base.py`, `camera_opencv.py`, `distance_hcsr04.py`, `distance_tof.py`, `motors_l298n.py`; `scoutbot/perception/*`; `scoutbot/safety/*`; `scoutbot/tools/camcheck.py`, `yolo_bench.py`, `sensor_check.py`, `motor_check.py`; `config/profiles/pi.yaml`; the config sections `hw`, `motion`, `speeds`, `safety`, `perception`; `scripts/pi_setup.sh`; `requirements-pi.txt`; new `requirements-yolo.txt`; tests `test_gate.py`, `test_deadman.py`, `test_fusion.py`, new `test_robot_*.py`; new `docs/scoutbot/robot.md`.

## Setup

```bash
git fetch origin && git checkout -b agent/robot origin/main && git push -u origin agent/robot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install ultralytics
python -m pytest -q tests          # expect all to pass before you change anything
```

Create `docs/scoutbot/robot.md` with the headings "What works", "How to run", "Measurements", "Pi bring-up log", "Known limits". Fill it in as you go.

---

## P0: laptop-only work (start now)

### A1. Fix `motor_check` (KI-01) ★ small
- **Change:** in `scoutbot/tools/motor_check.py`, for each action, call `motors.apply(action)` every 0.1 s for 1.0 s, then `motors.stop()` and wait 1 s. Print the action name and `motors.current()` halfway through each step. Keep the typed "yes" confirmation. Keep `motors.stop()` in `finally`.
- **Also:** support `--profile mac`/`sim` (fake motors, no confirmation needed), so it can be tested without hardware. Skip the prompt when `hw.motors == "fake"`.
- **Test:** `tests/test_robot_tools.py`: run the step function with `FakeMotors` and assert `current()` is non-zero during FORWARD and zero after stop.
- **Done when:** `python -m scoutbot.tools.motor_check --profile sim` prints non-zero wheel values for every moving action.

### A2. Camera auto-detect (KI-33, KI-34 for your files)
- **Add to `camera_opencv.py`:**
  - `OpenCVCamera.has_picture(tries=10) -> bool` (a frame with mean brightness > 8).
  - `open_best_camera(preferred: int, candidates=range(4), verbose=True) -> OpenCVCamera`: try the preferred index first; if it's missing or black, try the others; return the first with a picture. If none has a picture, return the first that opened (a dark room is still a camera), otherwise a closed camera with `ok=False`. When it switches, print `[camera] camera 1 has no picture; using camera 0 (set CAMERA_INDEX=0 in .env to skip this search)`.
  - On Windows, open with `cv2.VideoCapture(i, cv2.CAP_DSHOW)` (much faster).
  - All prints ASCII only.
- **Use it in** `hw/base.build()` (the `opencv` branch) and `tools/camcheck.py`. camcheck should print which index it used, the resolution, the FPS, and whether frames are black, then save 20 frames to `data/camcheck/`.
- **Change the base default** `hw.camera_index` to 0, with a comment. Matthew's `.env` has `CAMERA_INDEX=1`, so his Mac is unaffected.
- **Test:** unit-test the selection logic with a fake capture class (monkeypatch `_capture`), covering: preferred works; preferred black → next; none works → ok False.
- **Done when:** on the laptop, `camcheck` finds the webcam even with a wrong `CAMERA_INDEX`.

### A3. YOLO for real on the webcam
- `pip install ultralytics` (the first run downloads `yolov8n.pt`, about 6 MB). **Add `*.pt`, `*.onnx`, `*_ncnn_model/` and `data/camcheck/` to `.gitignore`**: a wiring edit to C's file, committed alone.
- **Create `requirements-yolo.txt`** with `ultralytics`, plus a comment ("big download, optional"). Tell C in STATUS so C removes `ultralytics` from `requirements.txt` (KI-37).
- **Run** `python -m scoutbot.tools.yolo_bench --imgsz 320`, then `--imgsz 640`, and fix anything broken. Record the FPS for both in `robot.md`.
- **Run the real system:** `python -m scoutbot --profile mac`, open the dashboard and check:
  - The YOLO chip shows "running" and an FPS.
  - Standing in view draws a box within about 1 s (the 2-of-3 confirmation).
  - A survivor record appears (once you're mid or near).
  - Press **Start auto**: the brain STOPs when you're "near" (rule 5 if Gemini is on, or the gate's "person ahead (YOLO)" if Gemini is off). Set the center slider far (200) so the sensors don't mask it.
- **Done when:** all of the above works and is written in `robot.md`. ★ Merge.

### A4. Tune near/mid/far (the distance buckets)
- **Measure:** stand (or have someone stand) facing the webcam at 0.7, 1.0, 1.5, 2.5 and 4.0 m. Log the YOLO box height as a fraction of the image height. Add a `--log-boxes` flag to `yolo_bench` that prints every box's height fraction.
- **Set** `perception.yolo.near_frac` and `mid_frac` so near is under about 1 m and mid is about 1–2.5 m. Put the measurement table in `robot.md`.
- **Also check:** a person lying down or partly hidden (behind a chair) is still detected at 1.5 m. Note the limits.
- **Update `test_fusion.py`** if the boundaries change.

### A5. NCNN export for the Pi (KI-05)
- `yolo_bench --export-ncnn --imgsz 320` should call `model.export(format="ncnn", imgsz=320)` and print the folder (e.g. `yolov8n_ncnn_model/`) plus the exact line to put in `pi.yaml`.
- **Make `YoloDetector` load either** a `.pt` file or an exported folder (ultralytics accepts both with `YOLO(path)`; pass `task="detect"` for folders). Check that NCNN runs on the laptop too, and record its FPS.
- `pi.yaml` already sets `model: yolov8n_ncnn_model`. Document that the folder must be copied to the Pi, or exported on the Pi with the same command.
- ★ Merge.

### A6. Remote YOLO end to end
- **Terminal 1:** `python -m scoutbot --profile mac --set perception.yolo.where=remote`.
- **Terminal 2:** `python -m scoutbot.perception.worker_remote --robot http://localhost:8000 --profile mac`.
- **Check:** the chip says "remote (laptop worker)" and shows the worker's FPS, boxes appear, survivors are created, and stopping the worker makes detections vanish within `max_age_s` (1 s).
- **Fix:** the worker should reconnect when the robot restarts, and should back off quietly (one message, not a flood) when the robot is down. Add `--token`. Validate `POST /api/detections` bodies: bad input → 400, not 500. That's a request to C, or a ≤10-line wiring edit in `server/app.py`.
- **Document** the Pi setup: on the Pi, `pi.yaml` has `where: remote`; on the laptop, run the worker command with the Pi's IP.
- ★ Merge.

### A7. Safety review and hardening (keep invariants, add proof)
- Re-read `03-contracts.md §3`. For each of the 7 invariants, make sure a test proves it. Add any missing ones to `test_deadman.py`/`test_gate.py`. The likely gaps:
  - E-stop calls `motors.stop()`: a runtime-level test. Ask C, or add `tests/test_robot_runtime_safety.py` that builds `Runtime` with the sim profile, `start_workers=False`, and calls `runtime.command({"type":"estop"})` with a spy motors object.
  - A `control_tick` exception stops the motors.
  - Nothing but `control_tick` calls `Motors.apply`: a static test that greps `scoutbot/` for `.apply(` outside `runtime.py` and `tools/motor_check.py`.
- **Link loss in a live run:** run `--profile sim`, open the dashboard, take control, hold W, close the tab. The robot must be STOPPED within 0.5 s (C's UI test did this once; make it a documented manual check in `robot.md`).
- **Do not** loosen any threshold without writing why in STATUS.

---

## P1: Raspberry Pi bring-up (prepare scripts now; run when hardware arrives)

### A8. `scripts/pi_setup.sh`: one command, safe to repeat (KI-06)
- Tell the user to install Raspberry Pi OS **64-bit** (Bookworm) and enable SSH.
- **Essential apt packages:** `python3-venv python3-dev espeak-ng mpg123 libgl1 libglib2.0-0 i2c-tools git`. **Optional** (`|| true`): `libatlas-base-dev`, `libopenblas-dev`.
- **Enable I2C:** `sudo raspi-config nonint do_i2c 0`. Add the user to the `gpio` and `i2c` groups.
- **Create `.venv`** if it's missing, then `pip install -r requirements-pi.txt -r requirements-yolo.txt`. If that fails, print a clear "YOLO failed; use where: remote" and carry on.
- **Copy `.env.example` → `.env`** if it's missing.
- **Print:** the Pi's IP, the laptop Ollama URL to put in `pi.yaml` (`talk.ollama.url` is B's key, but the value is filled here: tell B), and the next steps (camcheck, yolo_bench, sensor_check, motor_check).
- **Optional:** a `systemd` unit file `scripts/scoutbot.service` (disabled by default) for auto-start. Document it and don't enable it automatically.
- **Test:** `bash -n scripts/pi_setup.sh` (syntax check). If you have a Linux box or Docker with `arm64` Debian, dry-run it.

### A9. Pins and sensor type
- **Ask Matthew or the hardware team (STATUS → "Blocked on")** for: the actual GPIO pins (trig/echo per sensor; L298N IN1–IN4, ENA, ENB), the sensor type (HC-SR04 or VL53L0X/VL53L1X), the camera model, and the motor battery voltage. Until then, keep the placeholders.
- **HC-SR04:** confirm the voltage dividers on the echo pins (5 V → 3.3 V). Otherwise **the Pi can be damaged**. Write this in bold in `robot.md`.
- **ToF:** test `distance_tof.py`. VL53L1X needs a different library (`adafruit-circuitpython-vl53l1x`); support both via `hw.tof_model`. Out of range = 200 cm valid; errors = invalid.
- **Distance driver timing:** `read()` should take ≤ 200 ms for three sensors, and log a warning if it takes longer.

### A10. Bench bring-up (the next-steps spec §14 checklist), logged in `robot.md`
1. `bash scripts/pi_setup.sh`
2. `python -m scoutbot.tools.camcheck --profile pi`: look at the saved frames.
3. `python -m scoutbot.tools.yolo_bench --profile pi --imgsz 320`. Under 3 FPS → set `perception.yolo.where: remote` in `pi.yaml` and use A6.
4. `python -m scoutbot.tools.sensor_check --profile pi` at 20, 50 and 100 cm with a tape measure: error < 3 cm, no-echo < 10%. Then all three sensors on together (no crosstalk).
5. **Wheels off the ground:** `python -m scoutbot.tools.motor_check --profile pi`. Every action should spin the right wheels the right way. Fix wrong directions by swapping signs in `speeds`, or swapping `fwd`/`back` pins in config, **not the wiring**.
6. **Calibrate on the floor:** time 1 m at FORWARD, 1 m at FORWARD_SLOW, 1 m at BACK_UP, and one full turn at TURN_LEFT. Fill in `motion.forward_cm_s`, `slow_cm_s`, `backup_cm_s`, `turn_deg_s`, and the trims if it drifts. Then request that C use the per-action numbers in `pose.py` (KI-22).
7. **Dead-man:** run `python -m scoutbot --profile pi` and open the dashboard from the laptop. Take control, hold forward (wheels off the ground), then turn the laptop's Wi-Fi off: the wheels stop within 0.5 s. Then `kill -9` the Python process while driving: the wheels stop. **If they don't**, the L298N keeps its last PWM when the process dies. Document it and propose a hardware fix (a pull-down on ENA/ENB, or a relay) to the hardware team.
8. **First autonomous run at slow speed:** set `speeds.FORWARD` to the same value as `FORWARD_SLOW` for the first run. Drive toward a wall: it must stop or turn before touching it. Then run for 5 minutes in a cluttered area.
- ★ Merge after each passing step group (1–3, 4–6, 7–8).

---

## P2: if time allows

### A11. Sensor layout and blind spot (KI-39)
- **Add** `hw.sensor_angles: [30, 0, -30]` (left, center, right degrees, CCW positive) and `hw.sensor_beam_deg: 15`. Your drivers don't use angles, but the map and sim do: request that C read them in `simworld.py` and `mapping.py`.
- **Using the sim** (ask C for a `--set hw.sensor_angles=[45,0,-45]` run, or run it yourself), compare contacts over 10 seeds × 5 minutes for the current layout vs ±45°. Recommend the better one to the hardware team in `robot.md` and STATUS.

### A12. "Continue search" after finding a survivor (KI-38, joint with C)
- **Goal:** the responder presses "Continue search (S-0001 handled)" and the robot resumes exploring instead of holding STOP at that person forever. **The brain rules stay unchanged.**
- **Your part:** in `fusion.py`, add `Fuser.suppress(where_hint, until)`, or better, suppression by survivor position. Given a list of "handled" positions from the runtime (C), YOLO/Gemini persons whose estimated position is within 100 cm of a handled survivor are ignored for 60 s, both in fusion and in the gate's YOLO hold. Unit-test it.
- **C's part:** the button, the `{"type":"handled","survivor_id":...}` command, and passing handled positions to fusion.

### A13. Cliff sensor (KI-40)
- **Add** optional `read_cliff() -> float | None` to `DistanceSensors` (default None in all drivers), and a real implementation for a 4th HC-SR04 or ToF pointing down (`hw.cliff`: none, hcsr04 or tof, plus pins). Request that C pass it to `controller.step(..., cliff=value)` (rule 2 already handles `cliff > cliff_max` → BACK_UP).

---

## Pitfalls

- Never import `gpiozero`, `lgpio` or `board` at module top level. Import them inside the class, so the laptop and the tests still import cleanly.
- `Ramp.set()` with dt=0 doesn't move. Real motor code must call `apply()` repeatedly (the control loop does, at 10 Hz).
- On macOS, OpenCV camera capture must stay on the **main thread** (C's `camera_loop` does this). Don't add camera reads in other threads, except in tools that run on their own.
- `ultralytics` prints a lot: always pass `verbose=False`.
- YOLO class 0 = person. Don't detect other classes (it wastes the Pi).
- The Pi 4 overheats under YOLO: note the temperature (`vcgencmd measure_temp`) in the bench log, and recommend a heatsink or fan.

## A is done when

- [ ] KI-01, 04, 05, 06, 33 fixed; camera auto-detect works.
- [ ] YOLO works on the laptop webcam, with measured FPS and tuned near/mid/far in `robot.md`.
- [ ] NCNN export and remote YOLO both work end to end.
- [ ] Every safety invariant has a test; the manual link-loss check is documented.
- [ ] `pi_setup.sh` is one command and safe to repeat; the bring-up checklist has run, or is ready with a clear "waiting on hardware" in STATUS.
- [ ] Everything merged to `main`, and STATUS is current.
