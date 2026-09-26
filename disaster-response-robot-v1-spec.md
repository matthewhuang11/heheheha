# Disaster Response Robot – V1 Spec

Date: 2026-09-25

## 1. Goal and scope

V1 is a robot that drives itself around a space using a camera and three distance sensors, where a plain program (not the AI) makes every movement decision.

The camera image goes to a vision AI model (VLM) in the cloud. The model only describes what it sees, in a fixed format. A deterministic program then combines that description with the distance readings and picks the next move.

**In scope for v1**

- Read three ultrasonic distance sensors continuously.
- Grab frames from the GoPro and send them to a cloud VLM every 1 to 3 seconds.
- Get back a strict, validated description of the scene (terrain, hazards, whether the way ahead looks clear, whether a person is visible).
- Pick one move from a short fixed list: forward, slow forward, turn left, turn right, back up, stop.
- Drive the motors, with automatic stops if anything goes stale or fails.
- Log everything so runs can be replayed and debugged.

**Out of scope for v1 (but designed for, see section 11)**

Voice and talking to people, mapping, the local VLM on the Pi, multiple robots, any remote control UI beyond a basic status view.

**Definition of done**

1. The robot drives across a cluttered test area for 5 minutes without hitting anything.
2. It slows or turns when the VLM reports a hazard, even when the sensors see nothing.
3. It stops safely if the VLM, Wi-Fi, or a sensor goes offline.
4. The whole decision logic runs on a laptop with no robot, using recorded or fake data.

## 2. Assumptions

I made these choices so the spec is concrete. Each one is isolated behind a config setting or a small interface, so changing it later is cheap.

| Area | Assumption | If wrong |
| --- | --- | --- |
| Computer | Raspberry Pi 5 running Raspberry Pi OS, Python 3.11+ | Pi 4 works for v1 since the VLM is in the cloud |
| Camera | GoPro over USB, read as a video stream on the Pi | Fall back to Wi-Fi preview stream, or a cheap USB webcam for testing |
| Sensors | 3 HC-SR04 ultrasonic sensors: left, center, right, with voltage dividers on Echo pins | Any sensor works if it returns centimeters |
| Drive | Two-wheel differential drive (left and right motor) through a motor driver board | Only the motor layer changes |
| VLM | One cloud VLM behind a simple interface, picked by config (Moondream or Gemini first) | Swap by writing one small adapter file |
| Network | Robot has Wi-Fi or a phone hotspot to reach the cloud | Robot runs in sensor-only mode when offline |
| Control rate | Safety loop 20 times per second, VLM loop about once per 2 seconds | Both are config values |

**Why these fit the research:** cloud VLM calls take roughly 1 to 4 seconds, and small VLMs on a Pi are far too slow today, so the design never waits on the VLM to stay safe.

## 3. Architecture

The robot runs two loops at different speeds that share one small object called the world state. The fast loop keeps the robot safe, and the slow loop makes it smarter.

```text
FAST LANE (sensors, safety)
  [3 distance sensors] --> [Sensor reader, 20x/sec] ---\
                                                        v
                                                 [ WORLD STATE ] --> [Decision engine] --> [Safety gate] --> [Motors]
                                                        ^             (plain rules)        (can veto any
  [GoPro camera] -----> [VLM client, ~every 2s] --------/                                   move; also reads
SLOW LANE (cloud AI)                                                                        sensors directly)
```

Only the decision engine and the safety gate can produce motor commands, and neither ever waits on the cloud.

**Three rules that hold the design together**

1. The VLM describes, it never commands. Its answer is treated as data, checked against a schema, and then used as one input to the rules.
2. Sensors win close calls. If a sensor says something is near, the safety gate stops or turns the robot no matter what the VLM said.
3. Every fact has a timestamp. The world state remembers when each reading arrived, and old facts expire so the robot never acts on stale information.

Each box is its own small worker (a Python thread or async task). Workers only write to or read from the world state, and never call each other directly. That is what makes it easy to add or swap pieces later.

## 4. Components

Each component has one job and one small interface. Hardware pieces also have a fake version so the rest of the code can run without the robot.

