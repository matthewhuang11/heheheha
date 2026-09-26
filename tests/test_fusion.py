from robot.types import SceneReport
from scoutbot.perception.fusion import Fuser, fresh_person
from scoutbot.perception.yolo import Confirmer, box_to_detection
from scoutbot.types import PersonDetection

NOPE = {"visible": False, "where": "none", "distance": "none"}
def scene(people=NOPE):
    return SceneReport(path_ahead="clear", best_direction="none", terrain="flat", hazards=[], people=people, objects=[], confidence=1, notes="")
def det(where="center", dist="near", at=10.0): return PersonDetection(source="yolo", where=where, distance=dist, confidence=0.8, at=at)
Y = {"near_frac": 0.5, "mid_frac": 0.2}

def test_box_to_where_and_distance():
    assert box_to_detection(0.0, 0.2, 0.2, 0.9, 0.9, Y, 0).where == "left"
    d = box_to_detection(0.4, 0.2, 0.6, 0.9, 0.9, Y, 0); assert (d.where, d.distance) == ("center", "near")
    d = box_to_detection(0.8, 0.4, 0.95, 0.7, 0.9, Y, 0); assert (d.where, d.distance) == ("right", "mid")
    assert box_to_detection(0.4, 0.4, 0.5, 0.5, 0.9, Y, 0).distance == "far"

def test_two_of_three_confirmation():
    c = Confirmer(2, 3); d = [det()]
    assert c.push(d) == []            # 1 of 1
    assert c.push([]) == []           # 1 of 2
    assert c.push(d) == d             # 2 of 3
    assert c.push([]) == []           # no person in this frame -> nothing to report

def test_yolo_adds_a_person_gemini_missed():
    s = scene(); out = Fuser().fuse(s, det("left", "near"))
    assert out is not s and out.people.visible and out.people.where == "left" and out.people.distance == "near"

def test_yolo_never_removes_gemini_person_and_nearer_wins():
    s = scene({"visible": True, "where": "right", "distance": "near"})
    assert Fuser().fuse(s, None) is s                                    # no YOLO person: Gemini's stays
    assert Fuser().fuse(s, det("center", "far")).people.distance == "near"   # Gemini nearer: keep it
    s2 = scene({"visible": True, "where": "right", "distance": "far"})
    assert Fuser().fuse(s2, det("center", "mid")).people.distance == "mid"   # YOLO nearer: use it

def test_fused_copy_is_cached_so_scene_filter_is_not_flooded():
    f = Fuser(); s = scene(); a = f.fuse(s, det()); b = f.fuse(s, det())
    assert a is b                                                        # same object while nothing changes
    c = f.fuse(s, det("left", "mid")); assert c is not a                 # YOLO changed -> rebuilt

def test_fresh_person_expires():
    assert fresh_person([det()], 10.0, 10.5, 1.0) is not None
    assert fresh_person([det()], 10.0, 11.5, 1.0) is None
    near_and_far = [det("left", "far"), det("right", "near")]
    assert fresh_person(near_and_far, 10.0, 10.1, 1.0).where == "right"

def test_where_off_from_yaml_false_means_off():
    """`--set perception.yolo.where=off` arrives as False (YAML 1.1); it must switch YOLO off, not try to load it."""
    from scoutbot import settings
    from scoutbot.perception.yolo import PerceptionWorker
    from scoutbot.state import Shared
    cfg = settings.load("sim", ["perception.yolo.where=off"], load_env=False)
    assert cfg["perception"]["yolo"]["where"] is False
    sh = Shared(); PerceptionWorker(cfg, sh).run()
    assert sh.det_status == "off"
