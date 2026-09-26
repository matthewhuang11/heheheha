"""Bounded cloud-VLM client. Providers describe evidence and never command motion."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass
from typing import Protocol
from robot.fakes.inputs import Frame
from robot.types import SceneReport
from robot.vlm.validate import ValidationError, validate

class VLMProvider(Protocol):
    provider_id: str
    def describe(self, frame: Frame, prompt: str) -> str: ...

@dataclass(frozen=True)
class VlmResult:
    scene: SceneReport | None
    status: str
    error: str
    consecutive_failures: int
    round_trip_ms: int

class VLMClient:
    def __init__(self, provider: VLMProvider, prompt: str, timeout_ms: int = 4000, scene_ttl_ms: int = 6000) -> None:
        self.provider, self.prompt = provider, prompt
        self.timeout_ms, self.scene_ttl_ms, self.failures = timeout_ms, scene_ttl_ms, 0

    def describe(self, frame: Frame | None, now_ms: int) -> VlmResult:
        if frame is None:
            return self._failure("camera", 0)
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.provider.describe, frame, self.prompt)
            try:
                raw = future.result(timeout=self.timeout_ms / 1000)
            except TimeoutError:
                future.cancel()
                return self._failure("timeout", self.timeout_ms)
            except Exception:
                return self._failure("provider", 0)
        try:
            scene = validate(raw, observed_ms=now_ms, frame_observed_ms=frame.observed_ms, now_ms=now_ms, ttl_ms=self.scene_ttl_ms)
        except ValidationError:
            return self._failure("validation", 0)
        self.failures = 0
        return VlmResult(scene, "online", "none", 0, max(1, now_ms - frame.observed_ms))

    def _failure(self, error: str, round_trip_ms: int) -> VlmResult:
        self.failures = min(3, self.failures + 1)
        return VlmResult(None, "offline" if self.failures >= 3 or error == "camera" else "degraded", error, self.failures, round_trip_ms)
