# Scoutbot demo operator

## Before the audience arrives

1. Confirm the laptop has internet, camera permission, a running Ollama with
   `qwen2.5:3b`, and working Gemini, ElevenLabs, MongoDB, and Tiger settings in
   `.env`. Never display that file.
2. Run `./start.command`, choose **5**, and resolve every required service warning.
3. Run `./start.command`, choose **2**, and choose to share. Open the printed
   `http://<LAN-IP>:8000` address on the projector and a same-Wi-Fi phone.
4. Keep a terminal ready with `./start.command` for the sim backup.

## Three-minute script

1. Say: “Scoutbot searches disaster sites so responders do not have to go in
   first.” Show the dashboard stopped, with the service chips and map visible.
2. Press **Start auto**. Say: “AI describes; plain safety rules decide motion.”
   Show the decision card as it explores.
3. Have the teammate enter view, partly behind an obstacle. Say: “It finds
   people.” Show the YOLO box, STOP, survivor card, and spoken greeting.
4. Type or say: “My leg is stuck, I cannot move it.” Say: “It writes a
   preliminary triage note.” Show **IMMEDIATE (trapped)** and the Gemini reply.
5. Press **Simulate offline**. Say: “It keeps working when the internet is
   gone.” Show the Ollama/local-voice reply and queued status.
6. Turn the offline toggle off. Say: “When the link returns, records sync.”
   Wait for Mongo and Tiger to turn green, then show the prepared queries in
   `docs/scoutbot/cloud.md`.
7. Press **Take control**. Drive toward the slider wall, release the control,
   then press **STOP**. Say: “A responder can take over, but cannot override
   the safety gate.”

## If a live component fails

- Gemini, voice, sync, camera, or the robot fails: say the system has a safe
  fallback, run `./start.command`, choose **1** (sim), choose share, and show
  the same dashboard on the projector and phone.
- Phone cannot connect: use a phone hotspot, restart with share, and open the
  newly printed address.
- Ollama is unavailable: open Ollama and run `ollama pull qwen2.5:3b`; until it
  is ready, do not claim the offline-local-reply step passed.
- Sound fails: check volume, then run `python -m scoutbot.tools.voice_check`.
- The dashboard does not start: run menu option **5** and use its specific
  service or port guidance. Port 8000 is the demo port.

## Shutdown

Press **STOP** before closing the dashboard or terminal.
