# Scoutbot team STATUS board

Rules: edit ONLY your own section; update on every merge to main, when blocked, when you change a contract, and at least hourly. Read the other sections every time you merge `origin/main`. Format and rules: `docs/scoutbot/parallel/01-shared-rules.md` section 4.

**main health:** green at `3b61ce8` (C final integration checks 12:55: 144 tests; 60 s demo sim: 1 survivor, 0 contacts, 0 watchdog trips). Robot and Cloud integration merges are on main.

---

## A – Robot   (updated 2026-09-26 12:41 EDT, branch agent/robot @ fc3094f)
Done (on main): A1 / KI-01 motor_check fix, fake-motor regression test, and robot run notes.
Done (on my branch, not merged yet): A2 camera auto-detect; A3/A5 YOLO benchmark, optional requirements, NCNN export and folder loading; KI-04 sensor no-echo reporting; KI-06 repeat-safe Pi setup; static motor-apply safety proof. Merged origin/main through C13 (continue-search).
Doing now: Push validated Robot fixes for integration.
Next: Hardware-only Pi bring-up when the physical robot details are available.
Blocked on: Pi hardware details: actual GPIO pins, sensor type, camera model, and motor battery voltage (Matthew or hardware team).
Requests for B:
Requests for C: None. KI-22 is implemented on main; A still needs physical speed measurements for pi.yaml calibration.
Edits to files I don't own:
Contract changes: None.
Numbers measured: Sim motor bench halfway values: forward +0.60/+0.60, slow +0.35/+0.35, turns +/-0.45, backup -0.35/-0.35. Laptop camera: index 1, 1280x720, 37.3 FPS, not black. YOLO: 6.88 FPS at 320, 7.75 FPS at 640, NCNN export 12.4 s. Latest targeted Robot suite: 35 passed in 1.18 s; full suite 144 passed in 14.29 s; 20-second demo sim: 1 survivor, 0 contacts, 0 watchdog trips.
Known issues fixed (KI-xx): KI-01 on main (75bac90); KI-04, KI-06, KI-33 pending merge.

---

## B – Cloud & Talk   (updated 12:47 EDT, branch agent/cloud @ pending push)
Done (on main): B1 / KI-03 safe `.env.example`; cached Gemini scene calls; configured prompt/history support; cross-platform cloud and local voice; automatic configured sync sinks; Mongo indexes; Tiger TLS; safe manual service-check tools and cloud guide.
Done (on my branch, not merged yet): Merged current `origin/main`; B11 safety filter now covers model replies, canned fallback, and greeting wording.
Doing now: Validating and pushing the safety completion.
Next: Record live measurements with authorized Gemini, Ollama, ElevenLabs, MongoDB, and Tiger services.
Blocked on: Live-service acceptance checks require configured external accounts and services; no credentials or local service endpoints are available in this environment.
Requests for A: None.
Requests for C: None (`sync.sinks: []` profile overrides are removed on current main).
Edits to files I don't own: `scoutbot/runtime.py`, 3-line automatic sink wiring in 7d13014, merged to main.
Contract changes: Added `resolve_sinks(cfg) -> list[str]` as documented in the existing contract plan; callers retain the same Outbox API.
Numbers measured: 19 targeted cloud/talk tests passed in 0.73 s; full suite 139 passed in 23.09 s. Required 20-second sim: 1 survivor, 0 contacts, 0 watchdog trips. No live-service figures claimed.
Known issues fixed (KI-xx): KI-03, KI-10, KI-12, KI-20, KI-35, KI-36, KI-43.

---

## C – Station   (updated 12:57 EDT, integration on main @ 3b61ce8)
Done (on main): C1-C7 one-step setup (0f4ea19); C9 command safety + fast state; C10 dashboard polish; C11 survivors/pose plus stable identity matching (1d0110b, full 15/15 sweep); C13 dashboard/runtime state, 60 s expiry, and Fuser/gate suppression (219082b); C15 record/replay (9d2edd0, b619502); simulator uses a drawn camera (e6b763f). Final A/B integration: Robot `dc0bd68`, then Cloud `3b61ce8`.
Done (on my branch, not merged yet): -
Doing now: Final integration evidence recorded; `demo-ready` remains intentionally untagged.
Next: Run the remaining physical/live acceptance checks on the demo laptop, phone Wi-Fi, and Pi before tagging.
Blocked on: Windows `start.bat` on real Windows; phone `--share` and laptop webcam dashboard; Pi hardware/motor shutdown; Ollama/local-voice offline flow; live Gemini/ElevenLabs/Mongo/Tiger sync. This environment had no usable LAN address, denied camera permission, and no running Ollama.
Requests for A: Please provide Pi hardware validation, including the motor-stop acceptance check, when hardware is available.
Requests for B: Please provide live provider validation (Ollama, ElevenLabs, Mongo, Tiger, and Gemini as needed) on the demo environment.
Edits to files I don't own: 1f673bb base.yaml talk.gemini.timeout_s 8 -> 12 (B's section, 1 line). 72d309b `perception/fusion.py`: handled-position suppression boundary for C13, with contract and regression updates.
Contract changes: new WebSocket command `ping` -> reply `{for: "ping", ok, t}` (RTT); `sim`/`sensor` refused unless server.test_controls (03-contracts.md section 8 updated). `--profile mac` = alias of `laptop`. `survivors.merge_cm` 100 -> 85. Dashboard chips: "Gemini scene" (from vlm.* + services.gemini_scene) and "Gemini talk" (services.gemini). `PersonDetection.track_id` and `Survivor.track_id` are optional stable detector identities; the registry prefers a matching ID over spatial merging, and old records remain valid. `Fuser.suppress(positions)` now accepts handled survivor positions each tick and applies the same decision to fusion and the YOLO gate hold.
Integration passes (time, commits, result): 10:37 origin/main c73ec55 (B): green. 11:35 ★ agent/station -> main 0f4ea19: 121 tests, headless OK. 11:44: 132 tests, headless demo 2 survivors / 0 contacts. 12:14: 136 tests passed; 60 s headless demo sim passed (1 survivor, 0 contacts, 0 watchdog trips); C13 continue-search and C15 record/replay regression tests passed. Sim now uses synthetic video, avoiding a webcam-permission warning. 12:17 ★ f2f3fc6: 136 tests and headless 20 s demo passed; pushed to origin/main. 12:20: explicit sweep was 13/15. 12:25: stable sim track identities fixed demo seeds 2 and 4; full 15/15 sweep and 137 tests passed. 12:27: 60 s demo sim found 2 survivors with 0 contacts and 0 watchdog trips. 12:29 ★ 1d0110b: 137 tests and headless 20 s demo passed; pushed to origin/main. 12:37 ★ 219082b: 137 tests and headless 20 s demo passed; C13 Fuser/gate suppression tests passed. 12:53 ★ `dc0bd68` Robot merge: 144 tests; 60 s sim 1 survivor / 0 contacts / 0 watchdog trips; pushed. 12:55 ★ `3b61ce8` Cloud merge: 144 tests; 60 s sim 1 survivor / 0 contacts / 0 watchdog trips; pushed. 12:57 local fresh clone of final main: setup (`--no-yolo`), launcher doctor, and 20 s sim passed; camera permission denied and remote clone authentication unavailable.
Known issues fixed (KI-xx): KI-02, 07, 08, 21, 22, 30, 31, 32, 34 (my files), 37, 38, 42, 44.

---

## Decisions log (anyone may append; never edit someone else's line)
- 2026-09-26: plan split into A/B/C per docs/scoutbot/parallel/. Brain rules in robot/ frozen.
