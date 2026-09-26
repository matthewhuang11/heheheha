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

## C – Station   (updated —, branch agent/station @ —)
Done (on main):
Done (on my branch, not merged yet):
Doing now:
Next:
Blocked on:
Requests for A:
Requests for B:
Edits to files I don't own:
Contract changes:
Integration passes (time, commits, result):
Known issues fixed (KI-xx):

---

## Decisions log (anyone may append; never edit someone else's line)
- 2026-09-26: plan split into A/B/C per docs/scoutbot/parallel/. Brain rules in robot/ frozen.
