# V1 Safety Case

**Document ID:** DRR-V1-SC
**Revision:** 1.0
**Status:** Argument and evidence plan for controlled, supervised field-test research

## 1. Claim and scope

### Top claim G0

**G0:** For the exact V1 hardware, software, configuration, and test procedure under review, it is acceptably safe to conduct the specified controlled, supervised field-test research activity **only** within the ODD in `../requirements/odds-and-constraints.md`, provided all listed preconditions and verification evidence are current.

G0 does **not** claim that V1 is safe, certified, suitable, or effective for rescue, disaster response, public deployment, unattended use, person interaction, hazardous environments, or operation outside that ODD.

### Context and assumptions

| ID | Context or assumption | Safety consequence |
| --- | --- | --- |
| C-001 | V1 is a low-speed differential-drive research robot with three front/side ultrasonic protective channels, a camera, a cloud VLM, deterministic decision logic, a safety gate, and a physical E-stop. | The safety argument credits only the functions and interfaces expressly verified. |
| C-002 | V1 has no rear protective sensor. | Autonomous reverse is prohibited, not mitigated by operator observation. |
| C-003 | Ultrasonic sensing cannot reliably detect all soft, angled, irregular, transparent, or absorbing targets. | Such materials and terrain are excluded from the ODD. A clear reading is not treated as evidence of an all-hazard clear path. |
| C-004 | A cloud VLM can be delayed, offline, malformed, or wrong. | It is description-only, cannot enable additional motion authority, and baseline loss of VLM/camera/cloud causes a safe stop. |
| C-005 | The operator and controlled test site are part of the safety control set. | If supervision or ODD conditions are absent, no movement is authorized. |
| C-006 | Evidence has not yet been collected merely because this document defines it. | Claims remain conditional until the listed evidence is reviewed and accepted for the exact configuration. |

## 2. Argument structure

```text
G0  Controlled supervised field testing is acceptably safe within the stated ODD
|
+-- G1  Exposure to people, uncontrolled terrain, and prohibited uses is prevented
|   +-- G1.1 ODD is constrained, checked before use, and continuously supervised
|   +-- G1.2 V1 does not approach or interact with people
|
+-- G2  Intended motion remains slow, bounded, and protected by fresh proximity evidence
|   +-- G2.1 Only the independent safety gate can issue short-lived motion permits
|   +-- G2.2 Any missing, stale, invalid, or unsafe required sensor channel stops motion
|   +-- G2.3 Rearward motion is impossible in V1
|
+-- G3  Loss or error of camera/VLM/cloud service cannot silently increase hazard exposure
|   +-- G3.1 VLM output is validated description data with no motor authority
|   +-- G3.2 Baseline VLM/camera/cloud loss transitions to safe stop
|
+-- G4  Foreseeable control, power, and actuation failures lead to a safe state
|   +-- G4.1 Deadline, permit, and reset controls prevent stale or surprise motion
|   +-- G4.2 A hardwired physical E-stop independently removes motor energy
|   +-- G4.3 Power, interface, and mechanical constraints are checked
|
+-- G5  Safety controls are verified, logged, and re-assessed after changes or incidents
```

## 3. Claims, strategies, evidence, and acceptance criteria

