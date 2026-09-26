"""Rule-based triage (spec 10.2). The model only EXTRACTS facts; these plain rules pick the category. Loosely based on
START adult triage, simplified because the robot cannot measure breathing rate or pulse. Always preliminary."""
from __future__ import annotations
import json, re
from pydantic import ValidationError
from scoutbot.types import Triage, TriageFacts

RULES = [
    ("can walk", lambda f: f.can_walk == "yes", "MINOR"),
    ("not responsive", lambda f: f.responsive == "no", "IMMEDIATE"),
    ("breathing trouble or visible bleeding", lambda f: f.breathing_trouble == "yes" or f.visible_bleeding == "yes", "IMMEDIATE"),
    ("trapped", lambda f: f.trapped == "yes", "IMMEDIATE"),
    ("responsive, cannot walk", lambda f: f.responsive == "yes", "DELAYED"),
]

def categorize(facts: TriageFacts, model: str) -> Triage:
    for name, cond, cat in RULES:
        if cond(facts): return Triage(category=cat, rule=name, facts=facts, model=model)
    return Triage(category="UNKNOWN", rule="not enough information", facts=facts, model=model)

def parse_facts(text: str) -> TriageFacts:
    """Model reply -> TriageFacts. Tolerates ```json fences and text around the object. Raises ValueError if unusable."""
    t = (text or "").strip(); t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    if not t.startswith("{"):
        m = re.search(r"\{.*\}", t, re.S)
        if not m: raise ValueError("no JSON object in reply")
        t = m.group(0)
    data = json.loads(t)
    if not isinstance(data, dict): raise ValueError("reply is not an object")
    for k in ("responsive", "can_walk", "trapped", "visible_bleeding", "breathing_trouble"):
        v = str(data.get(k, "unknown")).strip().lower()
        data[k] = v if v in ("yes", "no", "unknown") else "unknown"
    for k in ("hazards_nearby", "injuries_reported"):
        v = data.get(k) or []
        data[k] = [str(x)[:60] for x in (v if isinstance(v, list) else [v])][:12]
    data["summary"] = str(data.get("summary", ""))[:240]
    try: return TriageFacts.model_validate(data)
    except ValidationError as e: raise ValueError(str(e)) from e

def unknown(model: str, why: str = "") -> Triage:
    return Triage(category="UNKNOWN", rule="model reply unusable" + (f": {why}"[:80] if why else ""), facts=TriageFacts(), model=model)

FACTS_SCHEMA = TriageFacts.model_json_schema()
