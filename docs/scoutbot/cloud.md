# Cloud and Talk

## What works

- Empty, quoted, or whitespace-only optional environment values are treated as not set.
- Gemini scene reports keep the frozen `SceneReport` schema, use JPEG quality 70, retry server overloads, and reuse a client per API key.
- Gemini, Ollama, and canned replies route through a three-failure, 30-second circuit breaker. Triage extracts facts and applies local preliminary rules.
- Talk uses the configured history limit and v1/v2 prompts. The v2 prompt enforces short, calm replies with one question.
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
| Gemini scene p50/p95 | Not measured | Requires an authorized live API run. |
| Ollama cold/warm | Not measured | Run `ollama_check` on the intended laptop. |
| ElevenLabs first audio | Not measured | Requires a live key and installed player. |
| Mongo/Tiger flush | Not measured | Requires real cloud database URLs. |

## Demo queries

Tiger survivors: `SELECT triage, last_seen, x_cm, y_cm FROM survivors ORDER BY triage, last_seen DESC;`

Tiger sightings: `SELECT survivor_id, time_bucket('10 seconds', time), count(*), avg(x_cm), avg(y_cm) FROM sightings GROUP BY 1,2 ORDER BY 2;`

Tiger path: `SELECT time, action, rule, x_cm, y_cm FROM telemetry WHERE time > now() - interval '5 minutes' ORDER BY time;`

Mongo survivors: `db.survivors.find({}, {triage:1,last_seen:1,pose:1}).sort({'triage.category':1,last_seen:-1})`

Mongo sightings: `db.sightings.aggregate([{$group:{_id:'$survivor_id',count:{$sum:1},last:{$max:'$time'}}}])`

## Known limits

Live Gemini, Ollama, ElevenLabs, MongoDB Atlas, and Tiger Data measurements are intentionally not fabricated. Run the matching checks with authorized services before a live demo. The profile overrides `sync.sinks: []` in `mac.yaml` and `sim.yaml` still need removal by Station for automatic sync to activate in those profiles.
