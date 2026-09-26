from scoutbot.talk.router import CircuitBreaker, TalkRouter
from scoutbot.types import TriageFacts

class Clock:
    def __init__(self): self.t = 0.0
    def __call__(self): return self.t

class Model:
    def __init__(self, name, fail=False): self.name = name; self.label = name; self.fail = fail; self.calls = 0
    def reply(self, chat, ctx):
        self.calls += 1
        if self.fail: raise RuntimeError("down")
        return f"hello from {self.name}"
    def triage_facts(self, chat, ctx, snap=None):
        self.calls += 1
        if self.fail: raise RuntimeError("down")
        return TriageFacts(responsive="yes", trapped="yes")

def test_breaker_opens_after_threshold_and_half_opens():
    c = Clock(); b = CircuitBreaker(3, 30, clock=c)
    for _ in range(3): assert b.allow(); b.failure()
    assert b.state == "open" and not b.allow()
    c.t = 31; assert b.state == "half-open" and b.allow()
    b.failure(); assert b.state == "open"                     # failed probe re-opens
    c.t = 62; b.success(); assert b.state == "closed"

def test_online_uses_gemini():
    g, o = Model("gemini"), Model("ollama")
    r = TalkRouter(lambda: True, g, o)
    assert r.reply([], "") == ("hello from gemini", "gemini")
    t = r.triage([], "", None); assert t.category == "IMMEDIATE" and t.model == "gemini"

def test_offline_goes_straight_to_ollama():
    g, o = Model("gemini"), Model("ollama")
    r = TalkRouter(lambda: False, g, o)
    assert r.reply([], "")[1] == "ollama" and g.calls == 0

def test_gemini_failures_fall_back_and_open_breaker():
    c = Clock(); g, o = Model("gemini", fail=True), Model("ollama")
    r = TalkRouter(lambda: True, g, o, breaker=CircuitBreaker(3, 30, clock=c))
    for _ in range(3): assert r.reply([], "")[1] == "ollama"
    calls = g.calls; r.reply([], ""); assert g.calls == calls   # breaker open: Gemini not even tried

def test_everything_down_gives_canned_and_unknown():
    r = TalkRouter(lambda: True, Model("gemini", True), Model("ollama", True))
    text, src = r.reply([], ""); assert src == "canned" and text
    assert r.triage([], "", None).category == "UNKNOWN"
