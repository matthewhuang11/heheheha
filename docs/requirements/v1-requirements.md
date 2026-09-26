# V1 System Requirements

**Document ID:** DRR-V1-REQ
**Revision:** 1.0
**Status:** Baseline for controlled, supervised field-test research
**Applies to:** the V1 differential-drive research robot described in `disaster-response-robot-v1-spec.md`

## 1. Purpose, safety position, and conventions

V1 is a supervised research prototype for evaluating deterministic, sensor-assisted navigation in a controlled test area. It is **not** a certified rescue robot, an emergency-response product, a public-deployment system, or a system permitted to carry, transport, approach, or assist people. Passing these requirements authorizes only the Operational Design Domain (ODD) in `odds-and-constraints.md`.

This document resolves ambiguous or conflicting source-specification statements conservatively. In particular:

- loss, staleness, or invalidity of any required proximity channel results in a motion stop, rather than treating the other channels as sufficient;
- an unavailable, stale, malformed, or untrusted cloud VLM report results in a motion stop in the baseline V1 mode. A tightly constrained, separately approved sensor-only experiment is defined in **REQ-VLM-006**, but is not the normal behavior;
- V1 has no rear-obstacle sensor, so autonomous rearward motion is prohibited;
- the physical emergency stop (E-stop) is a hardwired, latching removal of motor drive energy and cannot depend on software, network, battery telemetry, or cloud services.

A requirement uses **shall** for a mandatory condition. Values labelled **baseline maximum** may be made more conservative in configuration but shall not be increased without revising this document and completing the associated verification again.

### 1.1 Terms

| Term | Meaning |
| --- | --- |
| Valid sensor sample | A sensor value produced by a completed measurement, within the configured physical range, with a successful echo, filter status valid, and a monotonic timestamp. A missing echo is invalid, never “far.” |
| Fresh | The age, measured from the sample timestamp to the safety-gate evaluation time, is no greater than the stated limit. |
| Safety gate | The final, independent software function that receives an intended action and emits only a permitted motor command or `STOP`. |
| Motion permit | A time-bounded output from the safety gate that the motor layer must receive and validate before energizing motors. |
| Safe state | Motor drive energy removed or commanded to zero, no autonomous restart, and a latched stop cause displayed and logged. |
| VLM usable | A report that passes the exact current schema, is from a frame no older than the stated limit, has a known result, and is within its validity age. |
| Operator | A trained test participant assigned to supervise the run and able to activate the physical E-stop immediately. |

## 2. System boundary and modes

| ID | Requirement | Verification |
| --- | --- | --- |
| REQ-SCP-001 | V1 shall operate only in the controlled, supervised research ODD defined in `odds-and-constraints.md`. Software, test procedures, and status displays shall identify the system as “RESEARCH TEST ONLY – NOT FOR RESCUE OR PUBLIC USE.” | Inspection of boot/status text and test procedure. |
| REQ-SCP-002 | V1 shall not autonomously approach, contact, carry, tow, or direct a person. A detected person at any reported distance shall cause `STOP`, latch a person-detected stop indication, and require operator acknowledgement before another start. | Unit test with every valid `people.visible=true` value and observed system test with a person outside the exclusion boundary. |
| REQ-ARC-001 | Only the safety gate shall issue a motion permit to the motor layer. Decision logic, VLM client, network, status UI, logging, and test fakes shall have no direct motor-drive interface. | Static interface inspection and automated architecture test or code search. |
| REQ-ACT-001 | The externally selectable action set shall be limited to `STOP`, `FORWARD`, `FORWARD_SLOW`, `TURN_LEFT`, and `TURN_RIGHT`. `BACK_UP` from the source design shall be rejected by the safety gate as `STOP` in V1. | Unit test each allowed action and attempted `BACK_UP`; interface inspection. |
| REQ-MODE-001 | On boot, reset, E-stop reset, watchdog trip, or any latched safety fault, V1 shall enter the safe state. Motion shall require an explicit local operator start after all active safety faults are cleared. | Bench test each transition and log review. |
| REQ-MODE-002 | The canonical lifecycle shall use only the states in `../interfaces/state-machine.md`: `BOOTING`, `SELF_TEST`, `READY`, `ACTIVE`, `FAILSAFE_LATCHED`, `E_STOP_LATCHED`, and `SHUTDOWN`. The operator display shall show the derived condition `SAFE_STOP` whenever motor enable is disabled, `RUNNING` only during `ACTIVE`, and an accompanying fault indication (`VLM_FAULT`, `SENSOR_FAULT`, or `CONTROL_FAULT`) when applicable. The display and log shall record the canonical state and derived condition within 250 ms of the corresponding transition. | Instrumented fault-injection test and log timestamp comparison. |

