# Scoutbot Manual Control Spec

Status: draft v0.1, 2026-09-27
Scope: driving the robot by hand (takeover from AUTO), Raspberry Pi 4, four DC motors.
Repo: `heheheha` (branch `agent/robot`). Files named below are relative to the repo root.

## 1. What this is, in plain words

Scoutbot normally drives itself. A human should be able to say "I've got it", take over, and steer the robot smoothly with a keyboard, a phone, or a game controller. When they let go, or anything goes wrong, the robot stops.

Most of the plumbing already exists. This spec is about making it good enough to drive a real robot by hand, and about doing it safely.

## 2. What already exists (from reading the code)

| Piece | Where | What it does today |
| --- | --- | --- |
| Modes | `scoutbot/safety/modes.py` | `STOPPED`, `AUTO`, `MANUAL`. Boots into `STOPPED`. E-stop goes to `STOPPED` from anywhere. |
| Drive command | `scoutbot/server/app.py`, `scoutbot/runtime.py` (`command`) | Dashboard sends `{"type":"drive","action":"FORWARD"...}` every 100 ms over the WebSocket. Only accepted in `MANUAL`. |
| Command expiry | `scoutbot/safety/deadman.py` (`manual_action`) | A drive command dies 0.3 s after it arrives. Let go of the key, the robot stops. |
| Link watchdog | `link_check` | No WebSocket message for 0.5 s in `MANUAL` (2 s in `AUTO`) means `STOPPED`. |
| Motor watchdog | `MotorWatchdog` | If nothing has fed the motors for 0.5 s, it forces stop and keeps re-sending stop. |
| Safety gate | `scoutbot/safety/gate.py` | Last check before the motors in every mode. Blocks forward under `stop_cm`, caps to slow near obstacles, blocks turns toward a near wall, limits reverse to 1.5 s bursts (no rear sensor). |
| Ramp | `scoutbot/hw/base.py` (`Ramp`) | Smooths wheel speed over 0.15 s. Stop is instant. |
| Motors | `scoutbot/hw/motors_l298n.py` | L298N driver via `gpiozero`. Left side on channel A, right side on channel B (two motors per side wired together). |
| Dashboard | `scoutbot/server/static/responder.html` | "Take control" button, WASD/arrows, Shift = slow, Space = STOP, on-screen pad. |
| Bench tool | `scoutbot/tools/motor_check.py` | Steps each action with wheels off the ground. |

Today's manual control is "one of five buttons": `FORWARD`, `FORWARD_SLOW`, `TURN_LEFT`, `TURN_RIGHT`, `BACK_UP`, at fixed speeds from `config/profiles/base.yaml` (`speeds:`). It cannot go faster or slower smoothly, cannot curve while moving, and has no controller support.

Facts that matter for this work:

- Only the control loop (`Runtime.control_tick`) may call `Motors.apply()`. A regression test enforces this. Keep that rule.
- `config/profiles/pi.yaml` has no real GPIO pins yet. `base.yaml` pins are placeholders. STATUS.md says Robot is blocked on actual pins, battery voltage, and sensor type.
- The repo has extra folders (`scoutbot-a`, `-b`, `-c`, `-cloud`). They are untracked copies. Edit the top-level `scoutbot/` only.

## 3. A conflict we must decide on

The safety docs say the opposite of what the dashboard does today:

- `REQ-SEC-001` / `HZ-012`: remote interfaces may only show status and send STOP. No remote non-stop motion.
- `REQ-ACT-001` / `REQ-MOT-004`: no reverse, ever, in V1.
- `REQ-MOT-001`: max 0.10 m/s.
- `REQ-ESTOP-001..003`: a physical, hardwired, latching E-stop is mandatory before any moving test.

The current `MANUAL` mode already breaks the first two. Manual takeover therefore needs a deliberate, written amendment, not a quiet code change.

Recommendation: treat manual drive as an operator-in-the-loop tele-op mode with these conditions, and record it as a documented deviation (`docs/safety/`, new `DEC-` entry):

1. Physical E-stop present and tested before any floor driving.
2. A local arm switch (see section 8) has to be on for `MANUAL` to accept drive commands.
3. Robot stays inside the existing gate rules (obstacle stop, stale sensor stop, speed caps).
4. Reverse is allowed only slowly and in short bursts (existing gate behaviour).

