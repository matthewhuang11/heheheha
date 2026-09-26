# Scoutbot team STATUS board

Rules: edit ONLY your own section; update on every merge to main, when blocked, when you change a contract, and at least hourly. Read the other sections every time you merge `origin/main`. Format and rules: `docs/scoutbot/parallel/01-shared-rules.md` section 4.

**main health:** green @ 705ccab (99 tests, headless sim OK) — C updates this line after each integration pass.

---

## A – Robot   (updated 2026-09-26 10:30 EDT, branch agent/robot @ 75bac90)
Done (on main): A1 / KI-01 motor_check fix, fake-motor regression test, and robot run notes.
Done (on my branch, not merged yet):
Doing now: A2 camera auto-detect.
Next: YOLO laptop work after A2.
Blocked on: Pi hardware details: actual GPIO pins, sensor type, camera model, and motor battery voltage (Matthew or hardware team).
Requests for B:
Requests for C: KI-22 needs pose.py to use the existing motion.slow_cm_s and motion.backup_cm_s calibrations once Pi measurements are available. KI-37: please move ultralytics out of requirements.txt; A adds requirements-yolo.txt in A3.
Edits to files I don't own:
Contract changes: None.
Numbers measured: Sim motor bench halfway values: forward +0.60/+0.60, slow +0.35/+0.35, turns +/-0.45, backup -0.35/-0.35. A1 integration: 100 tests and demo headless sim passed.
Known issues fixed (KI-xx): KI-01 on main (75bac90).

---

## B – Cloud & Talk   (updated —, branch agent/cloud @ —)
Done (on main):
Done (on my branch, not merged yet):
Doing now:
Next:
Blocked on:
Requests for A:
Requests for C:
Edits to files I don't own:
Contract changes:
Numbers measured:
Known issues fixed (KI-xx):

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
