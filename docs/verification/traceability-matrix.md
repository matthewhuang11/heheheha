# V1 Traceability Matrix

## Scope and status

This matrix maps the requested SYS-, SAFE-, HW-, SW-, DATA-, and TEST- verification-index IDs to the authoritative controlled-test baseline in `../requirements/v1-requirements.md`. The planning IDs organize this verification set only. `REQ-*` IDs are authoritative. All rows are **Planned** until the stated evidence is retained and reviewed.

| Planning ID | Authoritative baseline requirement(s) | Verification / acceptance evidence | Procedure / gate | Status |
| --- | --- | --- | --- | --- |
| SYS-001 | REQ-ARC-001, REQ-ACT-001, REQ-MOT-004 | Only safety gate issues permit; accepted actions exclude reverse and attempted `BACK_UP` becomes `STOP`. | BP-01, BP-05, VG-0 | Planned |
| SYS-002 | REQ-VER-001, REQ-LOG-001 to REQ-LOG-003 | Supervised 300 s ODD run, zero contact/abort/fault, complete evidence. | FP-07, VG-6 | Planned |
| SYS-003 | REQ-VLM-004, REQ-CTL-002 | Hazard/person reports can only reduce authority to stop or permitted slow motion. | BP-01, BP-07, VG-0 | Planned |
| SYS-004 | REQ-SEN-004, REQ-VLM-005, REQ-CTL-001 | Sensor, VLM/camera, and control failures latch protected state. | BP-06, FP-05, VG-5 | Planned |
| SYS-005 | REQ-LOG-003 | Synthetic and recorded snapshots execute offline with fake motors. | BP-01, BP-08, VG-0 | Planned |
| SYS-006 | REQ-SCP-001 | Boot/status text and test records identify the robot as research-test-only and prohibit rescue/public-use claims. | BP-01, FP-01, PRE-001 | Planned |
| SAFE-001 | REQ-SEN-003, REQ-SEN-005 | All channels have atomic valid/fresh snapshots and timing evidence. | BP-02, BP-06, VG-3 | Planned |
| SAFE-002 | REQ-SEN-002, REQ-SEN-004 | Any invalid/stale channel produces `SENSOR_FAULT` and inhibits permit. | BP-02, BP-06, VG-3 | Planned |
| SAFE-003 | REQ-CTL-001 | Three missed 50 ms deadlines or gate exception removes permit and latches fault. | BP-05, VG-2 | Planned |
| SAFE-004 | REQ-MOT-005, REQ-MOT-006, REQ-CTL-002 | Directional boundary truth table yields `STOP` below 25 cm and all permit prerequisites hold. | BP-01, BP-05, FP-03, VG-4 | Planned |
| SAFE-005 | REQ-MOT-003, REQ-MOT-007 | Permit age is at most 150 ms, invalid permit stops within 100 ms, and 500 ms unrenewed motion stops. | BP-05, VG-2 | Planned |
| SAFE-006 | REQ-ESTOP-001 to REQ-ESTOP-004 | Latching hardwired E-stop is reachable, independent, removes motor energy within 100 ms, and requires reset plus explicit start. | BP-05, VG-2 | Planned |
| SAFE-007 | REQ-MODE-001, REQ-MODE-002 | Boot/reset/fault enter safe state, local explicit start required, transition display/log within 250 ms. | BP-05, BP-06, VG-2 | Planned |
| SAFE-008 | REQ-VLM-005, REQ-VLM-006, REQ-CAM-001 | Baseline VLM/camera loss produces `VLM_FAULT` and stop. Any sensor-only exception has written authorization and all exception constraints. | BP-04, BP-06, FP-05, VG-5 | Planned |
| SAFE-009 | REQ-SEN-001, REQ-SEN-002 | Missing echo/out-of-range/filter failure is invalid, never far or substituted. | BP-02, BP-06, VG-3 | Planned |
| SAFE-010 | REQ-SCP-002, REQ-VLM-004 | Every valid person-visible report stops, latches indication, and needs acknowledgement before start. | BP-01, BP-07, VG-0 | Planned |
| SAFE-011 | REQ-MOT-008 | Four turns in 10 s without 1 s forward travel enters safe stop, no automatic reverse. | BP-01, VG-0 | Planned |
| SAFE-012 | REQ-ESTOP-002 | The normally-closed hardwired E-stop path removes actual motor-driver energy within 100 ms independently of the Pi, network, and cloud. | BP-05, FP-01, VG-2 | Planned |
| HW-001 | REQ-SEN-001, REQ-SEN-006 | Three channels sequential, three checks at 25–100 cm, absolute error at most 5 cm, crosstalk within limit. | BP-02, VG-3 | Planned |
| HW-002 | REQ-CAM-001 | Twenty retained timestamped frames; stall/frozen frame invokes VLM fault protection. | BP-03, BP-06, VG-1/VG-5 | Planned |
| HW-003 | REQ-MOT-001 to REQ-MOT-003 | Permitted wheel directions, speed caps, acceleration limits, and motor permit timing are measured. | BP-05, FP-02, VG-2/VG-4 | Planned |
| HW-004 | REQ-ESTOP-001 to REQ-ESTOP-003 | Actual E-stop circuit and energy-removal measurement satisfy latching/restart controls. | BP-05, VG-2 | Planned |
| HW-005 | REQ-MOT-002, REQ-PWR-001 | Actual robot motion stays within acceleration limits and motor/load faults or power disturbances cause safe stop without corrupting sensor/control timing. | BP-05, FP-02, VG-2/VG-4 | Planned |
| SW-001 | REQ-VLM-002, REQ-VLM-003, REQ-VLM-005 | Exact validation, 4 s cancellation, 6 s age limit, fault state and stop are shown by injection. | BP-04, BP-06, VG-1/VG-5 | Planned |
| SW-002 | REQ-VLM-001, REQ-VLM-002 | Schema corpus rejects malformed/extra/semantic-invalid reports as whole reports; notes do not decide. | BP-01, BP-04, VG-1 | Planned |
| SW-003 | REQ-VLM-004, REQ-MOT-005, REQ-MOT-006, REQ-MOT-008 | Decision and gate truth tables cover conservative sensor/VLM rule interactions. | BP-01, BP-07, VG-0/VG-4 | Planned |
| SW-004 | REQ-SEN-005, REQ-CTL-001 | Atomic snapshot and independent 20 Hz sensor/safety scheduling are inspected and stressed. | BP-01, BP-06, VG-3 | Planned |
| SW-005 | REQ-ARC-001, REQ-CTL-002 | Architecture and action traces show independent gate before every permit. | BP-01, BP-05, VG-0/VG-2 | Planned |
| SW-006 | REQ-ACT-001, REQ-MOT-001, REQ-MOT-004 | Only five external actions, no reverse, and configuration caps are verified. | BP-01, BP-05, VG-0/VG-4 | Planned |
| SW-007 | REQ-VLM-005, REQ-VLM-006 | Baseline loss stops. Exception test only occurs under written authorization and 0.05 m/s limit. | BP-06, FP-05, VG-5 | Planned |
| SW-008 | REQ-LOG-003 | Decision/safety replay uses fake motors with retained revision-linked result. | BP-01, BP-08, VG-0 | Planned |
| SW-009 | REQ-SEC-001 | Remote interfaces can display status and request `STOP` only, and cannot arm, drive, reset, or clear a safety latch. | BP-01, BP-05, VG-0 | Planned |
| DATA-001 | REQ-VLM-002 | Exact schema/current version, timestamp trust, and logging-only notes are evidenced. | BP-04, VG-1 | Planned |
| DATA-002 | REQ-LOG-001, REQ-LOG-002 | Gate log includes timestamp, state, sensor/VLM ages/status, intended/gated action, permit, rule/veto, faults, E-stop, and 50 ms event ordering. | BP-08, VG-6 | Planned |
| DATA-003 | REQ-CAM-001, REQ-LOG-003 | Frame retention/correlation and replay package are complete. | BP-03, BP-08, VG-1/VG-6 | Planned |
| DATA-004 | REQ-VLM-002, REQ-LOG-002 | Prompt/schema/provider/configuration identity accompanies each VLM evidence set. | BP-04, VG-1 | Planned |
| TEST-001 | REQ-LOG-003, REQ-CTL-002 | Unit truth tables map each safety and decision scenario to expected result. | BP-01, VG-0 | Planned |
| TEST-002 | REQ-VLM-002, REQ-VLM-003 | Validator and delayed-provider corpus includes valid, malformed, extra text, wrong enum/type, empty, stale, and timeout cases. | BP-04, VG-1 | Planned |
| TEST-003 | REQ-LOG-003 | Same log replays identically twice and artifacts are retained. | BP-08, VG-0 | Planned |
| TEST-004 | REQ-LOG-003, REQ-ARC-001 | Fakes exercise integrated brain without a motor-drive interface. | BP-01, VG-0 | Planned |
| TEST-005 | REQ-VER-001 | Staged bench and field evidence is current before each moving test. | BP-02 to BP-08, FP-01 to FP-07 | Planned |

## Coverage review

All six requested planning categories are represented. Every authoritative `REQ-*` ID in `../requirements/v1-requirements.md` appears in this matrix with evidence-producing procedure and measurable gate or pre-run control. The evidence scope remains controlled research testing only.
