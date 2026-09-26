from __future__ import annotations
import os, cv2
from google import genai
from google.genai import types
from robot.types import SceneReport
PROMPT="Describe only what is in this image. Answer unknown when unsure. Never suggest actions or commands."
def shrink(frame):
    h,w=frame.shape[:2]; nw=min(w,640)
    return cv2.resize(frame,(nw,max(1,int(h*nw/w)))) if nw<w else frame
def describe(frame)->SceneReport:
    key=os.environ["GEMINI_API_KEY"]; model=os.getenv("GEMINI_MODEL","gemini-2.5-flash")
    ok, encoded=cv2.imencode(".jpg",shrink(frame));
    if not ok: raise RuntimeError("frame encoding failed")
    response=genai.Client(api_key=key).models.generate_content(model=model,contents=[PROMPT,types.Part.from_bytes(data=encoded.tobytes(),mime_type="image/jpeg")],config=types.GenerateContentConfig(response_mime_type="application/json",response_schema=SceneReport))
    return SceneReport.model_validate_json(response.text)
