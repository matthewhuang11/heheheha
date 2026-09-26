# World-state interface, V1

**Status:** normative for V1 runtime workers
**Interface version:** `world-state/v1`
**Related interfaces:** [VLM contract](vlm-contract-v1.schema.json), [configuration reference](configuration-reference.md), [state machine](state-machine.md), and [log schema](log-schema-v1.json).

## 1. Purpose and ownership

`WorldState` is the single in-process, thread-safe latest-value store. Workers may publish only their assigned facts and may not call one another or command a motor through this interface. A `snapshot()` is immutable and represents one atomically captured view.

| Writer | May write | May not write |
| --- | --- | --- |
| sensor reader | `sensors` | scene, lifecycle, commands, motor output |
| camera source | `frame` metadata | scene, sensor values, commands |
| VLM client and validator | `scene` and VLM health | actions, lifecycle, motor output |
| control loop | `control_health`, decision record | raw measurements, motor output |
| safety gate | `safety` and final action record | sensor or scene facts |
| lifecycle controller | `lifecycle` | actions or source observations |

The motor layer accepts a command only from the safety gate after the lifecycle controller permits motion. `WorldState` itself has no method that drives hardware.

## 2. Common representation and clock rules

All state records use the following fields. Names are `snake_case`; enum values are lowercase ASCII.

| Field | Type and strict rule |
| --- | --- |
| `schema_version` | Exact string `world-state/v1`. A reader must reject any other major version. |
| `observed_at` | UTC RFC 3339 timestamp with `Z` offset and millisecond precision, for example `2026-09-26T02:37:56.382Z`. This is when the source measured or captured the fact. |
| `received_at` | UTC RFC 3339 timestamp in the same format. This is when the process accepted the fact. It MUST be no earlier than `observed_at` and no more than 10 s later. |
| `monotonic_observed_ms` | Integer milliseconds from the current process monotonic clock, range `0..9_007_199_254_740_991`. Used for expiry because wall clocks may change. |
| `source_id` | `^[a-z][a-z0-9_-]{0,31}$`, stable for a process run, such as `ultrasonic_center` or `gemini`. |
| `provenance` | One of `hardware`, `provider`, `derived`, `operator`, `replay`, or `simulation`. |
| `validity` | One of `valid`, `invalid`, `expired`, `unavailable`, or `rejected`. `valid` means the record passed its source and interface checks, not that an area is safe. |
| `expires_at_monotonic_ms` | Integer monotonic expiry. It MUST equal `monotonic_observed_ms + ttl_ms`; it is never extended by a reader. |

A fact is **usable** only when `validity == valid`, its required fields meet their range rules, and `snapshot.monotonic_now_ms < expires_at_monotonic_ms`. At equality it is expired. A snapshot exposes both the stored validity and `usable` so replay can retain evidence after expiry. Consumers MUST use `usable`, not a recomputed wall-clock age.

The publisher validates raw values before replacing a prior record. An invalid, unavailable, or rejected record is published as a new record and does not silently preserve an older valid value. Clock regression or a received timestamp more than 10 s after observation makes the record `rejected`.

## 3. Snapshot shape

```text
Snapshot {
  schema_version: "world-state/v1"
  snapshot_id: UUIDv4
  captured_at: UTC timestamp
  monotonic_now_ms: non-negative integer
  lifecycle: LifecycleFact
  sensors: { left: DistanceFact, center: DistanceFact, right: DistanceFact }
  frame: FrameFact | null
  scene: SceneFact | null
  vlm_health: VlmHealthFact
  control_health: ControlHealthFact
  decision: DecisionFact | null
  safety: SafetyFact
}
```

`captured_at` and `monotonic_now_ms` are captured under the same state lock. A snapshot never mixes fields from different atomic updates. `null` means no record has ever been accepted in the current run, not a valid negative observation.

### 3.1 DistanceFact

```text
DistanceFact {
  common fields
  ttl_ms: integer 1..500, default 500
  distance_cm: number 2.0..400.0 | null
  filter_window_samples: integer 3..5
  usable: boolean
  invalid_reason: none | no_echo | out_of_range | electrical_fault |
                  timestamp_error | source_error
}
```

When `validity` is `valid`, `distance_cm` is required and `invalid_reason` is `none`. Otherwise `distance_cm` MUST be `null` and `invalid_reason` MUST NOT be `none`. Centimetres are measured from the transducer face along its configured axis. `no_echo` is not evidence of clear space. The sensor reader samples one transducer at a time and publishes the median of the stated filter window.

All three fields have independent expiry. A fresh left or right value does not make a stale center value fresh. The safety gate MUST treat a sensor snapshot as stale if **any** distance fact is not usable. The decision engine MUST stop if all three are invalid or unavailable, and follow the configured stale-sensor policy otherwise.

### 3.2 FrameFact

