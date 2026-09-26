"""Fuse YOLO person detections with Gemini's people report WITHOUT changing the brain (spec 8.3).
1. Gemini report fresh: if YOLO sees a person Gemini missed (or nearer), a COPY of the report with people set from YOLO
   goes into Controller.step(). YOLO can add a person, never remove one Gemini saw. Nearer distance wins.
2. Gemini offline/stale: the brain skips its camera rules; the safety gate adds 'person ahead (YOLO)' (see gate.py).
3. There is ONE fused copy per Gemini report (KI-11). A YOLO-only change updates that copy's people in place, so the
   controller's SceneFilter (which treats every new report object as a new report) sees exactly one report per Gemini call."""
from __future__ import annotations
from robot.types import People, SceneReport
from scoutbot.perception.yolo import DIST_RANK, nearest
from scoutbot.types import PersonDetection

def fresh_person(dets: list[PersonDetection], det_at: float | None, now: float, max_age: float) -> PersonDetection | None:
    if not dets or det_at is None or now - det_at > max_age: return None
    return nearest(dets)

class Fuser:
    def __init__(self):
        self._key = None; self._out = None; self.disagreements = {"yolo_only": 0, "gemini_only": 0}; self._last_state = None
        self._suppressed: list[tuple[float, float, float]] = []
        self._copy_src = None; self._copy = None          # KI-11: the one fused copy of the current Gemini report

    def suppress(self, positions: list[tuple[float, float, float]]):
        """Replace the active handled-survivor positions for this control tick: (x_cm, y_cm, radius_cm)."""
        self._suppressed = positions

    def is_suppressed(self, position: tuple[float, float] | None) -> bool:
        if position is None: return False
        x, y = position
        return any((x - sx) ** 2 + (y - sy) ** 2 <= radius ** 2 for sx, sy, radius in self._suppressed)

    def fuse(self, scene: SceneReport | None, person: PersonDetection | None,
             person_position: tuple[float, float] | None = None,
             scene_position: tuple[float, float] | None = None) -> SceneReport | None:
        if scene is None: return None
        person_suppressed = person is not None and self.is_suppressed(person_position)
        scene_suppressed = scene.people.visible and self.is_suppressed(scene_position)
        yk = None if person is None else (person.where, person.distance)
        key = (id(scene), yk, person_suppressed, scene_suppressed)
        if key == self._key: return self._out
        out = scene
        gp = scene.people
        if scene_suppressed:
            gp = People(visible=False, where="none", distance="none")
        if person_suppressed: person = None
        people = gp
        if person is not None:
            if not gp.visible or DIST_RANK[person.distance] > DIST_RANK[gp.distance]:
                people = People(visible=True, where=person.where, distance=person.distance)
        if people is not scene.people:
            # KI-11: ONE private copy per Gemini report. When only YOLO's person (or suppression) changes, update that copy's
            # people in place instead of making a new object, so the brain's SceneFilter (which counts every new object as a
            # new report) never sees phantom extra reports that double-count hazards in its 2-of-3 rule.
            if self._copy_src is not scene:
                self._copy_src = scene; self._copy = scene.model_copy()
            self._copy.people = people
            out = self._copy
        elif self._copy_src is scene and self._out is self._copy:
            # the copy was already handed to the brain for this report: keep handing it over, with Gemini's own people
            self._copy.people = scene.people; out = self._copy
        state = ("yolo_only" if person is not None and not gp.visible else "gemini_only" if person is None and gp.visible else None)
        if state and state != self._last_state: self.disagreements[state] += 1
        self._last_state = state
        self._key = key; self._out = out
        return out