| Component | Job | Interface (what it gives or takes) | Fake version for testing |
| --- | --- | --- | --- |
| Sensor reader | Trigger the 3 sensors one at a time, filter noise (median of 3 to 5 readings), publish distances | Writes `left_cm`, `center_cm`, `right_cm`, each with a timestamp and a `valid` flag | Replays a CSV or scripted values |
| Camera source | Pull the newest frame from the GoPro, shrink it (about 640 px wide), keep only the latest | `get_latest_frame() -> Frame` | Reads a folder of images or a webcam |
| VLM client | Send a frame plus the fixed prompt to the cloud model, get JSON back, time out after 4 seconds | `describe(frame) -> SceneReport or Error` | Returns canned reports |
| Validator | Check the JSON against the schema, clamp values, reject anything odd | `validate(raw) -> SceneReport or Error` | Same code, no fake needed |
| World state | One thread-safe object holding the latest sensor readings, latest scene report, and their ages | `update_*()` and `snapshot()` | Same code |
| Decision engine | Turn a snapshot into one action using the rules in section 6 | `decide(snapshot) -> Action` (pure function, no side effects) | Same code, tested directly |
| Safety gate | Final check before motors: veto or override the action | `gate(action, snapshot) -> Action` | Same code |
| Motor layer | Turn an action into left and right wheel speeds, ramp speeds smoothly, cut power on stop | `execute(action)` | Prints the command instead of driving |

**Fixed action list.** The decision engine can only return one of these: `STOP`, `FORWARD`, `FORWARD_SLOW`, `TURN_LEFT`, `TURN_RIGHT`, `BACK_UP`. Each has fixed wheel speeds set in config. Adding a new behavior later means adding an action to this list, never bypassing it.

**Why `decide()` is a pure function.** It only reads a snapshot and returns an action, so you can test it by feeding it fake data and checking the answer. This is the core of v1 and the most important thing to keep clean.

## 5. VLM contract

The VLM must answer with exactly this JSON and nothing else. Every field is a fixed choice or a number, never free text the program has to interpret. Free text is allowed only in `notes`, which is logged but never used for decisions.

```json
{
  "schema_version": 1,
  "path_ahead": "clear | partially_blocked | blocked | unknown",
  "best_direction": "left | center | right | none",
  "terrain": "flat | rubble | uneven | stairs_or_drop | water | unknown",
  "hazards": [
    { "type": "fire | smoke | water | wire | glass | drop_off | unstable_debris | other",
      "where": "left | center | right",
      "distance": "near | mid | far" }
  ],
  "people": { "visible": true, "where": "left | center | right | none", "distance": "near | mid | far | none" },
  "confidence": 0.0,
  "notes": "short free text, logging only"
}
```

**Prompt rules**

- The prompt is a fixed file in the repo (`prompts/scene_v1.txt`), versioned with the schema. It tells the model to answer `unknown` when unsure rather than guess.
- Ask for JSON only, and use the provider's structured output or JSON mode if it has one.
- Keep images small and prompts short. Both cut latency more than any other change.
- The prompt never asks the model what the robot should do. It only asks what is in the picture.

**Validation and failure handling**

| What goes wrong | What the program does |
| --- | --- |
| Reply is not valid JSON or fails the schema | Discard it, count an error, keep the last good report until it expires |
| A field has an unexpected value | Treat the whole report as invalid (no partial trust) |
| Request takes longer than 4 seconds | Cancel it, count an error, send the next frame |
| Three errors in a row | Mark the VLM as `offline` and drop to sensor-only behavior until one call succeeds |
| Report is older than 6 seconds | Treat as `unknown` in every rule |

**Provider adapter.** All cloud models sit behind one `VLMProvider` interface with a single method, `describe(frame, prompt) -> raw_text`. The client, validator, and everything after it are the same for every provider, so swapping Moondream, Gemini, or Claude means writing one small file.

## 6. Decision logic

The decision engine checks rules from top to bottom and returns the first one that matches. Higher rules are about safety, lower rules are about making progress. Numbers are starting values to tune on the real robot and live in config.

