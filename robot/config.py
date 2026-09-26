"""All tunable numbers in one place. Stop distance is derived from robot speed, not guessed
(RSS-style: distance covered during reaction delay + braking distance + margin)."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Policy:
    stop_cm: float = 25.0        # center closer than this -> avoid (rule 2)
    slow_cm: float = 60.0        # center closer than this -> slow (rule 7)
    side_near: float = 15.0      # side closer than this -> turn away (rule 3)
    side_slow: float = 30.0      # side closer than this -> slow
    side_backup: float = 40.0    # both sides closer than this (and center blocked) -> back up
    leave_margin: float = 8.0    # hysteresis: once "near", stay near until this many cm farther
    ttc_stop: float = 0.8        # time-to-collision (s) below this -> avoid
    ttc_slow: float = 2.0
    cliff_max: float = 15.0      # downward sensor reading above this = drop ahead
    low_conf: float = 0.4        # camera confidence below this -> treat camera as unsure (slow)
    cam_stale_s: float = 6.0
    sensor_stale_s: float = 0.5

    @classmethod
    def from_speed(cls, v_cm_s=30.0, reaction_s=0.35, brake_cm_s2=60.0, margin_cm=7.0, **kw):
        stop = v_cm_s * reaction_s + v_cm_s ** 2 / (2 * brake_cm_s2) + margin_cm
        return cls(stop_cm=round(stop, 1), slow_cm=round(2 * stop + 10, 1), **kw)

DEFAULT = Policy.from_speed()
