from scoutbot.tools.vision_check import assess, yolo_check


def test_vision_check_assessment_marks_good_samples_and_manual_items():
    rows = dict((name, passed) for name, passed, _ in assess(
        [100, 110], [20, 22], [40, 42], 15, {"healthy": True, "reasons": []}, (True, "4.0 FPS")
    ))
    assert rows["camera health"] and rows["brightness"] and rows["contrast"] and rows["sharpness"] and rows["capture FPS"]
    assert not rows["dashboard delay"] and rows["YOLO FPS"]


def test_vision_check_accepts_a_remote_yolo_worker_without_benchmarking():
    ok, detail = yolo_check({"perception": {"yolo": {"where": "remote"}}}, "pi")
    assert ok and "remote worker" in detail
