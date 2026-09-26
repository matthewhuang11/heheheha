# Agent B – Cloud & Talk (Gemini, Ollama, router, triage, voice, sync)

> **Brief (paste this as the agent's first message):**
> You are Agent B on a 3-agent team finishing Scoutbot, a disaster-response robot for a hackathon happening today. The repo is `heheheheha` (GitHub `origin`). Read, in order: `docs/scoutbot/parallel/00-START-HERE.md`, `01-shared-rules.md` (required: ownership and git rules), `02-codebase-map.md`, `03-contracts.md`, `04-known-issues.md`, then this file (`20-agent-b-cloud.md`) fully. You own everything that talks to the cloud or produces words: the Gemini scene call (`robot/vlm.py`, with its fields frozen), Gemini and Ollama triage and survivor replies, the online/offline router and circuit breaker, ElevenLabs and the local offline voice on Mac/Windows/Linux/Pi, and MongoDB + Tiger Data survivor sync. Keys are in `.env`: never print, log or commit them. Work only on branch `agent/cloud`. Commit every working step (at least every 30 minutes), push after every commit, merge `origin/main` into your branch at least hourly, merge to `main` at every ★ milestone (only when all tests and the 20 s headless sim pass), and keep your section of `docs/scoutbot/STATUS.md` current. Edit only files you own; anything else goes through STATUS requests or ≤10-line wiring edits. Your code must never import `scoutbot.hw`, `scoutbot.safety` or `scoutbot.runtime` (`tests/test_isolation.py`).

## Context you need

- **Design (next-steps spec §10–12):**
  - The model only **extracts facts**; plain rules pick the triage category (START-like). Triage is always labeled *preliminary*.
  - Replies: at most 2 short, calm sentences, one question at a time, never promise times or rescue, and no medical advice beyond "keep pressure on bleeding" and "don't move if your neck or back hurts".
- **Offline means no internet.** Wi-Fi between the Pi and the laptop still works. Ollama runs on the **laptop**, and the Pi reaches it at `http://<laptop-ip>:11434`.
- **Earlier finding:** Gemini's `response_schema` structured-output mode failed for `SceneReport`, so the schema is embedded in the prompt instead (keep it that way unless you prove the other way works). Gemini sometimes returns 503 "high demand", and `describe()` retries 3×.
- **Matthew's `.env`** uses `GEMINI_MODEL=gemini-flash-lite-latest`.
- **Your known issues:** KI-03, 10, 12, 20, 34 (your files), 35, 36, 41, 43.

## Your files

`scoutbot/talk/*` (including `prompts/`), `scoutbot/voice/*`, `scoutbot/sync/*`, `scoutbot/net.py`, `robot/vlm.py`, `check_gemini.py`, `eval_vlm.py`, `capture_dataset.py`, `scoutbot/tools/ollama_check.py` and new `talk_check.py`, `voice_check.py`, `sync_check.py`; config sections `talk`, `voice`, `sync`, `net`, `scene`; `.env.example`; tests `test_router.py`, `test_triage.py`, `test_outbox.py`, `test_talk_worker.py`, `test_isolation.py`, new `test_cloud_*.py`; new `docs/scoutbot/cloud.md`.

## Setup

```bash
git fetch origin && git checkout -b agent/cloud origin/main && git push -u origin agent/cloud
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python -m pytest -q tests
# Ollama (laptop): install from ollama.com, then:
ollama pull qwen2.5:3b
```

Create `docs/scoutbot/cloud.md` with the headings "What works", "How to run", "Measurements", "Demo queries", "Known limits".

---

## P0 (start now)

### B1. `.env.example` (KI-03) ★ small
- Every optional key is **empty**, with a comment above each saying what it turns on, what happens without it, and where to get it.
- Keys: `GEMINI_API_KEY` (aistudio.google.com/apikey), `GEMINI_MODEL=gemini-flash-lite-latest` (keep this default), `GEMINI_TALK_MODEL=` (optional; defaults to `GEMINI_MODEL`), `ELEVENLABS_API_KEY=`, `ELEVENLABS_VOICE_ID=` (optional; defaults to a stock voice), `MONGODB_URI=`, `TIGER_DATABASE_URL=`, `CAMERA_INDEX=` (optional; empty = auto-detect, which A is building), `SCOUTBOT_TOKEN=` (optional; empty = no login).
- Header: "Copy to .env. Everything is optional. Never commit .env."
- **Make empty values mean "not set" everywhere in your code**, including values that are only whitespace or quotes.

### B2. Gemini scene call, live (`robot/vlm.py`, `check_gemini.py`)
- Run `python -m scoutbot --profile mac` with the real key. The dashboard "Scene" row should update about every 2 s, and `vlm.calls` should grow.
- **Measure** over 30 calls: p50 and p95 latency, valid-JSON rate, and the most common failure. Put the table in `cloud.md`.
- **Speed:** cache the `genai.Client` (KI-10). Keep images at 640 px wide (already done) and try JPEG quality 70. If `gemini-flash-lite-latest` fails or is slow, test 1–2 other current fast models and document the choice. **Don't change the `SceneReport` fields.**
- **Errors:** the scene loop (C's) counts failures from `describe()` exceptions. Make the messages short and readable, with no URLs that contain keys.
- **Accuracy (optional but valuable):** use the existing `capture_dataset.py` and `eval_vlm.py` on 20–40 frames. The key number is the **false-clear rate** (Gemini says "clear" when it isn't).

### B3. Gemini triage and replies, live
- **Get a survivor:** `python -m scoutbot --profile sim --set sim.world=demo` (the sim creates one within about 20 s in AUTO, and needs no camera), or stand in front of the webcam with `--profile mac`.
- **In the dashboard**, type survivor lines: "hello?", "my leg is stuck under a shelf", "I'm bleeding from my arm", "I can walk but my friend is not answering", "I can't breathe well". For each, check:
  - The reply is ≤ 2 sentences, calm and safe.
  - Triage is valid JSON and the category makes sense: stuck → IMMEDIATE (trapped); bleeding → IMMEDIATE; can walk → MINOR; responsive and can't walk → DELAYED.
- **New tool `python -m scoutbot.tools.talk_check [--model gemini|ollama|both]`:** runs 6 fixed scripted conversations (add them to `scoutbot/talk/fixtures.py`) through each model. Print a table: expected category, got category, triage latency, reply latency, and the reply text. Flag any reply that breaks the rules (a simple keyword check: "minutes", "promise", "will be fine", "move toward", ...).
- **Tune the prompts** as `triage_v2.txt` and `reply_v2.txt`, keeping `_v1`. Pick the version with config `talk.prompt_version` (default: the best one). Use Gemini's JSON mode (`response_mime_type=application/json`, as now).
- **Wire `talk.history_messages`** (KI-20) into `transcript()` for both models.
- ★ Merge.

### B4. Ollama, real
- **Fix and extend `ollama_check`:**
  - Model matching should accept `qwen2.5:3b` whether or not the tag is spelled out.
  - `/api/pull` should use `{"model": ..., "stream": false}` (newer servers) and fall back to `{"name": ...}`.
  - Measure **cold** (first) and **warm** reply times, and confirm JSON triage using `format` = JSON schema.
  - Print the laptop's LAN URL and how to expose it: `OLLAMA_HOST=0.0.0.0` (Mac: `launchctl setenv OLLAMA_HOST 0.0.0.0`, then restart the Ollama app; Linux: systemd override; Windows: environment variable).
- **Warm-up:** `TalkWorker` already warms the model up once. Make sure it doesn't block startup, and shows `ollama: warming up` → `ready`.
- **Optional:** compare `llama3.2:3b` for speed and JSON validity, and pick the default with numbers in `cloud.md`.
- **Timeouts:** Ollama `timeout_s` 20 is fine for the chat. Triage can take longer on a slow CPU, so consider a separate `talk.ollama.triage_timeout_s`.

### B5. Router end to end (offline, broken Gemini, everything down)
Run `--profile sim --set sim.world=demo` with a survivor present, then:
1. **Simulate offline** (dashboard toggle): the next reply's source is `ollama`, triage `model` = `ollama:qwen2.5:3b`, and the "Gemini (offline)" chip is amber. **Driving is unchanged** (check the action and rule in the dashboard).
2. **Online again, bad Gemini key** (`GEMINI_API_KEY=bad python -m scoutbot ...`): after 3 failures the breaker opens, the status shows `error (open)`, and Ollama answers. After 30 s one probe goes to Gemini. Write this sequence in `cloud.md`.
3. **Stop Ollama too:** replies become canned, triage becomes `UNKNOWN` (model `canned`), nothing crashes, and the chip shows `unreachable`.
4. **Start Ollama again:** within 10 s the chip says ready and replies come from Ollama.
- Add tests for any logic you change. The existing `test_router.py` has fake models.
- ★ Merge.

### B6. Voice on every OS (KI-35)
- **ElevenLabs** (`eleven_flash_v2_5`):
  - With `mpg123` or `ffplay` present: stream MP3 into the player (speech starts early).
  - Mac without them: fetch the MP3 and play it with `afplay`. Suggest `brew install mpg123` in `cloud.md` for faster start.
  - **Windows** (no MP3 player): request `output_format=pcm_22050`, wrap it as WAV with the standard-library `wave` module (mono, 16-bit, 22050 Hz), and play it with PowerShell `(New-Object Media.SoundPlayer '<path>').PlaySync()`.
  - Linux with neither player: WAV via `aplay`.
  - One function, `play_audio_file(path) -> bool`, holds the per-OS choice.
- **Local offline voice** (`LocalVoice`): Mac `say`; **Windows** `powershell -NoProfile -Command "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('<text with single quotes doubled>')"`; Linux/Pi `espeak-ng -s 150` (or `espeak`); otherwise print `[SAY] ...`.
- **The fallback must be automatic:** ElevenLabs is used only when online **and** a key is set; any ElevenLabs error → the local voice for that clip, and the status shows why.
- **New tool `python -m scoutbot.tools.voice_check`:** speaks one line through ElevenLabs and one through the local voice, and prints time-to-first-audio for each. Record the numbers in `cloud.md`.
- **Prune `Speaker.recent`** (KI-12). Keep the per-survivor dedupe key.
- **Test:** unit-test the WAV wrapping, and the choice of player per OS (monkeypatch `platform.system`/`shutil.which`). No sound is played in tests.
- ★ Merge.

---

## P1

### B7. Sync turns itself on (KI-36)
- **Add** `scoutbot/sync/__init__.py: resolve_sinks(cfg) -> list[str]`. If `cfg["sync"]["sinks"] == "auto"`, return `mongo` if `MONGODB_URI` is set and `tiger` if `TIGER_DATABASE_URL` is set; if it's a list, return it unchanged.
- **Set** `sync.sinks: auto` in `base.yaml` (your section). Ask C to remove the `sinks: []` overrides in `mac.yaml`/`sim.yaml` (C owns those), or do it as a wiring edit.
- **Wiring edit in `runtime.py`** (≤10 lines, committed alone and announced): `Outbox(data_dir, resolve_sinks(cfg))`.
- **Status:** a sink that was requested but has no URL shows `not configured (add MONGODB_URI to .env)`.

### B8. MongoDB Atlas, live
- **New tool `python -m scoutbot.tools.sync_check [--sink mongo|tiger|both]`:** connects, upserts a test survivor twice (version 1 then 2, then 1 again, which must be ignored), inserts 3 sightings and 3 telemetry rows, reads them back, then **deletes the test data**. Print PASS/FAIL per step with timings.
- **End-to-end test:**
  1. Run `--profile sim` with the URI set.
  2. Simulate offline and let it run 2 minutes; 2 survivors get created.
  3. Chips show `offline (queued)` with counts.
  4. Go online: within 10 s the queue reaches 0 and the documents are in Atlas.
- **Indexes:** `survivors._id` (default), `sightings: {survivor_id, time}`, `telemetry: {time}`. Create them on connect, safely if they already exist.

### B9. Tiger Data (Tiger Cloud), live
- **Same `sync_check` and end-to-end test.** Confirm `sightings` and `telemetry` are hypertables (`SELECT hypertable_name FROM timescaledb_information.hypertables`).
- **Connection strings:** `sslmode=require` must be present; add it if missing.
- **Write the demo queries in `cloud.md`**, tested against real data:
  1. Survivors by triage category, with last seen and position.
  2. Sightings per survivor over time: `time_bucket('10 seconds', time)`, with counts and average position.
  3. The robot's path and actions over the last 5 minutes, from `telemetry`.
  4. The matching MongoDB queries (the survivors collection sorted by triage; a sightings aggregation).
- ★ Merge.

---

## P2

### B10. Survivor speech-to-text (KI-41)
- **Dashboard:** press-to-talk, recording in the browser with `MediaRecorder` → `POST /api/survivors/{id}/audio`. That endpoint is C's: request it with the exact contract.
- **Your side:** `scoutbot/talk/stt.py: transcribe(audio_bytes, mime) -> str`. Use ElevenLabs speech-to-text online (same key) and, offline, a small local model if one installs easily (optional). The result goes to `TalkWorker.submit("survivor_says", sid, text, source="speech")`.

### B11. Reply safety filter
- A post-filter on every model reply: strip time promises ("in 5 minutes"), rescue promises and medical instructions outside the two allowed lines. If a reply is removed, use a safe canned line.
- Tests with canned bad model outputs.

### B12. Scene prompt accuracy
- With `eval_vlm.py` data, tune the scene prompt to cut false-clears. **Scene fields stay frozen.**

---

## Pitfalls

- **Never** print `os.environ`, `.env` contents, full exception strings from HTTP clients (they can include URLs with passwords), or request headers.
- The isolation test runs in a subprocess. Don't import `scoutbot.runtime` "just for a type".
- Keep network calls out of tests. Use fakes and `httpx.MockTransport` if needed.
- **The Pi uses Linux paths and `espeak-ng`; Windows uses PowerShell.** Test the per-OS branches with monkeypatching.
- Gemini's `HttpOptions(timeout=...)` is in **milliseconds**.
- Ollama's first reply after a model loads can take 10–30 s on a laptop CPU. Warm-up and `keep_alive` matter.

## B is done when

- [ ] KI-03, 10, 12, 20, 35, 36, 43 fixed.
- [ ] Gemini scene, triage and replies work live, with measured numbers in `cloud.md`.
- [ ] Offline chat and triage work through Ollama; broken-Gemini and everything-down behave as described in B5.
- [ ] Voice works online and offline on the Mac, and on Windows/Linux paths (tested by unit tests, and on a real machine if one is available).
- [ ] Mongo and Tiger sync end to end (offline queue → online flush), with demo queries written and tested.
- [ ] Everything merged to `main`, and STATUS is current.
