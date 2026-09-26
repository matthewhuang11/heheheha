"""Final fail-closed motion-permit authority for V1."""
from robot.types import Action, GateResult, Lifecycle, Snapshot

def gate(requested: Action | str, snapshot: Snapshot) -> GateResult:
    now = snapshot.monotonic_now_ms
    reasons: set[str] = set()
    try:
        action = requested if isinstance(requested, Action) else Action(requested)
    except ValueError:
        return GateResult(Action.STOP, None, frozenset({"reverse_rejected"}))
    if snapshot.manual_kill:
        return GateResult(Action.STOP, None, frozenset({"manual_kill"}), "E_STOP")
    if snapshot.lifecycle is not Lifecycle.ACTIVE:
        reasons.add("lifecycle_not_active")
    if snapshot.motor_fault:
        reasons.add("motor_fault")
    if not snapshot.all_sensors_usable():
        reasons.add("sensor_invalid")
    scene_ok = snapshot.scene is not None and snapshot.scene.usable(now) and snapshot.vlm_status == "online"
    if not scene_ok:
        reasons.add("vlm_fault")
    if snapshot.decision_started_ms is not None and now - snapshot.decision_started_ms > 3000:
        reasons.add("decision_timeout")
    if snapshot.last_renewed_ms is not None and now - snapshot.last_renewed_ms > 500:
        reasons.add("renewal_expired")
    if action is Action.STOP:
        return GateResult(Action.STOP, None, frozenset(reasons))
    if reasons:
        return GateResult(Action.STOP, None, frozenset(reasons), "CONTROL_FAULT" if "motor_fault" in reasons else None)
    distances = {"left": snapshot.left.distance_cm, "center": snapshot.center.distance_cm, "right": snapshot.right.distance_cm}
    if action in {Action.FORWARD, Action.FORWARD_SLOW}:
        if any(distance < 25 for distance in distances.values()):
            return GateResult(Action.STOP, None, frozenset({"forward_clearance"}))
        threshold = 60 if action is Action.FORWARD else 40
        if distances["center"] < threshold:
            return GateResult(Action.STOP, None, frozenset({"forward_clearance"}))
    if action in {Action.TURN_LEFT, Action.TURN_RIGHT}:
        toward = "left" if action is Action.TURN_LEFT else "right"
        if distances["center"] < 25 or distances[toward] < 25:
            return GateResult(Action.STOP, None, frozenset({"turn_clearance"}))
    return GateResult(action, now, frozenset())
