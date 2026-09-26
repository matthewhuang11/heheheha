"""Pure, conservative decision function. It cannot authorize motion."""
from robot.types import Action, Decision, Snapshot

_REDUCING_HAZARDS = {"fire", "smoke", "water", "wire", "glass", "drop_off", "unstable_debris"}

def decide(snapshot: Snapshot) -> Decision:
    now = snapshot.monotonic_now_ms
    if not snapshot.all_sensors_usable():
        return Decision(Action.STOP, 1)
    if len([t for t in snapshot.turn_attempts_ms if now - t <= 10_000]) >= 4:
        return Decision(Action.STOP, 8)
    # A valid person always stops, irrespective of reported distance.
    scene = snapshot.scene if snapshot.scene and snapshot.scene.usable(now) and snapshot.vlm_status == "online" else None
    if scene and scene.people_visible:
        return Decision(Action.STOP, 5)
    # The baseline does not permit visual evidence to select turn direction.
    if scene and (scene.path_ahead in {"blocked", "partially_blocked"} or scene.terrain in {"stairs_or_drop", "water"} or any(h["type"] in _REDUCING_HAZARDS for h in scene.hazards)):
        return Decision(Action.FORWARD_SLOW if scene.path_ahead == "partially_blocked" else Action.STOP, 4 if scene.path_ahead == "clear" else 6)
    if snapshot.center.distance_cm < 60 or (scene and scene.terrain in {"rubble", "uneven"}):
        return Decision(Action.FORWARD_SLOW, 7)
    # Baseline runs fail closed if VLM/camera evidence is unavailable.
    if scene is None:
        return Decision(Action.STOP, 1)
    return Decision(Action.FORWARD, 8)
