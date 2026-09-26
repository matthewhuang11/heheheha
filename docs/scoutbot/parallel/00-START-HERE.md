# Scoutbot three-agent build: start here

Date: 2026-09-26. Repo: `heheheheha` (GitHub `origin`). Starting point: `main` at `705ccab` or later.

Scoutbot is a small disaster-response robot. It drives itself with a Raspberry Pi 4, a camera and distance sensors, finds people, and lets a responder see, drive and talk to survivors from a laptop dashboard. Gemini, ElevenLabs and survivor databases are used when there is internet; Ollama on the laptop takes over when there isn't.

**Every box on the architecture diagram already has first-version code, and 99 tests pass.** What's left is making each piece work for real, fixing what breaks, and polishing. The work is split across three agents that run at the same time.

## The three agents

| Agent | Owns | Branch | Commit prefix | Brief |
| --- | --- | --- | --- | --- |
| **A – Robot** | hardware drivers, YOLO person detection, safety layer, Raspberry Pi bring-up | `agent/robot` | `[robot]` | [10-agent-a-robot.md](10-agent-a-robot.md) |
| **B – Cloud & Talk** | Gemini, Ollama, online/offline router, triage, ElevenLabs + local voice, MongoDB + Tiger Data sync | `agent/cloud` | `[cloud]` | [20-agent-b-cloud.md](20-agent-b-cloud.md) |
| **C – Station** | runtime wiring, dashboard + server, survivors + map, simulator, setup on any computer, README, keeping `main` green | `agent/station` | `[station]` | [30-agent-c-station.md](30-agent-c-station.md) |

## Reading order for every agent

1. This file.
2. [01-shared-rules.md](01-shared-rules.md): file ownership, the git workflow (commit and push often), STATUS updates, definition of done. **Required.**
3. [02-codebase-map.md](02-codebase-map.md): what every file does and how data flows. Read it before touching code.
4. [03-contracts.md](03-contracts.md): the exact interfaces between the three areas. Don't break these.
5. [04-known-issues.md](04-known-issues.md): bugs and gaps found so far, each already assigned to an agent.
6. Your own brief (10, 20 or 30).
7. [40-integration-and-demo.md](40-integration-and-demo.md): timeline, merge checkpoints, the final demo checklist.
8. [STATUS.md](../STATUS.md): the live team board. Read it every time you pull `main`, and update your own section.

Background design docs (read the sections your brief points to): `scoutbot-next-steps-spec.md` (full design), `disaster-response-robot-v1-spec.md` (the original brain), and the Claude project docs `robot/decision-policy.md` and `robot/build-notes.md`.

## Step 0: Matthew does this once, before starting the agents

1. **Push `main` to GitHub.** GitHub is far behind the Mac, and the agents need to start from the same place:
   ```bash
   cd heheheheha && git checkout main && git push origin main
   ```
2. **Keys:** on every machine an agent uses, `.env` (in the repo folder, never committed) should hold what you have:
   `GEMINI_API_KEY`, `GEMINI_MODEL=gemini-flash-lite-latest`, `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` (optional), `MONGODB_URI`, `TIGER_DATABASE_URL`, and `CAMERA_INDEX` (optional; your Mac uses 1).
3. **Ollama** (ollama.com) installed and opened once on the laptop Agent B uses.
4. **If two agents share one computer:** give each its own clone (`git clone <repo> scoutbot-a`, `scoutbot-b`, ...). **Two agents must never work in the same folder**, because switching branches there changes the other agent's files underneath it.
5. **Paste each agent's "Brief" box** (at the top of its file) as its first message, and tell it where the repo folder is.

## What "done" means for the whole team

The demo checklist at the end of [40-integration-and-demo.md](40-integration-and-demo.md) passes on `main`, tagged `demo-ready`.
