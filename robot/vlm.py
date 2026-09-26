from __future__ import annotations
import json, os, re, time
import cv2
from google import genai
from google.genai import types, errors
from robot.types import SceneReport

_SCHEMA = json.dumps(SceneReport.model_json_schema(), separators=(",", ":"))
_CLIENTS: dict[str, object] = {}
PROMPT = (
    "You are the eyes of a small ground robot. Describe ONLY what is in the image. Never suggest actions or commands. "
    "Answer 'unknown' when unsure.\n"
    "Field rules:\n"
    "- path_ahead: judge the floor straight ahead of the camera. clear = open floor; partially_blocked = obstacles cover part of the way; "
    "blocked = an obstacle fills most of the way; unknown = you cannot tell (dark, ceiling, extreme close-up).\n"
    "- best_direction: the side (left, center, right) with the most open floor, or none if nowhere looks passable.\n"
    "- terrain: flat, rubble, uneven, stairs_or_drop, water, or unknown.\n"
    "- hazards: only REAL dangers (fire, smoke, water on the floor, exposed wire, broken glass, a drop-off or stair edge, unstable debris). "
    "Do not list ordinary furniture or objects. where = which third of the image; distance = near (very close or fills a big part of the view), mid, or far.\n"
    "- people: visible=true if ANY person or part of a person (face, body, hand) is in the image, even a close-up. where = which third of the image; "
    "distance = near if they are very close or fill a big part of the view, else mid or far. If nobody is visible, visible=false with where and distance 'none'.\n"
    "- objects: up to 10 short nouns for things you see. confidence: 0 to 1. notes: one short sentence.\n"
    "Reply with ONLY one JSON object (no markdown, no extra text) that matches this JSON Schema exactly:\n" + _SCHEMA
)

def shrink(frame):
    h, w = frame.shape[:2]; nw = min(w, 640)
    return cv2.resize(frame, (nw, max(1, int(h * nw / w)))) if nw < w else frame

def parse(text: str) -> SceneReport:
    """Turn the model's reply into a validated SceneReport (tolerates ```json fences)."""
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    data = json.loads(text)
    if isinstance(data, dict):   # trim/clamp instead of rejecting a whole good report over a too-long field
        if isinstance(data.get("notes"), str): data["notes"] = data["notes"][:240]
        if isinstance(data.get("objects"), list): data["objects"] = [str(x) for x in data["objects"][:20]]
        if isinstance(data.get("hazards"), list): data["hazards"] = data["hazards"][:12]
        if isinstance(data.get("confidence"), (int, float)): data["confidence"] = min(1.0, max(0.0, float(data["confidence"])))
    p = data.get("people")
    if isinstance(p, dict) and not p.get("visible"):   # invisible people -> location must be none
        data["people"] = {"visible": False, "where": "none", "distance": "none"}
    return SceneReport.model_validate(data)

def describe(frame) -> SceneReport:
    key = os.environ.get("GEMINI_API_KEY", "").strip().strip('"').strip("'")
    if not key: raise RuntimeError("GEMINI_API_KEY is missing or empty (check .env)")
    model = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest").strip().strip('"').strip("'") or "gemini-flash-lite-latest"
    ok, encoded = cv2.imencode(".jpg", shrink(frame), [cv2.IMWRITE_JPEG_QUALITY, 70])
    if not ok: raise RuntimeError("frame encoding failed")
    client = _CLIENTS.setdefault(key, genai.Client(api_key=key))
    for attempt in range(3):   # Gemini sometimes answers 503 "high demand"; retry briefly
        try:
            response = client.models.generate_content(
                model=model,
                contents=[PROMPT, types.Part.from_bytes(data=encoded.tobytes(), mime_type="image/jpeg")],
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0),
            )
            break
        except errors.ServerError:
            if attempt == 2: raise
            time.sleep(1.5)
    return parse(response.text)
