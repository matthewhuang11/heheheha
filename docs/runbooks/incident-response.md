# V1 Test Incident-Response Runbook

## 1. Purpose and limits

Use this runbook for any anomaly during V1 bench or controlled test activity, including an abort, near miss, contact, unexpected movement, failed stop mechanism, sensor/telemetry fault, VLM/network behavior anomaly, or electrical/mechanical/battery concern.

This is a test-incident procedure, not an emergency-services plan. If there is fire, smoke, injury, electrical hazard, battery leakage/thermal event, or any immediate danger, prioritize people and follow local emergency procedures. Do not continue robot troubleshooting in an unsafe area.

## 2. Immediate response order

1. **Call “ABORT.”** Any observer may do this.
2. **Stop motion.** Use the physical cutoff first when safe and accessible. Use manual kill only if cutoff is unavailable or after cutoff. Do not rely on cloud, network, VLM, or normal software stop paths.
3. **Protect people.** Keep people and animals out of the area. Do not reach toward a moving robot or wheels.
4. **De-energize.** After motion is visibly stopped, disconnect power only when safe. For an electrical/thermal/battery event, do not handle a hot, damaged, leaking, or swollen component.
5. **Secure the scene.** Maintain boundary, do not move the robot/fixture unless needed to prevent harm, and prevent restart.
6. **Escalate.** Seek appropriate local emergency or technical help for injury, fire/smoke, electrical hazard, or battery event.

No person may restart the robot following an incident. “It looks fine” is not a release criterion.

## 3. Trigger-specific actions

| Trigger | Immediate action | Preserve / inspect after safe shutdown |
| --- | --- | --- |
| Unexpected, wrong-direction, or uncommanded motion | Cutoff, establish separation, retain boundary. | Video if available, log window before/after event, chosen/gated action, configuration, motor/wheel condition. |
| Contact or near contact | Cutoff, check people first, do not resume. | Contact point, obstacle layout, timestamp, log/frame evidence, damage inspection. |
| Manual kill or cutoff fails/uncertain | Use the alternate stop and then remove power if safe. Treat as critical test failure. | Stop-method sequence, wiring/actuator condition, controller state. Do not conduct powered tests until reverified. |
| Stale/invalid sensor supports motion | Cutoff immediately. | Sensor values, validity flags, ages, rule/gate decision, cabling/mount condition. |
| VLM/network/camera anomaly | Activate/command stop immediately. Baseline loss, unusable report, or camera fault requires `VLM_FAULT` and `SAFE_STOP`; do not continue in sensor-only mode without written REQ-VLM-006 authorization. | Request/error history, raw response IDs, timeout/error count, mode, report/frame age, provider/prompt/schema identity. |
| Logging/status loss | Stop motion and do not continue blind. | Storage/console state, last intact log, clock/state details. |
| Smoke, heat, odor, arcing, battery swelling/leakage | Cutoff if safe, isolate area, follow local emergency/battery procedure. Do not touch hot/leaking parts. | Photos/observations only from a safe distance, component identity, power state. |
| Mechanical looseness, wheel/mount/sensor/camera damage | Cutoff and de-energize. | Component condition, fasteners, fixture layout, prior vibration/noise observations. |
| Person/animal or unauthorized entry | Cutoff or command stop before any approach risk. Clear area. | Boundary breach time, robot state, observer position. |

## 4. Severity and disposition

| Level | Examples | Minimum disposition |
| --- | --- | --- |
| Critical | Injury, actual contact with person, fire/smoke, battery event, inability to stop drive, uncontrolled motion. | Stop all powered testing. Secure equipment, obtain appropriate emergency/technical review, and require formal corrective-action review plus full relevant re-verification. |
| Major | Near contact, wrong direction, stale data that did not protect, lost logs during motion, unexpected VLM/mode behavior, damaged component. | Stop current testing. Repair/investigate, review the incident, repeat affected bench gates and all entry criteria. |
| Minor | Controlled test stopped before risk due to a known, benign setup issue with complete evidence and no abnormal motion. | Correct setup, document, and repeat the affected procedure from its start. Escalate to Major if recurrence or cause is uncertain. |

When uncertain, classify at the higher severity. A successful stop does not reduce an event to a pass; it may demonstrate a safety response but the test remains aborted unless the procedure explicitly evaluates that fault.

## 5. Evidence preservation and incident record

After the scene is safe, create an incident record containing:

- incident ID, date/time, site/test level, test procedure/test card, and roles present;
- robot, software, configuration, prompt/schema, VLM provider, real/fake hardware, and battery identifiers;
- objective sequence of events, including called stop command and which stop method actually stopped motion;
- observed motion/contact/damage/injury status and environment/fixture condition;
- raw `.jsonl` logs, console/service output, retained frames, video, network/VLM error data, and file checksums or immutable copies where practical;
- immediate action, preliminary severity, test disposition, and any external escalation;
- proposed corrective action owner and required re-verification procedures.

Preserve originals read-only where possible. Do not edit `.jsonl` records, rename evidence in a way that loses time ordering, overwrite configuration, or retry just to obtain a cleaner log.

## 6. Investigation and return-to-test controls

Before another test:

1. Identify the triggering condition and affected requirement IDs using `../verification/traceability-matrix.md`.
2. Record root-cause hypothesis separately from facts. Unknown cause is not an acceptable closure for powered retest.
3. Inspect and correct hardware, configuration, software, fixture, or process issue as applicable.
4. Re-run the lowest affected verification level first. For any stop failure, unexpected motion, safety-gate anomaly, power change, sensor/motor change, or threshold change, repeat relevant BP-01 through BP-06 before ground motion.
5. For any change to safety thresholds, sensor layout, motor control, VLM provider, prompt/schema, decision rules, or safety gate, invalidate affected evidence and perform traceability review.
6. Test lead and safety observer review the completed corrective action and required gate evidence before authorizing a new test card.

Never compensate for an unresolved issue by widening the test area, increasing observation, increasing speed, disabling a protection, or treating a VLM result as a safety authority.

## 7. Mandatory re-verification map

| Incident type | Minimum re-verification before a new L2/L3 attempt |
| --- | --- |
| Failed cutoff/manual kill, wrong motor direction, unexpected motion | BP-05, BP-06, VG-2, VG-5, same-day stop check |
| Sensor stale/invalid or crosstalk anomaly | BP-02, BP-06, VG-3, VG-5 |
| VLM timeout/validation/offline-mode anomaly | BP-04, BP-06, VG-1, VG-5 |
| Log/frame loss or corrupt evidence | BP-08 and the full affected procedure; no credit from incomplete run |
| Contact/near-contact or boundary breach | BP-05, relevant FP-01 through FP-05, then a new reviewed L2 test card |
| Hardware/battery/electrical issue | Safe technical inspection, affected bench procedures, and all power/stop tests before motion |
| Unexplained or repeated issue | Treat as Critical/Major as appropriate. No powered retest until independent review resolves the cause and re-verification scope. |

## 8. Requirement links

This runbook protects and collects evidence relevant to REQ-SCP-002, REQ-SEN-001 to REQ-SEN-006, REQ-VLM-001 to REQ-VLM-006, REQ-CAM-001, REQ-CTL-001 to REQ-CTL-002, REQ-ESTOP-001 to REQ-ESTOP-004, REQ-LOG-001 to REQ-LOG-003, and the mapped SYS-, SAFE-, HW-, SW-, DATA-, and TEST- planning IDs in the traceability matrix.