```text
FrameFact {
  common fields
  ttl_ms: integer 1..6000, default 3000
  frame_id: UUIDv4
  width_px: integer 160..1920
  height_px: integer 120..1080
  encoding: jpeg | png
  content_sha256: lowercase 64-character SHA-256 hex
  storage_ref: opaque relative run-local path | null
  usable: boolean
}
```

The camera timestamp is capture time, not VLM response time. `storage_ref` must not be an absolute path, URL containing credentials, or user-identifying filename. Raw frame access is local, least-privilege, and governed by the retention settings in [configuration reference](configuration-reference.md#logging-and-privacy).

### 3.3 SceneFact and VLM health

`SceneFact` contains the complete object accepted by [the VLM JSON Schema](vlm-contract-v1.schema.json), plus common fields and:

| Field | Strict rule |
| --- | --- |
| `frame_id` | Required UUIDv4 of the exact input frame. |
| `prompt_version` | `scene-v1` only. |
| `request_id` | UUIDv4 generated client-side. |
| `round_trip_ms` | Integer `1..4000`; requests that exceed 4000 ms are rejected. |
| `ttl_ms` | Integer `1..6000`, default 6000, measured from `frame.observed_at`, not response receipt. |
| `usable` | Computed using this expiry rule. |

A report is publishable only if schema validation succeeds with no coercion, the referenced frame is known, the frame hash is recorded in the request provenance, and the request completed within the configured timeout. Validation failures use `validity: rejected` and have no decision content. VLM output is descriptive evidence only: it may not select an action or turn direction, alter lifecycle, clear a safety latch, reset a watchdog, or assert that a sensor path is safe. See [VLM bounded role](vlm-contract-v1.schema.json).

`VlmHealthFact` has `status` of `online`, `degraded`, or `offline`; `consecutive_failures` `0..3`; `last_success_at` or `null`; and `last_error` of `none`, `timeout`, `transport`, `provider`, or `validation`. Three consecutive failures set `offline`. One valid report sets `online` and zeroes the counter. In the baseline profile, an offline status or unusable scene enters `FAILSAFE_LATCHED` with the derived `VLM_FAULT` indication and no motion permit. Only a test-specific REQ-VLM-006 authorization may select the separately recorded sensor-only experiment profile. That profile begins with VLM unavailable, permits only `FORWARD_SLOW` or turns at its lower speed cap, and still stops and latches on every sensor, control, operator, or ODD fault.

### 3.4 Control, decision, and safety facts

`ControlHealthFact` includes `tick_sequence` (`0..2^63-1`), `tick_period_ms` (`10..100`, default 50), and `consecutive_missed_ticks` (`0..3`). A missed tick occurs when the elapsed monotonic time since the preceding completed tick exceeds twice `tick_period_ms`. At 3, the lifecycle controller enters `FAILSAFE_LATCHED`.

`DecisionFact` records `decision_id` (UUIDv4), `decided_at`, requested action (`STOP`, `FORWARD`, `FORWARD_SLOW`, `TURN_LEFT`, or `TURN_RIGHT`), rule ID `1..8`, and `decision_snapshot_id`. The controlled V1 safety gate records a requested source-design `BACK_UP` as a rejected action with final `STOP`. A decision is evidence only until paired with a safety record.

`SafetyFact` records the final action in the same enum, `outcome` (`passed`, `overridden`, `latched_stop`, `cut_power`), a `motion_permit` result, and zero or more veto reasons: `sensor_stale`, `sensor_invalid`, `all_sensors_invalid`, `forward_clearance`, `turn_clearance`, `permit_expired`, `renewal_expired`, `decision_timeout`, `loop_watchdog`, `manual_kill`, `lifecycle_not_active`, `vlm_fault`, `camera_fault`, `reverse_rejected`, or `motor_fault`. It must include `evaluated_snapshot_id` and `evaluated_at`. A final action is authoritative only when it references the current or immediately preceding control snapshot, is no more than 50 ms old, and lifecycle is `ACTIVE`.

## 4. Versioning and compatibility

The `world-state/v1` major version is immutable. Producers may add optional fields only after a minor release is documented, but consumers MUST ignore unknown optional fields and MUST reject changed meanings, units, enums, or required fields under V1. Any incompatible change requires `world-state/v2`, a new schema/document, and a dual-reader migration period. Never infer units from a field name or convert values on receipt.

## 5. Privacy and replay provenance

World state is in-memory operational data. It MUST NOT contain names, faces, voice content, location coordinates, account identifiers, prompt secrets, API keys, network credentials, or free-text VLM content except the bounded `notes` field accepted by the VLM contract. `notes` is non-control data and is subject to log redaction. Replay or simulation inputs MUST set `provenance` accordingly and MUST NOT be presented as hardware evidence.

Every persisted snapshot reference is logged according to [log-schema-v1.json](log-schema-v1.json). Logs preserve `source_id`, `provenance`, validation outcome, and schema versions so decisions can be reproduced without treating stale facts as current.
