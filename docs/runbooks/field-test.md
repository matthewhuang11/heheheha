# V1 Controlled Field-Test Runbook

## Scope

This runbook authorizes only controlled research tests in the ODD, never rescue/disaster response, public use, production use, standards compliance, or operation where a person relies on the robot. `../requirements/odds-and-constraints.md` and `v1-requirements.md` govern. No autonomous reverse, remote arming/reset/driving, unattended operation, or VLM/camera-loss continuation is permitted in a baseline run.

## Roles and site limits

A trained operator remains within 2 m, keeps unaided direct sight of the robot, performs no other task, and has immediate physical E-stop access. A separate safety observer monitors the marked boundary and may abort. Observers remain outside a 2 m exclusion zone from the possible path. No person or animal may be in the marked area while motion is armed.

Use only a private access-controlled area, dry, continuous, firm, level to no more than 3°, physically bounded from uninspected edges, and free of stairs, curbs, pits, drains, ramps, drops, loose material, water, smoke, fire, chemicals, wires, glass, soft/angled/reflective obstacles, unstable debris, and traffic. Test obstacles must be fixed, benign, non-fragile, non-conductive, non-entangling, and have a documented 1 m path perimeter except for an approved low-speed approach-to-stop objective.

## Required pre-run release

The test lead records Pass/Fail for PRE-001 through PRE-010. All must pass, including:

- [ ] Current VG-0 through VG-5, REQ-SEN-006, REQ-ESTOP-001 to REQ-ESTOP-003, REQ-MOT-003, REQ-CTL-001, and REQ-LOG-001 evidence for the exact configuration.
- [ ] Logged hardware/software/configuration, speed cap, E-stop circuit, sensor/camera arrangement, ODD layout, provider/prompt/schema, and roles.
- [ ] Same-day witnessed E-stop action, with current measurement showing motor energy removal no later than 100 ms; explicit reset/local-start behavior is confirmed.
- [ ] Left, center, and right channels are valid/fresh; baseline VLM report and camera frame are usable; no fault/unknown state exists.
- [ ] Translation cap is no more than 0.10 m/s and turning cap no more than 0.35 rad/s; no configuration change occurs in-run.
- [ ] Boundary, 2 m observer exclusion, operator position, E-stop reachability, lighting, dry surface, and obstacle inventory are confirmed.

Failure of one item is no-go. Extra observers, a shorter run, or a software stop do not compensate.

## Execution

### FP-01: Stationary readiness

Power on in the start zone. Verify `SAFE_STOP`, no movement before explicit local start, complete status/log state, fresh valid sensor channels, current usable VLM/camera, and E-stop-ready acknowledgement. Abort on any failure.

### FP-02: Short action and dynamics check

At minimum speed, perform one short action then stop and inspect. Verify only permitted actions, no reverse, correct direction, motor permit, speed/acceleration caps, and full log record. Do not proceed after any anomaly.

### FP-03: Low-speed approach-to-stop check

Use only a documented stable benign barrier in an otherwise clear ODD area. Begin with ample stopping distance. The observer aborts at credible contact risk rather than waiting for software. Pass only if all permit conditions remain valid and robot stops before contact. Contact or near contact is an incident.

### FP-04: Semantic and fault response

Use prevalidated report fixtures, not live hazards or people. A person-visible input at any distance must stop and latch. Hazard inputs may only reduce authority. Inject one controlled sensor fault and one VLM/camera/network fault while stationary or with motion safely inhibited. Each produces the appropriate fault and safe stop. Baseline test does not continue in sensor-only mode.

### FP-05: Sensor-only exception, if separately authorized

This is not a default field test. Conduct only with written REQ-VLM-006 authorization that identifies flat/dry/bounded/obstacle-free location, absent hazards/people, 0.05 m/s cap, `FORWARD_SLOW`/turn-only motion, operator within 2 m, direct sight, current E-stop/sensor/log controls, and immediate stop on any fault. Absence of the authorization means do not run this procedure.

### FP-06: Benign obstacle scenario

After same-day FP-01 through FP-04 pass, conduct one bounded scenario with documented benign fixtures and approved duration. Do not alter configuration, layout, roles, or ODD conditions. Record every stop, fault, intervention, and event marker. A fault, E-stop use, contact, boundary condition, or incomplete evidence is aborted, not passed.

### FP-07: Five-minute controlled demonstration

After reviewed FP-06 pass, repeat the exact approved layout/configuration for at least 300 s. Pass only with zero contact, zero abort, no active fault/E-stop event, complete logs/frames, and unchanged ODD. This satisfies only the controlled SYS-002/VG-6 demonstration criterion.

## Abort criteria and post-run

Immediately call **ABORT** and use the physical E-stop when safe for any person/animal entry, unexpected/wrong motion, contact or credible contact risk, fault/unknown/missing-log state, unavailable/uncertain E-stop, stale/invalid sensor, VLM/camera failure, loss of sight/2-m operator position, ODD/boundary/lighting/surface change, thermal/electrical/battery/mechanical concern, or doubt.

After abort or completion, command/verify `SAFE_STOP`, disarm before entry, preserve raw log/frames/configuration/layout/video/notes, inspect robot and E-stop, and record outcome. Any incident blocks further motion under `incident-response.md` until corrective action and required re-verification are complete.

**Planning ID coverage:** SYS-002 to SYS-004; SAFE-001 to SAFE-011; HW-003 to HW-004; SW-003 and SW-005 to SW-007; DATA-002 to DATA-003; TEST-005.