| Priority | Condition | Action |
| --- | --- | --- |
| 1 | Sensor data older than 0.5 s, or all three sensors invalid | `STOP` |
| 2 | Center distance under 25 cm | `BACK_UP` if both sides are under 40 cm, otherwise turn toward the side with more room |
| 3 | Left or right distance under 15 cm | Turn away from that side |
| 4 | VLM reports a drop, stairs, or fire/smoke ahead at near or mid range | `BACK_UP`, then turn toward `best_direction` (or the roomier side) |
| 5 | VLM sees a person at near range | `STOP` and raise a flag (v1 just holds still and logs it) |
| 6 | VLM says `path_ahead` is `blocked` | Turn toward `best_direction` if given, otherwise toward the roomier side |
| 7 | Center under 60 cm, or `path_ahead` is `partially_blocked`, or terrain is rubble or uneven | `FORWARD_SLOW` |
| 8 | Everything else | `FORWARD` |

**How sensors and VLM are paired.** The sensors say how close things are in three directions. The VLM says what those things are and where the open way seems to be. Rules 2 and 3 use only sensors. Rules 4 to 6 use the VLM. Rules 7 and 8 use both, and either one can slow the robot down, but only the sensors can declare the way clear enough to go full speed.

**When the VLM is offline or stale.** Skip rules 4 to 6 and treat `path_ahead` as `unknown`. The robot then never goes faster than `FORWARD_SLOW`, so losing the cloud makes it cautious instead of blind.

**Keeping it from jittering or getting stuck**

- Once a turn starts, hold it for at least 0.6 s before re-deciding, so the robot does not flip left and right.
- If the robot has turned or backed up 4 times in 10 s without going forward for 1 s, it is stuck. Switch the turn direction once, and if that fails, `STOP` and flag it.
- Log the rule number that fired for every decision. This makes every strange move explainable afterward.

## 7. Safety and failsafes

The safety gate is a separate, tiny piece of code that runs right before the motors. It exists so that a bug in the decision engine cannot drive the robot into a wall.

| Failsafe | Trigger | Result |
| --- | --- | --- |
| Sensor watchdog | No fresh reading from a sensor for 0.5 s | `STOP` until readings return |
| Loop watchdog | The main control loop misses 3 ticks in a row | Cut motors |
| Hard distance veto | Center under 15 cm and the action moves forward | Override to `STOP` |
| Speed ramp | Any change in wheel speed | Change gradually, not instantly, so the robot does not jerk or tip |
| Action timeout | An action lasts longer than 3 s without a fresh decision | `STOP` |
| Manual kill | Keyboard key, physical button, or a `STOP` command over the network | Cut motors immediately and stay stopped until reset |
| Startup state | Boot or restart | Motors off, robot waits for an explicit start |
| Error rate | VLM errors exceed the limit in section 5 | Sensor-only mode, slower speeds |

**Two things to do before any driving test:** wire a physical power cutoff you can reach by hand, and run the first tests with the wheels off the ground.

**One more rule for disaster settings.** Ultrasonic sensors miss soft, angled, or sound-absorbing surfaces like cloth, foam, and loose rubble. So a reading of "nothing there" is weaker evidence than a reading of "something close." The reader marks a missing echo as `invalid`, not as `far`, and rule 1 treats three invalid sensors as a stop.

## 8. Code structure, config, and logging

The folders follow the boxes in section 3, so each piece is easy to find, replace, and test.

```text
robot/
  config/
    default.yaml          # thresholds, rates, pins, provider choice
  prompts/
    scene_v1.txt          # the VLM prompt, versioned with the schema
  src/robot/
    types.py              # Frame, SceneReport, Snapshot, Action (shared data shapes)
    state.py              # WorldState (thread-safe, timestamps)
    hardware/
      sensors.py          # real ultrasonic reader
      camera.py           # real GoPro source
      motors.py           # real motor driver
    fakes/
      sensors.py  camera.py  motors.py   # replay and print-only versions
    vlm/
      base.py             # VLMProvider interface
      moondream.py  gemini.py            # one small file per provider
      client.py           # timeouts, retries, error counting
      validate.py         # schema check
    brain/
      decide.py           # decide(snapshot) -> Action (pure)
      safety.py           # gate(action, snapshot) -> Action
    app.py                # starts the workers and the control loop
    logging.py            # writes the run log
  tests/
    test_decide.py  test_safety.py  test_validate.py
  tools/
    replay.py             # run a saved log through the brain
```

