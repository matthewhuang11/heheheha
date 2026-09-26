# Shared rules: all three agents (required)

## 1. Ground rules for the code

1. **Don't rebuild what exists.** Read [02-codebase-map.md](02-codebase-map.md) first. Improve and fix in place.
2. **The AI never drives.** Gemini, YOLO, Ollama and ElevenLabs only produce descriptions and words. Only the brain (`robot/controller.py`, via `Runtime.control_tick`) or a responder's held drive button produces an action, and every action passes through `scoutbot/safety/gate.py`.
3. **Anything that talks cannot move.** `scoutbot/talk`, `scoutbot/voice` and `scoutbot/sync` must never import `scoutbot.hw`, `scoutbot.safety` or `scoutbot.runtime`. `tests/test_isolation.py` enforces this.
4. **`robot/` (the original brain) is frozen.** The only exception is B's edits to `robot/vlm.py`, and those must keep the `SceneReport` fields unchanged. Any other change to `robot/` needs agreement from all three agents, recorded in STATUS, first. The original 52 tests (`test_brain.py`, `test_policy.py`, `test_rules_table.py`) must always pass unchanged.
5. **Every box has a fake and a real version**, picked by config. Everything must keep running on a laptop with no robot: `--profile sim` must always work.
6. **Numbers go in config** (`config/profiles/*.yaml`), never hard-coded.
7. **Secrets:** never print, log, commit or show a key. Keys live only in `.env`. When you paste an error message into STATUS or a commit, strip any URL that holds a password.
8. **Plain words** in anything a person reads: dashboard text, console messages, docs.
9. **Cross-platform:** the laptop side must work on Mac, Windows and Linux. Use `pathlib`, `encoding="utf-8"` on every file read and write, no shell-only tricks in Python, and ASCII in console prints. Pi-only code (GPIO, I2C) is imported inside the function or class that needs it, never at module top level.

## 2. File ownership

Each file has **one owner**. You may freely change files you own.

