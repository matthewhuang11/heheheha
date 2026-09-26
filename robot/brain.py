"""Deterministic decision rules. Rules run top to bottom and the FIRST match wins.
evaluate() returns every rule with the evidence behind it (used by the dashboard trace);
decide() just returns the first match, so the trace and the real decision can never disagree.
Philosophy: sensors decide close-range safety; the camera adds things sensors cannot see (fire, smoke, drops, people,
glass) and can only make the robot MORE cautious, never override a close sensor reading. FORWARD (full speed) requires
everything to agree: sensors clear AND camera fresh, healthy, sure, and saying clear + flat."""
from __future__ import annotations
from dataclasses import dataclass, field
from robot.types import Action, SceneReport, Sensors
from robot.config import Policy, DEFAULT

STALE_S = 0.5; NEAR = 25; SIDE_NEAR = 15; SIDE_BACKUP = 40; SLOW = 60; VLM_STALE_S = 6   # kept for reference / older imports
DANGER = {"fire", "smoke", "drop_off"}
RULE_NAMES = {1: "Sensor data stale or all invalid", 2: "Something close ahead (or closing fast, or a floor drop)", 3: "Something close on a side",
              4: "Camera sees fire, smoke or a drop", 5: "Camera sees a person nearby", 6: "Camera says the path is blocked",
              7: "Limited clearance, or anything uncertain", 8: "Everything agrees it is clear"}

@dataclass
class Context:
    """Extra live inputs. All optional: the defaults reproduce the plain rules."""
    policy: Policy = DEFAULT
    camera_healthy: bool = True
    ttc: float | None = None            # seconds to collision at current closing speed (center sensor)
    cliff: float | None = None          # downward sensor cm to floor; None = no such sensor; 999 = no echo (drop)
    latched: frozenset = frozenset()    # {"left","center","right"} still "near" because of hysteresis

@dataclass
class Step:
    rule: int
    name: str
    matched: bool
    applicable: bool
    evidence: str
    action: Action
    reason: str

def _cm(v): return "no echo" if v is None else f"{v:.0f} cm"

def camera_note(sensors, scene, now, scene_at, ctx):
    if scene is None or scene_at is None: return "no camera report yet"
    if not sensors.vlm_online: return "Gemini offline"
    if not ctx.camera_healthy: return "camera image unusable (dark / blocked / frozen)"
    if now - scene_at > ctx.policy.cam_stale_s: return f"camera report is {now - scene_at:.0f}s old (stale)"
    return ""

