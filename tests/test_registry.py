import numpy as np
from scoutbot import settings
from scoutbot.survivors.registry import Registry
from scoutbot.sync.outbox import Outbox
from scoutbot.types import PersonDetection, Pose

CFG = settings.load("base", load_env=False)
def det(where="center", dist="mid", box=(0.4, 0.3, 0.6, 0.7)):
    return PersonDetection(source="yolo", where=where, distance=dist, confidence=0.9, bbox=box, at=0)
FRAME = np.zeros((90, 160, 3), np.uint8)

def test_new_then_merge(tmp_path):
    r = Registry(CFG, data_dir=tmp_path); p = Pose()
    s1, new1 = r.sighting(det(), p, 0.0, FRAME); assert new1 and s1.id == "S-0001"
    s2, new2 = r.sighting(det(), Pose(x_cm=20), 20.0, FRAME); assert not new2 and s2.id == "S-0001" and s2.sightings == 2
    s3, new3 = r.sighting(det(), Pose(x_cm=0, y_cm=800), 900.0, FRAME); assert new3 and s3.id == "S-0002"

def test_two_people_in_one_frame_are_two_survivors(tmp_path):
    r = Registry(CFG, data_dir=tmp_path); used = set()
    a, _ = r.sighting(det("left", "mid"), Pose(), 0.0, FRAME, exclude=used); used.add(a.id)
    b, new = r.sighting(det("center", "mid"), Pose(), 0.0, FRAME, exclude=used)
    assert new and a.id != b.id

def test_far_sighting_never_creates_but_updates(tmp_path):
    r = Registry(CFG, data_dir=tmp_path)
    s, new = r.sighting(det("center", "far"), Pose(), 0.0, FRAME); assert s is None and not new and r.all() == []
    a, _ = r.sighting(det("center", "mid"), Pose(), 0.0, FRAME)
    b, new = r.sighting(det("center", "far"), Pose(x_cm=-200), 0.0, FRAME)      # same person, seen from farther back
    assert b is not None and not new and b.id == a.id and b.sightings == 2

def test_snapshots_capped_and_best_kept(tmp_path):
    r = Registry(CFG, data_dir=tmp_path)
    for i in range(10):
        h = 0.1 + 0.08 * i                                   # the person gets bigger (closer) every time
        s, _ = r.sighting(det(box=(0.4, 0.5 - h / 2, 0.6, 0.5 + h / 2)), Pose(), 0.0, FRAME)
    assert len(s.snapshots) == CFG["survivors"]["max_snapshots"]
    assert len(list((tmp_path / "snapshots").glob("*.jpg"))) == CFG["survivors"]["max_snapshots"]
    assert s.best_snapshot == s.snapshots[-1]

def test_reload_from_disk_and_outbox(tmp_path):
    ob = Outbox(tmp_path, ["mongo"]); r = Registry(CFG, outbox=ob, data_dir=tmp_path)
    s, _ = r.sighting(det(), Pose(), 0.0, FRAME)
    r.update(s.id, lambda x: setattr(x, "sightings", 7))
    r2 = Registry(CFG, data_dir=tmp_path)
    assert r2.get(s.id).sightings == 7
    s3, new = r2.sighting(det(), Pose(x_cm=0, y_cm=900), 900.0, FRAME); assert new and s3.id == "S-0002"   # ids keep counting
    assert (tmp_path / "outbox" / "mongo" / "survivors" / f"{s.id}.json").exists()
    assert ob.queued("mongo") >= 2                            # survivor file + sighting rows