**Config.** One YAML file holds every number that might need tuning (distances, rates, timeouts, speeds, pins, which provider, real or fake hardware). Nothing is hard-coded, so you tune at the test site without editing code.

**Logging.** Every control tick writes one line to a `.jsonl` file: time, the sensor values, the latest scene report and its age, the rule that fired, the action chosen, and the action after the safety gate. Frames are saved to disk every few seconds, tagged with the tick number. This log is the most valuable thing in v1: it lets you replay any run, debug strange moves, and later build training or test data.

**Shared data shapes.** `Frame`, `SceneReport`, `Snapshot`, and `Action` live in one file and every component uses them. Later features add fields to these instead of inventing their own formats.

## 9. Testing

You can test most of v1 on a laptop before the robot exists, in three layers.

1. **Unit tests on the brain.** Feed `decide()` and `gate()` hand-made snapshots and check the action. Every row in the section 6 table becomes at least one test, plus edge cases: stale data, all sensors invalid, VLM offline, conflicting sensor and VLM input.
2. **Validator tests.** Feed the validator good JSON, missing fields, wrong values, extra text around the JSON, and empty replies. Only good JSON should pass.
3. **Replay tests.** Run a saved `.jsonl` log through the brain with `tools/replay.py` and check that it makes the same decisions, or see how a rule change would have changed them.

**Hardware bring-up checklist.** Do these in order and do not move on until each passes.

- [ ] Each sensor reads a known distance correctly (tape measure, three distances), with the voltage divider in place.
- [ ] All three sensors run in turns with no crosstalk (readings stay steady when all are on).
- [ ] Pi receives frames from the GoPro at a steady rate; save 20 frames and look at them.
- [ ] Cloud VLM returns valid JSON for 20 saved frames, and you record the average round trip time.
- [ ] Motors spin the right way for each action, wheels off the ground.
- [ ] Manual kill and the physical power cutoff both work.
- [ ] Robot drives toward a wall and stops or turns before touching it, at slow speed first.
- [ ] Turn off Wi-Fi mid-run: robot drops to sensor-only mode and keeps its safe behavior.
- [ ] Cover a sensor: robot stops on the stale or invalid rule.
- [ ] Five-minute run in a cluttered area with the full loop.

## 10. Build order

Build the brain first with fake inputs, then plug in real hardware one piece at a time. This way the riskiest and most valuable part is finished early, and hardware problems cannot block it. I do not know your hackathon length, so this is ordered by dependency, and the split between people is a suggestion.

| Step | What to build | Done when | Who |
| --- | --- | --- | --- |
| 1 | Shared types, config loader, world state, logging | Fake data can be written to and read from the state and appears in the log | Software |
| 2 | `decide()`, `gate()`, and their unit tests | All rule tests pass with fake snapshots | Software |
| 3 | Fake sensors, fake camera, fake motors, and `app.py` wiring | The full loop runs on a laptop and prints sensible actions | Software |
| 4 | VLM provider, client, validator, prompt | 20 saved images give valid reports, and round trip time is measured | Software |
| 5 | Real sensor reader (parallel with 4) | Bring-up checks for sensors pass | Hardware |
| 6 | Real GoPro frame source (start early, this is the riskiest part) | Steady frames arrive on the Pi | Hardware |
| 7 | Real motor layer plus kill switch | Each action moves the robot correctly, wheels off the ground | Hardware |
| 8 | Integrate on the robot at slow speed | Section 1 definition of done | Everyone |
| 9 | Tune thresholds from the logs | Fewer stops and stuck events per run | Everyone |

**Start step 6 first, on day one.** The GoPro over USB is the most uncertain piece. If it does not work in about an hour, switch to the Wi-Fi preview stream or a cheap USB webcam so the rest of the project is not blocked. Everything else in the design does not care where the frames come from.

## 11. Beyond v1

Every planned feature should plug in through one of five doors that v1 already has: a new worker that writes to the world state, a new field in the shared data shapes, a new action, a new rule, or a new provider behind an interface. Nothing on this list needs the v1 brain to be rewritten.

