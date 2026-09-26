# V1 Operational Design Domain, Constraints, and Open Decisions

**Document ID:** DRR-V1-ODD
**Revision:** 1.0
**Status:** Baseline for controlled, supervised field-test research

## 1. Authorization boundary

V1 may operate only as a controlled research experiment under the requirements in `v1-requirements.md`. It is not authorized for rescue, disaster response, public spaces, unsupervised operation, emergency operation, operation near bystanders, or any use where a person may depend on it for safety.

The ODD is deliberately narrower than the intended future disaster-response concept. It is a test envelope, not a claim that V1 can recognize or safely manage all hazards inside it.

## 2. Permitted ODD

| ID | Permitted condition | Measurable boundary / required control | Verification before run |
| --- | --- | --- | --- |
| ODD-001 | Site | A private, access-controlled indoor test area or similarly controlled outdoor area that has a marked test boundary. No public access or through traffic is allowed. | Test lead signs site layout and boundary check. |
| ODD-002 | Surface | Dry, continuous, level, firm surface with no loose material. Measured grade shall not exceed **3°** in any travel direction. | Visual inspection and inclinometer measurement at representative locations. |
| ODD-003 | Geometry | No stairs, curbs, pits, drop-offs, ledges, open drains, ramps, or surface discontinuities within the marked test area or within **1 m** of its boundary. The test area shall be physically bounded so the robot cannot reach an uninspected edge. | Walkdown and recorded boundary measurement. |
| ODD-004 | Obstacles | Only fixed, benign, non-fragile test obstacles may be introduced. They shall be stable, non-sharp, non-conductive, and not capable of entangling wheels. Their placement shall preserve a minimum **1 m** clear perimeter around the run path unless the specific test objective is a low-speed approach-to-stop test. | Obstacle inventory and layout review. |
| ODD-005 | People and animals | No person or animal may be in the marked test area while motion is armed. Observers shall remain outside a **2 m** exclusion zone from the robot’s possible path. The assigned operator may enter only to activate the E-stop or after the robot is in `SAFE_STOP`. | Test lead confirms exclusion zone and observer briefing. |
| ODD-006 | Operator supervision | One trained operator shall maintain direct, unaided line of sight to the robot, remain within **2 m**, and have immediate access to the physical E-stop throughout motion. The operator shall not perform another task while the robot moves. | Witnessed pre-run position check. |
| ODD-007 | Environment | Lighting shall make the test surface, robot, E-stop, and boundary clearly visible to the operator. The test area shall be dry and free of smoke, fog, steam, dust clouds, flame, water, hazardous chemicals, and electromagnetic or acoustic conditions known to disrupt equipment. | Visual/environment check recorded on checklist. |
| ODD-008 | Communications and VLM | Baseline runs require a current usable VLM report as defined by REQ-VLM-002 and REQ-VLM-003. Loss of service invokes `SAFE_STOP`. The sensor-only exception is permitted only under REQ-VLM-006. | Status display and forced-disconnect test evidence. |
| ODD-009 | Robot configuration | The exact tested hardware, software revision, safety-gate configuration, speed limits, sensor arrangement, E-stop circuit, and log schema shall match the approved test record. | Configuration hash/version and physical configuration inspection. |
| ODD-010 | Energy | Battery, wiring, motor driver, and E-stop circuit shall have passed the current pre-run inspection. Charging, battery replacement, and exposed electrical work are outside the motion area and occur with motor drive disabled. | Checklist and physical inspection. |

## 3. Explicit exclusions

The following conditions are outside V1’s ODD. Encountering or discovering one during setup requires cancellation or transition to `SAFE_STOP`; it shall not be handled by “trying carefully.”

