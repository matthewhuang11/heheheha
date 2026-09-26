"""xAI's OpenAI-compatible scene-vision adapter.

This module intentionally uses HTTPS directly instead of the Gemini SDK or an
OpenAI SDK.  It shares Scoutbot's frozen SceneReport parser with the Gemini
lane, but never includes a model response or credentials in raised errors.
"""
from __future__ import annotations

import base64
import os
import re
import time
from urllib.parse import urlsplit

import cv2
import httpx

from robot.vlm import PROMPT, parse, shrink
from robot.types import SceneReport

DEFAULT_BASE_URL = "https://api.x.ai/v1"
DEFAULT_MODEL = "grok-4.3-latest"
_MODEL_RE = re.compile(r"grok-[A-Za-z0-9._:-]{1,120}\Z")
_REASONING_EFFORTS = {"none", "low", "medium", "high", "xhigh"}


class XaiSceneError(RuntimeError):
    """A safe, displayable xAI scene-provider failure."""


def _required_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise XaiSceneError(f"xAI {label} must be a non-empty string")
    return value.strip()


def _base_url(value: object) -> str:
    raw = _required_string(value, "base URL")
    parsed = urlsplit(raw)
    # Keeping the host fixed makes this configurable setting unable to turn
    # into a request proxy or a route to a private network service.
    if (parsed.scheme, parsed.hostname, parsed.port, parsed.username, parsed.password,
            parsed.query, parsed.fragment) != ("https", "api.x.ai", None, None, None, "", ""):
        raise XaiSceneError("xAI base URL must be https://api.x.ai/v1")
    if parsed.path.rstrip("/") != "/v1":
        raise XaiSceneError("xAI base URL must be https://api.x.ai/v1")
    return DEFAULT_BASE_URL


def _bounded_number(value: object, label: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not minimum <= value <= maximum:
        raise XaiSceneError(f"xAI {label} must be between {minimum:g} and {maximum:g}")
    return float(value)


class XaiSceneProvider:
    """Make bounded, schema-constrained xAI visual scene requests."""

    def __init__(self, cfg: dict, client: httpx.Client | None = None, sleep=time.sleep):
        xai = cfg.get("scene", {}).get("xai", {})
        if not isinstance(xai, dict):
            raise XaiSceneError("xAI scene configuration must be a mapping")
        self.base_url = _base_url(xai.get("base_url", DEFAULT_BASE_URL))
        self.model = _required_string(xai.get("model", DEFAULT_MODEL), "model")
        if not _MODEL_RE.fullmatch(self.model):
            raise XaiSceneError("xAI model must be a Grok model name")
        self.timeout_s = _bounded_number(xai.get("timeout_s", 15), "timeout_s", 1, 60)
        retries = xai.get("retries", 1)
        if isinstance(retries, bool) or not isinstance(retries, int) or not 0 <= retries <= 2:
            raise XaiSceneError("xAI retries must be an integer between 0 and 2")
        self.retries = retries
        self.reasoning_effort = _required_string(xai.get("reasoning_effort", "xhigh"), "reasoning_effort").lower()
        if self.reasoning_effort not in _REASONING_EFFORTS:
            raise XaiSceneError("xAI reasoning_effort must be none, low, medium, high, or xhigh")
        self._client = client or httpx.Client(timeout=httpx.Timeout(self.timeout_s))
        self._sleep = sleep

    @property
    def endpoint(self) -> str:
        return self.base_url + "/chat/completions"

    def _payload(self, jpeg: bytes) -> dict:
        image = "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Return only the requested JSON scene report."},
                {"role": "user", "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {"url": image, "detail": "low"}},
                ]},
            ],
            "temperature": 0,
            "max_tokens": 800,
            "reasoning_effort": self.reasoning_effort,
            "response_format": {"type": "json_object"},
        }

    def describe(self, frame) -> SceneReport:
        key = os.environ.get("XAI_API_KEY", "").strip().strip('"').strip("'")
        if not key:
            raise XaiSceneError("XAI_API_KEY is missing or empty (check .env)")
        ok, encoded = cv2.imencode(".jpg", shrink(frame), [cv2.IMWRITE_JPEG_QUALITY, 70])
        if not ok:
            raise XaiSceneError("scene frame encoding failed")
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        last_error = "xAI scene request failed"
        for attempt in range(self.retries + 1):
            try:
                response = self._client.post(self.endpoint, headers=headers, json=self._payload(encoded.tobytes()))
                if response.status_code >= 400:
                    last_error = f"xAI scene request failed (HTTP {response.status_code})"
                    if response.status_code < 500:
                        raise XaiSceneError(last_error)
                    raise httpx.HTTPError(last_error)
                body = response.json()
                text = body["choices"][0]["message"]["content"]
                if not isinstance(text, str):
                    raise KeyError("content")
                try:
                    return parse(text)
                except Exception as exc:
                    raise XaiSceneError("xAI scene response did not match SceneReport") from exc
            except XaiSceneError:
                raise
            except httpx.TimeoutException:
                last_error = "xAI scene request timed out"
            except (httpx.HTTPError, KeyError, TypeError, ValueError):
                last_error = "xAI scene request failed"
            if attempt < self.retries:
                self._sleep(0.25 * (2 ** attempt))
        raise XaiSceneError(last_error)
