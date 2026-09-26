"""Fuse YOLO person detections with Gemini's people report WITHOUT changing the brain (spec 8.3).
1. Gemini report fresh: if YOLO sees a person Gemini missed (or nearer), a COPY of the report with people set from YOLO
   goes into Controller.step(). YOLO can add a person, never remove one Gemini saw. Nearer distance wins.
2. Gemini offline/stale: the brain skips its camera rules; the safety gate adds 'person ahead (YOLO)' (see gate.py).
3. The fused copy is CACHED and only rebuilt when a new Gemini report arrives or YOLO's person changes, because the
   controller's SceneFilter treats every new report object as a new report."""
from __future__ import annotations
from robot.types import People, SceneReport
from scoutbot.perception.yolo import DIST_RANK, nearest
from scoutbot.types import PersonDetection

def fresh_person(dets: list[PersonDetection], det_at: float | None, now: float, max_age: float) -> PersonDetection | None:
    if not dets or det_at is None or now - det_at > max_age: return None
    return nearest(dets)

class Fuser:
    def __init__(self): self._key = None; self._out = None; self.disagreements = {"yolo_only": 0, "gemini_only": 0}; self._last_state = None
    def fuse(self, scene: SceneReport | None, person: PersonDetection | None) -> SceneReport | None:
        if scene is None: return None
        yk = None if person is None else (person.where, person.distance)
        key = (id(scene), yk)
        if key == self._key: return self._out
        out = scene
        gp = scene.people
        if person is not None:
            if not gp.visible or DIST_RANK[person.distance] > DIST_RANK[gp.distance]:
                out = scene.model_copy(update={"people": People(visible=True, where=person.where, distance=person.distance)})
        state = ("yolo_only" if person is not None and not gp.visible else "gemini_only" if person is None and gp.visible else None)
        if state and state != self._last_state: self.disagreements[state] += 1
        self._last_state = state
        self._key = key; self._out = out
        return out