| ID | Excluded condition | Reason / required response |
| --- | --- | --- |
| CON-001 | Rescue, search-and-rescue, emergency, medical, firefighting, hazardous-materials, or disaster-site use | V1 is not certified, has no validated all-hazard perception, and shall not be relied on by people. Do not deploy. |
| CON-002 | Any public, shared, or uncontrolled space | Bystanders cannot be kept outside the exclusion zone. Do not arm motion. |
| CON-003 | People or animals within the motion area | No safe person-interaction or approach function exists. Stop and clear the area. |
| CON-004 | Stairs, drops, ramps over 3°, water, mud, rubble, loose gravel, cloth, foam, glass, wires, fire, smoke, chemicals, unstable debris, or reflective/soft/angled obstacles | The sensors and VLM cannot be credited to detect or classify these hazards reliably. Do not enter. |
| CON-005 | Rain, standing water, wet floor, high wind, poor visibility, darkness, or lighting that prevents direct supervision | Environmental degradation and electrical/mechanical risk. Do not operate. |
| CON-006 | Autonomous reverse movement | V1 has no rear protective sensor. The safety gate rejects `BACK_UP`; move the powered-down robot by hand if repositioning is needed. |
| CON-007 | Remote driving, remote arming, remote reset, or remote clearance of a safety fault | Remote functions may request only `STOP` and display status. |
| CON-008 | Unattended or beyond-line-of-sight operation | The operator and physical E-stop are required protective measures. |
| CON-009 | Payload transport, towing, manipulation, or use near fragile property | V1 has no validated stability, load, or contact-safety case. |
| CON-010 | Software, firmware, wiring, sensor, camera, or configuration changes not represented in current verification evidence | A change invalidates the specific test baseline until reassessed under REQ-VER-001 and the change-control rule. |

## 4. Operating constraints and required preconditions

### 4.1 Pre-run release checklist

The test lead shall record each item as pass, fail, or not applicable. Any fail means no moving test.

| ID | Required check | Pass criterion |
| --- | --- | --- |
| PRE-001 | Test scope | The written objective is compatible with the permitted ODD and does not claim rescue or public-use capability. |
| PRE-002 | Site walkdown | ODD-001 through ODD-007 have been checked and recorded. |
| PRE-003 | Personnel | Operator is designated, briefed on stop authority, within 2 m, and observers are outside the exclusion zone. |
| PRE-004 | Hardware | Frame, wheels, fasteners, wires, battery, motor driver, and sensor mounts are intact. No exposed conductor, heat damage, or loose component is present. |
| PRE-005 | E-stop | Physical E-stop satisfies a current witnessed actuation test and is reset only after the test lead confirms safe conditions. The result is linked to the configuration. |
| PRE-006 | Sensor health | REQ-SEN-006 calibration/cross-talk evidence is current. The live display shows valid, fresh left, center, and right readings. |
| PRE-007 | Control health | Control loop, safety gate, permit expiry, and log writer are healthy. A commanded software stop reaches `SAFE_STOP`. |
| PRE-008 | Vision/cloud health | Baseline mode has a usable current VLM report and current camera frame. If intentionally testing sensor-only behavior, the written authorization required by REQ-VLM-006 is present instead. |
| PRE-009 | Configuration | Software revision, configuration version/hash, ODD layout, speed cap, and hardware build are recorded in the run log before arming. |
| PRE-010 | Initial state | Robot is stationary, drive area is clear, E-stop is accessible, and `READY` is displayed before explicit local start. |

### 4.2 In-run stop conditions

The operator shall activate the physical E-stop, or use a redundant software stop if it is faster to reach, on any of the following. The operator need not diagnose the issue first.

| ID | Stop condition | Required action |
| --- | --- | --- |
| RUN-001 | Any person, animal, or unbriefed observer approaches the exclusion zone | Stop immediately, secure the area, and restart only through PRE-001 through PRE-010 as applicable. |
| RUN-002 | Robot moves unexpectedly, fails to follow expected stop behavior, contacts any object, tips, drags a wire, or produces unusual sound, heat, smell, or smoke | E-stop, isolate power, preserve log, and treat as a safety incident. |
| RUN-003 | Any `SENSOR_FAULT`, `VLM_FAULT`, `CONTROL_FAULT`, `E_STOP`, missing log status, or unknown state | Do not attempt to continue. Enter safe state and investigate. |
| RUN-004 | Surface, lighting, weather, boundary, obstacle, or communication conditions leave the ODD | Stop and cancel or re-authorize a new ODD assessment. |
| RUN-005 | Operator loses direct line of sight, moves beyond 2 m, becomes distracted, or cannot reach the E-stop | Stop immediately. |
| RUN-006 | A test objective is completed, a run reaches its approved duration, or the robot is stuck | Stop, disarm, and review the log before another run. |

### 4.3 Post-run controls

| ID | Control | Required result |
| --- | --- | --- |
| POST-001 | Disarm | Robot reaches `SAFE_STOP` and motor drive is disabled before anyone enters the motion area. |
| POST-002 | Inspect | Inspect robot, E-stop, wiring, wheels, and sensors for damage or abnormal heat before re-use. |
| POST-003 | Preserve evidence | Retain the run log, configuration version, test layout, fault/event records, and any video or photos relevant to unexpected behavior. |
| POST-004 | Incident review | Any contact, unexpected movement, E-stop use during motion, missed watchdog, or ODD excursion blocks further moving tests until the hazard log and safety case are reviewed. |

