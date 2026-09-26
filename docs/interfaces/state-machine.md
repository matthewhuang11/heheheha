# Safety lifecycle state machine, V1

**Status:** normative hard safety interface
**Machine version:** `lifecycle/v1`
**Related interfaces:** [world state](world-state.md), [configuration reference](configuration-reference.md), and [log schema](log-schema-v1.json).

## States and invariant

| State | Motors | Meaning |
| --- | --- | --- |
| `BOOTING` | disabled | Process starts. No command may be emitted. |
| `SELF_TEST` | disabled | Hardware and configuration checks run. |
| `READY` | disabled | Self-test passed. Awaiting a local start authorization. |
| `ACTIVE` | enabled only through safety gate | Deterministic control may issue one bounded action. |
| `FAILSAFE_LATCHED` | disabled | A safety fault occurred. Stop is latched pending physical reset. |
| `E_STOP_LATCHED` | physically cut or disabled | Manual kill occurred. Stop is latched pending physical reset. |
| `SHUTDOWN` | disabled | Process is stopping. |

**Invariant:** In every state other than `ACTIVE`, motor-enable is deasserted and the final action is `STOP`. `ACTIVE` does not grant motion by itself. The safety gate must still approve a fresh action using usable sensor data. Any controller uncertainty, state-store failure, motor feedback fault, or illegal transition is handled as `FAILSAFE_LATCHED` and an immediate stop.

### Operator-status projection

The canonical lifecycle values above are the only state values recorded in the lifecycle event. To satisfy the operator-facing terminology used by the controlled baseline, the status display and control-tick record also project a derived condition: `SAFE_STOP` whenever motor enable is disabled, `RUNNING` only in `ACTIVE`, and one or more fault indications (`SENSOR_FAULT`, `VLM_FAULT`, or `CONTROL_FAULT`) when the relevant cause enters or remains in `FAILSAFE_LATCHED`. `E_STOP_LATCHED` additionally displays `E_STOP`. These derived conditions are not additional lifecycle states and cannot create a transition or reset a latch.

## Allowed transitions

| From | To | Trigger and guard | Authority | Required effect |
| --- | --- | --- | --- | --- |
| `BOOTING` | `SELF_TEST` | Config parses and motor enable is confirmed low | system | Emit transition log. |
| `BOOTING` | `FAILSAFE_LATCHED` | Parse failure, state initialization failure, or motor-enable is high | system | Cut/disable motors. |
| `SELF_TEST` | `READY` | Every configured check passes, including kill input, sensor availability, motor-disable feedback, and log sink | system | Keep motors disabled. |
| `SELF_TEST` | `FAILSAFE_LATCHED` | Any self-test fails or times out | system | Cut/disable motors. |
| `READY` | `ACTIVE` | Explicit local start action, fresh usable sensors, no active fault, safety-gate initial check passes, and either a current usable VLM/camera record exists or the test-specific REQ-VLM-006 sensor-only authorization is recorded | local operator | Begin control loop. |
| `ACTIVE` | `FAILSAFE_LATCHED` | Any stale, invalid, unavailable, frozen, or timestamp-faulted required sensor; loop watchdog; motor fault; state failure; illegal transition; permit/renewal/decision timeout; or baseline VLM/camera/cloud fault | system | Final action `STOP`, disable motor-enable, and record the fault indication/cause. |
| `ACTIVE` | `READY` | Explicit local stop with no fault | local operator | Final action `STOP`, disable motor-enable. |
| `FAILSAFE_LATCHED` | `SELF_TEST` | Physical reset accepted | physical reset switch | Reset volatile control state, then rerun every self-test. |
| `E_STOP_LATCHED` | `SELF_TEST` | Kill input released **and** physical reset accepted | physical reset switch | Reset volatile control state, then rerun every self-test. |
| any non-`SHUTDOWN` and non-`E_STOP_LATCHED` | `E_STOP_LATCHED` | Manual kill asserted | system | Independently cut motor-drive energy immediately and record the latch. |
| any non-`SHUTDOWN` | `SHUTDOWN` | Process shutdown | system | Final action `STOP`, disable motor-enable. |

No transition not listed above is legal. `READY` is never entered directly from a latched state, and no transition enters `ACTIVE` after boot, fault, kill, or restart without passing `SELF_TEST` and `READY`.

## Hard veto and latching semantics

The safety gate reevaluates each requested action immediately before motor output. It must override `FORWARD` and `FORWARD_SLOW` to `STOP` when any forward-relevant protective distance is below `safety.forward_stop_cm`, any sensor is not usable, lifecycle is not `ACTIVE`, a permit is older than `safety.permit_ttl_ms`, renewal is older than `safety.action_renewal_ms`, the decision episode is older than `safety.decision_timeout_ms`, or motor feedback is faulty. It must override a turn to `STOP` unless all protective channels are usable, center and the turned-toward side are at least 25 cm, and the lifecycle is `ACTIVE`. It must override `BACK_UP` and every unrecognized action to `STOP`. It records every override in the [log](log-schema-v1.json).

A stale, invalid, unavailable, frozen, or timestamp-faulted individual sensor event, all-invalid sensor event, loop watchdog event, state-store failure, illegal transition, permit failure, motor fault, or baseline VLM/camera/cloud fault enters `FAILSAFE_LATCHED`. A requested or actual manual kill enters `E_STOP_LATCHED` from any non-shutdown state and wins every race. The physical E-stop independently removes motor-drive energy through its hardwired normally-closed path even if the lifecycle controller, Pi, software, network, or cloud is unavailable. Power loss, process restart, or loss of communications leaves motors disabled and begins at `BOOTING`; it never clears a physical kill or authorizes driving.

A valid VLM report can slow or influence the deterministic choice only within [the VLM contract](vlm-contract-v1.schema.json). It cannot suppress a veto, prevent a latch, create a transition, claim reset authority, or authorize `ACTIVE`.

## Reset authority

`physical_reset_switch` means a locally reachable, hardware-wired momentary reset input on the robot. Its acceptance requires the input's configured debounce interval, an inactive manual-kill input for `E_STOP_LATCHED`, motor-enable feedback low, and an event log record. The reset controller creates a cryptographically random `reset_token_id` only after these conditions pass and includes that token in the lifecycle transition event.

There is no remote, cloud, VLM, API, configuration, log-replay, or automatic reset path. A local keyboard command may request a normal `ACTIVE -> READY` stop and an operator may request `READY -> ACTIVE`, but neither can clear either latched state. In simulation or replay, the harness may model the physical reset input only when `hardware.mode` is `simulation` or `replay`; it must set non-hardware provenance and must not control physical motors.

## Transition logging and versioning

Every attempted and completed transition emits a `lifecycle_transition` event under [log schema V1](log-schema-v1.json), including states, trigger, authority, timestamp, monotonic time, run ID, and `reset_token_id` when applicable. Rejected transitions are additionally reported as safety faults and lead to `FAILSAFE_LATCHED` unless already `E_STOP_LATCHED`.

`lifecycle/v1` is closed: adding a state, changing a guard, changing a latch reset path, or relaxing authority requires `lifecycle/v2`, a migration review, and new validation tests. Optional observability fields may be added only if they do not change state semantics or motor safety.