## 3. Motion and physical safety requirements

| ID | Requirement | Verification |
| --- | --- | --- |
| REQ-MOT-001 | In the baseline ODD, commanded translational speed shall not exceed **0.10 m/s** and commanded turning shall not exceed **0.35 rad/s**. Configuration shall enforce these maxima. | Configuration inspection and wheel-speed measurement on blocks and on the test surface. |
| REQ-MOT-002 | The motor layer shall apply a bounded speed ramp whose measured acceleration does not exceed **0.20 m/s²** translationally or **0.50 rad/s²** rotationally. A safety stop may bypass the normal ramp to remove drive energy. | Instrumented motor-command and motion measurement. |
| REQ-MOT-003 | Every non-stop motor command shall require a valid motion permit generated no more than **150 ms** before motor-layer acceptance. If a permit is absent, expired, malformed, or from an invalid state, the motor layer shall command zero drive within **100 ms**. | Fault-injection timing test at motor-driver input. |
| REQ-MOT-004 | V1 shall not command or permit negative translational velocity. No configuration setting, VLM response, decision rule, remote message, or replay input may enable reverse motion in V1. A human may reposition a powered-down robot only. | Unit tests, configuration inspection, and hardware command capture. |
| REQ-MOT-005 | Before a forward command is permitted, center, left, and right protective distances shall each be valid and fresh per REQ-SEN-003. Center distance shall be at least **60 cm** for `FORWARD` and at least **40 cm** for `FORWARD_SLOW`. At any distance below **25 cm** in any forward-relevant direction, the safety gate shall issue `STOP`. | Boundary-value unit tests at 15, 25, 40, and 60 cm, plus measured wall approach test. |
| REQ-MOT-006 | Before a turn is permitted, all three protective channels shall be valid and fresh, the center distance shall be at least **25 cm**, and the direction being turned toward shall be at least **25 cm**. Otherwise the safety gate shall issue `STOP`. | Directional boundary tests and physical test with obstacles at each side. |
| REQ-MOT-007 | A continuous non-stop action shall expire after **500 ms** unless re-evaluated and renewed by the safety gate. Independently, no action episode shall remain non-stop for more than **3 s** without a new decision record. Expiry shall produce the safe state. | Simulated time and hardware watchdog tests. |
| REQ-MOT-008 | If four turn attempts occur within 10 s without at least 1 s of forward travel, V1 shall enter `SAFE_STOP` and require operator assessment. It shall not automatically reverse or alternate indefinitely. | Replay and unit test with stuck-event traces. |

## 4. Sensor acquisition, validity, and watchdogs

| ID | Requirement | Verification |
| --- | --- | --- |
| REQ-SEN-001 | V1 shall use left, center, and right ultrasonic readings as three separate protective channels. The reader shall trigger them sequentially and shall record raw result, filtered result, validity, and timestamp for each channel. | Hardware integration test and log inspection. |
| REQ-SEN-002 | The sensor reader shall treat a missing echo, out-of-range value, impossible timestamp, failed acquisition, or filter failure as an invalid sample. It shall not substitute a prior good value, a maximum-range value, or an inferred “clear” value. | Fault-injection unit tests. |
| REQ-SEN-003 | Each protective channel shall publish a valid sample at least once every **250 ms**. A sample is stale at age greater than **500 ms**. The safety gate shall require a valid sample from **each** channel with age no greater than 500 ms for every motion permit. | Timed simulated sensor streams and hardware timing capture. |
| REQ-SEN-004 | The sensor watchdog shall trip if any channel fails to publish a valid sample for more than **500 ms**, if its timestamp stops advancing, or if its data-quality state is invalid at safety-gate evaluation. On trip it shall command `STOP`, latch `SENSOR_FAULT`, inhibit new motion permits, and log the affected channel and reason. It shall not clear merely because other channels remain healthy. | Cover, unplug, stale-timestamp, and malformed-value fault tests. |
| REQ-SEN-005 | The sensor watchdog shall execute independently of VLM calls and shall be evaluated at least **20 Hz**. The safety gate shall use a single timestamped snapshot and shall fail closed if the snapshot cannot be obtained atomically. | Scheduling inspection, stress test during delayed VLM calls, and unit test for snapshot failure. |
| REQ-SEN-006 | Before a moving field test, each sensor shall be checked against three measured distances spanning the intended 25–100 cm operating range. The absolute error shall be no greater than **5 cm** at each check point, and cross-talk testing shall show no invalid or >5 cm deviation caused by sequential operation. Failure excludes the robot from motion testing. | Recorded calibration and cross-talk test. |

