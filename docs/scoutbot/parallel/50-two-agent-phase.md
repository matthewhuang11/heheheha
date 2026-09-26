# Phase 2: two agents (from main @ 3bb7eaa, 2026-09-26 ~13:30 EDT)

Phase 1 (three agents) finished the code. `main` is green: 144 tests, and the 60 s demo sim finds survivors with 0 contacts. What's left is mostly **proving it works for real** (real keys, webcam, speakers, phone, databases, Pi) and a few robot items. The two agents run **on Matthew's Mac**, where `.env`, the webcam, the speakers and Ollama are.

| Agent | Job | Branch | Commit prefix | Port |
| --- | --- | --- | --- | --- |
| **L – Live demo** | live cloud services, the laptop webcam demo, phone sharing, the offline flow, databases, the final integration and the `demo-ready` tag | `agent/live` (new) | `[live]` | 8000 |
| **R – Robot** | YOLO tuning with a real person, remote YOLO, safety live checks, the sensor blind spot, cliff sensor, the hardware hand-off sheet, Pi bring-up | `agent/robot` (continue) | `[robot]` | 8001 |

Everything in `01-shared-rules.md` still applies (commit and push often, merge `origin/main` hourly, merge to main only when green, STATUS updates, never commit `.env`), with the changes below.

---

## 1. What's done (don't redo)

- **A (robot):** motor_check fix; camera auto-detect; YOLO bench (M1 CPU: 6.9 FPS at 320 px, 7.8 at 640, **NCNN 16.5 FPS**); NCNN export and loading; optional `requirements-yolo.txt`; sensor_check no-echo; repeat-safe `pi_setup.sh`; a static proof that only the control loop drives motors. **Not done:** near/mid/far tuning with a real person (A4), remote YOLO end to end (A6), the live link-loss check (A7), the blind spot (KI-39), cliff (KI-40), and Pi bring-up (blocked on hardware details).
- **B (cloud):** safe `.env.example`; cached Gemini client; prompt versions and history; voice on Mac/Windows/Linux; automatic sync sinks; Mongo indexes and Tiger TLS; the tools `talk_check`, `voice_check`, `sync_check`; the reply safety filter. **Not done: any live measurement.** B ran without keys, so every row in `cloud.md` "Measurements" says "Not measured". Also not done: speech-to-text (KI-41), scene accuracy (B12).
- **C (station):** one-step setup (`start.command`/`start.sh`/`start.bat`, `scripts/setup.py`, start menu, doctor, `--share`); fresh-clone tests on Mac and Linux passed; dashboard polish (phone layout, chips, offline banner, export); command safety; fast state; survivor identity matching (15/15 sweep); continue-search (C13); record/replay (C15); README. **Not done:** the laptop webcam demo run, the phone test, Windows `start.bat` on a real PC, the live offline flow, and the `demo-ready` tag.
- **A real bug found with real keys:** the Gemini API rejects deadlines under 10 s, so `talk.gemini.timeout_s` is now 12.

## 2. Ownership (two agents)

| Owner | Files |
| --- | --- |
| **L – Live** | everything B and C owned in phase 1: `scoutbot/talk/`, `voice/`, `sync/`, `net.py`, `robot/vlm.py`, `scoutbot/server/` (dashboard), `runtime.py`, `state.py`, `types.py`, `settings.py`, `__main__.py`, `start.py`, `scoutbot/survivors/registry.py` and `pose.py`, `config/profiles/base.yaml` layout plus `laptop.yaml` and `sim.yaml`, `README.md`, launchers, `scripts/setup.py`, `tools/doctor.py`, `talk_check.py`, `voice_check.py`, `sync_check.py`, `ollama_check.py`, `.env.example`, `.gitignore`, `.gitattributes`, `docs/scoutbot/cloud.md`, `station.md`, the STATUS layout |
| **R – Robot** | everything A owned (`scoutbot/hw/` real drivers and `base.py`, `perception/`, `safety/`, `camcheck`, `yolo_bench`, `sensor_check`, `motor_check`, `pi.yaml`, `pi_setup.sh`, `requirements-pi.txt`, `requirements-yolo.txt`, `docs/scoutbot/robot.md`), **plus** the simulator and map, for the blind-spot work: `hw/simworld.py`, `distance_fake.py`, `motors_fake.py`, `survivors/mapping.py`, `config/worlds/`, `tests/test_simworld.py`; new `docs/scoutbot/hardware-handoff.md` |

