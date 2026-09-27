from scoutbot.hw.manual_arm import ManualArm


def test_optional_arm_is_open_when_not_required():
    arm = ManualArm({"manual": {"require_arm": False}})
    assert arm.armed()


def test_required_arm_without_a_configured_pin_fails_closed():
    arm = ManualArm({"manual": {"require_arm": True, "arm_pin": None}})
    assert not arm.armed()
    assert "not configured" in arm.reason
