# V1 Hazard Log

**Document ID:** DRR-V1-HZ
**Revision:** 1.0
**Status:** Baseline hazard log for controlled, supervised field-test research

## 1. Scope and risk method

This log covers V1 only in the constrained ODD in `../requirements/odds-and-constraints.md`. It does not establish that the robot is safe for rescue, public, unattended, or hazardous-environment use.

### 1.1 Ratings

| Rating | Severity (S) | Likelihood (L) in the stated ODD |
| --- | --- | --- |
| 1 | Negligible: no injury, no meaningful property damage | Rare: not expected in normal testing |
| 2 | Minor: reversible minor injury or limited equipment/property damage | Unlikely: credible but not expected with controls |
| 3 | Serious: injury requiring medical attention or significant property damage | Possible: can occur without effective controls |
| 4 | Severe: life-threatening injury, permanent harm, fire, or major damage | Likely: expected repeatedly or readily initiated |

**Residual-risk rule:** a hazard may be accepted for a field test only if its stated controls are verified for the exact configuration, residual severity is no greater than S2, residual likelihood is no greater than L2, and it has no open control gap marked **blocking**. A single contact, unexpected motion, E-stop failure, missed watchdog, or ODD excursion triggers incident review and suspends further moving tests under POST-004.

Severity is a consequence rating, not a claim of probability. The tight ODD, low speed, exclusion zone, and operator are essential controls, not optional mitigations.

## 2. Hazard register

