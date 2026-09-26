# V1 Verification Plan

## 1. Purpose, baseline, and limits

This plan defines evidence for the V1 controlled research test baseline. It is subordinate to `../requirements/v1-requirements.md` and `../requirements/odds-and-constraints.md`. Where the source concept differs, the controlled baseline takes precedence: no autonomous reverse, loss of a required sensor or baseline VLM/camera service produces `SAFE_STOP`, and the hardwired E-stop is the primary stop mechanism.

This plan does not claim standards compliance, production readiness, rescue capability, or authorization beyond the documented controlled ODD. A gate pass permits only the next constrained verification step.

For requested planning coverage, SYS-, SAFE-, HW-, SW-, DATA-, and TEST- IDs in `traceability-matrix.md` are verification-index labels mapped to the authoritative `REQ-*` baseline IDs. They do not create or revise requirements.

## 2. Test levels and controlled scope

| Level | Scope | Entry | Exit |
| --- | --- | --- | --- |
| L0 | Laptop, synthetic/recorded data, fake motors only | None | Offline logic, validator, replay pass |
| L1 | Bench, wheels clear or translation mechanically prevented | E-stop and observer available | Inputs, stop chain, and permit checks pass |
| L2 | Private, access-controlled indoor test area | L1 evidence and ODD pre-run release | Short supervised low-speed checks pass |
| L3 | Documented benign obstacle layout in the same ODD | L2 plus reviewed test card | Scenario or 300 s demonstration completes or aborts |

For L2/L3: dry, firm, continuous, level surface with measured grade no greater than 3°; marked bounded area with no stairs, curbs, pits, drops, drains, ramps, or discontinuities within 1 m; no person or animal in the marked area; observers outside the robot path exclusion zone; operator within 2 m with direct sight and E-stop access. Exclude water, loose material, smoke, fire, wires, glass, soft/angled/reflective targets, unstable obstacles, public/shared space, and remote or unattended operation.

## 3. Evidence and decision rules

Each run record shall include test ID, build/configuration hash, hardware build, prompt/schema/provider identity, ODD layout, roles, pre-run checklist, raw logs, retained frames, measured results, pass/fail/abort disposition, and reviewer. At every safety-gate evaluation, retain the fields required by REQ-LOG-001. Missing, corrupt, or non-time-correlated evidence is inconclusive.

Any changed safety threshold, action set, sensor/camera arrangement, motor/E-stop circuit, VLM contract/provider, or decision/safety logic invalidates affected evidence and requires traceability review before powered testing.

## 4. Measurable acceptance gates

| Gate | Measurable gate | Baseline requirements and planning IDs | Evidence |
| --- | --- | --- | --- |
| VG-0 | Every permitted decision/safety truth-table case passes. `BACK_UP` is rejected to `STOP`; no component except safety gate can issue a motion permit. Two replay executions produce identical intended and gated outcomes. | REQ-ARC-001, REQ-ACT-001, REQ-MOT-004, REQ-CTL-002, REQ-LOG-003; SYS-001, SW-003, SW-005, SW-008, TEST-001 to TEST-004 | Automated results, architecture review, two replays |
| VG-1 | Validator corpus accepts only exact current schema. Every request exceeding 4.0 s is cancelled. A report or frame older than 6.0 s is unusable. Twenty saved frames have recorded capture/receipt/schema results. | REQ-VLM-001 to REQ-VLM-003, REQ-CAM-001; SW-001, SW-002, DATA-001, DATA-004, TEST-002 | Corpus, 20-frame record, timeout/fault logs |
| VG-2 | On the actual motor path: E-stop energy removal is measured at no more than 100 ms, latches, and does not restart on reset; absent/expired/invalid permit drives zero within 100 ms; non-stop permit age is no more than 150 ms; 3 missed 50 ms deadlines, exception, or 500 ms unrenewed action produces safe stop. | REQ-MODE-001, REQ-MOT-003, REQ-MOT-007, REQ-CTL-001, REQ-ESTOP-001 to REQ-ESTOP-004; SAFE-003 to SAFE-007, HW-003 to HW-004 | Timing capture, bench logs, witnessed test |
| VG-3 | Each sensor passes three checks across 25–100 cm with absolute error no greater than 5 cm. Sequential crosstalk causes no invalid or greater-than-5-cm deviation. Every channel publishes valid data at least once per 250 ms and any invalid/stale channel inhibits motion. | REQ-SEN-001 to REQ-SEN-006; SAFE-001, SAFE-002, SAFE-009, HW-001 | Calibration sheet, 60 s timing/crosstalk record, fault log |
| VG-4 | Configured translation is no more than 0.10 m/s, turning no more than 0.35 rad/s, and measured acceleration no more than 0.20 m/s² / 0.50 rad/s². Forward needs all channels valid/fresh, center at least 60 cm for full speed or 40 cm for slow, and any relevant direction below 25 cm yields stop. | REQ-MOT-001, REQ-MOT-002, REQ-MOT-005, REQ-MOT-006; SYS-002, SAFE-004, SW-006, TEST-005 | Configuration, instrumented motion and boundary tests |
| VG-5 | Wi-Fi, provider, camera, malformed report, stale report, or three consecutive VLM errors creates `VLM_FAULT` and `SAFE_STOP`. Sensor-only movement is not a baseline pass criterion and is tested only under a written REQ-VLM-006 authorization. | REQ-VLM-005, REQ-VLM-006, REQ-CAM-001; SYS-004, SAFE-008, SW-001, SW-007 | Fault-injection log and approval if exception used |
| VG-6 | One continuous supervised L3 run of at least 300 s completes in the approved ODD with no contact, no abort, no active fault, no E-stop use, complete logs, and no unapproved configuration/layout change. | REQ-VER-001, REQ-LOG-001 to REQ-LOG-003; SYS-002, DATA-002, DATA-003, TEST-005 | Timed record, raw log/frame package, signed review |

VG-6 cannot be attempted without current VG-0 through VG-5 evidence for the tested configuration. It is a controlled demonstration criterion only.

## 5. Required procedures

| Procedure | Required outcome |
| --- | --- |
| BP-01 | Offline architecture, decision/safety truth tables, schema validation, and deterministic replay |
| BP-02 | Sensor calibration, validity, timing, and crosstalk evidence |
| BP-03 / BP-04 | Camera retention and VLM timeout/contract evidence |
| BP-05 | Raised-wheel permit, timing, E-stop, watchdog, and motor checks |
| BP-06 | Sensor, control, VLM, and camera fault-injection checks |
| BP-07 | Safe fixture-based semantic-input exercise, with no real people or hazards |
| BP-08 | Log completeness and replay package |
| FP-01 to FP-07 | Controlled ODD preflight, low-speed motion, boundary, fault, and five-minute demonstration checks |

See `bench-procedures.md`, `../runbooks/bring-up.md`, and `../runbooks/field-test.md`.

## 6. Universal abort criteria

Call **ABORT**, activate the physical E-stop when safe, and follow `../runbooks/incident-response.md` for any unexpected/wrong motion, contact or credible contact risk, failed or inaccessible E-stop, any `SENSOR_FAULT`, `VLM_FAULT`, `CONTROL_FAULT`, `E_STOP`, missing/unknown state, missing log status, person/animal entering the exclusion zone, ODD change, loss of direct sight or within-2-m operator position, thermal/electrical/battery/mechanical concern, or doubt about safe continuation.

Do not resume after an abort by issuing start. Preserve evidence, correct the cause, and repeat affected gates and pre-run controls.
