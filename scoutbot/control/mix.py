"""Pure manual skid-steer input mixing.  This module deliberately has no hardware imports."""
from __future__ import annotations


def _shape(value: float, deadzone: float, expo: float) -> float:
    value = max(-1.0, min(1.0, float(value)))
    if abs(value) <= deadzone:
        return 0.0
    # Rescale after the dead zone so the first non-zero value remains gentle.
    magnitude = (abs(value) - deadzone) / max(1.0 - deadzone, 1e-9)
    magnitude = (1.0 - expo) * magnitude + expo * magnitude ** 3
    return magnitude if value > 0 else -magnitude


def mix(v: float, w: float, cfg: dict, slow: bool = False) -> tuple[float, float]:
    """Convert normalized speed/turn axes into normalized left/right wheel targets.

    `cfg` is the `manual` configuration block.  Inputs are clamped, shaped and
    normalized before per-side trim and inversion are applied last.
    """
    deadzone = float(cfg.get("deadzone", 0.08))
    expo = float(cfg.get("expo", 0.30))
    v = _shape(v, deadzone, expo)
    w = _shape(w, deadzone, expo)
    if slow:
        v *= float(cfg.get("slow_factor", 0.58))
        w *= float(cfg.get("slow_factor", 0.58))

    # A stationary stick may rotate at its own conservative cap.  While moving,
    # the common max-forward cap keeps the combined wheel output gentle.
    if v == 0.0:
        v *= float(cfg.get("max_forward", 0.60))
        w *= float(cfg.get("max_turn_in_place", 0.45))
    else:
        v *= float(cfg.get("max_forward", 0.60)) if v > 0 else float(cfg.get("max_reverse", 0.35))
        w *= float(cfg.get("max_forward", 0.60))

    left, right = v + w, v - w
    peak = max(1.0, abs(left), abs(right))
    left, right = left / peak, right / peak
    left *= float(cfg.get("trim_left", 1.0))
    right *= float(cfg.get("trim_right", 1.0))
    if cfg.get("invert_left", False):
        left = -left
    if cfg.get("invert_right", False):
        right = -right
    return max(-1.0, min(1.0, left)), max(-1.0, min(1.0, right))
