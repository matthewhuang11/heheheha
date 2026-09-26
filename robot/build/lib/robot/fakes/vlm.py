"""Canned VLM provider for deterministic laptop tests."""
from collections import deque
from robot.fakes.inputs import Frame

class CannedVLMProvider:
    provider_id = "canned"
    def __init__(self, responses: list[str]) -> None:
        self.responses = deque(responses)
    def describe(self, frame: Frame, prompt: str) -> str:
        if not self.responses:
            raise RuntimeError("no canned VLM response")
        return self.responses.popleft()
