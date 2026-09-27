from scoutbot.tools.vision_check import assess


def test_vision_check_assessment_marks_good_samples_and_manual_items():
    rows = dict((name, passed) for name, passed, _ in assess(
        [100, 110], [20, 22], [40, 42], 15, {"healthy": True, "reasons": []}
    ))
    assert rows["camera health"] and rows["brightness"] and rows["contrast"] and rows["sharpness"] and rows["capture FPS"]
    assert not rows["dashboard delay"] and not rows["YOLO FPS"]