| Feature | How it plugs in | What v1 already provides | What to add later |
| --- | --- | --- | --- |
| Local VLM on the Pi (or a small accelerator) | A new `VLMProvider` file that runs the model on the robot | Provider interface, validator, timeouts, offline mode | A local provider, plus a rule for cloud first and local as backup. Keep the schema small since local models are slow |
| Voice: hearing people | A speech-to-text worker that writes `operator_command` (for example "stop", "come here") into world state | World state with timestamps, one safety gate that everything passes through | A mode layer that reads commands. Voice can request a move but can never bypass the safety gate |
| Voice: talking to people | A second output channel next to movement, `SPEAK(text)`, triggered by rules such as "person seen near" | Rule 5 already detects a nearby person and raises a flag | A speaker worker and text-to-speech. Speech is separate from movement so it never touches the motors |
| Mapping | A mapping worker that turns movement plus sensor readings into a grid map stored in world state | The log already records every action, time, and sensor reading, so movement can be estimated and replayed | Wheel encoders or an IMU (a motion sensor), because without them the map drifts. A rule that prefers unexplored directions |
| Finding and helping people | A mission mode such as "search": explore, then approach and hold near a person | `people` field in the scene report, the fixed action list | A mode layer above the rules, and a way to mark where people were found on the map |
| Better distance sensing | New readings added to the sensor snapshot (lidar or depth camera) | Sensors are already hidden behind one reader and a snapshot | Update rules 2, 3, and 7 to use the richer data |
| Remote view and control | A small web server that reads world state and can send `STOP` or a mode change | The log format, the kill switch, and the one-object world state | A status page showing the camera, sensors, and the rule that fired |
| More than one robot | Each robot runs the same stack and shares scene reports and map data | Schema version number and shared types | A shared map and a coordinator that assigns areas |

**The one addition worth planning now: a mode layer.** V1 has a single behavior, explore. Later features need more (search, hold near a person, return home, follow a voice command). The clean way is to put a small `mode` value in the world state and have `decide()` pick a rule set based on it. Rules 1 to 3 (the safety rules) apply in every mode. In v1, the mode is always `explore`, so this costs almost nothing but saves a rewrite.

**Keep these habits from day one** so later features stay easy: never let any worker talk to the motors except through the safety gate, put every tunable number in config, log every decision with the rule that fired, and bump the schema version whenever the VLM contract changes.

## 12. Risks and open questions

| Risk | Why it matters | Plan |
| --- | --- | --- |
| GoPro stream on the Pi does not work or lags | It is the only camera and no confirmed recipe exists for HERO12 or HERO13 on a Pi | Test on day one. Fallbacks: Wi-Fi preview stream, then a USB webcam |
| VLM round trip is slower than 2 to 4 seconds | Robot reacts to old information | Small images, short prompt, small model, and the sensors handle close calls. Measure real times in step 4 |
| Venue Wi-Fi is unreliable | Cloud VLM drops out | Phone hotspot, and the sensor-only mode is already designed in |
| Ultrasonic sensors miss soft or angled surfaces | Robot could drive at rubble or cloth | Treat missing echoes as invalid, use the VLM as a second opinion, and keep speeds low |
| VLM gives confident wrong answers | A wrong "clear" could be dangerous | The VLM can only slow or steer the robot, never speed it past what sensors allow, and rule 8 needs sensors to agree |
| Motor power and noise cause sensor glitches | Random false readings | Separate power for motors and the Pi, filter readings, keep sensor wires short |
| Pi overheats | Slowdowns or crashes | Heatsink and airflow, and keep VLM work off the Pi in v1 |

**Questions to answer before or during the build**

- [ ] Which exact GoPro model is it, and does it show up as a network device or webcam when plugged into the Pi?
- [ ] Is the Pi a 4 or a 5, and what motor driver board is being used?
- [ ] Which cloud VLM to start with? I would suggest starting with one that supports structured output and comparing a second one if time allows.
- [ ] Does the target behavior for the demo mean exploring an area, following a path, or finding a person or hazard? This decides which rules to polish first.
- [ ] What is the demo environment (indoor, floor type, lighting), so we can pick sensible starting thresholds?
- [ ] Who is on the hardware side and who is on the software side?
