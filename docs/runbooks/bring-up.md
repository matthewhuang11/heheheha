# V1 Bring-Up Runbook

## Purpose and boundary

This runbook prepares the V1 research robot for L0/L1 verification only. It does not authorize moving tests, rescue/disaster use, public use, standards compliance, or production readiness. Baseline requirements in `../requirements/v1-requirements.md` and `../requirements/odds-and-constraints.md` control if they differ from the source concept.

## Roles and no-go rule

The operator performs steps. A separate safety observer has continuous access to the conspicuous, hardwired, latching E-stop. Either may stop work. For powered work, if either role, the E-stop, logging, or a pre-power check is absent, do not energize.

## Pre-power checklist

- [ ] Wheels are raised clear or translation is mechanically prevented.
- [ ] Work area is dry, clear, and free of people/animals near the robot.
- [ ] Battery, wiring, E-stop circuit, motor driver, wheels, fasteners, sensors, and camera are intact, cool, and secure. Echo voltage dividers are present.
- [ ] E-stop is red, mushroom-head, reachable without crossing the robot, hardwired independent of Pi/network/cloud, and its reset/start sequence is known.
- [ ] Build/configuration hash, hardware build, prompt/schema/provider identity, logger path, and test ID are recorded.
- [ ] Lowest configuration within 0.10 m/s translation and 0.35 rad/s turn caps is selected. No unreviewed threshold/action/safety change is present.
- [ ] Logging storage and time source are available.

Any failure is no-go. Do not use a software/network stop as a substitute for the physical E-stop.

## Startup and staged verification

1. Start logging, power on, and verify `SAFE_STOP` with no motor motion before explicit local start. Verify state display/log responds within 250 ms.
2. Complete BP-01 before physical hardware. Require deterministic replay, strict validation, permit architecture, rejected reverse, and fake motors.
3. With motor drive disabled/raised, complete BP-02 through BP-04. Require sensor 25–100 cm checks within 5 cm, 250 ms channel publication, crosstalk pass, 20 frames, 4 s VLM timeout, and VLM/camera fault stop evidence.
4. Complete BP-05. Measure actual E-stop energy removal no later than 100 ms, E-stop latch/no restart, permit age no more than 150 ms, invalid/absent permit zero drive within 100 ms, 500 ms renewal expiry, control-deadline response, and motion caps/ramp.
5. Complete BP-06 through BP-08. Any sensor/VLM/camera/control fault must enter the appropriate fault state and `SAFE_STOP`; logs must be complete and replayable.

Baseline VLM or camera loss is not sensor-only operation. It is `VLM_FAULT` and `SAFE_STOP`. A sensor-only motion experiment requires the separate written REQ-VLM-006 authorization and is not a normal bring-up outcome.

## Release to controlled motion

Only the test lead may release a robot to `field-test.md` after all items are evidenced for the exact configuration:

- [ ] VG-0 through VG-5 pass.
- [ ] REQ-SEN-006, REQ-ESTOP-001 through REQ-ESTOP-003, REQ-MOT-003, REQ-CTL-001, and REQ-LOG-001 evidence is current.
- [ ] No open incident, failed stop, unresolved fault, incomplete log, or unreviewed change exists.
- [ ] ODD PRE-001 through PRE-010 are prepared, including physical layout and observer plan.

Release authorizes only the ODD-limited test, not deployment.

## Abort, shutdown, and records

Abort using E-stop for unexpected/wrong motion, inaccessible/failed E-stop, fault/unknown state, missing logs, heat/smell/smoke/arcing, battery/mechanical damage, or doubt. After stationary confirmation, disconnect power safely, inspect hardware, preserve raw logs/frames/configuration, and label Pass, Fail, Aborted, or Inconclusive. Do not restart after abort without `incident-response.md`, corrective action, and repeated affected verification.

**Planning ID coverage:** SAFE-001 to SAFE-009, HW-001 to HW-004, SW-001 to SW-007, DATA-001 to DATA-004, TEST-001 to TEST-005.
