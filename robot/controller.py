"""Stateful wrapper around the pure rules: filters sensors and camera reports, applies hysteresis, holds turns
so the robot does not flicker, and notices when it is stuck. This is what a real robot loop (or the dashboard) calls ~10 Hz."""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
from robot.types import Action, Sensors
from robot.config import Policy, DEFAULT
from robot.brain import Context, evaluate, first_match, Step
from robot.sensing import SensorFilter
from robot.scene_filter import SceneFilter

TURNS = {Action.TURN_LEFT, Action.TURN_RIGHT}
FWD = {Action.FORWARD, Action.FORWARD_SLOW}
AVOID = TURNS | {Action.BACK_UP}
TURN_HOLD_S = 0.6

@dataclass
class Decision:
    action: Action; rule: int; reason: str; steps: list[Step]; fired: int
    filtered: Sensors; scene: object; notes: list = field(default_factory=list); stuck: bool = False

def _flip(a): return Action.TURN_RIGHT if a == Action.TURN_LEFT else Action.TURN_LEFT if a == Action.TURN_RIGHT else a

class Controller:
    def __init__(self, policy: Policy = DEFAULT):
        self.P = policy; self.f = [SensorFilter() for _ in range(3)]; self.sf = SceneFilter(); self.cliff = None
        self.latched: set = set(); self.last_report_id = None
        self.last_turn = None; self.last_turn_at = -99.0
        self.avoid_starts = deque(); self.prev_action = None; self.fwd_since = None
        self.flip_until = -1.0; self.last_flip_at = -99.0; self.stop_until = -1.0
        self.events = {"stuck": 0, "flips": 0}

    def step(self, raw: Sensors, report, report_at, cam_healthy: bool, now: float, cliff=None, bypass_scene_filter=False) -> Decision:
        P = self.P; notes = []
        raws = (raw.left if raw.valid[0] else None, raw.center if raw.valid[1] else None, raw.right if raw.valid[2] else None)
        if raw.fresh(now, P.sensor_stale_s):
            vals = [f.push(v, now) for f, v in zip(self.f, raws)]
        else: vals = [f.value() for f in self.f]
        filt = Sensors(left=vals[0], center=vals[1], right=vals[2], updated_at=raw.updated_at, vlm_online=raw.vlm_online)
        if report is not None and report_at is not None and id(report) != self.last_report_id:
            self.sf.push(report, report_at); self.last_report_id = id(report)
        scene = None if report is None else (report if bypass_scene_filter else self.sf.current(now))
        if bypass_scene_filter and report is not None: notes.append("scene filter bypassed (frozen / random test scene)")
        # hysteresis: once "near", stay near until clearly farther
        for name, v, thr in (("center", vals[1], P.stop_cm), ("left", vals[0], P.side_near), ("right", vals[2], P.side_near)):
            if v is not None and v < thr: self.latched.add(name)
            elif name in self.latched and (v is None or v >= thr + P.leave_margin): self.latched.discard(name)
        ctx = Context(P, cam_healthy, self.f[1].ttc(now), cliff, frozenset(self.latched))
        steps = evaluate(filt, scene, now, report_at, ctx); fs = first_match(steps)
        action, rule, reason = fs.action, fs.rule, fs.reason
        # keep turning briefly instead of flip-flopping (never delays a STOP, BACK_UP or close-range rule)
        if action in TURNS | FWD and rule > 2 and self.last_turn and now - self.last_turn_at < TURN_HOLD_S and action != self.last_turn:
            notes.append(f"holding {self.last_turn.value} for {TURN_HOLD_S}s to avoid flicker"); action = self.last_turn
        # stuck handling
        if now < self.stop_until: action, rule, reason = Action.STOP, 0, "stuck: stopped, waiting for a person"; notes.append("stuck")
        elif now < self.flip_until and action in TURNS: action = _flip(action); notes.append("stuck recovery: turning the other way")
        if action != self.prev_action:
            if action in AVOID and self.prev_action not in AVOID: self.avoid_starts.append(now)
            self.fwd_since = now if action in FWD else None
        if action in FWD and self.fwd_since is not None and now - self.fwd_since >= 1.0: self.avoid_starts.clear()
        while self.avoid_starts and now - self.avoid_starts[0] > 10: self.avoid_starts.popleft()
        stuck = False
        if len(self.avoid_starts) >= 4 and now >= self.stop_until:
            self.avoid_starts.clear()
            if now - self.last_flip_at < 20: self.stop_until = now + 3; self.events["stuck"] += 1; stuck = True; notes.append("STUCK: stopping")
            else: self.flip_until = now + 3; self.last_flip_at = now; self.events["flips"] += 1; notes.append("stuck recovery started")
        if action in TURNS and (self.prev_action not in TURNS or action != self.prev_action): self.last_turn_at = now   # a new turn starts
        if action in TURNS: self.last_turn = action
        self.prev_action = action
        return Decision(action, rule, reason, steps, steps.index(fs), filt, scene, notes, stuck)
