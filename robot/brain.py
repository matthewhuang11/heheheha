from __future__ import annotations
from robot.types import Action, SceneReport, Sensors
STALE_S=0.5; NEAR=25; SIDE_NEAR=15; SIDE_BACKUP=40; SLOW=60; VLM_STALE_S=6

def decide(sensors: Sensors, scene: SceneReport|None, now: float, scene_at: float|None=None)->tuple[Action,int,str]:
    left, center, right=sensors.values(); scene_ok=scene is not None and sensors.vlm_online and scene_at is not None and now-scene_at<=VLM_STALE_S
    if not sensors.fresh(now) or all(v is None for v in (left,center,right)): return Action.STOP,1,"sensor data stale or all invalid"
    if center is not None and center<NEAR:
        if left is not None and right is not None and left<SIDE_BACKUP and right<SIDE_BACKUP: return Action.BACK_UP,2,"center blocked, both sides tight"
        return (Action.TURN_LEFT if (left or -1)>=(right or -1) else Action.TURN_RIGHT),2,"center blocked, turn to more room"
    if left is not None and left<SIDE_NEAR: return Action.TURN_RIGHT,3,"left too close"
    if right is not None and right<SIDE_NEAR: return Action.TURN_LEFT,3,"right too close"
    if scene_ok:
        danger=any(h.where=="center" and h.distance in {"near","mid"} and h.type in {"fire","smoke","drop_off"} for h in scene.hazards)
        if danger or scene.terrain=="stairs_or_drop": return Action.BACK_UP,4,"visual center hazard or drop"
        if scene.people.visible and scene.people.distance=="near": return Action.STOP,5,"person near"
        if scene.path_ahead=="blocked":
            if scene.best_direction=="left": return Action.TURN_LEFT,6,"VLM says blocked, left"
            if scene.best_direction=="right": return Action.TURN_RIGHT,6,"VLM says blocked, right"
            return (Action.TURN_LEFT if (left or -1)>=(right or -1) else Action.TURN_RIGHT),6,"VLM says blocked, roomier side"
        if (center is not None and center<SLOW) or scene.path_ahead=="partially_blocked" or scene.terrain in {"rubble","uneven"}: return Action.FORWARD_SLOW,7,"limited clearance or visual caution"
    if not scene_ok: return Action.FORWARD_SLOW,8,"VLM unavailable or stale"
    return Action.FORWARD,8,"clear sensors and scene"
