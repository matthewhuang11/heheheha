# V1 Bench Procedures

## Common controls

These procedures support L0/L1 only. They do not authorize moving tests. Follow the baseline requirements and ODD in `../requirements/`. For powered work, use a stable support with wheels clear or prevent translation mechanically; keep an independent safety observer at the hardwired, latching E-stop; use the lowest configuration within the 0.10 m/s and 0.35 rad/s caps; start logging before energizing; and abort on unexpected motion, unavailable E-stop, missing logs, heat/smell/smoke/arcing, battery concern, damage, or uncertainty.

No test may validate autonomous reverse. `BACK_UP` shall be rejected to `STOP`. Baseline VLM/camera loss shall enter `VLM_FAULT` and `SAFE_STOP`, not sensor-only continuation. The latter is an exception only under written REQ-VLM-006 authorization.

## BP-01: Offline architecture, truth tables, validator, and replay

**Requirements:** REQ-ARC-001, REQ-ACT-001, REQ-MOT-004 to REQ-MOT-008, REQ-CTL-002, REQ-VLM-001 to REQ-VLM-004, REQ-LOG-003. **Planning IDs:** SYS-001, SYS-003, SYS-005, SAFE-004, SAFE-010, SAFE-011, SW-002 to SW-008, DATA-001, TEST-001 to TEST-004.

1. Run fake-motor tests proving only the safety gate emits a permit and all external action requests are limited to `STOP`, `FORWARD`, `FORWARD_SLOW`, `TURN_LEFT`, and `TURN_RIGHT`.
2. Test attempted `BACK_UP`, negative speed, permit bypass, stale/missing/invalid channel, and VLM command-like text. Record `STOP`/rejection outcomes.
3. Test every forward/turn boundary: valid/fresh all three channels, 25/40/60 cm distances, 6 s report/frame age, person visible, blocked/semantic hazard, ignored `best_direction` turn suggestions, and four turns in 10 s without 1 s forward travel.
4. Use corpus cases for exact valid schema, extra text, missing/unknown enum/type, empty input, invalid JSON, invalid timestamps, and altered notes. Only exact valid current schema passes; notes do not decide.
5. Replay one retained `.jsonl` input twice with identical configuration and compare intended action, gated action, permit, state, and veto/rule on every tick.

**Pass:** all expected outcomes match and two replay outputs are identical. Any mismatch, direct motor interface, reverse acceptance, or missing evidence fails.

## BP-02: Sensor calibration, validity, timing, and crosstalk

**Requirements:** REQ-SEN-001 to REQ-SEN-006. **Planning IDs:** SAFE-001, SAFE-002, SAFE-009, HW-001, TEST-005.

1. Inspect voltage dividers before energizing Echo inputs.
2. For left, center, right channels, measure three target distances spanning 25–100 cm. Record actual, filtered, raw where available, validity, timestamp, and absolute error. Each error shall be at most 5 cm.
3. Operate all channels in normal sequential order for at least 60 s. Record per-channel publication timing, validity, and deviation. Each valid channel publishes at least once per 250 ms; crosstalk causes neither invalid result nor deviation above 5 cm.
4. Inject missing echo, out-of-range, failed filter, and stopped/non-monotonic timestamp. Each must become invalid, latch the applicable sensor fault, and prevent a motion permit. It shall not become far or a retained good value.

**Pass:** all stated numeric criteria pass. Any one failed channel excludes the robot from motion testing.

## BP-03: Camera acquisition and retention

**Requirements:** REQ-CAM-001, REQ-LOG-001, REQ-LOG-003. **Planning IDs:** HW-002, DATA-003.

Capture and retain 20 sequential timestamped frames without selecting only successes. Record source, configuration, capture time, tick correlation, storage location, and corruption/drop events. Simulate a six-second camera stall or bad timestamp and show VLM unusable state followed by `VLM_FAULT` and `SAFE_STOP`.

**Pass:** 20 inspectable, correlated frames and correct fault behavior. A camera failure cannot support continued baseline motion.

## BP-04: VLM contract, timeout, and fault handling

