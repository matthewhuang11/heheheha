# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Hackathon judges (primary, this weekend).** HackGT 13 expo, Sunday morning, ~3-minute demo per team. They stand at the expo table and lean in over a 13-15" laptop while the robot drives on the floor beside them. They decide in minutes whether the robot is real and the idea matters.
- **Search-and-rescue responders (the fiction the demo proves).** An incident commander at a base station outside a collapsed building, sending a scout robot in ahead of people.

## Product Purpose

scoutbot is a search-and-rescue scout rover. It drives into a comms-dead disaster zone on its own, finds survivors with a camera, talks to them and records their answers, marks where they are, retraces its path out, and dumps everything to HQ, where AI turns it into triage reports. The responder dashboard is where the mission is launched, watched, and where the survivors appear once the robot is back in range.

Success this weekend: the dashboard makes judges say "wow" within the demo and makes the blackout-then-sync moment unmistakable.

## Positioning

Store-and-forward autonomy: the robot does not need a connection to search. It works dark, then syncs. Most rescue-robot demos are remote-controlled camera carts that die when the link drops; this one is designed around the link dropping.

## Operating Context

- Demo flow: start mission (robot goes dark, "blackout") -> robot explores autonomously, avoids obstacles, approaches a person, speaks, records -> return home (retraces path) -> "back in range" -> survivors fill in with transcripts and triage reports live.
- Manual driving (WASD / on-screen pad) is always available and instantly overrides autonomy.
- Served by the robot's Raspberry Pi 4 (FastAPI) over a phone hotspot; opened in a laptop browser. The dashboard polls `/api/state` about every 700 ms.

## Capabilities and Constraints

- Single static file `dashboard/index.html`; no build step. Every existing API call and behavior must keep working (see `pi/app.py`).
- Data available per poll: brain mode (online / blackout / hq-local / no-brain), autonomy state + mission countdown, camera ok, detector fps + live detections, pose (x, y m from entry, heading), sonar distances (front/left/right), survivors (id, x, y, found time, contacted, audio, transcript, triage report + source, status pending/processed), event feed.
- Live video is an MJPEG `<img>` from `/stream`; survivor photo at `/api/victims/{id}/snap`, audio at `/api/victims/{id}/audio`.
- Web fonts are allowed (user confirmed). The HQ laptop may be offline during the demo, so anything external must degrade gracefully.
- Position is dead reckoning from commanded speed (no encoders yet): approximate, and should not be presented as survey-precise.

## Brand Commitments

- Name is lowercase: "scoutbot".
- UI copy is lowercase and plain, no hype.

## Evidence on Hand

- Working robot software on the Pi; autonomy passes a 12-check simulation (`tools/sim_autonomy.py`).
- No real survivor data, photos, or field deployments exist. Demo survivors are teammates. Never fabricate deployments, partners, or accuracy numbers.

## Product Principles

1. The blackout is the story: going dark and coming back must be the most visible state change on screen.
2. A human can always take over instantly; controls for stopping never hide.
3. Show what the robot actually knows, including uncertainty (approximate positions, "saved on robot" vs "triaged at hq").
4. Survivors are people, not detections: each gets a face (photo), a voice (audio), and words (transcript).