| Claim | Strategy and supporting requirements | Primary hazards controlled | Required evidence and acceptance criterion | Claim status |
| --- | --- | --- | --- | --- |
| G1: Exposure is constrained to a manageable research setting. | Restrict use to ODD-001 through ODD-010 and enforce PRE-001 through PRE-010, RUN-001 through RUN-006, and POST-001 through POST-004. | HZ-003, HZ-005, HZ-006, HZ-015 | Signed site walkdown, operator briefing, boundary/exclusion-zone observation, and completed pre-run checklist. All must match the tested layout and configuration. | Conditional, procedural evidence required per run |
| G1.2: People are not exposed to intentional autonomous approach. | REQ-SCP-002 stops on a VLM person report. The stronger primary control is an empty access-controlled motion area and 2 m exclusion zone. | HZ-005 | Unit tests for `people.visible=true`; witnessed site control; stop drill with a person remaining outside the motion area. No test intentionally places a person in the path. | Conditional |
| G2: Motion is limited and bounded by current protective evidence. | Enforce REQ-MOT-001 through REQ-MOT-008, especially 0.10 m/s maximum, 25 cm veto, and 500 ms action expiry. | HZ-001, HZ-008, HZ-013 | Hardware speed, acceleration, turning, and stop-distance measurements on the actual ODD surface. Boundary tests shall show stop at every unsafe threshold without contact. | Conditional, hardware evidence required |
| G2.1: Safety gate is the single motion authority. | REQ-ARC-001, REQ-CTL-002, and REQ-MOT-003 require a fresh safety-gate permit before motor energization. | HZ-008, HZ-012 | Interface/code inspection plus fault test demonstrating zero drive within 100 ms for absent, expired, malformed, or invalid permits. | Conditional, timing evidence required |
| G2.2: Sensor failure fails closed. | REQ-SEN-001 through REQ-SEN-006 require independent 20 Hz watchdog evaluation, valid samples from all channels, and stop/latch on any invalid or stale channel. | HZ-001, HZ-002 | Calibration, cross-talk, covered-sensor, unplug, stale-timestamp, frozen-value, and snapshot-failure tests. Each must result in no motion permit or safe stop within the specified timing. | Conditional, fault evidence required |
| G2.3: Rear hazard exposure is removed rather than inferred. | REQ-ACT-001 and REQ-MOT-004 reject `BACK_UP` and every negative velocity source. | HZ-007 | Action-enumeration unit test, configuration inspection, and motor command capture showing no negative translational command. | Conditional, command evidence required |
| G3: Vision/cloud faults do not silently permit travel. | REQ-VLM-001 through REQ-VLM-005 make VLM description-only, validate the complete report, bound time/age, and stop baseline V1 on unavailability. | HZ-004, HZ-006 | Validator corpus, delayed request, cloud disconnect, malformed output, stale report, camera disconnect, and frozen-frame tests. Each must yield `VLM_FAULT` and safe stop in baseline mode. | Conditional, fault evidence required |
| G3.2: Any sensor-only experiment remains an explicitly bounded exception. | REQ-VLM-006 requires prior written authorization, a pre-inspected benign area, 0.05 m/s maximum, direct 2 m supervision, and all non-VLM controls. | HZ-003, HZ-004, HZ-005, HZ-006 | Test-specific authorization plus witnessed checklist and fault test. Absence of this package means sensor-only motion is prohibited. | Not enabled by default |
| G4: Control, reset, power, and actuator failures lead to safe state. | REQ-MODE-001, REQ-MODE-002, REQ-CTL-001, REQ-PWR-001, and REQ-SEC-001 combine watchdog, fault latch, explicit local start, power controls, and restricted remote functions. | HZ-008, HZ-009, HZ-011, HZ-012, HZ-014 | CPU-stall/exception tests, reset-path test, power-load/fault test, remote-interface test, and log-completeness test. All failed conditions must produce safe stop and an auditable event. | Conditional, integration evidence required |
| G4.2: Operator retains an independent physical means to remove motor energy. | REQ-ESTOP-001 through REQ-ESTOP-004 require a reachable red latching mushroom E-stop, hardwired normally-closed path, ≤100 ms energy removal, and no automatic restart. | HZ-010, HZ-005, HZ-008 | Physical inspection, reachability observation, oscilloscope/logic-analyzer measurement at the actual motor driver, Pi-off test, and reset/no-restart test. Every item must pass before any powered moving test. | **Blocking evidence required** |
| G5: Claims remain tied to observable behavior and invalidate on change. | REQ-LOG-001 through REQ-LOG-003, REQ-VER-001, POST-004, and requirements change control preserve traceability and stop testing after anomalies. | HZ-014 and all hazards after change | Sampled logs reconstruct sensor age, VLM state, action, permit, veto, and faults to 50 ms. Test records identify hardware/configuration/software revision. Change or incident review is completed before resumption. | Conditional, record evidence required |

## 4. Evidence package and release gates

The following evidence identifiers are planned records. An identifier is **not** evidence until it contains the test date, tester, exact configuration, method, raw or retained result, pass/fail decision, and reviewer sign-off.

