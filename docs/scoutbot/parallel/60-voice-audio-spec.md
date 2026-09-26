# Scoutbot – Voice & Audio Spec (microphone, speaker, buzzer)

Date: 2026-09-26. Builds on `main` (phase 2). Read `docs/scoutbot/parallel/01-shared-rules.md` and `03-contracts.md` first.

## 0. Summary

The robot will have a **microphone**, a **speaker** (for ElevenLabs speech) and a **buzzer** (for beeps). This task makes two-way talking with survivors work **on a laptop now**, using the laptop mic and speakers, and the buzzer played as tones through the laptop speakers. The code is built so the real parts drop in later with a config change, not a rewrite.

The conversation loop:

```
survivor found ─► buzzer "attention" chirp ─► robot speaks (ElevenLabs) ─► "listening" beep
      ▲                                                                        │
      │                                                   mic records until they stop talking
      │                                                                        ▼
 robot speaks reply ◄── talk lane (Gemini ▸ Ollama ▸ canned) + triage ◄── speech-to-text (ElevenLabs Scribe ▸ local Whisper)
```

Plus: a periodic **locator chirp** so trapped people can hear where the robot is; a **knock mode** for people who can't speak ("knock once for yes, twice for no"); and dashboard controls (mute mic, push-to-listen, buzzer buttons, live transcript).

**Not in scope:** the actual hardware wiring (§11 lists what to buy and wire later); ElevenLabs' all-in-one Conversational AI agent (see §2).

## 1. Assumptions (check these, see §13)

1. The **buzzer** is a separate piezo buzzer for beeps. A piezo buzzer **can't play speech**, so ElevenLabs voice needs a small speaker. If the robot only has a buzzer, add a speaker (§11).
2. The **microphone** will be a USB mic, or an I2S mic like the INMP441, on the Pi. Either way, the code sees it as a normal audio input device.
3. **For now:** the laptop's built-in mic and speakers stand in for the robot's. The buzzer is imitated with generated tones.
4. The robot is **stopped** while talking. The brain already STOPs for a nearby person (rule 5), so motor noise isn't a problem during conversations.

## 2. Key decisions

| Decision | Choice | Why |
| --- | --- | --- |
| Conversation engine | **Our own pipeline:** mic → voice detection → speech-to-text → our existing talk lane → ElevenLabs TTS | We keep triage, the reply safety filter, the Gemini ▸ Ollama ▸ canned fallback, and the offline mode. ElevenLabs' Conversational AI agent would bypass all of that and needs internet. |
| Speech-to-text (online) | **ElevenLabs Scribe, batch:** `POST https://api.elevenlabs.io/v1/speech-to-text`, form fields `model_id=scribe_v2` (fall back to `scribe_v1` if the account rejects it), `file=<wav>`, `tag_audio_events=true`, optional `language_code` | Same key as the voice. Accurate. One request per utterance is simple. `tag_audio_events` also reports things like coughing or crying, which help the triage notes. |
| Speech-to-text (streaming, P2) | `wss://api.elevenlabs.io/v1/speech-to-text/realtime`, `model_id=scribe_v2_realtime`, `audio_format=pcm_16000`, `commit_strategy=vad`; send `input_audio_chunk` (base64), receive `partial_transcript` / `committed_transcript` | About 150 ms, and shows live partial text on the dashboard. Batch comes first because it's simpler. |
| Speech-to-text (offline) | **faster-whisper** (`tiny.en` or `base.en`, int8, CPU) on the laptop | Pip-installable on Mac, Windows and Linux, and fast enough on a laptop CPU. On the Pi, it runs on the base-station laptop. |
| Audio input/output | **`sounddevice`** (PortAudio) + numpy | Works on Mac, Windows and Linux with pip wheels. Linux/Pi needs `libportaudio2` from apt. |
| Detecting speech | Energy-based voice activity detection with noise-floor calibration (numpy only); optional `webrtcvad-wheels` | No extra native dependencies to start. Good enough while the robot is stopped. |
| Echo | **Half-duplex:** the mic is ignored while the robot speaks or buzzes, plus a 300 ms tail | Otherwise the robot transcribes its own voice. Talking over the robot (barge-in) is P2. |
| Buzzer on the computer | Sine and square tones generated with numpy and played via `sounddevice` | Same patterns and timings as the real buzzer, so they can be tuned now. |
| Buzzer on the Pi | `gpiozero.TonalBuzzer` (passive piezo, PWM) or `gpiozero.Buzzer` (active, on/off) | Two lines of config to switch. |

