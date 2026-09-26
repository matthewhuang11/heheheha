"""Closed lifecycle/v1 controller. Latches only a physical reset may clear."""
from __future__ import annotations
import secrets
from robot.types import Lifecycle

_ALLOWED = {
    (Lifecycle.BOOTING, Lifecycle.SELF_TEST), (Lifecycle.BOOTING, Lifecycle.FAILSAFE_LATCHED),
    (Lifecycle.SELF_TEST, Lifecycle.READY), (Lifecycle.SELF_TEST, Lifecycle.FAILSAFE_LATCHED),
    (Lifecycle.READY, Lifecycle.ACTIVE), (Lifecycle.ACTIVE, Lifecycle.READY),
    (Lifecycle.ACTIVE, Lifecycle.FAILSAFE_LATCHED),
    (Lifecycle.FAILSAFE_LATCHED, Lifecycle.SELF_TEST), (Lifecycle.E_STOP_LATCHED, Lifecycle.SELF_TEST),
}

class LifecycleController:
    def __init__(self) -> None:
        self.state = Lifecycle.BOOTING
        self.faults: set[str] = set()
        self.reset_token_id: str | None = None

    @property
    def motor_enabled(self) -> bool:
        return self.state is Lifecycle.ACTIVE

    def transition(self, to: Lifecycle, *, local_start=False, physical_reset=False, self_test_ok=False) -> bool:
        if to is Lifecycle.SHUTDOWN:
            self.state = to
            return True
        if to is Lifecycle.E_STOP_LATCHED:
            self.state = to
            self.faults.add("E_STOP")
            return True
        if (self.state, to) not in _ALLOWED:
            self.fail("illegal_transition")
            return False
        if to is Lifecycle.READY and not self_test_ok:
            self.fail("self_test_failed")
            return False
        if to is Lifecycle.ACTIVE and not local_start:
            return False
        if self.state in {Lifecycle.FAILSAFE_LATCHED, Lifecycle.E_STOP_LATCHED} and not physical_reset:
            return False
        if physical_reset:
            self.reset_token_id = secrets.token_hex(16)
            self.faults.clear()
        self.state = to
        return True

    def fail(self, reason: str) -> None:
        if self.state is not Lifecycle.E_STOP_LATCHED:
            self.state = Lifecycle.FAILSAFE_LATCHED
            self.faults.add(reason)

    def manual_kill(self) -> None:
        self.state = Lifecycle.E_STOP_LATCHED
        self.faults.add("E_STOP")