## 5. VLM, camera, and cloud-service requirements

| ID | Requirement | Verification |
| --- | --- | --- |
| REQ-VLM-001 | The VLM shall provide scene description only. It shall not issue motor commands, set speeds, enable motion, clear safety faults, or bypass the safety gate. | Interface inspection and adversarial response unit tests. |
| REQ-VLM-002 | A VLM report shall be used only when it exactly conforms to the current schema version, contains no unexpected semantic values, and has a trustworthy frame and receipt timestamp. Any parse, schema, provider, timeout, or timestamp failure shall invalidate the whole report. Free-text notes shall be logged only and shall not affect a decision. | Validator corpus tests including extra text, wrong enum, missing fields, and invalid timestamps. |
| REQ-VLM-003 | A VLM request shall time out and be cancelled at **4 s**. A report older than **6 s** from receipt, or based on a frame captured more than **6 s** before the safety-gate decision, shall be unusable. The usable state shall be recomputed each control tick. | Simulated-clock and delayed-provider tests. |
| REQ-VLM-004 | A usable VLM report that indicates `blocked`, `partially_blocked`, `stairs_or_drop`, `fire`, `smoke`, `water`, `wire`, `glass`, `drop_off`, `unstable_debris`, or `people.visible=true` in the intended path shall only reduce motion authority: it shall cause `STOP` or, where allowed by other requirements, `FORWARD_SLOW`. No VLM field, including `best_direction`, shall select a turn. It shall never cause an increase from stop to motion or from slow to full speed. | Decision and safety-gate truth-table tests. |
| REQ-VLM-005 | Three consecutive VLM request failures, any VLM report becoming unusable, loss of camera freshness, or loss of cloud connectivity shall set `VLM_FAULT` and command `SAFE_STOP` in baseline V1. This requirement supersedes the source specification’s general “sensor-only mode” statement because ultrasonic sensing cannot reliably detect drops, soft obstacles, angled surfaces, or visual hazards. | Wi-Fi disconnect, provider timeout, camera stall, and malformed-response integration tests. |
| REQ-VLM-006 | A sensor-only continuation experiment may occur only under a written test-specific authorization that records a flat, dry, bounded, obstacle-free area; confirms no stairs, drops, people, fire, smoke, water, loose debris, wires, or glass; limits speed to **0.05 m/s**; limits motion to `FORWARD_SLOW` and turns; keeps the operator within **2 m** with direct line of sight; and retains all sensor, watchdog, E-stop, and logging requirements. It shall begin only with VLM status already known unavailable and shall stop immediately on any sensor, control, or operator fault. This exception shall never be used to claim rescue or public-use capability. | Review of authorization and witnessed pre-run checklist, then controlled fault-injection test. |
| REQ-CAM-001 | Camera failure, no new frame for **6 s**, or frame timestamp anomaly shall be treated as VLM unusable and shall invoke REQ-VLM-005. | Camera-disconnect and frozen-frame tests. |

## 6. Control integrity, emergency stop, and power