| Evidence ID | Evidence item | Requirements / hazards supported | Minimum acceptance condition | Field-test gate |
| --- | --- | --- | --- | --- |
| EV-001 | Configuration and interface inspection | REQ-ARC-001, REQ-ACT-001, REQ-SEC-001, HZ-007, HZ-012 | Only safety gate issues permits, no reverse source, no remote non-stop control. | Required before powered test |
| EV-002 | Sensor calibration and cross-talk record | REQ-SEN-001 to REQ-SEN-006, HZ-001, HZ-002 | All three channels within 5 cm at three 25–100 cm points, sequential operation shows no >5 cm cross-talk deviation. | Required before moving test |
| EV-003 | Sensor and snapshot fault-injection report | REQ-SEN-002 to REQ-SEN-005, HZ-002 | Missing, invalid, stale, frozen, unplugged, and atomic-snapshot failure each inhibit/stop motion and record the cause. | Required before moving test |
| EV-004 | VLM/camera validator and fault report | REQ-VLM-001 to REQ-VLM-005, REQ-CAM-001, HZ-004, HZ-006 | Invalid or stale data and cloud/camera loss transition baseline V1 to safe stop. | Required before baseline moving test |
| EV-005 | Motion-limit, threshold, and stop-distance report | REQ-MOT-001 to REQ-MOT-008, HZ-001, HZ-008, HZ-013 | Measured speed/acceleration meet limits and approach tests stop without contact before the 25 cm veto boundary is violated. | Required before obstacle test |
| EV-006 | Permit/deadline/reset-path fault report | REQ-MOT-003, REQ-MOT-007, REQ-MODE-001, REQ-CTL-001, HZ-008, HZ-009 | Expired permit, control deadline miss, exception, boot, reset, and fault recovery cannot create continued or surprise motion. | Required before moving test |
| EV-007 | Physical E-stop test package | REQ-ESTOP-001 to REQ-ESTOP-004, HZ-010 | Reachable latching E-stop independently removes motor energy in ≤100 ms with Pi/network unavailable, and reset does not restart motion. | **Absolute blocker before powered moving test** |
| EV-008 | Power and mechanical inspection/load report | REQ-PWR-001, REQ-MOT-002, HZ-011, HZ-013 | No observed wiring damage, hazardous heating, control corruption, unstable structure, or sensor/control degradation during representative load. | **Absolute blocker before powered moving test** |
| EV-009 | ODD and run authorization | ODD-001 to ODD-010, PRE-001 to PRE-010, HZ-003, HZ-005, HZ-015 | Current site walkdown, named operator, exclusion zone, configuration match, and all checks pass. | Required per run |
| EV-010 | Log/replay and incident-review record | REQ-LOG-001 to REQ-LOG-003, HZ-014 | Log reconstructs a run and every safety event ordering to 50 ms. | Required before extended test |

### Release decision

A test lead may authorize a **specific** moving field test only when EV-001 through EV-009 are passed for the exact configuration and the hazard register has no blocking gap. EV-010 is required before an extended or repeatability run. The authorization is automatically void if the ODD changes, a safety fault occurs, the E-stop is used during unexpected behavior, a control is changed, or a listed evidence item expires or no longer matches the build.

## 5. Traceability matrix

| Safety-case claim | Requirements | ODD/procedure | Hazard IDs | Evidence |
| --- | --- | --- | --- | --- |
| G1 / G1.2 | REQ-SCP-001, REQ-SCP-002 | ODD-001 to ODD-010, PRE-001 to PRE-010, RUN-001 to RUN-006 | HZ-003, HZ-005, HZ-006, HZ-015 | EV-009 |
| G2 / G2.1 | REQ-ARC-001, REQ-MOT-001 to REQ-MOT-008, REQ-CTL-002 | ODD-002 to ODD-006 | HZ-001, HZ-008, HZ-013 | EV-001, EV-005, EV-006 |
| G2.2 | REQ-SEN-001 to REQ-SEN-006 | PRE-006, RUN-003 | HZ-001, HZ-002 | EV-002, EV-003 |
| G2.3 | REQ-ACT-001, REQ-MOT-004 | CON-006, CON-007 | HZ-007 | EV-001 |
| G3 / G3.2 | REQ-VLM-001 to REQ-VLM-006, REQ-CAM-001 | ODD-008, PRE-008 | HZ-003, HZ-004, HZ-005, HZ-006 | EV-004 and, if exception used, explicit authorization |
| G4 / G4.1 | REQ-MODE-001, REQ-MODE-002, REQ-CTL-001, REQ-PWR-001, REQ-SEC-001 | PRE-004, PRE-007, POST-002 | HZ-008, HZ-009, HZ-011, HZ-012, HZ-013 | EV-006, EV-008 |
| G4.2 | REQ-ESTOP-001 to REQ-ESTOP-004 | ODD-006, PRE-005 | HZ-010 | EV-007 |
| G5 | REQ-LOG-001 to REQ-LOG-003, REQ-VER-001 | POST-003, POST-004 | HZ-014 and all changed hazards | EV-010 and review record |

## 6. Limitations and invalidation rules

This argument is intentionally conservative and incomplete outside its scope. It becomes invalid for a field test if any of the following occurs: operation outside the ODD, reverse enablement, use near people or uncontrolled obstacles, an unverified hardware or software change, lack of a reachable physical E-stop, missing/failing evidence, an incident requiring POST-004 review, or a claim that V1 is a rescue or public-deployment system.

A review shall update this safety case, the hazard log, the requirements, and applicable evidence before resuming after any invalidating event. No test result may be generalized from the narrow V1 ODD to disaster response, emergency use, or certification.