## 3. Ownership and git

- **Owner:** a new agent, **V – Voice & Audio**, on branch `agent/audio`, with commit prefix `[audio]`. Or Agent L, if it has finished its list.
- **V owns:** new `scoutbot/audio/` (everything), `scoutbot/tools/audio_check.py`, `scoutbot/tools/voice_chat.py`, `config/profiles/*` section `audio`, new tests `tests/test_audio_*.py`, and `docs/scoutbot/audio.md`.
- **Shared files V needs to touch** (announce in STATUS first; the owners are L or C for the dashboard and runtime, and L for voice and talk):
  - `scoutbot/voice/speaker.py`: add "is speaking" events and an output device setting (§6.1).
  - `scoutbot/talk/worker.py`: accept `source="speech"` and `"knock"`, and add a `new_survivor` → conversation hook.
  - `scoutbot/runtime.py`: start the audio worker, and pass "active survivor" and mode.
  - `scoutbot/server/app.py` + `responder.html`: mic and buzzer controls, transcript and level (§8).
  - `requirements.txt`: add `sounddevice` (core). New `requirements-audio-offline.txt` for `faster-whisper`.
- **The same rules as before:** commit every working step, push after every commit, merge `origin/main` hourly, merge to main only when all tests and the 20 s headless sim pass, and keep STATUS updated.
- **Safety invariant (new):** `scoutbot/audio/` must **never import** `scoutbot.hw.motors_*`, `scoutbot.safety` or `scoutbot.runtime`. Add it to `tests/test_isolation.py`. Audio can ask for things only through the talk worker and the bus. It can never move the robot. Voice commands to *drive* are explicitly out of scope.

## 4. Package layout: `scoutbot/audio/`

| File | What it does |
| --- | --- |
| `devices.py` | `list_devices()`; `pick_input(cfg)` and `pick_output(cfg)` by name substring or index (e.g. `"USB"`, `"MacBook"`), falling back to the system default; prints what it chose. |
| `mic.py` | `Mic` interface: `start()`, `frames() -> Iterator[np.ndarray]` (16 kHz mono int16, 30 ms frames), `level() -> float` (dBFS), `stop()`. Versions: `SoundDeviceMic` (laptop or USB/I2S mic on the Pi), `WavFileMic` (replays a `.wav`; for tests and demos without talking), `NullMic` (silence). |
| `vad.py` | `EnergyVAD`: calibrates the noise floor over the first 1 s, then speech = RMS > floor × `vad.speech_ratio` (default 3.0, about +9.5 dB) for ≥ 150 ms; end = below the threshold for `vad.end_silence_ms` (default 900). Optional `WebRtcVAD` wrapper. |
| `recorder.py` | `UtteranceRecorder(mic, vad)`: `listen(max_wait_s, max_utterance_s) -> Utterance | None` (audio bytes as a 16 kHz WAV, duration, peak dBFS, started_at). Keeps 300 ms of pre-roll so the first word isn't cut. |
| `stt.py` | `Transcriber` interface: `transcribe(wav_bytes) -> Transcript(text, language, confidence, events[], latency_s, engine)`. Versions: `ElevenLabsSTT` (batch), `WhisperSTT` (faster-whisper, lazy import), `FakeSTT` (returns scripted lines, for tests). `STTRouter` works like the talk router: online + key → ElevenLabs, then Whisper, then "not understood". It uses its own circuit breaker (3 failures → 30 s open). |
| `buzzer.py` | `Buzzer` interface: `play(pattern_name)`, `stop()`, `busy`. Versions: `ComputerBuzzer` (tones via sounddevice), `GpioTonalBuzzer` (passive piezo, `gpiozero.TonalBuzzer`), `GpioActiveBuzzer` (`gpiozero.Buzzer`), `FakeBuzzer` (prints `[BUZZ] attention`). Patterns come from config (§7). |
| `knock.py` (P2) | `KnockDetector`: detects sharp transients (a sudden energy jump over 15 dB within 10 ms, gaps of 150–1500 ms). `wait_for_knocks(timeout) -> int` (0, 1, 2, 3+). |
| `conversation.py` | `ConversationManager`: the state machine (§5). It owns the mic, recorder, STT and buzzer, and talks to the `TalkWorker` and `Speaker`. |
| `worker.py` | `AudioWorker`: a thread that runs the conversation manager and the locator-chirp timer, handles dashboard commands, and publishes `audio` events and status. |