def evaluate(sensors: Sensors, scene: SceneReport | None, now: float, scene_at: float | None = None, ctx: Context | None = None) -> list[Step]:
    ctx = ctx or Context(); P = ctx.policy
    L, C, R = sensors.values()
    fresh = sensors.fresh(now, P.sensor_stale_s)
    cam_note = camera_note(sensors, scene, now, scene_at, ctx)
    ok = cam_note == ""
    roomier = Action.TURN_LEFT if (L or -1) >= (R or -1) else Action.TURN_RIGHT
    skip = f"skipped: {cam_note}"
    steps: list[Step] = []
    def add(n, matched, evidence, action, reason, applicable=True):
        steps.append(Step(n, RULE_NAMES[n], bool(matched) and applicable, applicable, evidence if applicable else skip, action, reason))

    add(1, (not fresh) or all(v is None for v in (L, C, R)),
        f"sensor data {'fresh' if fresh else 'STALE'}; left {_cm(L)}, center {_cm(C)}, right {_cm(R)}",
        Action.STOP, "sensor data stale or all invalid")
    tight = L is not None and R is not None and L < P.side_backup and R < P.side_backup
    c_near = C is not None and (C < P.stop_cm or "center" in ctx.latched)
    ttc_hit = ctx.ttc is not None and ctx.ttc < P.ttc_stop and C is not None and C < 4 * P.stop_cm
    cliff_hit = ctx.cliff is not None and ctx.cliff > P.cliff_max
    ev2 = f"center {_cm(C)}  (needs < {P.stop_cm:.0f} cm{', latched' if 'center' in ctx.latched and C is not None and C >= P.stop_cm else ''})"
    if ctx.ttc is not None: ev2 += f"; time to collision {ctx.ttc:.1f}s (needs < {P.ttc_stop}s)"
    if ctx.cliff is not None: ev2 += f"; floor sensor {ctx.cliff:.0f} cm (drop if > {P.cliff_max:.0f})"
    if c_near: ev2 += f"; both sides < {P.side_backup:.0f}? {'yes' if tight else 'no'}"
    act2 = Action.BACK_UP if (tight or cliff_hit) else roomier
    add(2, c_near or ttc_hit or cliff_hit, ev2, act2,
        "floor drop ahead" if cliff_hit else "center blocked, both sides tight" if (tight and c_near) else "closing fast on center" if (ttc_hit and not c_near) else "center blocked, turn to more room")
    l_hit = L is not None and (L < P.side_near or "left" in ctx.latched)
    r_hit = R is not None and (R < P.side_near or "right" in ctx.latched)
    add(3, l_hit or r_hit, f"left {_cm(L)}, right {_cm(R)}  (needs < {P.side_near:.0f} cm)",
        Action.TURN_RIGHT if l_hit else Action.TURN_LEFT, "left too close" if l_hit else "right too close")
    if scene is not None:
        haz = [h for h in scene.hazards if h.type in DANGER and (h.distance == "near" or (h.where == "center" and h.distance == "mid"))]
        add(4, bool(haz) or scene.terrain == "stairs_or_drop",
            f"terrain {scene.terrain}; dangerous hazards (fire/smoke/drop, center near-or-mid, or anywhere near): " + (", ".join(f"{h.type} {h.where}/{h.distance}" for h in haz) or "none"),
            Action.BACK_UP, "visual fire, smoke or drop", ok)
        p = scene.people
        add(5, p.visible and p.distance == "near", "person: " + (f"{p.where}, {p.distance}" if p.visible else "none seen"),
            Action.STOP, "person near", ok)
        d = scene.best_direction
        add(6, scene.path_ahead == "blocked", f"path ahead: {scene.path_ahead}; best direction: {scene.best_direction}",
            Action.TURN_LEFT if d == "left" else Action.TURN_RIGHT if d == "right" else roomier,
            f"camera says blocked, {d}" if d in ("left", "right") else "camera says blocked, roomier side", ok)
    else:
        for n, a, r in ((4, Action.BACK_UP, "visual fire, smoke or drop"), (5, Action.STOP, "person near"), (6, roomier, "camera says blocked")):
            add(n, False, "", a, r, False)
    parts, hit = [], False
    if C is None: parts.append("center sensor has no echo, cannot confirm it is clear"); hit = True
    elif C < P.slow_cm: parts.append(f"center {_cm(C)} < {P.slow_cm:.0f} cm"); hit = True
    else: parts.append(f"center {_cm(C)} (needs < {P.slow_cm:.0f})")
    side_close = [n for n, v in (("left", L), ("right", R)) if v is not None and v < P.side_slow]
    if side_close: parts.append(f"{' and '.join(side_close)} < {P.side_slow:.0f} cm"); hit = True
    if ctx.ttc is not None and ctx.ttc < P.ttc_slow: parts.append(f"closing, collision in {ctx.ttc:.1f}s"); hit = True
    if ok and scene is not None:
        why = []
        if scene.path_ahead in ("partially_blocked", "unknown"): why.append(f"path {scene.path_ahead}")
        if scene.terrain != "flat": why.append(f"terrain {scene.terrain}")
        if scene.hazards: why.append("hazards: " + ", ".join(f"{h.type} {h.where}/{h.distance}" for h in scene.hazards))
        if scene.people.visible: why.append(f"person {scene.people.where}/{scene.people.distance}")
        if scene.confidence < P.low_conf: why.append(f"camera unsure (confidence {scene.confidence:.2f})")
        if why: parts.append("camera: " + "; ".join(why)); hit = True
        else: parts.append("camera: path clear, flat, nothing else seen")
    add(7, hit, "; ".join(parts), Action.FORWARD_SLOW, "limited clearance or something uncertain")
    add(8, True, "nothing above matched" + ("" if ok else f" ({cam_note}, so speed is capped at SLOW)"),
        Action.FORWARD if ok else Action.FORWARD_SLOW, "sensors and camera agree it is clear" if ok else "camera unavailable, sensors only")
    return steps

def first_match(steps: list[Step]) -> Step:
    return next(s for s in steps if s.matched)

def decide(sensors: Sensors, scene: SceneReport | None, now: float, scene_at: float | None = None, ctx: Context | None = None) -> tuple[Action, int, str]:
    s = first_match(evaluate(sensors, scene, now, scene_at, ctx))
    return s.action, s.rule, s.reason
