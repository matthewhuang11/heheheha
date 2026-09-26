from robot.types import Action as A
from scoutbot.safety.deadman import MotorWatchdog, link_check, manual_action
from scoutbot.safety.modes import ModeController
from scoutbot.state import Shared
from scoutbot.types import DriveCommand, Mode

SAFETY = {"link_required": True, "link_timeout_manual_s": 0.5, "link_timeout_auto_s": 2.0, "auto_on_link_loss": "stop"}

class FakeMotors:
    def __init__(self): self.stops = 0
    def stop(self): self.stops += 1

class Clock:
    def __init__(self): self.t = 0.0
    def __call__(self): return self.t

def test_boot_is_stopped_and_estop_from_every_mode():
    sh = Shared(); m = ModeController(sh); assert m.mode == Mode.STOPPED
    for mode in (Mode.AUTO, Mode.MANUAL):
        m.request(mode); assert m.mode == mode; m.estop(); assert m.mode == Mode.STOPPED

def test_leaving_manual_clears_drive_command():
    sh = Shared(); m = ModeController(sh); m.request(Mode.MANUAL)
    sh.drive_cmd = DriveCommand(action=A.FORWARD, received_at=1.0); m.request(Mode.AUTO)
    assert sh.drive_cmd is None

def test_manual_command_expires():
    cmd = DriveCommand(action=A.FORWARD, received_at=10.0)
    assert manual_action(cmd, 10.2, 0.3) == A.FORWARD
    assert manual_action(cmd, 10.31, 0.3) == A.STOP
    assert manual_action(None, 10.0, 0.3) == A.STOP

def test_link_timeouts_per_mode():
    assert link_check(Mode.STOPPED, None, 100, SAFETY) is None
    assert link_check(Mode.MANUAL, 99.6, 100, SAFETY) is None
    assert link_check(Mode.MANUAL, 99.4, 100, SAFETY) is not None
    assert link_check(Mode.AUTO, 98.5, 100, SAFETY) is None
    assert link_check(Mode.AUTO, 97.9, 100, SAFETY) is not None
    assert link_check(Mode.AUTO, None, 100, SAFETY) is not None
    assert link_check(Mode.AUTO, 50, 100, {**SAFETY, "auto_on_link_loss": "continue"}) is None
    assert link_check(Mode.MANUAL, 50, 100, {**SAFETY, "link_required": False}) is None

def test_motor_watchdog_trips_and_keeps_resending_stop():
    m = FakeMotors(); c = Clock(); w = MotorWatchdog(m, 0.5, 0.2, clock=c)
    c.t = 1.0; w.fed(); c.t = 1.4; assert not w.check(); assert m.stops == 0
    c.t = 1.6; assert w.check(); assert m.stops == 1 and w.trips == 1
    c.t = 1.7; w.check(); assert m.stops == 1          # resend only every 0.2 s
    c.t = 1.85; w.check(); assert m.stops == 2
    c.t = 1.9; w.fed(); assert not w.check()          # commands resume