**Config (`config/profiles/base.yaml`, new `audio` section):**

```yaml
audio:
  enabled: true
  input_device: default        # "default", a name substring ("USB", "MacBook"), or an index
  output_device: default       # used by the speaker AND the computer buzzer
  sample_rate: 16000
  vad: {speech_ratio: 3.0, min_speech_ms: 150, end_silence_ms: 900, calibrate_s: 1.0}
  listen: {max_wait_s: 8, max_utterance_s: 12, echo_tail_ms: 300, no_answer_limit: 3}
  stt: {provider: elevenlabs, fallback: whisper, model: scribe_v2, whisper_model: base.en, language: en, timeout_s: 10}
  buzzer: {kind: computer, pin: 26, volume: 0.3}      # computer | tonal | active | fake
  locator: {enabled: true, every_s: 20, only_in_auto: true}
  save_audio: true             # keep survivor clips in data/audio/ for responder review (never synced)
  auto_converse: true          # start a conversation automatically when a new survivor is found
```

Profiles:
- `laptop` = computer mic, speaker and buzzer.
- `sim` = `WavFileMic` with fixture clips + `FakeSTT` + `FakeBuzzer` (no sound; runs anywhere).
- `pi` = `input_device: "USB"`, `buzzer.kind: tonal`.
- Add `--set audio.enabled=false` to switch it all off.

## 5. Conversation state machine (`conversation.py`)

States: `IDLE`, `ATTENTION`, `SPEAKING`, `LISTENING`, `TRANSCRIBING`, `THINKING`, `KNOCK_MODE`, `PAUSED`.

| From | Event | Do | To |
| --- | --- | --- | --- |
| IDLE | new survivor (bus `survivor` with `sightings==1`) and `auto_converse`, or the dashboard "Talk to S-xxxx" button | set active survivor; buzzer `attention` | ATTENTION |
| ATTENTION | buzzer done | the talk worker sends the greeting (it already exists); wait for the speaker | SPEAKING |
| SPEAKING | speaker idle + `echo_tail_ms` | buzzer `listen`; start the recorder | LISTENING |
| LISTENING | an utterance is captured | buzzer `got_it` (a short soft blip) | TRANSCRIBING |
| LISTENING | nothing for `max_wait_s` | count no-answers; if under the limit: say a canned "I'm listening. Can you hear me?"; otherwise go to knock mode | SPEAKING / KNOCK_MODE |
| TRANSCRIBING | text (not empty) | `TalkWorker.submit("survivor_says", sid, text, source="speech")`, plus `events` (e.g. `[coughing]`) as context | THINKING |
| TRANSCRIBING | empty or not understood | say "Sorry, I didn't catch that. Please say it again." (at most 2 times in a row) | SPEAKING |
| THINKING | the talk worker publishes the robot's reply `chat` for this survivor | (the speaker is already saying it) | SPEAKING |
| KNOCK_MODE (P2) | enter | say "If you can hear me but can't talk, knock once for yes, twice for no. Can you hear me?" | wait for knocks |
| KNOCK_MODE | 1 or 2 knocks | submit `survivor_says` with text "(knocked once: yes)" / "(knocked twice: no)", source `knock`; then ask the next scripted yes/no question (§9) | KNOCK_MODE |
| any | dashboard **Mute mic** / mode STOPPED / responder takes over speaking | stop the recorder | PAUSED |
| PAUSED | **Unmute** | — | LISTENING |
| any | the active survivor is marked handled (continue search) or there are no sightings for 60 s | say "Help is coming. Stay where you are." and end | IDLE |