| ID | Hazard and initiating conditions | Potential harm | Initial S/L | Required controls | Verification / evidence | Residual S/L | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HZ-001 | Forward collision with a fixed obstacle because of incorrect decision, braking delay, or insufficient clearance | Minor injury to an operator entering the area, robot/property damage | S3 / L3 | Low 0.10 m/s cap, 25 cm hard stop, 40/60 cm forward thresholds, 500 ms permit expiry, 2 m exclusion zone, direct operator supervision | REQ-MOT-001, REQ-MOT-003, REQ-MOT-005, REQ-MOT-007, ODD-004 through ODD-006; boundary and wall-approach tests | S2 / L2 | Open pending hardware verification |
| HZ-002 | Stale, absent, invalid, cross-talk-corrupted, or frozen ultrasonic channel is treated as clear | Collision or movement without reliable proximity evidence | S3 / L3 | Invalid is never far, every channel required, 500 ms watchdog, 20 Hz independent evaluation, calibration/cross-talk gate | REQ-SEN-001 through REQ-SEN-006; cover, unplug, timestamp, and malformed-value fault tests | S2 / L1 | Open pending verification |
| HZ-003 | Ultrasonic blind spot or misleading reflection from soft, angled, narrow, irregular, or absorbing material | Collision, entanglement, or travel toward a hazard | S3 / L3 | Exclude these materials and terrain, VLM may only reduce authority, low speed, operator/E-stop, no claim of all-hazard detection | CON-004, ODD-004, REQ-VLM-004, REQ-MOT-001, REQ-ESTOP-001 | S2 / L2 | Controlled only within ODD |
| HZ-004 | VLM, cloud, Wi-Fi, camera, or request pipeline is stale, offline, malformed, or delayed | Robot proceeds without visual hazard awareness such as drops or people | S3 / L3 | Whole-report validation, 4 s request timeout, 6 s expiry, baseline VLM fault stops, camera loss stops, narrow separately authorized sensor-only exception only | REQ-VLM-002 through REQ-VLM-006, REQ-CAM-001; disconnect, timeout, and frozen-frame tests | S2 / L1 | Open pending fault-injection evidence |
| HZ-005 | Person or animal enters path, is not detected, or is detected but movement continues | Contact injury, panic response, property damage | S4 / L3 | Access-controlled site, empty marked area, 2 m exclusion zone, direct supervision, VLM person report stops, immediate E-stop authority | ODD-001, ODD-005, ODD-006, REQ-SCP-002, REQ-ESTOP-001; witnessed boundary test | S2 / L1 | Controlled only within ODD |
| HZ-006 | VLM gives a confident but wrong “clear” description, misses a semantic hazard, or report is adversarial | Travel toward a drop, debris, or visual hazard | S4 / L3 | VLM never enables speed or clears sensor veto, baseline ODD excludes hazards, VLM loss stops, schema validation, operator supervision | REQ-VLM-001, REQ-VLM-002, REQ-VLM-004, REQ-VLM-005, CON-004 | S2 / L2 | Controlled only within ODD |
| HZ-007 | Reverse movement with unobserved rear obstacle because V1 lacks rear sensing | Collision with person, object, cable, or edge behind robot | S3 / L3 | Reject `BACK_UP`, prohibit all negative velocity and remote non-stop movement, reposition manually with drive disabled | REQ-ACT-001, REQ-MOT-004, CON-006, CON-007; motor command capture and unit tests | S1 / L1 | Open pending command-capture verification |
| HZ-008 | Stale action, decision-engine defect, safety-gate defect, deadlock, or scheduler stall produces continued or unintended motion | Collision or unexpected movement | S3 / L3 | Safety gate is sole permit source, permits fresh within 150 ms, zero drive within 100 ms on invalid permit, 20 Hz control loop, deadline watchdog, 500 ms action expiry | REQ-ARC-001, REQ-MOT-003, REQ-MOT-007, REQ-CTL-001, REQ-CTL-002; stall, exception, and replay tests | S2 / L1 | Open pending timing evidence |
| HZ-009 | Unexpected autonomous restart after boot, fault recovery, software reset, or E-stop reset | Surprise movement and contact | S3 / L2 | Safe boot state, latched faults, explicit local start, E-stop reset cannot restore a permit | REQ-MODE-001, REQ-MODE-002, REQ-ESTOP-003; sequence test for every reset path | S1 / L1 | Open pending reset-path verification |
| HZ-010 | Physical E-stop unavailable, ineffective, non-latching, software-dependent, or too slow | Operator cannot stop unexpected movement | S4 / L3 | Red mushroom latching E-stop, hardwired normally-closed motor-energy removal, independent of Pi/network, ≤100 ms measured removal, reachability within 2 m | REQ-ESTOP-001 through REQ-ESTOP-004, ODD-006, PRE-005; oscilloscope and Pi-off test | S2 / L1 | **Blocking until verified** |
| HZ-011 | Battery, wiring, motor-driver, thermal, or electrical fault causes fire, shock, uncontrolled motor behavior, or reset | Fire, burns, electrical injury, loss of control | S4 / L2 | Pre-run physical inspection, protected power distribution, faults cause safe stop, no wet/hazardous environment, no unattended charging, incident isolation | REQ-PWR-001, ODD-007, ODD-010, PRE-004, POST-002; power-load and inspection evidence | S2 / L1 | **Blocking until verified** |
| HZ-012 | Unauthorized or faulty network/status interface arms, drives, resets, or clears a fault | Unexpected movement or defeated safety controls | S3 / L2 | Remote interface is status plus `STOP` only. No remote arming, non-stop command, E-stop reset, or fault clearance | REQ-SEC-001, REQ-ARC-001, CON-007; interface and permission test | S1 / L1 | Open pending verification |
| HZ-013 | Tip-over, wheel loss, loose component, cable snag, or mechanical instability during turn | Contact, damage, electrical exposure, obstructed E-stop access | S3 / L2 | Low speed/turn caps and acceleration limits, inspected hardware, flat/firm surface, no payload, post-run inspection, E-stop on abnormal motion | REQ-MOT-001, REQ-MOT-002, ODD-002, PRE-004, CON-009, RUN-002 | S2 / L1 | Open pending stability test |
| HZ-014 | Log, status display, or timestamp failure conceals a fault or prevents incident reconstruction | Repeated unsafe testing or inability to identify a failed control | S2 / L2 | State/log health precondition, 50 ms event ordering, preserve evidence, stop on missing status or unknown state | REQ-LOG-001 through REQ-LOG-003, PRE-007, RUN-003, POST-003 | S1 / L1 | Open pending verification |
| HZ-015 | Operator error: inadequate briefing, distraction, poor positioning, ignores ODD change, or restarts after an incident | Delayed stop, unsafe exposure, repeated error | S3 / L3 | Named operator and test lead, 2 m direct supervision, checklists, stop authority, mandatory review after an event, no concurrent tasks | ODD-005, ODD-006, PRE-001 through PRE-010, RUN-001 through RUN-006, POST-004 | S2 / L2 | Controlled only with procedure compliance |

## 3. Hazard-control completeness checks

| Check ID | Required conclusion | Evidence source |
| --- | --- | --- |
| HZC-001 | Every moving-test hazard has one or more verified preventive/detective controls and a defined safe-state response. | Requirement-to-hazard links above and safety case claim matrix. |
| HZC-002 | HZ-010 and HZ-011 are closed before the first powered moving test. | E-stop timing/no-restart and power inspection/load records. |
| HZC-003 | HZ-002, HZ-004, HZ-007, HZ-008, HZ-009, HZ-012, HZ-013, and HZ-014 have current verification evidence before the test type relying on those controls. | Verification records linked by REQ-VER-001. |
| HZC-004 | HZ-003, HZ-005, HZ-006, and HZ-015 remain acceptable only while the ODD and supervision controls are continuously satisfied. | Pre-run, in-run, and post-run records. |
| HZC-005 | Any incident or safety-relevant change reopens affected hazards, requirements, ODD controls, and safety-case evidence. | POST-004 and change-control review. |

## 4. Known residual limitations

Even when every listed control is verified, V1 has no validated ability to detect all people, drops, unstable surfaces, cables, soft objects, transparent objects, water, fire, smoke, or material properties. The hazard controls reduce exposure by excluding such conditions, keeping the robot slow, requiring a nearby operator, and stopping on missing critical evidence. They do not make V1 suitable for rescue or public deployment.
