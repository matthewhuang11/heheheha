"""Temporal filter over Gemini reports. Fast to believe danger, slow to believe safety.
 fire/smoke/drop_off: believed from 1 report, remembered 4 s.   person: believed from 1 report, remembered 2 s.
 other hazards: need 2 of the last 3 reports.   path 'clear' needs 2 clear reports in a row (worst of last 2).
 terrain: worst of last 2.   confidence, best_direction, objects, notes: from the latest report."""
from collections import deque
from robot.types import SceneReport, Hazard, People

FAST = {"fire": 4.0, "smoke": 4.0, "drop_off": 4.0}
PATH_ORDER = ["clear", "unknown", "partially_blocked", "blocked"]
TERRAIN_ORDER = ["flat", "unknown", "water", "uneven", "rubble", "stairs_or_drop"]
DIST_ORDER = ["far", "mid", "near"]
PERSON_HOLD = 2.0

class SceneFilter:
    def __init__(self): self.h = deque(maxlen=8)   # (time, report)
    def push(self, rep, t): self.h.append((t, rep))
    def current(self, now):
        if not self.h: return None
        t_last, last = self.h[-1]
        recent = list(self.h)[-3:]; last2 = [r for _, r in list(self.h)[-2:]]
        seen: dict = {}
        def note(h):
            k = (h.type, h.where)
            if k not in seen or DIST_ORDER.index(h.distance) > DIST_ORDER.index(seen[k].distance): seen[k] = h
        for t, r in self.h:                                        # fast hazards: remembered
            for h in r.hazards:
                if h.type in FAST and now - t <= FAST[h.type]: note(h)
        counts: dict = {}
        for _, r in recent:
            for h in r.hazards:
                if h.type not in FAST: counts.setdefault((h.type, h.where), []).append(h)
        for k, hs in counts.items():
            if len(hs) >= 2 or len(recent) < 2:                    # only one report so far: accept it
                for h in hs: note(h)
        people = last.people
        for t, r in reversed(self.h):
            if r.people.visible and now - t <= PERSON_HOLD: people = r.people; break
        path = max((r.path_ahead for r in last2), key=PATH_ORDER.index)
        terr = max((r.terrain for r in last2), key=TERRAIN_ORDER.index)
        return SceneReport(path_ahead=path, best_direction=last.best_direction, terrain=terr, hazards=list(seen.values())[:12],
                           people=People(**people.model_dump()), objects=last.objects, confidence=min(r.confidence for r in last2), notes=last.notes)
