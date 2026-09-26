# Scoutbot team STATUS board

Rules: edit ONLY your own section; update on every merge to main, when blocked, when you change a contract, and at least hourly. Read the other sections every time you merge `origin/main`. Format and rules: `docs/scoutbot/parallel/01-shared-rules.md` section 4.

**main health:** green @ 705ccab (99 tests, headless sim OK) — C updates this line after each integration pass.

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

## C – Station   (updated 11:35 EDT, branch agent/station @ 93842b1)
Done (on main): C1-C7 (merging now, see Integration passes).
Done (on my branch, not merged yet): -
Doing now: ★ merge C1-C7 to main; then C9 (KI-07 test controls, KI-08 fast state), C10 dashboard polish (KI-44), C11 (KI-21).
Next: C8 laptop demo run with real keys, C13 continue-search (with A), C15 recording.
Blocked on: a Windows machine to run start.bat for real (written + reviewed; CRLF via .gitattributes). Anyone with Windows: double-click start.bat in a fresh clone and paste the output in my Requests.
Requests for A: KI-37 done: ultralytics is out of requirements.txt; setup.py installs requirements-yolo.txt if it exists (else `pip install ultralytics`), a failure is only a warning. Please add requirements-yolo.txt. Doctor already calls your `open_best_camera` (cfg or index) if present. KI-22: will do pose per-action speeds once you post measured numbers.
Requests for B: done: removed `sync.sinks: []` from laptop.yaml and sim.yaml (f3a9240), so `sinks: auto` works.
Edits to files I don't own: none.
Contract changes: `--profile mac` is now an alias of `laptop` (cfg["profile"] == "laptop"); default profile is laptop. New `--share` flag. `settings.drop_placeholders()` ignores example values (your_..., replace_with..., user:password@) in .env. No state/WebSocket changes.
Integration passes (time, commits, result): 10:37 merged origin/main c73ec55 (B milestone): 121 tests pass, headless 20 s demo 1 survivor / 0 contacts / 0 trips. Log in docs/scoutbot/station.md.
Known issues fixed (KI-xx): KI-02, KI-30, KI-31, KI-32, KI-34 (my files), KI-37, KI-42.
How to start (everyone): Mac double-click start.command, Windows start.bat, Linux ./start.sh. Fresh clone -> dashboard in ~60 s on Mac, setup 29 s in Linux Docker python:3.10.

---

## Decisions log (anyone may append; never edit someone else's line)
- 2026-09-26: plan split into A/B/C per docs/scoutbot/parallel/. Brain rules in robot/ frozen.
