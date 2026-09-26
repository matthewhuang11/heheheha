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

## B – Cloud & Talk   (updated 10:32 EDT, branch agent/cloud @ 40cfebf)
Done (on main): B1 / KI-03: safe `.env.example` with empty optional values and documented behavior.
Done (on my branch, not merged yet): Client-cached Gemini scene calls, prompt/history configuration, cross-platform offline/cloud voice, automatic configured sync sinks, database safeguards, live-check tools, and cloud guide.
Doing now: Investigating a headless simulator process termination before merging the B3/B5/B6/B9 milestone.
Next: Re-run the required simulator successfully, merge the validated milestone, then record live-service measurements.
Blocked on: Two clean `--headless 20` invocations terminated early with signal exit code -1 after normal progress and `stopping: motors off`; no Python traceback. Live service measurements also require external authorized services.
Requests for A: None.
Requests for C: Please remove `sync.sinks: []` profile overrides after B7 lands, so auto-configured sinks work on laptops and sim.
Edits to files I don't own: `scoutbot/runtime.py`, 3-line automatic sink wiring in 7d13014.
Contract changes: Added `resolve_sinks(cfg) -> list[str]` as documented in the existing contract plan; callers retain the same Outbox API.
Numbers measured: 102 tests passed in 3.55 s. Cloud subset: 21 passed in 0.63 s. B1 sim: 1 survivor, 0 contacts, 0 watchdog trips. Current milestone sim: blocked by external process termination.
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
