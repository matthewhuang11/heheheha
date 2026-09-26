"""Talk worker end to end with fake models and a fake voice (no network)."""
import numpy as np
from scoutbot import settings
from scoutbot.state import Bus, Shared
from scoutbot.survivors.registry import Registry
from scoutbot.talk.router import TalkRouter
from scoutbot.talk.worker import TalkWorker
from scoutbot.types import PersonDetection, Pose, TriageFacts
from scoutbot.voice.speaker import Speaker

class Ollama:
    name = "ollama"; label = "ollama:test"; url = "x"
    def reply(self, chat, ctx): return "Stay still, a responder is coming."
    def triage_facts(self, chat, ctx, snap=None):
        said = " ".join(m.text for m in chat if m.role == "survivor")
        return TriageFacts(responsive="yes" if said else "unknown", trapped="yes" if "stuck" in said else "unknown")
    def healthy(self): return True
    def warm_up(self): pass

def setup(tmp_path):
    cfg = settings.load("base", ["voice.provider=fake", "voice.fallback=fake", f"survivors.data_dir={tmp_path}"], load_env=False)
    sh = Shared(); sh.internet = False; bus = Bus(); reg = Registry(cfg, bus, data_dir=tmp_path)
    voice = Speaker(cfg, sh); router = TalkRouter(sh.online, None, Ollama())
    return cfg, sh, bus, reg, voice, TalkWorker(cfg, sh, bus, reg, voice, router=router)

def det(): return PersonDetection(source="yolo", where="center", distance="mid", confidence=0.9, at=0)

def test_new_survivor_greeting_triage_and_chat(tmp_path):
    cfg, sh, bus, reg, voice, tw = setup(tmp_path)
    s, _ = reg.sighting(det(), Pose(), 0.0, np.zeros((10, 10, 3), np.uint8))
    tw.handle({"kind": "new_survivor", "sid": s.id})
    got = reg.get(s.id); assert got.chat[0].role == "robot" and got.triage.category == "UNKNOWN"
    tw.handle({"kind": "survivor_says", "sid": s.id, "text": "my leg is stuck", "source": "typed"})
    got = reg.get(s.id)
    assert [m.role for m in got.chat] == ["robot", "survivor", "robot"] and got.chat[-1].source == "ollama"
    assert got.triage.category == "IMMEDIATE" and got.triage.model == "ollama:test"
    tw.handle({"kind": "responder_says", "sid": s.id, "text": "we are coming"})
    assert reg.get(s.id).chat[-1].role == "responder"
    texts = [voice.q.get_nowait()[2] for _ in range(voice.q.qsize())]
    assert "we are coming" in texts and any("rescue robot" in t for t in texts)

def test_two_survivors_both_get_greeted(tmp_path):
    cfg, sh, bus, reg, voice, tw = setup(tmp_path)
    a, _ = reg.sighting(det(), Pose(), 0.0); b, _ = reg.sighting(det(), Pose(y_cm=900), 900.0)
    tw.handle({"kind": "new_survivor", "sid": a.id}); tw.handle({"kind": "new_survivor", "sid": b.id})
    assert voice.q.qsize() == 2
