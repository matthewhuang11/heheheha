"""Optional physical arm input for manual driving.

The input is intentionally separate from the hard-wired E-stop.  A missing
pin is fail-closed when a profile requires an arm switch.
"""
from __future__ import annotations


class ManualArm:
    def __init__(self, cfg: dict):
        manual = cfg.get("manual", {})
        self.required = bool(manual.get("require_arm", False))
        self.pin = manual.get("arm_pin")
        self.input = None
        self.reason = "not required" if not self.required else "manual arm GPIO is not configured"
        if self.required and self.pin is not None:
            try:
                from gpiozero import Button
                self.input = Button(int(self.pin), pull_up=bool(manual.get("arm_pull_up", False)))
                self.reason = "arm switch is off"
            except Exception as exc:
                self.reason = f"manual arm unavailable: {type(exc).__name__}"

    def armed(self) -> bool:
        if not self.required:
            return True
        if self.input is None:
            return False
        try:
            on = bool(self.input.is_pressed)
            self.reason = "armed" if on else "arm switch is off"
            return on
        except Exception as exc:
            self.reason = f"manual arm read failed: {type(exc).__name__}"
            return False

    def close(self) -> None:
        if self.input is not None:
            try:
                self.input.close()
            except Exception:
                pass