**Requirements:** REQ-VLM-001 to REQ-VLM-005. **Planning IDs:** SAFE-008, SW-001, SW-002, DATA-001, DATA-004, TEST-002.

1. Record provider, prompt/schema revision, frame and receipt timestamps, configuration, and raw response identifiers for 20 saved frames.
2. Verify only exact schema-valid reports are usable. Verify free-text notes do not affect decision.
3. Simulate elapsed request time greater than 4.0 s, stale report/frame age greater than 6.0 s, malformed result, and three consecutive request failures.
4. For each case, retain state transition and motor-permit result. Baseline result is `VLM_FAULT` and `SAFE_STOP`.

**Pass:** all invalid/late/unusable conditions stop and latch as required. Round-trip min/max/mean may be recorded as characterization only.

## BP-05: Raised-wheel motor, permit, watchdog, and E-stop test

**Requirements:** REQ-MODE-001 to REQ-MODE-002, REQ-MOT-001 to REQ-MOT-003, REQ-MOT-007, REQ-CTL-001, REQ-ESTOP-001 to REQ-ESTOP-004. **Planning IDs:** SAFE-003 to SAFE-007, HW-003, HW-004, SW-005, SW-006.

1. Verify boot/reset/fault state is `SAFE_STOP`, no motion occurs, and explicit local start is required. Measure/log display and log state transition no later than 250 ms.
2. For each permitted action, capture wheel direction, maximum commanded speed, and ramp response. Verify translation is at most 0.10 m/s, turn at most 0.35 rad/s, and measured acceleration at most 0.20 m/s² / 0.50 rad/s².
3. Measure the actual hardwired E-stop actuator to motor-driver energy-removal interval. It shall be at most 100 ms, remain latched, and not restart after reset without physical reset plus local explicit start.
4. Inject absent/expired/malformed permit and invalid state. Motor layer shall command zero within 100 ms. Verify permit age is no more than 150 ms.
5. Inject three missed 50 ms deadlines, gate exception, and an unrenewed 500 ms non-stop action. Each produces safe stop/fault.

**Pass:** every numeric/timing limit passes on actual motor path. E-stop failure is a critical failure: stop all powered tests.

## BP-06: Fault injection and safe state

**Requirements:** REQ-SEN-004 to REQ-SEN-005, REQ-VLM-005 to REQ-VLM-006, REQ-CAM-001, REQ-CTL-001. **Planning IDs:** SYS-004, SAFE-001, SAFE-002, SAFE-008, SW-001, SW-004, SW-007.

Inject each stale/invalid sensor channel, snapshot failure, VLM timeout/malformed response/network loss, camera stall, and control deadline fault. Record the applicable `SENSOR_FAULT`, `VLM_FAULT`, or `CONTROL_FAULT`, safe-stop state, log event, and inability to issue a permit. Do not perform sensor-only motion as part of this baseline test.

A sensor-only exception test requires the separate written authorization specified in REQ-VLM-006, including flat dry bounded obstacle-free area, no listed hazards/people, 0.05 m/s cap, direct operator within 2 m, and immediate stop on any fault.

## BP-07: Semantic-input reduction test

**Requirements:** REQ-SCP-002, REQ-VLM-004. **Planning IDs:** SYS-003, SAFE-010, SW-003.

Use prevalidated fixtures, not people or real hazards. Test person visible at every reported distance and blocked, partially blocked, stairs/drop, fire, smoke, water, wire, glass, drop-off, and unstable-debris reports. Each must only reduce authority to `STOP` or, where other requirements permit, `FORWARD_SLOW`; a person result must stop, latch, and require acknowledgement.

## BP-08: Log and replay package

**Requirements:** REQ-LOG-001 to REQ-LOG-003. **Planning IDs:** DATA-002, DATA-003, TEST-003.

For a 60 s representative interval, verify every gate evaluation records monotonic timestamp, state, each sensor value/validity/age, camera/VLM age/status, intended and gated action, permit outcome, rule/veto, active faults, E-stop state, and 50 ms-or-better event ordering. Preserve immutable raw log, frames, configuration, provider/prompt/schema identity, and two replay results.
