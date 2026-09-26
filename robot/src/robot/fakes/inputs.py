"""Deterministic laptop-only input sources for simulation and replay."""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
from robot.types import DistanceFact

@dataclass(frozen=True)
class Frame:
    frame_id: str
    observed_ms: int
    content: bytes
    encoding: str = "jpeg"

    @property
    def content_sha256(self) -> str:
        return sha256(self.content).hexdigest()

class ScriptedSensors:
    """Publishes one independently timestamped value per protective channel."""
    def __init__(self, samples: dict[str, list[float | None]], ttl_ms: int = 500) -> None:
        if set(samples) != {"left", "center", "right"}:
            raise ValueError("samples must define left, center, and right")
        self._samples = {name: deque(values) for name, values in samples.items()}
        self.ttl_ms = ttl_ms

    def read(self, channel: str, now_ms: int) -> DistanceFact:
        if channel not in self._samples:
            raise ValueError("unknown protective channel")
        value = self._samples[channel].popleft() if self._samples[channel] else None
        if value is None or not 2 <= value <= 400:
            return DistanceFact(None, now_ms, now_ms + self.ttl_ms, "invalid", source_id=f"fake_{channel}", invalid_reason="no_echo" if value is None else "out_of_range")
        return DistanceFact(float(value), now_ms, now_ms + self.ttl_ms, source_id=f"fake_{channel}")

class FolderCamera:
    """Reads fixture images in lexical order, retaining only the current frame."""
    def __init__(self, directory: str | Path) -> None:
        self._files = deque(sorted(Path(directory).glob("*")))

    def get_latest_frame(self, now_ms: int) -> Frame | None:
        if not self._files:
            return None
        path = self._files.popleft()
        return Frame(str(uuid4()), now_ms, path.read_bytes(), path.suffix.lstrip(".") or "jpeg")