| ID | Requirement | Verification |
| --- | --- | --- |
| REQ-CTL-001 | The control and safety-gate evaluation shall execute at least **20 Hz**. Three consecutive missed 50 ms control deadlines, or a detected safety-gate exception, shall remove motion permits, command zero drive, latch `CONTROL_FAULT`, and log the event. | Induced CPU stall and exception fault-injection test. |
| REQ-CTL-002 | The safety gate shall evaluate hard sensor vetoes after the decision engine and before each motor permit. A sensor or safety-state conflict shall resolve to `STOP`; a decision-engine request shall never override a safety-gate veto. | Unit tests for all conflicting action/sensor combinations. |
| REQ-ESTOP-001 | V1 shall have a conspicuous red, mushroom-head, manually actuated, mechanically latching physical E-stop that is reachable by the operator during the entire test. It shall be mounted on the robot or a hardwired pendant and shall not require an app, keyboard, network, cloud service, operating system, or microcontroller to actuate. | Physical inspection and operator reachability observation. |
| REQ-ESTOP-002 | Actuating the physical E-stop shall directly de-energize the motor-driver enable or motor power path through hardwired normally-closed circuitry, independent of the Pi and motor-command software. The measured interval from E-stop actuation to motor-driver energy removal shall be no more than **100 ms**. | Oscilloscope or logic-analyzer measurement at E-stop and motor-driver enable/power path. |
| REQ-ESTOP-003 | The E-stop shall remain latched after actuation. Releasing or resetting the E-stop shall not restart motors or restore a motion permit. A physical reset plus explicit local operator start after fault review shall be required. | Hardware reset sequence test. |
| REQ-ESTOP-004 | The software `STOP`, keyboard stop, and network stop may provide redundant stops but shall not be represented as the physical E-stop and shall not be required for E-stop functionality. | Architecture inspection and network/Pi-off E-stop demonstration. |
| REQ-PWR-001 | Motor and compute power distribution shall be protected against brownout and conducted noise such that motor actuation does not invalidate sensor timing or corrupt control state. A low-voltage, over-temperature, or motor-driver fault indication shall cause `SAFE_STOP`. | Power-load test with sensor/control log review and injected fault test where supported. |
| REQ-SEC-001 | No remote interface may issue a non-stop motor action, arm the motor driver, clear an E-stop, or clear a latched safety fault. Remote interfaces may display status and request `STOP` only. | Interface test and security/permission inspection. |

## 7. Logging, traceability, and verification records

| ID | Requirement | Verification |
| --- | --- | --- |
| REQ-LOG-001 | At every safety-gate evaluation, V1 shall record a monotonic timestamp, state, each sensor value/validity/age, camera and VLM ages/status, intended action, safety-gate action, motion-permit result, rule or veto ID, active faults, and E-stop state. | Log-schema test and sampled run-log inspection. |
| REQ-LOG-002 | A safety event, watchdog trip, VLM fault, E-stop actuation, start, reset, and configuration version shall be recorded with sufficient timestamps to reconstruct ordering to **50 ms** or better. | Event-injection test and replay comparison. |
| REQ-LOG-003 | The laptop replay environment shall execute decision and safety-gate logic against recorded and synthetic snapshots without physical motors. Each requirement whose verification names a unit, replay, or fault-injection test shall have a retained result linked to the software/configuration revision used. | Replay test and verification-record audit. |
| REQ-VER-001 | No moving test shall begin until the relevant pre-run checks in `odds-and-constraints.md` are completed and the verification evidence for REQ-SEN-006, REQ-ESTOP-001 through REQ-ESTOP-003, REQ-MOT-003, REQ-CTL-001, and REQ-LOG-001 is available for the tested configuration. | Test-readiness review. |

## 8. Requirement-to-safety traceability summary

| Safety concern | Principal requirements | Hazard log |
| --- | --- | --- |
| Person contact or unintended approach | REQ-SCP-002, REQ-MOT-001, REQ-MOT-005, REQ-VLM-004 | HZ-001, HZ-005 |
| Sensor loss or deceptive distance evidence | REQ-SEN-001 through REQ-SEN-006, REQ-MOT-005, REQ-MOT-006 | HZ-002, HZ-003 |
| VLM/cloud/camera loss or misdescription | REQ-VLM-001 through REQ-VLM-006, REQ-CAM-001 | HZ-004, HZ-006 |
| Rear collision without rear sensing | REQ-ACT-001, REQ-MOT-004 | HZ-007 |
| Runaway, stale command, or software failure | REQ-MOT-003, REQ-MOT-007, REQ-CTL-001, REQ-CTL-002 | HZ-008, HZ-009 |
| Failure to stop physically | REQ-ESTOP-001 through REQ-ESTOP-004, REQ-MODE-001 | HZ-010 |
| Electrical, power, or communications fault | REQ-PWR-001, REQ-SEC-001, REQ-LOG-002 | HZ-011, HZ-012 |

## 9. Change control

Any change to a numeric limit, action set, safety-gate rule, E-stop circuit, sensor set, VLM contract, or ODD shall be treated as a safety-relevant change. It requires documented hazard-log review, updated traceability, repeat of every affected verification, and explicit authorization before the changed configuration moves under power.
