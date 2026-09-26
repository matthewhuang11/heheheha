# Integration, timeline and the demo

## 1. Timeline (hours from when the agents start)

Rough targets. ★ = merge to `main`. Update STATUS whenever you hit (or miss) one.

| Time | A – Robot | B – Cloud & Talk | C – Station |
| --- | --- | --- | --- |
| 0:00–0:15 | branch, STATUS section, `robot.md` skeleton | branch, STATUS section, `cloud.md` skeleton | branch, STATUS section, `station.md` skeleton |
| by 1:00 | A1 motor_check ★, A2 camera auto-detect | B1 `.env.example` ★, B2 Gemini scene numbers | C1 profiles + C2 setup.py + C3 launchers |
| by 2:00 | A3 YOLO on webcam ★, A4 cut-offs | B3 triage/replies + talk_check ★ | C4 start menu, C5 doctor, C6 `--share` ★ |
| by 3:00 | A5 NCNN ★, A6 remote YOLO ★ | B4 Ollama, B5 router ★ | C7 fresh-machine test ★, first integration pass (C12) |
| by 4:00 | A7 safety tests ★, A8 pi_setup.sh | B6 voice on all OSes ★ | C8 laptop demo run, C9 command safety and performance |
| by 5:00 | A9–A10 Pi bring-up (if hardware) ★ | B7–B9 sync live + demo queries ★ | C10 dashboard polish, C11 survivors ★, integration pass |
| after | A11 sensor layout, A12 continue-search, A13 cliff | B10 speech-to-text, B11 reply filter, B12 scene accuracy | C13 continue-search, C14 README, C15 recording |

**Checkpoints for the whole team** (each agent posts one line in STATUS at each):
- **T+1:00:** everyone has merged at least once. C confirms `main` is green.
- **T+3:00:** integration pass 1 (C). The demo script runs in the sim with real Gemini and Ollama.
- **T+5:00:** integration pass 2 (C). The demo script runs on the laptop webcam with real voice and sync, and on the Pi if the hardware exists.
- **Final (about 20 minutes before the demo):** code freeze. Only fixes for demo-checklist failures, run through the whole process below.

## 2. Final integration (code freeze)

1. A and B merge their last work to `main` and post "frozen" in STATUS. They don't push to `main` again unless C asks for a fix.
2. C pulls `main` on the demo laptop, in a **fresh clone**:
   ```bash
   git clone <repo> scoutbot-demo && cd scoutbot-demo && cp ../heheheheha/.env .
   ./start.command        # or: python3 scripts/setup.py && .venv/bin/python -m scoutbot.start
   ```
3. C runs `python -m pytest -q tests`, the 60 s headless sim (`--headless 60`), and the doctor. Everything must pass.
4. C runs the whole demo checklist (§4) on the laptop profile with real keys. A runs the robot part on the Pi, if it exists.
5. Tag the commit: `git tag demo-ready && git push origin demo-ready`.
6. **Backup plan:** if the real robot fails on stage, run `start` → 1 (sim demo) with `--share` and show it on the projector. Every box on the diagram still works there.

## 3. Demo script (about 3 minutes)

| # | Say | Do | What the audience sees |
| --- | --- | --- | --- |
| 1 | "Scoutbot searches disaster sites so responders don't have to go in first." | Open the dashboard (on the projector, and on a phone via `--share`). The robot is STOPPED. | The dashboard: live video, map, all chips green. |
| 2 | "It drives itself. The AI never drives: it only describes, and plain rules decide." | Press **Start auto**. | The robot moves and avoids a box; the "Robot is doing" card shows the rule that fired. |
| 3 | "It finds people." | A teammate lies partly behind an obstacle. | YOLO box → robot STOPs (rule 5) → survivor pin on the map → greeting spoken (ElevenLabs). |
| 4 | "It talks to them and writes a preliminary triage note." | The teammate says, or someone types, "My leg is stuck, I can't move it." | Triage turns **red – IMMEDIATE (trapped)**, "Preliminary"; Gemini's reply is spoken. |
| 5 | "Disasters kill the internet. Scoutbot keeps working." | Toggle **Simulate offline** (or unplug the hotspot's internet). | Chips turn amber; the next reply comes from **Ollama** in the local voice; survivors show "queued". |
| 6 | "When the connection comes back, everything syncs." | Toggle back online. | Mongo and Tiger chips go green; show the Tiger `sightings` time-series query and the Mongo document. |
| 7 | "A responder can take over, and it still won't crash." | **Take control**, drive toward a wall, let go, press **STOP**. | "Blocked: something 20 cm ahead" veto; it stops when released; STOP works. |
| 8 | "The AI describes, the rules decide, and it degrades safely: that's Scoutbot." | | |

## 4. Demo acceptance checklist (must all pass on `demo-ready`)

- [ ] A fresh clone on the demo laptop: `start` → sim works with no manual steps beyond copying `.env`.
- [ ] The dashboard opens from a phone on the same Wi-Fi (`--share`).
- [ ] Start auto: explores (sim: 0 contacts in 60 s; real: stops before walls at slow speed), and the rule that fired is shown.
- [ ] A person in view: YOLO box within 1 s → STOP → survivor pin → spoken greeting.
- [ ] A survivor says they're stuck → IMMEDIATE (trapped, preliminary) → Gemini reply spoken.
- [ ] Simulate offline → reply from Ollama, spoken in the local voice → survivors "queued".
- [ ] Back online → Mongo and Tiger chips green within 10 s → records visible, with demo queries ready to paste.
- [ ] Take control → driving into a wall is vetoed → letting go stops within 0.3 s → STOP works from every mode.
- [ ] Closing the dashboard tab, or killing the program, stops the motors within 0.5 s.
- [ ] No key or password appears anywhere on screen or in the logs.

## 5. Troubleshooting (for the demo operator)

| Problem | Fix |
| --- | --- |
| Black video on a Mac | System Settings → Privacy & Security → Camera → allow Terminal. Or set `CAMERA_INDEX` (0/1/2) in `.env`. |
| "Gemini (offline)" but the internet works | Check `GEMINI_API_KEY`; run `python check_gemini.py`; check the "Simulate offline" toggle is off. |
| Ollama chip red | Open the Ollama app, run `ollama pull qwen2.5:3b`. On the Pi, `talk.ollama.url` must be the laptop's IP, and the laptop needs `OLLAMA_HOST=0.0.0.0`. |
| No sound | Volume up; `python -m scoutbot.tools.voice_check`; without an ElevenLabs key the built-in voice is used. |
| Phone can't open the dashboard | Start with `--share`; phone and laptop on the same Wi-Fi; some venue Wi-Fi blocks devices from seeing each other → use a phone hotspot. |
| Robot won't move | Mode must be AUTO or MANUAL; the link chip green; sensors not stale (the "Robot is doing" card says why). |
| Port 8000 busy | `--set server.port=8001`. |