Config sections: R = `hw`, `motion`, `speeds`, `safety`, `perception`, `sim`. L = the rest.
Wiring edits of 10 lines or fewer into the other agent's files are still allowed: commit them alone and log them in STATUS. The obvious one: R adds `cliff=` to `controller.step()` in `runtime.py`.

## 3. Sharing one Mac

1. **Separate folders.** Each agent uses its own clone. These already exist inside the main folder:
   - R uses `heheheheha/scoutbot-a`: `git fetch && git checkout agent/robot && git pull && git merge origin/main`.
   - L uses `heheheheha/scoutbot-b`: `git fetch && git checkout -b agent/live origin/main && git push -u origin agent/live`.
   - Copy `.env` into both (`cp ../.env .`).
   - **Never run agents in `heheheheha/` itself** (that's Matthew's folder, currently on `agent/robot`).
2. **L's first commit:** add `scoutbot-*/` to `.gitignore` on main. The clones live inside Matthew's folder, and a stray `git add -A` there would try to commit them.
3. **Ports.** L runs the dashboard on 8000. R always adds `--set server.port=8001`.
4. **The webcam is shared.** macOS usually lets two programs use it, but results get confusing. Schedule it:
   - R uses the webcam first (R1–R3, about the first hour) while L does L1–L4, which need no camera.
   - When R is done, it writes "**CAMERA FREE**" in its STATUS section. Then L does L5–L6.
   - If R needs the camera again later, it asks in STATUS.
5. **Ollama is shared** (one server at `localhost:11434`). That's fine.
6. **Speakers:** only L plays voice. R runs with `--set voice.provider=fake`.
7. **Some tasks need a person:**
   - R1: someone stands at set distances.
   - L5/L6: a person in view, and a phone.
   - Both agents put these in STATUS under "**Needs Matthew:** ..." with the exact steps and how long they take. Batch them so Matthew is interrupted as little as possible.

## 4. STATUS

