"""Simulation-only motor sink. Real motor implementations must enforce the same permit check."""
from dataclasses import dataclass
from robot.types import Action, GateResult, Lifecycle

@dataclass
class FakeMotors:
    action: Action = Action.STOP
    motor_enabled: bool = False

    def execute(self, result: GateResult, lifecycle: Lifecycle, now_ms: int) -> Action:
        """Accept only a fresh safety-gate permit, never a requested action."""
        if (lifecycle is not Lifecycle.ACTIVE or not result.permitted
                or now_ms - result.permit_issued_at_ms > 150):
            self.action, self.motor_enabled = Action.STOP, False
            return self.action
        self.action, self.motor_enabled = result.action, True
        return self.action

    def stop(self) -> None:
        self.action, self.motor_enabled = Action.STOP, False
