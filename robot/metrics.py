"""What to track while testing (see the policy doc, section 4). Feed it every decision tick; read summary() any time."""
from collections import Counter, deque

class Metrics:
    def __init__(self):
        self.vlm_ok = 0; self.vlm_fail = 0; self.lat = deque(maxlen=200)
        self.ticks = 0; self.cam_fresh = 0; self.cam_unhealthy = 0
        self.no_echo = [0, 0, 0]; self.actions = Counter(); self.rules = Counter()
        self.disagree = Counter(); self.events = deque(maxlen=40)
        self.near_miss = 0; self.stuck = 0; self.flips = 0
        self.turns = deque(); self.changes = deque(); self.last_action = None; self.last_turn = None; self._nm_on = False
    def vlm(self, ok, latency=None):
        if ok: self.vlm_ok += 1; self.lat.append(latency or 0)
        else: self.vlm_fail += 1
    def tick(self, now, wall, raw_vals, dec, cam_fresh, cam_healthy, stuck_events=0):
        self.ticks += 1; self.cam_fresh += bool(cam_fresh); self.cam_unhealthy += (not cam_healthy)
        for i, v in enumerate(raw_vals): self.no_echo[i] += (v is None)
        a = dec.action.value; self.actions[a] += 1; self.rules[dec.rule] += 1; self.stuck = stuck_events
        if a != self.last_action:
            self.changes.append(now)
            if dec.action.value.startswith("TURN"):
                if self.last_turn and self.last_turn != a: self.turns.append(now)
                self.last_turn = a
            self.last_action = a
        for dq in (self.turns, self.changes):
            while dq and now - dq[0] > 60: dq.popleft()
        C = raw_vals[1]; moving = a.startswith("FORWARD")
        nm = C is not None and C < 15 and moving
        if nm and not self._nm_on: self.near_miss += 1; self._log(wall, "NEAR MISS", f"center {C:.0f} cm while {a}")
        self._nm_on = nm
        f = dec.filtered; s = dec.scene; L, Cf, R = f.values()
        if cam_fresh and s is not None:
            self._d(wall, "camera clear, sensor near", s.path_ahead == "clear" and Cf is not None and Cf < 40, f"camera clear but center {Cf and round(Cf)} cm")
            self._d(wall, "camera blocked, sensors far", s.path_ahead == "blocked" and Cf is not None and Cf > 100 and (L or 999) > 60 and (R or 999) > 60, "camera blocked but all sensors far")
            self._d(wall, "hazard seen, sensors far", any(h.type in {"fire", "smoke", "drop_off"} for h in s.hazards) and Cf is not None and Cf > 100, "hazard the sensors cannot see")
            self._d(wall, "person near, sensors far", s.people.visible and s.people.distance == "near" and Cf is not None and Cf > 100, "person near but center far")
            self._d(wall, "no echo, camera says clear", Cf is None and s.path_ahead == "clear", "center no echo, camera clear")
    def _d(self, wall, name, cond, text):
        if cond:
            if name not in getattr(self, "_on", set()) : self.disagree[name] += 1; self._log(wall, "DISAGREE", f"{name}: {text}")
            self._on = getattr(self, "_on", set()) | {name}
        else: self._on = getattr(self, "_on", set()) - {name}
    def _log(self, wall, kind, text): self.events.appendleft({"t": wall, "kind": kind, "text": text})
    def summary(self):
        n = max(self.ticks, 1); calls = self.vlm_ok + self.vlm_fail; lat = sorted(self.lat)
        pct = lambda p: round(lat[min(len(lat) - 1, int(p * len(lat)))], 2) if lat else None
        return {"ticks": self.ticks, "vlm_valid_rate": round(self.vlm_ok / calls, 3) if calls else None, "vlm_calls": calls,
                "latency_p50": pct(.5), "latency_p95": pct(.95), "camera_fresh_pct": round(100 * self.cam_fresh / n, 1),
                "camera_unhealthy_pct": round(100 * self.cam_unhealthy / n, 1), "no_echo_pct": [round(100 * x / n, 1) for x in self.no_echo],
                "actions": dict(self.actions), "rules": {str(k): v for k, v in sorted(self.rules.items())}, "disagreements": dict(self.disagree),
                "near_misses": self.near_miss, "stuck_events": self.stuck, "turn_flips_per_min": len(self.turns), "action_changes_per_min": len(self.changes),
                "events": list(self.events)[:15]}
