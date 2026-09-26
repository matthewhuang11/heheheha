# Scoutbot team STATUS board

Rules: edit ONLY your own section; update on every merge to main, when blocked, when you change a contract, and at least hourly. Read the other sections every time you merge `origin/main`. Format and rules: `docs/scoutbot/parallel/01-shared-rules.md` section 4.

**main health:** green for the existing suite (C checks 12:20: 136 tests, 20 s headless demo sim: 1 survivor, 0 contacts, 0 watchdog trips). Station survivor-sweep acceptance is open: 13/15 exact.

---

## A – Robot   (updated 2026-09-26 10:28 EDT, branch agent/robot @ pending commit)
Done (on main):
Done (on my branch, not merged yet): A1 motor_check fix and regression test.
Doing now: Validating and committing A1, then camera auto-detect (A2).
Next: A2 camera auto-detect, then YOLO laptop work.
Blocked on: Pi hardware details: actual GPIO pins, sensor type, camera model, and motor battery voltage (Matthew or hardware team).
Requests for B:
Requests for C: KI-22 needs pose.py to use the existing motion.slow_cm_s and motion.backup_cm_s calibrations once Pi measurements are available. KI-37: please move ultralytics out of requirements.txt; A adds requirements-yolo.txt in A3.
Edits to files I don't own:
Contract changes: None.
Numbers measured: Sim motor bench halfway values: forward +0.60/+0.60, slow +0.35/+0.35, turns +/-0.45, backup -0.35/-0.35.
Known issues fixed (KI-xx): KI-01 on branch, pending merge.

---

## B – Cloud & Talk   (updated 10:34 EDT, branch agent/cloud @ 37a53e6)
Done (on main): B1 / KI-03 safe `.env.example`; cached Gemini scene calls; configured prompt/history support; cross-platform cloud and local voice; automatic configured sync sinks; Mongo indexes; Tiger TLS; safe manual service-check tools and cloud guide.
Done (on my branch, not merged yet):
Doing now: Awaiting live service measurements on authorized Gemini, Ollama, ElevenLabs, MongoDB, and Tiger accounts.
Next: Record live measurements and coordinate removal of Station's profile-level empty sync sink overrides.
Blocked on: No code blocker. Live-service acceptance checks require the configured external accounts and services.
Requests for A: None.
Requests for C: Please remove `sync.sinks: []` profile overrides after B7 lands, so auto-configured sinks work on laptops and sim.
Edits to files I don't own: `scoutbot/runtime.py`, 3-line automatic sink wiring in 7d13014, merged to main.
Contract changes: Added `resolve_sinks(cfg) -> list[str]` as documented in the existing contract plan; callers retain the same Outbox API.
Numbers measured: 103 tests passed in 4.12 s. Required 20-second demo sim passed: 0 contacts, 0 watchdog trips. Earlier B1 sim created 1 survivor with 0 contacts and 0 watchdog trips.
Known issues fixed (KI-xx): KI-03, KI-10, KI-12, KI-20, KI-35, KI-36, KI-43.

---

## C – Station   (updated 12:17 EDT, branch agent/station @ f2f3fc6)
Done (on main): C1-C7 one-step setup (0f4ea19); C9 command safety + fast state; C10 dashboard polish; C11 survivors/pose (except full survivor-sweep acceptance); C13 / KI-38 continue-search (95effb3); C15 record/replay (9d2edd0, b619502); simulator uses a drawn camera (e6b763f).
Done (on my branch, not merged yet): -
Doing now: survivor-record merge tuning for the 5-seed x 3-world acceptance sweep; then integrate A/B work after it reaches main.
Next: integration pass after A and B merge their available branch work to main.
Blocked on: a Windows machine to run start.bat for real (written + reviewed). Anyone with Windows: double-click start.bat in a fresh clone and paste the output here. The survivor sweep is 13/15 exact: demo seeds 2 and 4 merge two people; this is a C-owned acceptance blocker. A's camera/YOLO commits and B's reply-filter commit are available only on their branches; per workflow they must merge to main before Station integrates them.
Requests for A: (1) please merge your branch to main soon: A1 motor_check and A2 camera auto-detect are only on agent/robot. (2) add requirements-yolo.txt (setup.py installs it if present, else `pip install ultralytics`). (3) KI-22 is DONE on my side: pose.py + simworld use motion.forward_cm_s / slow_cm_s / backup_cm_s / turn_deg_s, interpolated in ramps. Just put your measured numbers in pi.yaml `motion:`. (4) KI-38 continue-search: DONE on the station side without touching fusion/gate: `Runtime.unhandled(dets, now)` drops detections (and Gemini's person) that fall on a survivor the responder marked handled, for 60 s, before fresh_person/Fuser. The gate and sensors are unchanged. Tested in the sim: rule-5 hold released, robot continues, 0 contacts. If you'd rather own this inside Fuser, say so and I'll switch.
Requests for B: FYI wiring edit 1f673bb in your `talk` section: `talk.gemini.timeout_s` 8 -> 12, because the Gemini API rejects deadlines under 10 s (every talk call was failing with real keys). Please keep it >= 10 in cloud code/tests. (Done earlier: removed sync.sinks [] from laptop/sim.)
Edits to files I don't own: 1f673bb base.yaml talk.gemini.timeout_s 8 -> 12 (B's section, 1 line).
Contract changes: new WebSocket command `ping` -> reply `{for: "ping", ok, t}` (RTT); `sim`/`sensor` refused unless server.test_controls (03-contracts.md section 8 updated). `--profile mac` = alias of `laptop`. `survivors.merge_cm` 100 -> 85. Dashboard chips: "Gemini scene" (from vlm.* + services.gemini_scene) and "Gemini talk" (services.gemini).
Integration passes (time, commits, result): 10:37 origin/main c73ec55 (B): green. 11:35 ★ agent/station -> main 0f4ea19: 121 tests, headless OK. 11:44: 132 tests, headless demo 2 survivors / 0 contacts. 12:14: 136 tests passed; 60 s headless demo sim passed (1 survivor, 0 contacts, 0 watchdog trips); C13 continue-search and C15 record/replay regression tests passed. Sim now uses synthetic video, avoiding a webcam-permission warning. 12:17 ★ f2f3fc6: 136 tests and headless 20 s demo passed; pushed to origin/main. 12:20: explicit 5 seeds x 3 worlds sweep found 13/15 exact (demo seeds 2 and 4 merged); documented as incomplete.
Known issues fixed (KI-xx): KI-02, 07, 08, 21, 22, 30, 31, 32, 34 (my files), 37, 38, 42, 44.

---

## Decisions log (anyone may append; never edit someone else's line)
- 2026-09-26: plan split into A/B/C per docs/scoutbot/parallel/. Brain rules in robot/ frozen.