| Owner | Files and folders |
| --- | --- |
| **A – Robot** | `scoutbot/hw/base.py`, `camera_opencv.py`, `distance_hcsr04.py`, `distance_tof.py`, `motors_l298n.py`, `hw/__init__.py`; all of `scoutbot/perception/`; all of `scoutbot/safety/`; `scoutbot/tools/camcheck.py`, `yolo_bench.py`, `sensor_check.py`, `motor_check.py`; `config/profiles/pi.yaml`; `scripts/pi_setup.sh`; `requirements-pi.txt`; new `requirements-yolo.txt`; tests `test_gate.py`, `test_deadman.py`, `test_fusion.py` and any new `test_robot_*.py`; `docs/scoutbot/robot.md` |
| **B – Cloud & Talk** | all of `scoutbot/talk/` (including `prompts/`); all of `scoutbot/voice/`; all of `scoutbot/sync/`; `scoutbot/net.py`; `robot/vlm.py` (fields frozen, see rule 4); `check_gemini.py`, `eval_vlm.py`, `capture_dataset.py`; `scoutbot/tools/ollama_check.py` and any new cloud tools (`talk_check.py`, `voice_check.py`, `sync_check.py`); `.env.example`; tests `test_router.py`, `test_triage.py`, `test_outbox.py`, `test_talk_worker.py`, `test_isolation.py` and any new `test_cloud_*.py`; `docs/scoutbot/cloud.md` |
| **C – Station** | `scoutbot/runtime.py`, `state.py`, `types.py`, `settings.py`, `__main__.py`, `__init__.py`, new `start.py`; all of `scoutbot/server/` (including `static/responder.html`); all of `scoutbot/survivors/`; `scoutbot/hw/simworld.py`, `distance_fake.py`, `motors_fake.py`; `config/profiles/base.yaml` layout, `mac.yaml`/`laptop.yaml`, `sim.yaml`; `config/worlds/`; `requirements.txt`; `README.md`; all `run_*.command`, new `start.command`, `start.sh`, `start.bat`; new `scripts/setup.py`; new `scoutbot/tools/doctor.py`; `.gitignore`, `.gitattributes`; `web_demo.py`, `dashboard.html`, `demo.py`, `simulate.py` (the old debug tools: keep them working, don't extend them); tests `test_server.py`, `test_registry.py`, `test_simworld.py`, `test_tools_smoke.py` and any new `test_station_*.py`; `docs/scoutbot/station.md`; the layout of `docs/scoutbot/STATUS.md` |
| **Nobody (frozen)** | `robot/*` except `robot/vlm.py`; `tests/test_brain.py`, `test_policy.py`, `test_rules_table.py`; `docs/interfaces`, `docs/requirements`, `docs/runbooks`, `docs/safety`, `docs/verification` (old design docs); `scoutbot-next-steps-spec.md`, `disaster-response-robot-v1-spec.md` |

### Editing a file you don't own

- **Small wiring edits (10 changed lines or fewer)** are allowed. Examples: one call in `runtime.py` to your new function, one `.gitignore` line, one line appended to `requirements.txt`. Commit that edit **alone** with a message starting `[<you>] wiring:`, push it immediately, and log it in STATUS under "Edits to files I don't own".
- **Anything bigger:** add it to the owner's **Requests** list in STATUS with exactly what you need (function name, arguments, behavior). Keep working on something else. Owners check requests every time they pull, and handle them before their own P1 work.

### Shared config (`config/profiles/base.yaml`)

Anyone may **add** keys, but only inside their own top-level sections. Never rename or delete someone else's key.

| Sections | Owner |
| --- | --- |
| `hw`, `motion`, `speeds`, `safety`, `perception` | A |
| `talk`, `voice`, `sync`, `net`, `scene` | B |
| `control`, `survivors`, `sim`, `server` | C |

New keys need a comment on the same line saying what they do, and a sensible default so the sim keeps working without touching them.

### Shared requirements

C owns `requirements.txt` (the core packages, no YOLO). A owns `requirements-yolo.txt` (`ultralytics`) and `requirements-pi.txt`. B may **append** a package to `requirements.txt` as a wiring edit, with a comment saying who needs it. Keep heavy packages (torch or anything over ~100 MB) out of `requirements.txt`.

## 3. Git workflow: commit and push often

The three agents can only keep up with each other if everything reaches GitHub quickly.

### Start (once)

```bash
git fetch origin
git checkout -b agent/<robot|cloud|station> origin/main
git push -u origin agent/<name>
```

### While working

- **Commit every working step, at least every 30 minutes.** A working step means the tests pass and the thing you changed does what it should. Don't commit broken code to your branch, except behind a flag or config setting that is off by default.
- **Push right after every commit:** `git push`.
- **Commit message:** prefix, then what changed, then why. Examples:
  - `[robot] yolo: load exported NCNN folder so the Pi 4 runs ~3x faster`
  - `[cloud] router: open circuit after 3 Gemini failures, probe after 30 s`
  - `[station] wiring: runtime calls sync.resolve_sinks(cfg)`

  End it with the attribution lines your tool normally adds.
- **Stage only files you meant to change:** `git add <paths>` rather than `git add -A`. Check `git status` before committing.
- **Never commit:** `.env`, `data/`, `logs/`, `.venv/`, `__pycache__/`, model weights (`*.pt`, `*.onnx`, `*_ncnn_model/`), recordings, or anything over 5 MB.

### Pull the others' work in: at least every hour, and before every merge to main

```bash
git fetch origin
git merge origin/main          # merge, NOT rebase: your branch is already pushed
python -m pytest -q tests
git push
```

**Never force-push, and never rewrite pushed history.** If a merge conflicts in a file you don't own, keep the owner's version (`git checkout --theirs <file>` when merging main into your branch), re-apply your wiring edit if you had one, and note it in STATUS.

### Merging into `main`

Do this whenever a milestone works (marked ★ in your brief), and at least every 2 hours if you have finished work.

```bash
git fetch origin
git checkout main && git merge --ff-only origin/main
git merge --no-ff agent/<name> -m "merge agent/<name>: <milestone in plain words>"
python -m pytest -q tests                                      # MUST pass
python -m scoutbot --profile sim --set sim.world=demo --headless 20   # MUST finish without errors
git push origin main
git checkout agent/<name> && git merge main && git push
```

- **`main` must always pass all tests and the 20-second headless sim.** If your merge breaks it, fix it on your branch first, or reset your local `main` (`git reset --hard origin/main`, local only and never pushed) and try again.
- If `git push origin main` is rejected (someone merged first): `git fetch && git merge origin/main`, re-run the checks, and push again.
- After merging to main, update STATUS.

## 4. STATUS.md: the team board

`docs/scoutbot/STATUS.md` has one section per agent. **Only edit your own section**, which keeps merge conflicts rare. If a conflict does happen in STATUS, keep both sides.

Update it when you merge to main, when you get blocked, when you change a contract (with the details), and at least every hour. Use this format:

```
## A – Robot   (updated 15:40, branch agent/robot @ 1a2b3c4)
Done (on main): ...
Done (on my branch, not merged yet): ...
Doing now: ...
Next: ...
Blocked on: ... (who/what can unblock)
Requests for B: ...
Requests for C: ...
Edits to files I don't own: ... (commit hash + one line)
Contract changes: ... (what, why, which callers were updated)
Numbers measured: ... (FPS, latency, etc.)
```

**Read the other two sections every time you merge `origin/main`.** Handle requests addressed to you before starting new P1/P2 work.

## 5. Tests and checks

```bash
python3 -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt                            # A also: pip install -r requirements-yolo.txt (ultralytics)
python -m pytest -q tests                                  # all must pass
python -m scoutbot --profile sim --set sim.world=demo --headless 20
```

- **New logic needs a test.** Tests must not need a network, keys, a camera or hardware: use fakes. Anything that needs a real service goes in a manual check tool (`scoutbot/tools/*_check.py`) and the numbers go in your docs.
- **Keep the whole suite under about 30 seconds.** Anything slow is marked or made smaller.
- **Before merging to main, also run the real thing you changed.** For example, open the dashboard and click the button.

## 6. Definition of done (every task)

- [ ] It works for real, not only in a test. You ran it yourself and wrote in your docs file how you checked.
- [ ] New logic has tests, all tests pass, and the 20-second headless sim passes.
- [ ] No new errors or warnings at startup for `--profile sim` and `--profile mac`.
- [ ] The config defaults keep the sim working without any keys.
- [ ] Your docs file (`docs/scoutbot/robot.md`, `cloud.md` or `station.md`) has, in plain words: what works, how to run it, the numbers you measured, and known limits.
- [ ] Committed, pushed, and STATUS updated.

## 7. When you're stuck

- **Blocked by another agent:** write it in STATUS ("Blocked on") and in the owner's Requests. Then move on to your next task.
- **Blocked by Matthew** (a key, hardware or a decision): write it under "Blocked on" with the exact question, pick the safest reasonable default, and carry on.
- **Unsure whether a change breaks a contract:** it probably does. Read [03-contracts.md](03-contracts.md) and write in STATUS before pushing.