Rules:
- **Half-duplex:** the recorder is off whenever `speaker.speaking` or `buzzer.busy`, plus `echo_tail_ms`.
- **One conversation at a time.** Other new survivors queue and get a `locator` chirp instead of a conversation, and the dashboard lets the responder switch.
- **Responder messages** (typed on the dashboard) always jump the queue. The existing voice priority already does this. The mic pauses while they play.
- **Every step publishes** `{"topic":"audio","payload":{"state","survivor_id","level_db","last_text","engine","latency_s"}}` on the bus so the dashboard can show it.
- **Timing targets** (log them):
  - End of speech → start of the reply's audio: **< 3.5 s online** (STT ~0.5–1 s + talk ~1–2 s + TTS first audio ~0.5 s), **< 7 s offline**.
  - The beep after the robot finishes talking: < 400 ms.

## 6. Changes to existing code

### 6.1 `scoutbot/voice/speaker.py` (coordinate with L)
- Add `speaking: threading.Event`, set while any clip plays (ElevenLabs or local).
- Add `wait_idle(timeout) -> bool`, and a callback list `on_start` / `on_done(text, source)`.
- `voice.output_device` (or `audio.output_device`): pass it to players that support it (sounddevice playback of decoded audio is the most portable). Keep `afplay`/`mpg123` as fallbacks.
- Add `stop_now()` to cut playback (used by E-stop and the responder "stop talking" button).

### 6.2 `scoutbot/talk/worker.py`
- Accept `source="speech"` and `"knock"` (the `ChatMessage.source` Literal gains `"knock"`: add it with the default unchanged).
- When the input came from speech, include `events` (e.g. `[coughing]`, `[crying]`) in the context sent to triage: "audio: coughing heard".
- **Short replies matter more when spoken:** keep the 2-sentence limit and end with at most one question.

### 6.3 `scoutbot/runtime.py`
- Build `AudioWorker(cfg, shared, bus, talk, voice, registry)` if `audio.enabled`, and start it.
- **Mode STOPPED does not stop the conversation.** The robot keeps talking to survivors while its motors are off. Only **E-stop** cuts sound: it calls `voice.stop_now()` and pauses the mic for 3 s. Write this rule into `03-contracts.md`.
- In `state()`: add `audio: {state, survivor_id, level_db, muted, stt_engine, last_text, locator_on}`.

## 7. Buzzer patterns

Patterns are lists of `[frequency_hz, duration_ms]` steps; `0` Hz = silence. The same list drives the laptop and the piezo.

| Name | Pattern | Used for |
| --- | --- | --- |
| `attention` | `[[1800,120],[0,80],[2400,120],[0,80],[1800,120]]` | before the robot first speaks to a new survivor |
| `listen` | `[[1200,80]]` | "your turn to talk" |
| `got_it` | `[[2000,40]]` | the robot heard something |
| `not_understood` | `[[600,150],[0,60],[600,150]]` | before "please say that again" |
| `locator` | `[[3000,60],[0,120],[3000,60],[0,120],[3000,60]]`, repeated every `locator.every_s` | so trapped people can hear where the robot is (AUTO mode, no conversation active) |
| `knock_prompt` | `[[1500,60],[0,60],[1500,60]]` | "knock now" |
| `alert` | `[[900,300],[0,100],[900,300],[0,100],[900,300]]` | hazard or low battery (future) |
| `test` | a sweep from 500 to 4000 Hz over 1 s | `audio_check` |

- Piezo buzzers are loudest at about 2–4 kHz, so keep the key patterns in that range.
- `buzzer.volume` scales the computer tones only (a GPIO piezo is fixed volume).
- Tones get 5 ms fade in/out to avoid clicks.

## 8. Dashboard (`responder.html`) and server

**New WebSocket commands** (update `03-contracts.md §8`):
```json
{"type":"audio","action":"talk_to","survivor_id":"S-0001"}   // start a conversation now
{"type":"audio","action":"mute"} / {"type":"audio","action":"unmute"}
{"type":"audio","action":"listen_now"}                        // push-to-listen: robot records one utterance
{"type":"audio","action":"stop_talking"}                      // cut current speech
{"type":"audio","action":"buzz","pattern":"locator"}          // test/alert buttons
{"type":"audio","action":"locator","on":true|false}
{"type":"audio","action":"knock_mode","survivor_id":"S-0001"}
```

