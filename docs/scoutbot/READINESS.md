# Scoutbot readiness handoff

**As of:** 2026-09-26 17:13 EDT (UTC-4)
**Scope:** established implementation and validation evidence only. A feature is
called *validated* below only where a recorded check exists; everything else is
explicitly unverified.

## Architecture status

### Robot

- **Validated:** the simulated robot path, safety gate, motor-check tooling,
  camera fallback, remote-YOLO handling, blind-spot study, and simulated cliff
  handling have recorded tests or live laptop checks. The current integration
  baseline recorded 144 passing tests and a 60-second headless demo with one
  survivor, zero contacts, and zero watchdog trips.
- **Unverified:** a physical Raspberry Pi, actual sensors/camera, motor
  direction and floor calibration, and hardware shutdown behavior. The Pi setup
  script has been syntax-checked, not run on Pi hardware.
- Details and measured robot results are in [robot.md](robot.md) and the
  hardware prerequisites are in [hardware-handoff.md](hardware-handoff.md).

### Base station

- **Validated:** launcher/setup, dashboard, simulator, survivor registry, and
  safety-command paths have integration evidence. A local fresh-clone check
  completed setup, doctor, and a 20-second simulation. The simulated camera
  does not require webcam permission.
- **Validated with qualification:** an earlier live laptop run recorded a
  healthy webcam/YOLO and successful Gemini scene and talk use. A later
  acceptance environment had camera permission denied, so the complete current
  webcam-plus-phone demo still needs to be rerun.
- **Unverified:** real Windows launcher, phone sharing on the presentation
  network, and the full operator demo.
- See [station.md](station.md) and [DEMO-OPERATOR.md](DEMO-OPERATOR.md).

### Cloud

- **Validated:** Gemini key discovery found 19 usable models; Gemini talk and
  triage passed all six fixture categories. The recorded scene benchmark was
  10/30 schema-valid responses at p50 0.17 s and p95 1.49 s, followed by a
  successful 3/3 retry. This supports integration readiness, not a general
  scene-accuracy claim.
- **Implemented but unverified live:** ElevenLabs synthesis and automatic
  MongoDB/Tiger sync. ElevenLabs has not been accepted because its API key and
  voice ID were unavailable. The local speech fallback did complete its check
  in 8.20 s.
- **Unverified:** MongoDB ingestion/flush and any Vultr-based ingest from the
  Raspberry Pi. Vultr is not claimed as configured or tested here.
- See [cloud.md](cloud.md).

### Offline fallback

- **Implemented:** Ollama is the local reply path; built-in local speech is the
  voice fallback; queued sync is designed to flush when connectivity returns.
- **Unverified live:** Ollama reply/triage, offline queue-and-flush, and the
  complete offline operator-demo step. The recorded environment had no service
  listening on `localhost:11434`.

## Verified evidence

- Full suite: **144 tests passed** at the recorded main integration baseline.
- Headless simulation: **60 seconds**, **1 survivor**, **0 contacts**, and
  **0 watchdog trips**.
- Laptop webcam plus Gemini: an earlier recorded live run had a healthy camera,
  YOLO, Gemini scene calls, and a Gemini-triaged survivor reply. It must be
  repeated after camera permission is available for current acceptance.
- Voice: local synthesis completed in **8.20 seconds**. **ElevenLabs synthesis
  is not yet live-validated**; only its integration and fallback behavior are
  established.

## Outstanding blockers

1. Camera permission and a person/phone are needed for the laptop and phone
   acceptance run.
2. Ollama and the required local model are not running for the offline check.
3. ElevenLabs, MongoDB, and Tiger settings are not configured for their live
   checks.
4. Windows has not had a real-machine launcher run.
5. Pi hardware details and the physical robot are required for bring-up,
   calibration, and motor/sensor acceptance.

## Intentionally deferred

- MongoDB setup and validation.
- Vultr ingest design/setup from the Raspberry Pi.
- Physical hardware wiring, Pi bring-up, calibration, and field tests.

These are separate follow-up workstreams; none is implied complete by the
software and simulator evidence above.

## Recommended resume sequence

1. Configure only the authorized service environment values locally, then run
   doctor and the manual cloud checks.
2. Start Ollama with the required model; validate local reply, triage, and the
   offline queue-to-flush flow.
3. Validate ElevenLabs, then MongoDB and the separately planned Vultr ingest.
4. Grant camera access and run the laptop webcam plus Gemini, voice, and
   phone-sharing acceptance steps using the operator guide.
5. Perform the Windows launcher check.
6. When hardware arrives, follow the hardware handoff and Pi bring-up checks;
   record calibration and physical safety results before claiming robot
   readiness.

## Secret-safe operating notes

- Keep all service values in the local `.env`; do not commit, print, paste, or
  log environment values, keys, passwords, tokens, or credential-bearing URLs.
- Commit only placeholders and documentation that names a required variable;
  never its value. Follow the repository's shared secret rule in
  [01-shared-rules.md](parallel/01-shared-rules.md).
