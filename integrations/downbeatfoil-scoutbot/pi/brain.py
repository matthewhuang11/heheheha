"""HQ processing: turns what the robot collected into triage reports.

Nothing here runs during a blackout. Once the robot is back in range:
  internet     -> Gemini hears the survivor's audio, sees the snapshot, writes the report
  HQ, no internet -> Ollama on the base laptop writes a report from the metadata (text only)
  neither      -> a plain template, so responders always get the location
"""
import json
import socket
import threading
import time
from pathlib import Path

import httpx

import config

_blackout = False
_net = {"t": 0.0, "up": False}
_base = {"t": 0.0, "up": False}
_lock = threading.Lock()


def set_blackout(on: bool):
    """Simulates the robot being out of range: no gemini, no base station."""
    global _blackout
    _blackout = on


def blackout() -> bool:
    return _blackout


def internet_up() -> bool:
    if _blackout or not config.GEMINI_API_KEY:
        return False
    with _lock:
        if time.time() - _net["t"] < 5:
            return _net["up"]
    try:
        socket.create_connection(("generativelanguage.googleapis.com", 443), timeout=2).close()
        up = True
    except OSError:
        up = False
    with _lock:
        _net.update(t=time.time(), up=up)
    return up


def base_station_up() -> bool:
    if _blackout:
        return False
    if time.time() - _base["t"] < 5:
        return _base["up"]
    try:
        up = httpx.get(f"{config.OLLAMA_URL}/api/tags", timeout=1.5).status_code == 200
    except httpx.HTTPError:
        up = False
    _base.update(t=time.time(), up=up)
    return up


def mode() -> str:
    if _blackout:
        return "blackout"
    if internet_up():
        return "online"
    return "hq-local" if base_station_up() else "no-brain"


# ---- backends ----

_gemini = None


def _gemini_client():
    global _gemini
    if _gemini is None:
        from google import genai
        _gemini = genai.Client(api_key=config.GEMINI_API_KEY)
    return _gemini


def _ask_gemini(prompt: str, image: Path | None = None, audio: Path | None = None, as_json=False) -> str:
    from google.genai import types
    parts = []
    if image and image.exists():
        parts.append(types.Part.from_bytes(data=image.read_bytes(), mime_type="image/jpeg"))
    if audio and audio.exists():
        parts.append(types.Part.from_bytes(data=audio.read_bytes(), mime_type="audio/wav"))
    parts.append(prompt)
    resp = _gemini_client().models.generate_content(
        model=config.GEMINI_MODEL,
        contents=parts,
        config=types.GenerateContentConfig(
            response_mime_type="application/json" if as_json else None,
            http_options=types.HttpOptions(timeout=int(config.GEMINI_TIMEOUT_S * 1000)),
        ),
    )
    return resp.text.strip()


def _ask_ollama(prompt: str) -> str:
    r = httpx.post(
        f"{config.OLLAMA_URL}/api/generate",
        json={"model": config.OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=config.OLLAMA_TIMEOUT_S,
    )
    r.raise_for_status()
    return r.json()["response"].strip()


# ---- triage ----

REPORT_FORMAT = """PRIORITY: <IMMEDIATE | DELAYED | MINOR | UNKNOWN> (START triage categories)
POSITION: <where they are relative to the entry point>
CONDITION: <injuries, consciousness, mobility, as far as the evidence shows>
HAZARDS: <anything that affects extraction, or "none observed">
NEXT STEP: <one concrete action for the responders>"""


def _facts(v):
    facts = (f"- position: {v['x']} m east, {v['y']} m north of the entry point\n"
             f"- found: {time.strftime('%H:%M:%S', time.localtime(v['found_at']))}, "
             f"detection confidence {v['conf']}, seen {v['sightings']} times\n"
             f"- robot spoke to them: {'yes' if v['contacted'] else 'no'}")
    env = v.get("env") or {}
    if env.get("temp_c") is not None:
        facts += f"\n- air at their location: {env['temp_c']:.0f} C, {env['humidity']:.0f}% humidity"
        if env.get("hot"):
            facts += " (hot: possible fire or heat hazard)"
    if env.get("heard_sound"):
        facts += "\n- the robot's microphone heard sound (knocking or voice) near them"
    return facts


GEMINI_PROMPT = """You are the triage assistant at a search-and-rescue HQ. A scout robot went into a
collapsed building with no connection, found this survivor, photographed them, asked them
to say their name, whether they are hurt, and whether anyone is with them, and recorded the
answer. Attached: the photo{audio_note}.

Robot data:
{facts}

Return JSON with exactly two keys:
"transcript": a verbatim transcript of what the survivor said (null if no audio or only silence/noise),
"report": a triage report as plain text lines, no markdown, in exactly this format:
{fmt}
Only state what the evidence supports. Say "unknown" rather than guess."""

LOCAL_PROMPT = """You are the triage assistant at a search-and-rescue HQ with no internet. A scout
robot found a survivor. You only have the robot's data below, no photo or audio.
Write a triage report as plain text lines, no markdown, in exactly this format:
{fmt}
Only state what the data supports. Say "unknown" rather than guess.

Robot data:
{facts}"""


def process_victim(v: dict, snap: Path, audio: Path | None) -> dict:
    """Returns fields to patch onto the victim: report, report_source, transcript."""
    if internet_up():
        try:
            note = " and a recording of their answer" if audio and audio.exists() else " (no audio was captured)"
            raw = _ask_gemini(GEMINI_PROMPT.format(audio_note=note, facts=_facts(v), fmt=REPORT_FORMAT),
                              image=snap, audio=audio, as_json=True)
            out = json.loads(raw)
            return {"report": out["report"].strip(), "transcript": out.get("transcript"), "report_source": "gemini"}
        except Exception as e:
            print(f"[brain] gemini failed, falling back: {e}")
    if base_station_up():
        try:
            text = _ask_ollama(LOCAL_PROMPT.format(facts=_facts(v), fmt=REPORT_FORMAT))
            return {"report": text, "report_source": "hq local model"}
        except Exception as e:
            print(f"[brain] ollama failed: {e}")
    return {
        "report": (f"PRIORITY: UNKNOWN\nPOSITION: {v['x']} m east, {v['y']} m north of entry\n"
                   f"CONDITION: unknown (no ai available)\nHAZARDS: unknown\n"
                   f"NEXT STEP: send a responder to the marked position"),
        "report_source": "template",
    }


# ---- live chat (only when online, from the dashboard) ----

REPLY_PROMPT = """You are the voice of a rescue robot talking to a trapped survivor.
Be calm, warm, and brief: one or two short sentences, spoken aloud.
Tell them help is coming, and ask ONE triage question at a time
(are you hurt, where, can you move, is anyone with you, can you breathe ok).
Conversation so far:
{conversation}
Robot:"""


def reply_to_victim(v: dict) -> tuple[str, str]:
    convo = "\n".join(f"{m['role']}: {m['text']}" for m in v["conversation"]) or "(nothing yet)"
    prompt = REPLY_PROMPT.format(conversation=convo)
    if internet_up():
        try:
            return _ask_gemini(prompt), "gemini"
        except Exception as e:
            print(f"[brain] gemini failed: {e}")
    if base_station_up():
        try:
            return _ask_ollama(prompt), "hq local model"
        except Exception as e:
            print(f"[brain] ollama failed: {e}")
    return "Help is on the way. Are you hurt?", "template"
