"""Laptop-safe control-tick orchestration. Hardware workers publish into WorldState."""
from robot.brain.decide import decide
from robot.brain.safety import gate
from robot.fakes.motors import FakeMotors
from robot.state import WorldState
from robot.types import Action, GateResult, Lifecycle

RESEARCH_STATUS = "RESEARCH TEST ONLY – NOT FOR RESCUE OR PUBLIC USE"

class ControlLoop:
    """The only orchestration path from state to a motor sink is decision -> gate -> permit."""
    def __init__(self, state: WorldState, motors: FakeMotors) -> None:
        self.state, self.motors = state, motors

    def tick(self, now_ms: int) -> tuple[Action, GateResult, int]:
        snapshot = self.state.snapshot(now_ms)
        decision = decide(snapshot)
        result = gate(decision.action, snapshot)
        self.motors.execute(result, snapshot.lifecycle, now_ms)
        if result.latched_fault and snapshot.lifecycle is not Lifecycle.E_STOP_LATCHED:
            self.motors.stop()
            self.state.update_lifecycle(Lifecycle.FAILSAFE_LATCHED)
        return decision.action, result, decision.rule_id
