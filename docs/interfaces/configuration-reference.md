# Configuration reference, V1

**Status:** normative for deployed and simulated V1 runs
**Configuration version:** `config/v1`
**Related interfaces:** [world state](world-state.md), [state machine](state-machine.md), [VLM contract](vlm-contract-v1.schema.json), and [log schema](log-schema-v1.json).

## Configuration document rules

The deployed YAML document MUST contain `config_version: config/v1`. Unknown keys, duplicate YAML keys, implicit units, non-finite numbers, environment-variable interpolation in safety fields, and values outside the ranges below are startup errors. The loader validates before any motor-enable request. All durations are integer milliseconds, all distances are decimal centimetres, rates are hertz, and motor duties are unitless fractions of full-scale output.

A run records the SHA-256 of the canonicalized, secret-free configuration in each run manifest. Credentials are references to an OS secret store and MUST NOT appear in YAML, snapshots, or logs. A config reload may update only reloadable VLM pacing and log-retention keys while `READY`; it can never reset a latch or alter a running safety threshold.

## Required settings

| YAML path | Type, unit, default | Allowed range | Rule |
| --- | --- | --- | --- |
| `control.rate_hz` | integer Hz, `20` | `10..100` | Control loop tick period is `1000 / rate_hz` ms. |
| `sensors.sample_rate_hz` | integer Hz, `20` | `10..50` | One complete left-center-right sequence per value. |
| `sensors.filter_window_samples` | integer samples, `3` | `3..5`, odd only | Median window per sensor. |
| `sensors.min_distance_cm` | decimal cm, `2.0` | `2.0..10.0` | Reject lower hardware reports. |
| `sensors.max_distance_cm` | decimal cm, `400.0` | `100.0..400.0` | Reject higher hardware reports. |
| `safety.sensor_ttl_ms` | integer ms, `500` | `100..500` | Must be `<= 10_000 / control.rate_hz`. |
| `safety.forward_stop_cm` | decimal cm, `25.0` | exactly `25.0` | Any forward-relevant protective channel below this distance vetoes forward motion. |
| `decision.center_near_cm` | decimal cm, `25.0` | `safety.forward_stop_cm..100.0` | Source decision-rule threshold, retained for non-motion planning only. |
| `decision.side_near_cm` | decimal cm, `15.0` | `5.0..50.0` | Rule 3 threshold. |
| `decision.center_slow_cm` | decimal cm, `60.0` | `decision.center_near_cm..200.0` | Rule 7 threshold. |
| `safety.permit_ttl_ms` | integer ms, `150` | `1..150` | A non-stop permit expires unless accepted by the motor layer within this interval. |
| `safety.action_renewal_ms` | integer ms, `500` | `1..500` | A continuous non-stop action requires safety-gate reevaluation and renewal within this interval. |
| `safety.decision_timeout_ms` | integer ms, `3000` | `100..3000` | A non-stop episode without a new decision record expires at this age. |
| `safety.max_missed_ticks` | integer ticks, `3` | exactly `3` | Do not weaken the loop watchdog in V1. |
| `motion.turn_hold_ms` | integer ms, `600` | `600..2000` | Minimum committed turn duration. |
| `motion.max_forward_duty` | decimal fraction, `0.35` | `0.01..0.35` | Absolute motor command cap for `FORWARD`. |
| `motion.max_slow_forward_duty` | decimal fraction, `0.20` | `0.01..motion.max_forward_duty` | Cap for `FORWARD_SLOW`. |
| `motion.max_turn_duty` | decimal fraction, `0.25` | `0.01..0.35` | Absolute duty cap for turns. |
| `motion.ramp_duty_per_s` | decimal fraction/s, `0.30` | `0.01..1.00` | Max output slew rate. |
| `motion.max_translation_mps` | decimal m/s, `0.10` | `0.01..0.10` | Measured translational-speed cap. |
| `motion.max_turn_rate_rad_s` | decimal rad/s, `0.35` | `0.01..0.35` | Measured turn-rate cap. |
| `motion.max_accel_mps2` | decimal m/s², `0.20` | `0.01..0.20` | Measured translational-acceleration cap. |
| `motion.max_angular_accel_rad_s2` | decimal rad/s², `0.50` | `0.01..0.50` | Measured rotational-acceleration cap. |
| `vlm.request_period_ms` | integer ms, `2000` | `1000..3000` | Latest frame only, never a queued backlog. |
| `vlm.timeout_ms` | integer ms, `4000` | `100..4000` | Timeout is inclusive: at 4001 ms reject. |
| `vlm.scene_ttl_ms` | integer ms, `6000` | `1000..6000` | Counts from frame capture time. |
| `vlm.offline_after_failures` | integer replies, `3` | exactly `3` | Do not increase in V1. |
| `logging.event_retention_days` | integer days, `30` | `1..30` | See [logging and privacy](#logging-and-privacy). |
| `logging.frame_retention_days` | integer days, `7` | `0..7` | `0` disables saving raw frames. |

The configuration MUST satisfy: `min_distance_cm < forward_stop_cm <= center_near_cm <= center_slow_cm <= max_distance_cm`; `max_slow_forward_duty <= max_forward_duty`; `permit_ttl_ms <= action_renewal_ms <= decision_timeout_ms`; `timeout_ms <= scene_ttl_ms`; and `frame_retention_days <= event_retention_days`. A failing relationship is a startup error, not a value to clamp.

## Actions and hardware mapping

The only accepted action names are `STOP`, `FORWARD`, `FORWARD_SLOW`, `TURN_LEFT`, and `TURN_RIGHT`. The source V1 `BACK_UP` value is not accepted by this controlled baseline and maps to `STOP` at the safety gate. `STOP` maps to left and right duty `0.0` and disables the motor-enable line. Every non-stop wheel duty must remain in `[-1.0, 1.0]` and within the action-specific caps above. Pin assignments are deployment-specific but must be non-negative integers `0..53`, unique across output functions, and validated against the selected board profile before startup.

`hardware.mode` is either `real`, `simulation`, or `replay`. `real` requires the physical kill input and motor-enable feedback. `simulation` and `replay` MUST set the corresponding [world-state provenance](world-state.md#2-common-representation-and-clock-rules) and MUST never energize a motor driver.

## Lifecycle and authority settings

`lifecycle.start_authority` is exactly `local_operator`. The optional local operator identity is an audited short ID matching `^[a-z][a-z0-9_-]{0,31}$`; it is not a network identity. `lifecycle.reset_authority` is exactly `physical_reset_switch`. These settings are immutable while running and are constraints, not permissions granted to software. A VLM response, provider result, remote request, config reload, log replay, or process restart can never start `ACTIVE` or reset `FAILSAFE_LATCHED` or `E_STOP_LATCHED`. See [state machine reset authority](state-machine.md#reset-authority).

## Logging and privacy

Logs conform to [log-schema-v1.json](log-schema-v1.json). Store JSONL logs encrypted at rest when the host supports it and restrict read access to authorized operators and replay tooling. Keep events no more than 30 days and raw frames no more than 7 days by default. Delete raw frames before their parent log unless an approved incident hold exists. The hold record must identify an authorized local operator, reason, item IDs, and expiry, but contains no image, credentials, or personal identity beyond the operator short ID.

Never log raw VLM responses, prompt text, API credentials, Wi-Fi credentials, absolute paths, face embeddings, names, voice content, or precise location. Store frame IDs, SHA-256 values, bounded schema fields, and redacted bounded notes only. No configuration option allows the VLM to change retention, redaction, action caps, safety thresholds, lifecycle, or reset authority.

## Versioning and deployment

A new optional key may be introduced in a compatible `config/v1` minor release only with a documented default. Removing a key, changing a unit, widening a safety maximum, or changing an enum requires `config/v2`. Deployment validates configuration, records its digest, executes self-test, and enters `READY` with motors disabled. A failure leaves the lifecycle in a non-active state as defined in [state machine](state-machine.md).