**UI:**
- An **audio chip:** "Mic: listening / muted / off", colored.
- On the survivor card: a **level meter** while listening; a **state label** ("Robot speaking…", "Listening…", "Transcribing…"); and the **transcript** in the chat (source `speech` shown with a mic icon, `knock` with a hand icon).
- **Buttons:** Talk to this survivor · Listen now · Mute/Unmute · Stop talking · Knock mode · Buzz: Locate / Attention.
- A **Locator chirp** toggle in the top bar.
- If `save_audio`: a small ▶ play button next to each speech message, served from `GET /api/audio/{survivor_id}/{clip}.wav` (safe path check, like `/snapshots`).

## 9. Knock mode questions (P2)

A fixed yes/no script, one question at a time. Each answer is added as a survivor message, so triage uses it:
1. "Can you hear me?"
2. "Are you trapped?"
3. "Are you bleeding?"
4. "Is it hard to breathe?"
5. "Is anyone else with you?"

After the script, say "Help is coming. Knock any time and I'll listen." and keep listening for knocks every 30 s.

## 10. Tools for testing on the computer now

1. **`python -m scoutbot.tools.audio_check`:**
   - lists devices and shows which input and output were chosen
   - records 3 s and plays it back
   - prints the noise floor and speech level (dBFS)
   - plays every buzzer pattern
   - transcribes the 3 s clip with every available STT engine, printing the text and latency
   - measures ElevenLabs TTS time-to-first-audio

   Flags: `--list`, `--input N`, `--output N`, `--no-stt`, `--pattern NAME`.
2. **`python -m scoutbot.tools.voice_chat [--offline] [--knock]`:**
   - **the main milestone:** a full spoken conversation with the laptop, without the robot, dashboard or camera
   - creates a pretend survivor `S-TEST`, runs the conversation manager, and prints every step with timings
   - `--offline` forces Whisper + Ollama + the local voice
   - Ctrl-C prints a summary: turns, average latency per stage, final triage
3. **`python -m scoutbot --profile laptop`:** the real integration. A person on the webcam → survivor → attention chirp → greeting → talk.
4. **`python -m scoutbot --profile sim`:** a `WavFileMic` plays fixture clips from `tests/fixtures/audio/` (`hello.wav`, `stuck.wav`, `silence.wav`, `knock2.wav`) with `FakeSTT`, so the whole loop runs silently, e.g. in CI.

**macOS:** the first run triggers a **Microphone permission** prompt for the terminal app. The doctor and `audio_check` must detect "permission denied / all zeros" and say: System Settings → Privacy & Security → Microphone → allow Terminal.
**Linux:** `sudo apt install libportaudio2`.
**Windows:** the sounddevice wheel includes PortAudio.

## 11. Hardware notes for later (not now)

| Part | Recommendation | Notes |
| --- | --- | --- |
| Microphone | USB mini mic (simplest), or an INMP441 I2S MEMS mic | USB needs no drivers. I2S needs a device-tree overlay. Point it forward and keep it away from the motors. Foam windscreen. |
| Speaker (needed for voice) | USB speaker, or a MAX98357A I2S amp + a 4 Ω 3 W speaker, or a small powered speaker on the Pi 4's 3.5 mm jack | A piezo buzzer can't play speech. Louder is better in rubble: 3 W minimum. |
| Buzzer | Passive piezo (for tones) on a free GPIO, e.g. **GPIO 26**, via a transistor if it draws > 15 mA; or an active 5 V buzzer via a transistor | GPIO 12/13/18/19 are the hardware PWM pins, and 12/18 are planned for the motor enables. Use software PWM (gpiozero) on 26. **Confirm with the hardware team.** |
| Placement | Mic and speaker at opposite ends, both facing forward | Less echo. The half-duplex rule handles the rest. |

