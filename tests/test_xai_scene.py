"""xAI scene provider requests are isolated, bounded, and schema-safe."""
from __future__ import annotations

import json

import httpx
import numpy as np
import pytest

from scoutbot import settings
from scoutbot.perception.xai_scene import XaiSceneError, XaiSceneProvider


REPORT = {
    "path_ahead": "clear", "best_direction": "center", "terrain": "flat",
    "hazards": [], "people": {"visible": False, "where": "none", "distance": "none"},
    "objects": ["floor"], "confidence": 0.9, "notes": "clear floor",
}


def provider(handler, **xai):
    cfg = {"scene": {"xai": xai}}
    return XaiSceneProvider(cfg, httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda _seconds: None)


def test_xai_scene_parses_valid_structured_response_and_sends_image(monkeypatch):
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(REPORT)}}]})

    monkeypatch.setenv("XAI_API_KEY", "test-key")
    report = provider(handler).describe(np.zeros((20, 30, 3), dtype=np.uint8))

    assert report.path_ahead == "clear"
    assert seen["url"] == "https://api.x.ai/v1/chat/completions"
    assert seen["auth"] == "Bearer test-key"
    body = seen["body"]
    assert body["model"] == "grok-4.3-latest"
    assert body["response_format"] == {"type": "json_object"}
    assert body["reasoning_effort"] == "xhigh"
    image = body["messages"][1]["content"][1]["image_url"]
    assert image["detail"] == "low" and image["url"].startswith("data:image/jpeg;base64,")


def test_xai_scene_rejects_invalid_model_output_without_exposing_it(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "test-key")

    def handler(_request):
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"path_ahead":"bad"}'}}]})

    with pytest.raises(XaiSceneError, match="did not match SceneReport") as error:
        provider(handler).describe(np.zeros((2, 2, 3), dtype=np.uint8))
    assert "path_ahead" not in str(error.value)


def test_xai_scene_retries_timeout_then_returns_safe_failure(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    calls = []

    def handler(_request):
        calls.append(1)
        raise httpx.ReadTimeout("network timeout")

    with pytest.raises(XaiSceneError, match="timed out"):
        provider(handler, retries=1).describe(np.zeros((2, 2, 3), dtype=np.uint8))
    assert len(calls) == 2


def test_xai_scene_retries_transient_server_failure_then_succeeds(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    calls = []

    def handler(_request):
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(503, json={"error": {"message": "do not expose this"}})
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(REPORT)}}]})

    report = provider(handler, retries=1).describe(np.zeros((2, 2, 3), dtype=np.uint8))
    assert report.notes == "clear floor" and len(calls) == 2


def test_xai_scene_validates_trusted_base_url_and_config_selects_xai():
    with pytest.raises(XaiSceneError, match="base URL"):
        XaiSceneProvider({"scene": {"xai": {"base_url": "http://127.0.0.1:8000/v1"}}})

    cfg = settings.load("laptop", ["scene.provider=xai"], load_env=False)
    assert cfg["scene"]["provider"] == "xai"
    assert cfg["scene"]["xai"]["model"] == "grok-4.3-latest"


def test_runtime_publishes_xai_scene_selection_without_starting_a_request(tmp_path, monkeypatch):
    from scoutbot.runtime import Runtime

    monkeypatch.chdir(tmp_path)
    cfg = settings.load("laptop", [
        "scene.provider=xai", "hw.camera=synthetic", "voice.provider=fake",
        "sync.sinks=[]", "talk.enabled=false", "perception.yolo.where=off",
        f"survivors.data_dir={tmp_path}",
    ], load_env=False)
    runtime = Runtime(cfg, start_workers=False)
    try:
        assert runtime.state()["services"]["scene"] == "xai"
    finally:
        runtime.stop()
