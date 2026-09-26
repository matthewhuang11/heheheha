# Cloud and Talk

## What works

- Empty, quoted, or whitespace-only optional environment values are treated as not set.
- Gemini scene reports keep the frozen `SceneReport` schema, use JPEG quality 70, retry server overloads, and reuse a client per API key.
- Gemini, Ollama, and canned replies route through a three-failure, 30-second circuit breaker. Triage extracts facts and applies local preliminary rules.
- Talk uses the configured history limit and v1/v2 prompts. The v2 prompt enforces short, calm replies with one question.
- All Gemini, Ollama, and canned replies pass a safety filter; promises of rescue/timing and unsafe medical instructions are replaced with a calm fallback question.
- ElevenLabs automatically falls back to local speech. Local speech supports macOS `say`, Windows PowerShell SpeechSynthesizer, and Linux/Pi `espeak-ng` or `espeak`. Windows ElevenLabs audio uses standard-library WAV wrapping.
- Sync resolves `sync.sinks: auto` from non-empty MongoDB/Tiger environment values. Mongo creates the required indexes and Tiger adds `sslmode=require` when missing.

## How to run

```sh
python -m scoutbot.tools.ollama_check
python -m scoutbot.tools.talk_check --model ollama
python -m scoutbot.tools.voice_check
python -m scoutbot.tools.sync_check --sink both
```

For Gemini scene use `python -m scoutbot --profile mac`, then watch the dashboard Scene values. For an offline router check, use the dashboard offline toggle with a demo survivor. The simulator remains key-free.

## Measurements

| Check | Result | Notes |
| --- | --- | --- |
| Cloud unit tests | 21 passed in 0.63 s | Router, triage, worker, outbox, isolation, WAV, auto-sink and Tiger TLS checks. |
| B1 integration | 99 passed in 3.15 s | 20-second demo sim created 1 survivor, 0 contacts, 0 watchdog trips. |
| Gemini model discovery | Pass | Live key listed 19 usable Gemini models. `gemini-flash-lite-latest`, `gemini-flash-latest`, `gemini-3.8-flash`, `gemini-3.6-flash`, and `gemini-3.5-flash-lite` completed the image smoke check; two preview models returned quota errors and `gemini-3.7-flash` returned temporary high demand. |
| Gemini scene p50/p95 | 0.17 s / 1.49 s | 30 calls to `gemini-flash-lite-latest` on a synthetic image: 10/30 schema-valid `SceneReport`s, 20 rejected responses. A later 3/3 retry succeeded. Alternate `gemini-3.8-flash`: 3/5 valid, 11.83 s mean; keep flash-lite. |
| Gemini six-case talk/triage | Pass | 6/6 expected categories; triage 0.69–0.97 s and reply 0.51–0.96 s. The check now loads `.env` and honors the configured 12 s Gemini timeout. |
| Ollama cold/warm | Blocked | No service listening at `http://localhost:11434`; no measurement or JSON triage result. |
| ElevenLabs first audio | Blocked | `ELEVENLABS_API_KEY` is not configured. Built-in macOS `say` completed the voice check in 8.20 s; `mpg123` is already installed at `/opt/homebrew/bin/mpg123`. |
| Mongo/Tiger flush | Blocked | `MONGODB_URI` and `TIGER_DATABASE_URL` are not configured; `sync_check --sink both` skipped both stores. |

## Demo queries

Tiger survivors: `SELECT triage, last_seen, x_cm, y_cm FROM survivors ORDER BY triage, last_seen DESC;`

Tiger sightings: `SELECT survivor_id, time_bucket('10 seconds', time), count(*), avg(x_cm), avg(y_cm) FROM sightings GROUP BY 1,2 ORDER BY 2;`

Tiger path: `SELECT time, action, rule, x_cm, y_cm FROM telemetry WHERE time > now() - interval '5 minutes' ORDER BY time;`

Mongo survivors: `db.survivors.find({}, {triage:1,last_seen:1,pose:1}).sort({'triage.category':1,last_seen:-1})`

Mongo sightings: `db.sightings.aggregate([{$group:{_id:'$survivor_id',count:{$sum:1},last:{$max:'$time'}}}])`

## Known limits

Gemini was checked live on the demo Mac. Ollama, ElevenLabs, MongoDB Atlas, and Tiger Data cannot be accepted until their local service/credentials are configured; the offline queue-and-flush demo is therefore not yet proven. `main` now removes the profile-level empty sync-sink overrides, so configured automatic sinks can activate.