Decision needed from Matthew: accept this amendment, or keep manual drive bench-only until the safety docs are updated.

## 4. Goals and non-goals

Goals

- Take over from `AUTO` with one press, with no lurch.
- Smooth analog driving: speed and steering both continuous.
- Three input types, one command format: keyboard, phone touch joystick, gamepad.
- A fallback that works over SSH on the Pi with no dashboard (bring-up and network trouble).
- Everything stops safely when the operator lets go, the link drops, or a sensor fails.
- Fully testable on the `sim` profile and with `FakeMotors` before touching hardware.

Non-goals (for this version)

- Bypassing the safety gate. There is no "override obstacle stop" button.
- Autonomy changes. The brain keeps running in the background ("brain would do X") but does not drive.
- Per-wheel independent control (mecanum, crab steering). See open questions.
- Wheel encoders / closed-loop speed. Speed is open-loop PWM for now.
- Internet control. Same Wi-Fi or hotspot only.

## 5. Hardware

Raspberry Pi 4, four DC motors. The current design (`motors_l298n.py`) runs them as two sides of a tank-style (skid-steer) robot:

```
Pi GPIO --> L298N channel A --> left motors  (front-left + rear-left, wired in parallel)
Pi GPIO --> L298N channel B --> right motors (front-right + rear-right, wired in parallel)
```

Per side the Pi needs three signals: `fwd`, `back`, and `en` (enable/PWM). Config keys are `hw.pins.left.{fwd,back,en}` and `hw.pins.right.{fwd,back,en}`. Placeholder values in `base.yaml`: left 5/6/12, right 13/19/18.

Things to confirm on the real robot (the linked chat may already have these; see section 12):

- Motor type and stall current. Two small TT motors per channel can pull more than an L298N's 2 A per channel at stall. Fine for light driving, hot if the robot is pushed against a wall.
- Battery voltage. The L298N drops about 2 V. Low battery voltage means slow, weak motors. Brownouts can also reset the Pi.
- Separate power for the Pi and for the motors, with a shared ground.
- Which side is which, and whether either side spins backward. Section 6 adds `invert_left` / `invert_right` settings so this is a config change, not a rewiring.
- Wire the physical E-stop so it cuts motor power or the L298N enable lines, independent of the Pi.

## 6. Drive model

### 6.1 Command

The operator input is two numbers, each from -1.0 to 1.0:

- `v`: speed. +1 full forward, -1 full reverse.
- `w`: turn. +1 turn right, -1 turn left.

### 6.2 Mixing (new module `scoutbot/control/mix.py`, pure function, easy to test)

```
apply deadzone (default 0.08): values under it become 0
apply expo curve (default 0.3): finer control near center
left  = v + w
right = v - w
if max(|left|, |right|) > 1: divide both by that max   # keeps the turn ratio
scale by speed cap (see below)
apply trim_left / trim_right and invert flags
```

Speed caps (config `manual:` section, new):