## 5. Conservative resolution of source-design ambiguities

| ID | Source-design tension | V1 decision | Traceability |
| --- | --- | --- | --- |
| DEC-001 | The source says sensor loss stops motion, while one decision rule names only stale data or all three invalid. | Any stale or invalid required sensor channel stops and latches `SENSOR_FAULT`. A healthy channel never compensates for a failed one. | REQ-SEN-002 through REQ-SEN-005, HZ-002 |
| DEC-002 | The source proposes sensor-only movement when VLM/Wi-Fi is offline, yet also relies on vision for drop-offs and semantic hazards. | Baseline loss of VLM/camera/cloud stops. A documented, low-speed sensor-only experiment is a narrow exception under REQ-VLM-006, not a fallback for unknown terrain. | REQ-VLM-005, REQ-VLM-006, HZ-004, HZ-006 |
| DEC-003 | The source action set includes `BACK_UP`, but no rear sensor is specified. | Autonomous reverse is prohibited. The safety gate converts `BACK_UP` to `STOP`; human repositioning occurs only with drive disabled. | REQ-ACT-001, REQ-MOT-004, HZ-007 |
| DEC-004 | The source calls for a physical power cutoff but also lists software and network manual kill. | A physical, hardwired, latching E-stop is mandatory and independent. Software/network stop is supplemental only. | REQ-ESTOP-001 through REQ-ESTOP-004, HZ-010 |
| DEC-005 | The source allows up to 3 s before an action timeout, which is too long for an unrefreshed command. | A motor-layer permit is fresh for no more than 150 ms and a continuous non-stop action requires safety-gate renewal within 500 ms. The 3 s limit remains only an upper bound on an episode with a new decision record. | REQ-MOT-003, REQ-MOT-007, HZ-008 |
| DEC-006 | The source uses VLM `best_direction` to influence turns, which would let probabilistic image interpretation choose a movement direction. | In the controlled baseline, the VLM is descriptive only. Hazard, terrain, path, and person fields may reduce authority to `STOP` or permitted slow forward motion, but no VLM field selects a turn or increases motion authority. `best_direction` is retained only as logged scene evidence for replay and research analysis. | REQ-VLM-001, REQ-VLM-004, HZ-004, HZ-006 |

## 6. Assumptions, dependencies, and open decisions

The entries below are not permission to operate outside the ODD. An unresolved high-risk item blocks affected field testing.

| ID | Assumption / open decision | Current safe disposition | Closure evidence |
| --- | --- | --- | --- |
| ODC-001 | Exact GoPro model and Pi camera interface are not confirmed. | No moving baseline run without current camera frames and usable VLM reports. Use a verified alternate camera only after change control. | 20-frame acquisition evidence and camera fault test. |
| ODC-002 | Exact motor driver and its behavior when enable/power is removed are not confirmed. | Do not arm motion until E-stop energy-removal timing and no-restart behavior are measured on the actual driver. | REQ-ESTOP-002 and REQ-ESTOP-003 test record. |
| ODC-003 | HC-SR04 performance on the final robot and test materials is uncertain. | Treat every channel as required and exclude soft, angled, or irregular obstacles. | REQ-SEN-006 calibration and representative obstacle tests. |
| ODC-004 | VLM latency, availability, and accuracy are variable. | VLM is not credited to enable faster motion, and loss stops baseline V1. | Timed provider test, invalid-response corpus, and disconnect test. |
| ODC-005 | Braking distance and stop dynamics on the final surface are unmeasured. | Use 0.10 m/s maximum and do not conduct approach tests until measured stopping performance shows no contact at the 25 cm stop threshold. | Instrumented stop-distance test with margin documented. |
| ODC-006 | Battery protection, thermal behavior, and motor current are unspecified. | No extended run or unattended charging. Any warning triggers `SAFE_STOP`. | Power/thermal inspection and representative load test. |
| ODC-007 | No formal functional-safety certification or independent assessment is planned for V1. | Claims remain limited to supervised research in this ODD. | Safety-case review and explicit test report wording. |

## 7. Test authority and change control

The test lead may make a limit more conservative, stop a run, or cancel a test without further approval. No one may widen the ODD, increase a motion limit, enable reverse, treat VLM loss as acceptable baseline behavior, bypass the E-stop, or waive a required verification through an informal decision. Such a change requires the safety-relevant change process in `v1-requirements.md` and updates to the hazard log and safety case.