Add these to `docs/scoutbot/hardware-handoff.md` (Agent R's file: request it via STATUS).

## 12. Tests (no real audio devices, no network)

- `test_audio_vad.py`: synthetic noise and tone at set levels → speech start and end detected within ±60 ms; noise floor adapts; pre-roll is included.
- `test_audio_buzzer.py`: every pattern renders to the expected number of samples; fades present; `FakeBuzzer` records calls; an invalid pattern → a clear error.
- `test_audio_stt.py`: `ElevenLabsSTT` via `httpx.MockTransport` (sends a multipart form with `model_id` and `file`, parses `text`/`words`/audio events; timeout → error); the `STTRouter` fallback order and breaker; `WhisperSTT` skipped if faster-whisper isn't installed.
- `test_audio_conversation.py`: with a fake clock, `WavFileMic`, `FakeSTT`, `FakeBuzzer` and a fake speaker, check:
  - new survivor → attention → greeting → listen → text → `survivor_says(source="speech")`
  - silence ×3 → knock mode
  - mute pauses
  - the half-duplex rule (the recorder never runs while `speaking`)
  - handled survivor → goodbye → IDLE
- `test_audio_knock.py` (P2): synthetic clicks → the right counts; speech isn't counted as knocks.
- `test_isolation.py`: add `scoutbot.audio.*`.
- `test_server.py`: `audio` commands accepted and refused per mode, and the `state().audio` shape.

## 13. Build order and "done"

| # | Milestone | Done when |
| --- | --- | --- |
| V0 | `audio_check` + devices + `ComputerBuzzer` | on the laptop: devices listed, 3 s record/playback works, every buzzer pattern audible |
| V1 | Mic + VAD + recorder | speaking into the laptop gives clean utterances with the start not clipped; silence gives none; level shown |
| V2 | STT router (ElevenLabs + Whisper + fake) | the same clip transcribes online and offline; latencies in `audio.md` |
| V3 | ★ `voice_chat` | **a full spoken back-and-forth with the laptop, online and `--offline`**, with triage updating from speech |
| V4 | Speaker events + half-duplex + stop | the robot never hears itself; "stop talking" works |
| V5 | ★ Runtime + dashboard integration | the laptop profile: a person on the webcam → attention chirp → greeting → conversation; the transcript shows on the dashboard; mute and listen-now work; the sim profile runs silently with fixtures |
| V6 | Locator chirp + buzzer controls | a chirp every 20 s in AUTO with no active conversation; the dashboard buttons work |
| V7 (P2) | Knock mode | 1 and 2 knocks recognized on the laptop mic (knock on the desk); the yes/no script feeds triage |
| V8 (P2) | Realtime streaming STT | live partial text on the dashboard while the survivor talks; lower latency |
| V9 | Pi readiness | the `pi` profile uses a USB mic and `GpioTonalBuzzer` (tested with a fake GPIO factory); the hardware notes are in the hand-off doc |

**The whole task is done when:** V0–V6 pass on the laptop with real ElevenLabs; the offline path works with Whisper + Ollama + the local voice; tests pass; the numbers are in `docs/scoutbot/audio.md`; the dashboard has the controls; and the demo script gains a step: "the survivor *speaks* instead of someone typing".

## 14. Open questions (for Matthew and the hardware team)

1. Is the "buzzer" a piezo buzzer, or a small speaker? Is there a speaker at all? Voice needs a speaker.
2. What is the mic model (USB or I2S)?
3. Which GPIO pin is free for the buzzer?
4. Should survivor audio clips be kept (`save_audio`)? The default is yes, locally only, never synced. They contain people's voices and medical details, so decide before the demo.
5. Language: English only for now (`language: en`). Scribe can auto-detect if needed.

## Sources
- [ElevenLabs – Create transcript (batch STT)](https://elevenlabs.io/docs/api-reference/speech-to-text/convert)
- [ElevenLabs – Realtime STT WebSocket](https://elevenlabs.io/docs/api-reference/speech-to-text/v-1-speech-to-text-realtime)
- [ElevenLabs – Speech to Text overview (models, formats)](https://elevenlabs.io/docs/overview/capabilities/speech-to-text)
- [ElevenLabs – Client-side streaming guide](https://elevenlabs.io/docs/developers/guides/cookbooks/speech-to-text/streaming)