| Setting | Default | Meaning |
| --- | --- | --- |
| `max_forward` | 0.60 | Same as today's `FORWARD` |
| `slow_factor` | 0.58 | Shift / "slow" toggle (about today's 0.35) |
| `max_reverse` | 0.35 | Same as today's `BACK_UP` |
| `max_turn_in_place` | 0.45 | Same as today's turns |
| `deadzone` | 0.08 | |
| `expo` | 0.30 | |

The existing `Ramp` (0.15 s) still smooths every change. Reversing direction still passes through zero first.

### 6.3 PWM notes

`gpiozero.Motor` with `pwm=True` puts PWM on the `fwd`/`back` pins and treats `en` as on/off. On a Pi 4, install `lgpio` (already in `requirements-pi.txt`). Default PWM is 100 Hz; if motors whine or feel weak at low speed, try a higher frequency in a bench test. Very low duty cycles will not move the robot (motors have a minimum "start" power); add `min_start` (default 0.15) so any nonzero command is at least that strong, and zero stays zero.

### 6.4 Four motors, two channels

V1 keeps side-paired control (section 5). If the four motors turn out to be wired to independent channels (two L298N boards), add an optional `hw.motors: l298n4` driver that takes `fl`, `fr`, `rl`, `rr` pins and a `layout: skid` setting so the same `(left, right)` output feeds both motors on a side. Nothing else in this spec changes.

## 7. Software design

### 7.1 Data flow

```
keyboard / touch / gamepad          (dashboard, or `drive` CLI on the Pi)
        |  WebSocket, 20 Hz: {type:"drive", v, w, seq}
        v
Runtime.command()                   validate, clamp, store DriveCommand
        v
control_tick() (10 Hz today)        mode == MANUAL?
        v
manual_wheels(cmd)                  expired? -> (0, 0)
        v
mix()                               (v, w) -> (left, right)
        v
Gate.check_analog()                 obstacle / stale sensor / reverse rules
        v
Motors.apply_wheels(left, right)    ramp -> PWM
        v
MotorWatchdog.fed()
```

### 7.2 Changes by file

- `scoutbot/types.py`: `DriveCommand` gets optional `v: float` and `w: float` (both default `None`). If `action` is given and `v`/`w` are not, the old button behaviour still works (backward compatible with the current dashboard and tests).
- `scoutbot/control/mix.py` (new): `mix(v, w, cfg) -> (left, right)`. No hardware imports.
- `scoutbot/safety/deadman.py`: `manual_wheels(cmd, now, valid_s)` returns `(v, w)` or `(0, 0)` when the command is missing or older than `manual_cmd_valid_s`.
- `scoutbot/safety/gate.py`: add `check_analog(...)`. It reuses the same thresholds in continuous form:
  - center under `stop_cm`: forward part of `v` becomes 0.
  - center between `stop_cm` and `slow_cm`: forward `v` scales down linearly to the slow speed.
  - turn toward a side under `side_near`: `w` toward that side becomes 0.
  - reverse: capped at `max_reverse`, and the existing 1.5 s on / 0.5 s rest burst rule applies.
  - stale sensors or no echo on all sensors: everything 0.
  - returns `(v, w, veto_reason)`.
- `scoutbot/hw/base.py`: add `apply_wheels(left, right)` to the `Motors` protocol. `apply(action)` stays and calls it. Fake and L298N drivers implement it.
- `scoutbot/hw/motors_l298n.py`, `motors_fake.py`: implement `apply_wheels`, plus `invert_left` / `invert_right` and `min_start`.
- `scoutbot/runtime.py`: `command("drive")` accepts `v`/`w`; `control_tick` MANUAL branch uses the new path; state adds `manual` block (see 7.4). Extend the "only the control loop calls the motors" regression test to cover `apply_wheels`.
- `scoutbot/safety/modes.py`: takeover handshake (7.3).
- `scoutbot/server/static/responder.html`: touch joystick, Gamepad API, speed-limit slider, on-screen "neutral first" hint.
- `scoutbot/tools/drive.py` (new): terminal driver for the Pi (section 8.3).
- `config/profiles/base.yaml`: new `manual:` section (defaults above). `pi.yaml`: real pins, inverts, trims once measured.
- `scoutbot/tools/motor_check.py`: add `--manual` to sweep `v` and `w` values and print wheel outputs.

### 7.3 Takeover and hand-back

Takeover (`AUTO` or `STOPPED` to `MANUAL`):

1. Operator presses "Take control" (or a gamepad button).
2. Robot brakes to zero (instant stop through the normal stop path; the brain stops driving immediately).
3. Mode becomes `MANUAL`, but drive commands are ignored until the operator sends one neutral command (`v` and `w` both within the deadzone). This prevents the robot lunging because a key or stick was already held.
4. Then normal driving starts.

Hand-back:

- "Release control" goes to `STOPPED`, not straight to `AUTO`. Resuming auto needs a separate, deliberate press of Start auto. (Matches the existing rule that leaving `STOPPED` needs an explicit press.)
- The dashboard shows "brain would do X" while in `MANUAL`, as it does today, so the operator can see what auto would have done.

E-stop and STOP work in every mode and win every race.

### 7.4 State the dashboard receives

Add to `Runtime.state()`:

```
"manual": {
  "armed": true,
  "neutral_seen": true,
  "cmd": {"v": 0.4, "w": -0.1, "age": 0.04},
  "wheels": [0.31, 0.44],
  "veto": "capped at slow: center 52 cm"
}
```

## 8. Operator interfaces and transport

### 8.1 Protocol

Same WebSocket as today (`/ws`, port 8000, optional `?token=`). New message:

```
{"type":"drive","v":0.42,"w":-0.10,"seq":1234}
```

- Sent at 20 Hz while an input is active. Keep sending zeros (or STOP) when idle so the link stays healthy.
- Server rules: `v` and `w` must be finite numbers; clamp to [-1, 1]; reject anything else with `{"ok":false,"error":...}`; ignore `seq` lower than the last one seen; any message still counts as a heartbeat but only `drive` keeps wheels moving (existing rule).
- Old `{"type":"drive","action":...}` messages keep working.

### 8.2 Inputs

- Keyboard: W/S set `v` toward +1/-1, A/D set `w`. Ramp the client-side value (about 0.25 s to full) so keys feel smooth. Shift = slow. Space = STOP (existing).
- Phone / touch: on-screen virtual joystick using pointer events (same approach as the existing pad). Release = center = zero.
- Gamepad: browser Gamepad API (works with USB or Bluetooth controllers on a laptop). Left stick = `v`/`w`, a shoulder button = slow, a face button = STOP, another = take/release control. If the gamepad disconnects or the tab loses focus, send zeros.

All three release to neutral when the tab is hidden or loses focus (the current code already does this for keys).

### 8.3 Local fallback on the Pi (`python -m scoutbot.tools.drive`)

A terminal program that connects to the running server at `localhost:8000` and sends the same `drive` messages from the keyboard (WASD, space = stop, q = quit). Purpose: bring-up over SSH, and driving when the dashboard is unreachable. Because it runs on the Pi it also counts as "local", which is useful for the arm rule below.

### 8.4 Arm switch

To support the safety recommendation in section 3, add `manual.require_arm` (default true on the `pi` profile, false on `sim` and `laptop`). "Armed" means a physical toggle switch on a Pi GPIO input (`manual.arm_pin`) is on. If not armed, `MANUAL` mode can be entered but drive commands are ignored and the dashboard says why. Turning the switch off at any time stops the robot. This is separate from, and does not replace, the hardwired E-stop.

### 8.5 Test from the responder's own computer

This is a required pre-hardware demo, not an optional developer exercise. A host computer runs a safe synthetic room and the responder uses a separate computer or phone on the same Wi-Fi, exactly as they will when the Pi is available.

1. On the host, start the LAN-only fake-robot profile:

   ```bash
   python -m scoutbot --profile sim-remote
   ```

   This profile is deliberately `synthetic` camera, `simworld` sensors, and `fake` motors. It never touches GPIO or physical motors.
2. On macOS, get the host's Wi-Fi address with `ipconfig getifaddr en0` (or use the address shown by the router). On Linux use `hostname -I`.
3. On the responder's computer or phone, browse to `http://<host-ip>:8000`, press **Take control**, leave all controls neutral for one heartbeat, then hold WASD/arrows or the on-screen pad. It works in any current desktop or mobile browser.
4. Confirm diagonal commands curve in the simulated map, release stops immediately, and closing the tab changes the mode to `STOPPED` within 0.5 s. Use the dashboard STOP button before ending the test.

`sim-remote` listens on the LAN so it must only be used on a trusted local network. Do not port-forward it. A real robot must also use `SCOUTBOT_TOKEN` and the physical E-stop / arm requirements in this document.

## 9. Safety summary

Independent layers, any one of which stops the robot:

1. Physical latching E-stop (hardware, no software involved). Required before floor tests.
2. Software STOP / E-stop button and Space key (all modes).
3. Command expiry: 0.3 s without a fresh `drive` message means zero. Heartbeats do not keep it moving.
4. Link watchdog: 0.5 s of silence in `MANUAL` means `STOPPED`.
5. Motor watchdog: 0.5 s without the control loop feeding the motors means forced stop.
6. Safety gate: obstacle, stale sensor, side, and reverse limits, always on.
7. Arm switch (section 8.4).
8. Speed caps and ramp, so a full-stick command is still gentle.
9. Process exit or crash: `atexit` stop (exists) plus watchdog.

Rules for changes: no new code path may call the motor driver except the control loop; any exception in the tick already stops the motors (keep that).

## 10. Implementation plan

Do these in order. Each step is testable without the next one.

| # | Step | Where it runs | Done when |
| --- | --- | --- | --- |
| M0 | Get the facts: real pins, battery voltage, driver board, motor wiring. Fill `pi.yaml`. | Robot | `motor_check --profile pi` moves each side the right way (wheels off ground). Invert flags set if not. |
| M1 | `mix()` + unit tests. | Laptop | Table tests pass (section 11). |
| M2 | `DriveCommand` v/w, server validation, `apply_wheels` on fake and L298N, config `manual:`. | Laptop (`sim`) | Sim robot follows analog input; old button commands still pass existing tests. |
| M3 | `Gate.check_analog` + tests. | Laptop | Analog obstacle tests pass; old gate tests unchanged. |
| M4 | Takeover handshake, hand-back rules, `manual` state block. | Laptop | Mode-transition tests pass. |
| M5 | Dashboard: keyboard smoothing, touch joystick, gamepad. | Laptop + phone | Drive the sim from all three. |
| M6 | `tools/drive.py` and `motor_check --manual`. | Pi | Wheels-off-ground sweep matches expected outputs. |
| M7 | Arm switch and physical E-stop verified. | Robot | Switch off = wheels stop within 100 ms; E-stop works with the Pi unplugged. |
| M8 | Floor tests, tune caps, deadzone, trims, ramp. Record in `docs/scoutbot/robot.md`. | Robot | Straight line stays straight; stop distance measured. |
| M9 | Safety-docs amendment (`DEC-` entry, hazard log update). | Docs | Reviewed and merged. |

Suggested branch: `agent/manual-control` off `agent/robot` (or off `main` once robot work is merged). Update the Robot section of `docs/scoutbot/STATUS.md` on each merge, as the repo rules require.

## 11. Test plan

Automated (`python -m pytest -q tests`, runs on a laptop):

- Mixing: `(1,0)` gives `(1,1)`; `(0,1)` gives `(1,-1)` scaled to the turn cap; `(1,1)` normalizes without changing the turn ratio; deadzone edge cases; expo curve monotonic; trim and invert applied last.
- Validation: NaN, infinity, strings, out-of-range values rejected or clamped; out-of-order `seq` ignored.
- Expiry: command older than 0.3 s gives zero; heartbeat alone gives zero.
- Takeover: drive commands ignored until a neutral one arrives; hand-back goes to `STOPPED`; E-stop from every mode.
- Gate (analog): center under `stop_cm` zeroes forward; scaling between `stop_cm` and `slow_cm`; side-turn block; stale sensors give zero; reverse burst limit; reverse cap.
- Architecture: only the control loop and the bench tool call `apply` / `apply_wheels`.
- Regression: all 144 existing tests still pass; 20 s `sim` headless run shows 0 watchdog trips.

Bench (wheels off the ground):

- `motor_check --profile pi` and `--manual`: each side spins the correct direction at each step; PWM output matches the printed values.
- Kill Wi-Fi (or close the browser tab) while driving: wheels stop within 0.5 s.
- Kill the Python process: wheels stop (watchdog / `atexit`).
- Unplug the ultrasonic sensors: forward stops.
- Arm switch off while driving: stop.
- E-stop with the Pi powered off: wheels cannot move.

Floor:

- Straight-line drift (tune `trim_left` / `trim_right`).
- Stop distance from each speed (record it; the safety docs need it).
- Obstacle approach at low speed toward a soft wall, operator holding full forward.

## 12. Open questions

1. Safety amendment (section 3): accept manual tele-op as a documented deviation, or bench-only for now?
2. Motor wiring: are the four motors paired per side on one L298N (as the code assumes), or on two boards with independent control? What driver is actually on the robot?
3. Battery: voltage and chemistry? (Sets real top speed and whether the L298N drop matters.)
4. Sensors on the real robot: HC-SR04 or ToF, and current GPIO pins?
5. Arm switch: is a toggle switch on a GPIO acceptable on this build, or should the E-stop be the only hard control?
6. Reverse: keep the 1.5 s bursts, or forbid reverse in manual until a rear sensor exists (safer, matches `REQ-MOT-004`)?
7. Which input do you want first: keyboard, phone joystick, or gamepad? (Plan builds keyboard first, since it already exists.)
8. The linked chat session (`session_01DcvrfnDMbvk2teuDzGTpZ5`) could not be opened from here, so anything decided there is not in this spec. Paste its key points (pins, wiring, battery, decisions) and section 5 and the open questions get updated.
