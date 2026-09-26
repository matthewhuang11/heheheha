# Scoutbot team STATUS board

Rules: edit ONLY your own section; update on every merge to main, when blocked, when you change a contract, and at least hourly. Read the other sections every time you merge `origin/main`. Format and rules: `docs/scoutbot/parallel/01-shared-rules.md` section 4.

**main health:** green @ 705ccab (99 tests, headless sim OK) — C updates this line after each integration pass.

---

## A – Robot   (updated —, branch agent/robot @ —)
Done (on main):
Done (on my branch, not merged yet):
Doing now:
Next:
Blocked on:
Requests for B:
Requests for C:
Edits to files I don't own:
Contract changes:
Numbers measured:
Known issues fixed (KI-xx):

---

## B – Cloud & Talk   (updated 10:28 EDT, branch agent/cloud @ 8a4a018)
Done (on main): B1 / KI-03: safe `.env.example` with empty optional values and documented behavior.
Done (on my branch, not merged yet):
Doing now: B2-B9 implementation audit and cloud reliability work.
Next: Cache and harden Gemini scene, then complete talk/router and voice milestones.
Blocked on: Live service measurements require the configured external services and are not yet run.
Requests for A: None.
Requests for C: Please remove `sync.sinks: []` profile overrides after B7 lands, so auto-configured sinks work on laptops and sim.
Edits to files I don't own: None.
Contract changes: None.
Numbers measured: B1 integration: 99 tests passed in 3.15 s; 20-second demo headless sim completed with 1 survivor, 0 contacts, 0 watchdog trips.
Known issues fixed (KI-xx): KI-03.

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
