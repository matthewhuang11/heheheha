"""The safety gate: the last check before the motors, in every mode (spec 6.2).
In AUTO the brain already follows these rules, so a veto there means a bug (it is logged). In MANUAL it is what stops a
responder driving into a wall. It reuses the brain's own thresholds (robot/config.py Policy)."""
from __future__ import annotations
from dataclasses import dataclass
from robot.config import Policy, DEFAULT
from robot.types import Action
from scoutbot.types import Mode

FWD = {Action.FORWARD, Action.FORWARD_SLOW}

def _cm(v): return "no echo" if v is None else f"{v:.0f} cm"

@dataclass
class GateResult:
    action: Action
    veto: str | None = None      # human-readable reason when the gate changed the action

class Gate:
    def __init__(self, policy: Policy = DEFAULT, backup_max_s: float = 1.5, backup_rest_s: float = 0.5):
        self.P = policy; self.backup_max_s = backup_max_s; self.backup_rest_s = backup_rest_s
        self.backup_since = None; self.rest_until = -1.0

    def check(self, action: Action, mode: Mode, L, C, R, sensors_fresh: bool, now: float, yolo_person_near: bool = False) -> GateResult:
        P = self.P
        if mode == Mode.STOPPED:
            self.backup_since = None; return GateResult(Action.STOP, None if action == Action.STOP else "mode is STOPPED")
        if not sensors_fresh or (L is None and C is None and R is None):
            self.backup_since = None; return GateResult(Action.STOP, "sensor data stale or all sensors have no echo")
        if action in FWD:
            if yolo_person_near: return self._done(Action.STOP, "person ahead (YOLO)")
            if C is not None and C < P.stop_cm: return self._done(Action.STOP, f"blocked: something {_cm(C)} ahead")
            if action == Action.FORWARD and (C is None or C < P.slow_cm):
                return self._done(Action.FORWARD_SLOW, f"capped at slow: center {_cm(C)}")
        if mode == Mode.MANUAL:
            if action == Action.TURN_LEFT and L is not None and L < P.side_near: return self._done(Action.STOP, f"blocked: left side {_cm(L)}")
            if action == Action.TURN_RIGHT and R is not None and R < P.side_near: return self._done(Action.STOP, f"blocked: right side {_cm(R)}")
        if action == Action.BACK_UP:          # no rear sensor: back up in short bursts only
            if now < self.rest_until: return GateResult(Action.STOP, "backing up paused (no rear sensor)")
            if self.backup_since is None: self.backup_since = now
            if now - self.backup_since > self.backup_max_s:
                self.backup_since = None; self.rest_until = now + self.backup_rest_s
                return GateResult(Action.STOP, f"backed up {self.backup_max_s:.1f}s: pausing (no rear sensor)")
            return GateResult(action)
        self.backup_since = None
        return GateResult(action)

    def _done(self, action, veto):
        self.backup_since = None; return GateResult(action, veto)

    def check_analog(self, v: float, w: float, mode: Mode, L, C, R, sensors_fresh: bool, now: float,
                     max_reverse: float = 0.35, unknown_forward_scale: float = 0.58) -> tuple[float, float, str | None]:
        """Continuously apply the same obstacle and reverse rules as `check`."""
        if mode != Mode.MANUAL:
            self.backup_since = None; return 0.0, 0.0, "mode is not MANUAL"
        if not sensors_fresh or (L is None and C is None and R is None):
            self.backup_since = None; return 0.0, 0.0, "sensor data stale or all sensors have no echo"
        vetoes = []
        if v > 0:
            if C is not None and C < self.P.stop_cm:
                v = 0.0; vetoes.append(f"blocked: something {_cm(C)} ahead")
            elif C is None or C < self.P.slow_cm:
                # A single missing center echo follows the legacy gate's
                # FORWARD -> FORWARD_SLOW behavior. All-three-missing was
                # rejected above, so this remains a guarded slow advance.
                scale = unknown_forward_scale if C is None else max(0.0, min(1.0, (C - self.P.stop_cm) / (self.P.slow_cm - self.P.stop_cm)))
                v *= scale; vetoes.append(f"capped at slow: center {_cm(C)}")
        if w < 0 and L is not None and L < self.P.side_near:
            w = 0.0; vetoes.append(f"blocked: left side {_cm(L)}")
        if w > 0 and R is not None and R < self.P.side_near:
            w = 0.0; vetoes.append(f"blocked: right side {_cm(R)}")
        if v < 0:
            v = max(v, -abs(max_reverse))
            if now < self.rest_until:
                return 0.0, 0.0, "backing up paused (no rear sensor)"
            if self.backup_since is None: self.backup_since = now
            if now - self.backup_since > self.backup_max_s:
                self.backup_since = None; self.rest_until = now + self.backup_rest_s
                return 0.0, 0.0, f"backed up {self.backup_max_s:.1f}s: pausing (no rear sensor)"
        else:
            self.backup_since = None
        return v, w, "; ".join(vetoes) or None
