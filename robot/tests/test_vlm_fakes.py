import json
from robot.fakes.inputs import Frame, ScriptedSensors
from robot.fakes.vlm import CannedVLMProvider
from robot.vlm.client import VLMClient


def report():
    return json.dumps({"schema_version": 1, "path_ahead": "clear", "best_direction": "center", "terrain": "flat", "hazards": [], "people": {"visible": False, "where": "none", "distance": "none"}, "confidence": 1, "notes": ""})


def test_scripted_sensor_never_turns_missing_data_into_clearance():
    source = ScriptedSensors({"left": [100], "center": [None], "right": [500]})
    assert source.read("left", 0).usable(1)
    assert source.read("center", 0).distance_cm is None
    assert source.read("right", 0).distance_cm is None


def test_vlm_client_validates_and_tracks_failures():
    client = VLMClient(CannedVLMProvider([report(), "not json", "not json", "not json"]), "prompt")
    frame = Frame("f", 0, b"frame")
    assert client.describe(frame, 1).status == "online"
    assert client.describe(frame, 2).status == "degraded"
    assert client.describe(frame, 3).status == "degraded"
    assert client.describe(frame, 4).status == "offline"
