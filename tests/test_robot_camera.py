import numpy as np

from scoutbot.hw import camera_opencv


class FakeCapture:
    def __init__(self, opened, frames=()):
        self.opened = opened
        self.frames = list(frames)
        self.released = False

    def isOpened(self):
        return self.opened

    def read(self):
        if not self.opened or not self.frames:
            return False, None
        return True, self.frames.pop(0)

    def release(self):
        self.released = True


def frame(brightness):
    return np.full((4, 4, 3), brightness, dtype=np.uint8)


def test_open_best_camera_keeps_working_preferred_camera(monkeypatch):
    preferred = FakeCapture(True, [frame(30)])
    monkeypatch.setattr(camera_opencv, "_capture", lambda index: {1: preferred}[index])

    camera = camera_opencv.open_best_camera(1, candidates=[1], verbose=False)

    assert camera.index == 1
    assert camera.ok
    assert not preferred.released


def test_open_best_camera_skips_black_preferred_camera(monkeypatch):
    black = FakeCapture(True, [frame(0)] * 10)
    bright = FakeCapture(True, [frame(40)])
    captures = {1: black, 0: bright}
    monkeypatch.setattr(camera_opencv, "_capture", lambda index: captures[index])

    camera = camera_opencv.open_best_camera(1, candidates=[0, 1], verbose=False)

    assert camera.index == 0
    assert camera.ok
    assert black.released


def test_open_best_camera_is_not_ok_when_no_camera_opens(monkeypatch):
    unavailable = {1: FakeCapture(False), 0: FakeCapture(False)}
    monkeypatch.setattr(camera_opencv, "_capture", lambda index: unavailable[index])

    camera = camera_opencv.open_best_camera(1, candidates=[0, 1], verbose=False)

    assert not camera.ok


def test_picamera2_source_converts_rgb_to_bgr(monkeypatch):
    class FakePiCamera:
        def create_video_configuration(self, **kw): return kw
        def configure(self, config): self.config = config
        def start(self): pass
        def capture_array(self, stream):
            assert stream == "main"
            return np.array([[[255, 0, 0]]], dtype=np.uint8)  # red in RGB
        def stop(self): pass
        def close(self): pass

    import sys, types
    monkeypatch.setitem(sys.modules, "picamera2", types.SimpleNamespace(Picamera2=FakePiCamera))
    monkeypatch.setattr(camera_opencv.time, "sleep", lambda _: None)
    camera = camera_opencv.PiCamera2Camera((320, 240), 15)
    assert camera.ok and camera.read()[0, 0].tolist() == [0, 0, 255]
    camera.close()


def test_picamera2_module3_requests_continuous_autofocus(monkeypatch):
    class FakePiCamera:
        def create_video_configuration(self, **kw): return kw
        def configure(self, config): pass
        def start(self): pass
        def stop(self): pass
        def close(self): pass
        def set_controls(self, controls): self.controls = controls

    import sys, types
    fake = FakePiCamera()
    monkeypatch.setitem(sys.modules, "picamera2", types.SimpleNamespace(Picamera2=lambda: fake))
    monkeypatch.setitem(sys.modules, "libcamera", types.SimpleNamespace(
        controls=types.SimpleNamespace(AfModeEnum=types.SimpleNamespace(Continuous="continuous"))))
    monkeypatch.setattr(camera_opencv.time, "sleep", lambda _: None)

    camera = camera_opencv.PiCamera2Camera((640, 360), 15)

    assert camera.ok and camera.autofocus == "continuous"
    assert fake.controls == {"AfMode": "continuous"}
    camera.close()
