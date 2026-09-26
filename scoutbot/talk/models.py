"""The three ways the robot can think of words: Gemini (online, sees the snapshot), Ollama (offline, text only, runs on the
laptop), and canned lines (when both are down). Each has triage_facts() and reply()."""
from __future__ import annotations
import json, os
from pathlib import Path
import httpx
from scoutbot.talk.triage import FACTS_SCHEMA, TriageFacts, parse_facts

PROMPTS = Path(__file__).resolve().parent / "prompts"
TRIAGE_PROMPT = (PROMPTS / "triage_v1.txt").read_text() + json.dumps(FACTS_SCHEMA, separators=(",", ":"))
REPLY_PROMPT = (PROMPTS / "reply_v1.txt").read_text()

GREETING = "Hello, I'm a rescue robot. Help is being called. Can you hear me?"
CANNED_REPLIES = [
    "Help is on the way. Stay where you are if you can. Are you hurt?",
    "A responder has been told where you are. Can you move your arms and legs?",
    "Stay still and stay calm. Is anyone else with you?",
]

def transcript(chat: list, limit: int = 12) -> str:
    lines = []
    for m in chat[-limit:]:
        who = {"survivor": "Survivor", "robot": "Robot", "responder": "Responder"}.get(m.role, m.role)
        lines.append(f"{who}: {m.text}")
    return "\n".join(lines) or "(no conversation yet)"

class GeminiTalk:
    name = "gemini"
    def __init__(self, timeout_s: float = 8):
        key = os.environ.get("GEMINI_API_KEY", "").strip().strip('"').strip("'")
        if not key: raise RuntimeError("GEMINI_API_KEY is missing (check .env)")
        from google import genai
        from google.genai import types
        self.types = types; self.model = os.getenv("GEMINI_TALK_MODEL") or os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
        self.client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=int(timeout_s * 1000)))
    @property
    def label(self): return self.model
    def _gen(self, parts, system=None, json_mode=False):
        cfg = self.types.GenerateContentConfig(temperature=0.2, system_instruction=system,
                                               response_mime_type="application/json" if json_mode else None)
        return self.client.models.generate_content(model=self.model, contents=parts, config=cfg).text or ""
    def triage_facts(self, chat, context: str, snapshot: bytes | None) -> TriageFacts:
        parts = [TRIAGE_PROMPT, f"Scene notes: {context}\nConversation so far:\n{transcript(chat)}"]
        if snapshot: parts.append(self.types.Part.from_bytes(data=snapshot, mime_type="image/jpeg"))
        return parse_facts(self._gen(parts, json_mode=True))
    def reply(self, chat, context: str) -> str:
        text = self._gen([f"Scene notes: {context}\nConversation so far:\n{transcript(chat)}\nWrite the robot's next line."], system=REPLY_PROMPT)
        return clean_reply(text)

class OllamaTalk:
    name = "ollama"
    def __init__(self, url: str, model: str, timeout_s: float = 20, keep_alive: str = "30m"):
        self.url = url.rstrip("/"); self.model = model; self.timeout = timeout_s; self.keep_alive = keep_alive
        self.http = httpx.Client(timeout=timeout_s)
    @property
    def label(self): return f"ollama:{self.model}"
    def healthy(self) -> bool:
        try: return self.http.get(self.url + "/api/tags", timeout=2).status_code == 200
        except Exception: return False
    def _chat(self, messages, fmt=None) -> str:
        body = {"model": self.model, "messages": messages, "stream": False, "keep_alive": self.keep_alive, "options": {"temperature": 0.2}}
        if fmt is not None: body["format"] = fmt
        r = self.http.post(self.url + "/api/chat", json=body); r.raise_for_status()
        return r.json()["message"]["content"]
    def triage_facts(self, chat, context: str, snapshot: bytes | None = None) -> TriageFacts:
        msg = f"{TRIAGE_PROMPT}\n\nScene notes (from the robot's camera, as text): {context}\nConversation so far:\n{transcript(chat)}"
        return parse_facts(self._chat([{"role": "user", "content": msg}], fmt=FACTS_SCHEMA))
    def reply(self, chat, context: str) -> str:
        return clean_reply(self._chat([{"role": "system", "content": REPLY_PROMPT},
                                       {"role": "user", "content": f"Scene notes: {context}\nConversation so far:\n{transcript(chat)}\nWrite the robot's next line."}]))
    def warm_up(self):
        try: self._chat([{"role": "user", "content": "Say OK."}])
        except Exception: pass

class CannedTalk:
    name = "canned"; label = "canned"
    def __init__(self): self.i = 0
    def triage_facts(self, chat, context, snapshot=None) -> TriageFacts:
        raise RuntimeError("no model available")
    def reply(self, chat, context) -> str:
        t = CANNED_REPLIES[self.i % len(CANNED_REPLIES)]; self.i += 1; return t

def clean_reply(text: str) -> str:
    t = " ".join((text or "").strip().strip('"').split())
    if not t: raise ValueError("empty reply")
    return t[:300]