Add two new sections at the top of `docs/scoutbot/STATUS.md`, `## L – Live` and `## R – Robot`, using the same format as before. Add a line **"Needs Matthew:"** (exact steps, and the estimated minutes). Leave the phase-1 A/B/C sections below as history (don't edit them). L updates the "main health" line.

---

## 5. Agent L – Live demo (cloud + station)

**Goal:** the full demo script (`40-integration-and-demo.md` §3) runs for real on this Mac with real keys, the checklist (§4) passes except the Pi rows (sim fallback is accepted for those), `cloud.md`/`station.md` hold real measurements, and `main` is tagged `demo-ready`.

### P0
- **L0. Setup and doctor.**
  - Run `./start.command` → 5 (doctor) in your clone. Every key present in `.env` must show OK. Fix anything the doctor gets wrong.
  - Add `scoutbot-*/` to `.gitignore` → ★ merge.
- **L1. Gemini live.**
  - `python check_gemini.py`, then `python -m scoutbot.tools.talk_check --model gemini`.
  - Measure scene latency over 30 calls (p50/p95, valid-JSON rate) and triage/reply latency and correctness across the 6 fixture conversations. Fill in `cloud.md`'s table.
  - Fix any live-only failure in talk/vlm code, as with the 10 s deadline bug.
  - If `gemini-flash-lite-latest` is slow or failing, test one or two alternatives and document the choice.
- **L2. Ollama live.**
  - Run `ollama_check`: cold and warm reply time, JSON triage validity.
  - Then `talk_check --model ollama`. Tune the Ollama prompt or timeouts if replies are too slow (over 8 s warm) or the JSON is invalid.
- **L3. ElevenLabs live.**
  - Run `voice_check`: time-to-first-audio for ElevenLabs and for the local voice.
  - If the Mac has no `mpg123`, check whether `brew install mpg123` is available and document the speed difference. **Don't install system software without asking Matthew in STATUS.**
- **L4. Mongo and Tiger live.**
  - Run `sync_check --sink both`. This must PASS and clean up after itself.
  - Then the end-to-end test: sim profile, simulate offline for 2 minutes, at least 2 survivors → queued → online → the queue empties within 10 s and the records are visible.
  - Run the demo queries in `cloud.md` against real data and fix any that fail.
  - ★ Merge after L1–L4 (docs plus any fixes).

### P1 (after R writes CAMERA FREE)
- **L5. Laptop webcam demo.**
  - `python -m scoutbot --profile laptop`, then walk through the demo script §3 steps 1–7 with a real person (Needs Matthew).
  - Checks: the chips are correct; the YOLO box → STOP → survivor → spoken greeting; survivor chat → IMMEDIATE triage + spoken Gemini reply; simulate offline → Ollama reply + local voice + "queued"; back online → Mongo and Tiger flush; take control → the veto near the slider wall → release stops → STOP.
  - Fix bugs in your files. File STATUS requests for R's (YOLO/gate/fusion).
  - Record pass/fail per step in `station.md`.
- **L6. Phone.**
  - `./start.command` → 2 → share yes. Open the printed LAN URL on a phone on the same Wi-Fi.
  - Check touch driving, the survivor card and chat.
  - If the venue or home Wi-Fi blocks it, test via a phone hotspot and document it.
- **L7. The real demo laptop run.**
  - Make a fresh clone into a new folder, copy `.env`, run `start.command` → 1 (sim) and → 2 (laptop) once each.
  - Time it and note any snags. This proves "any computer" on the Mac that will present.
- **L8. Integration and tag.**
  - After R's merges, and at least every 2 hours: full tests + a 60 s headless sim + a quick laptop-profile look.
  - When the checklist passes, `git tag demo-ready && git push origin demo-ready`.
  - Write a one-page `docs/scoutbot/DEMO-OPERATOR.md`:
    - start commands
    - which toggles to press in which order
    - what to say at each step
    - the backup plan if something fails live: sim + `--share`
    - troubleshooting

### P2
- **L9. Survivor speech-to-text (KI-41).** Press-to-talk on the dashboard (MediaRecorder) → `POST /api/survivors/{id}/audio` → ElevenLabs speech-to-text online → `TalkWorker.submit("survivor_says", source="speech")`. Offline: disable the button with a tooltip. Tests with a fake transcriber.
- **L10. Scene accuracy (B12).** `capture_dataset.py` 30–40 frames of Matthew's room/obstacles → `eval_vlm.py` → report the false-clear rate in `cloud.md`. Tune the scene prompt only if the false-clear rate is over 10% (fields frozen).
- **L11. Windows.** If any teammate has Windows: they clone and double-click `start.bat`, and send you the output. Fix anything that breaks. Otherwise leave it "blocked: no Windows machine" in STATUS.

**L is done when:** `cloud.md` has real numbers for Gemini, Ollama, ElevenLabs, Mongo and Tiger; the demo script passed on the laptop webcam and a phone; the fresh-clone run on the demo Mac passed; `DEMO-OPERATOR.md` exists; `demo-ready` is tagged; and STATUS is current.

---

## 6. Agent R – Robot (perception, safety, simulator, hardware hand-off, Pi)

**Goal:** YOLO distances are tuned on a real person; remote YOLO and the safety live checks are proven; the blind spot and cliff work is done in config, sim and code; the hardware team has a clear hand-off sheet; the Pi is brought up if the hardware arrives.

Always run with `--set server.port=8001 --set voice.provider=fake`.

### P0 (webcam tasks first, then write CAMERA FREE)
- **R1. Near/mid/far tuning (A4)** (Needs Matthew, about 5 minutes).
  - Run `yolo_bench --log-boxes` while a person stands at 0.7 / 1.0 / 1.5 / 2.5 / 4.0 m. Also try lying down, and partly hidden behind a chair, at 1.5 m.
  - Set `perception.yolo.near_frac`/`mid_frac` so near is under about 1 m and mid is about 1–2.5 m. Put the table in `robot.md`.
  - Update `test_fusion.py` if the boundaries move.
  - Also test NCNN on the laptop live: `--set perception.yolo.model=yolov8n_ncnn_model` should give the same boxes at higher FPS. If it does, consider making NCNN the laptop default when the folder exists.
- **R2. Live person → STOP.** Run `--profile laptop --set server.port=8001` with the center slider at 200. Press Start auto. A person walking in → box within 1 s → survivor → STOP (rule 5, or the gate's "person ahead (YOLO)" with Gemini off). Document both paths.
- **R3. Remote YOLO end to end (A6).**
  - Terminal 1: `--profile laptop --set perception.yolo.where=remote --set server.port=8001`.
  - Terminal 2: `python -m scoutbot.perception.worker_remote --robot http://localhost:8001`.
  - Check: the chip says remote, boxes appear, survivors get made, and killing the worker clears detections within 1 s.
  - Add reconnect/backoff to the worker (one message, not a flood).
  - `POST /api/detections` with bad bodies → 400, not 500. That's a wiring edit in `server/app.py` of 10 lines or fewer, or ask L.
- **R4. Camera auto-detect live (A2 revalidation).** Start with a wrong `CAMERA_INDEX` (e.g. 3): it must fall back to the working camera and print which one. Then write **CAMERA FREE** in STATUS. ★ Merge R1–R4.

### P1
- **R5. Safety live checks (A7), sim profile on port 8001.**
  - Take control, hold W, close the tab → STOPPED within 0.5 s.
  - Hold W, then kill the server process → the watchdog message and no motion.
  - E-stop from AUTO and from MANUAL.
  - Write each as a numbered manual check in `robot.md`, with the observed timing.
- **R6. The sensor blind spot (KI-39).**
  - Add `hw.sensor_angles: [30, 0, -30]` and `hw.sensor_beam_deg: 15`. Make `simworld.sensors()`/`raycast` and `MapBuilder` use them.
  - Run 10 seeds × 5 minutes (fast clock, reusing `tests/test_simworld.py: run()`) in `room_basic` and `rubble` for three layouts: ±30°, ±45° and ±60°. Report contacts per layout in `robot.md`.
  - Recommend a layout.
  - Keep the default at ±30° unless the hardware team agrees to change it, and add a regression test for the recommended layout.
- **R7. Cliff sensor (KI-40).**
  - Add `DistanceSensors.read_cliff() -> float | None` (default None in all drivers), a sim version (optional `drops` rectangles in the world YAML that make `read_cliff()` return 999), and real HC-SR04/ToF support behind `hw.cliff: none | hcsr04 | tof`, with pins.
  - Wiring edit in `runtime.py`: pass `cliff=` into `controller.step()` (rule 2 already handles it).
  - Add a demo world with a drop-off, and a test that the robot backs up at the edge.
- **R8. Hardware hand-off sheet: `docs/scoutbot/hardware-handoff.md`.**
  - A one-page wiring table for the hardware team, with the GPIO numbers from `base.yaml`/`pi.yaml` marked "placeholder – confirm":
    - L298N IN1–IN4/ENA/ENB → Pi GPIO
    - motor pairs per channel
    - HC-SR04 trig/echo per sensor **with the 5 V→3.3 V divider values** (e.g. 1 kΩ/2 kΩ), or the ToF XSHUT pins/I2C addresses
    - the cliff sensor
    - camera
    - power (a separate motor battery, a common ground, the Pi's 5 V 3 A supply)
    - a physical kill switch
  - The recommended sensor angles from R6.
  - A "send us back" list: actual pins, sensor model, camera model, battery voltage, photos of the wiring.
  - The exact commands to run once the Pi is wired (`pi_setup.sh` → camcheck → sensor_check → motor_check wheels-off → calibration).
  - Post a short summary in STATUS so Matthew can forward it.
- ★ Merge after R5–R8.

### P1 continued: the Pi (only once hardware and details exist; otherwise stay blocked in STATUS)
- **R9. Pi bring-up (A8–A10).** Follow `10-agent-a-robot.md` A10 exactly:
  1. `pi_setup.sh`
  2. camcheck
  3. yolo_bench NCNN 320 (under 3 FPS → `where: remote` plus the laptop worker)
  4. sensor_check with a tape measure
  5. motor_check wheels-off
  6. floor calibration → the `motion.*` numbers
  7. the dead-man checks (Wi-Fi off, kill -9)
  8. the first slow autonomous run
- Log everything in `robot.md`. ★ Merge per step group.

### P2
- **R10. KI-09:** `PerceptionWorker` stores the frame it detected on as `shared.det_frame`; the survivor snapshot uses it (a wiring edit in `runtime.py`, or ask L).
- **R11. KI-11:** propose and implement a fix for fused-report churn in `SceneFilter`: only rebuild the fused copy when the Gemini report changes, and apply YOLO-only changes via the gate hold. Tests. Write in STATUS first (it touches fusion semantics).
- **R12. A `pi-sim` profile** so the Pi's config path (Ollama at `LAPTOP_IP`, remote YOLO, 0.0.0.0, `test_controls` off) can be tested on the laptop with fake hardware.

**R is done when:** the near/mid/far table exists and the cut-offs are tuned; remote YOLO, camera fallback and the safety live checks are documented as passing; the blind-spot study and recommendation plus the cliff sensor are merged; `hardware-handoff.md` is ready to send; the Pi is brought up or clearly blocked; and STATUS is current.

---

## 7. End of phase: both agents

1. R merges last and posts "frozen" in STATUS.
2. L runs the final integration (tests + 60 s sim + the laptop demo script), then tags `demo-ready` and pushes the tag.
3. Both leave a final STATUS entry: what works, what's still blocked, and exactly what Matthew must do before presenting.
