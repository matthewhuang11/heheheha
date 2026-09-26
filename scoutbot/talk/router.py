"""Online/offline router with a circuit breaker (spec 10.1).
 - Gemini gets 1 quick retry. After fail_threshold failures in a row the circuit OPENS: all talk goes to Ollama for
   open_s seconds, then one test call is let through (half-open). Success closes it again.
 - No internet (or 'simulate offline') -> Ollama straight away. Ollama down too -> canned lines, triage UNKNOWN.
 - Every result records which model made it."""
from __future__ import annotations
import threading, time
from scoutbot.talk.triage import categorize, unknown
from scoutbot.types import Triage

class CircuitBreaker:
    def __init__(self, fail_threshold: int = 3, open_s: float = 30, clock=time.monotonic):
        self.n = fail_threshold; self.open_s = open_s; self.clock = clock; self.fails = 0; self.open_until = None; self.lock = threading.Lock()
    @property
    def state(self) -> str:
        with self.lock:
            if self.open_until is None: return "closed"
            return "open" if self.clock() < self.open_until else "half-open"
    def allow(self) -> bool:
        return self.state != "open"
    def success(self):
        with self.lock: self.fails = 0; self.open_until = None
    def failure(self):
        with self.lock:
            self.fails += 1
            if self.fails >= self.n or self.open_until is not None: self.open_until = self.clock() + self.open_s

class TalkRouter:
    def __init__(self, online_fn, gemini=None, ollama=None, canned=None, breaker: CircuitBreaker | None = None, status_fn=None):
        from scoutbot.talk.models import CannedTalk
        self.online = online_fn; self.gemini = gemini; self.ollama = ollama; self.canned = canned or CannedTalk()
        self.breaker = breaker or CircuitBreaker(); self.status = status_fn or (lambda k, v: None)

    def _chain(self):
        chain = []
        if self.gemini is not None and self.online() and self.breaker.allow(): chain.append(self.gemini)
        if self.ollama is not None: chain.append(self.ollama)
        return chain

    def _call(self, model, fn_name, *args):
        tries = 2 if model is self.gemini else 1
        for i in range(tries):
            try:
                out = getattr(model, fn_name)(*args)
                if model is self.gemini: self.breaker.success(); self.status("gemini", "ok")
                else: self.status("ollama", "ok")
                return out
            except Exception as e:
                err = f"{type(e).__name__}: {e}"[:160]
                if model is self.gemini:
                    if i == tries - 1: self.breaker.failure(); self.status("gemini", f"error ({self.breaker.state}): {err}")
                else: self.status("ollama", f"error: {err}")
                last = e
        raise last

    def triage(self, chat, context: str, snapshot: bytes | None) -> Triage:
        for m in self._chain():
            try: return categorize(self._call(m, "triage_facts", chat, context, snapshot), m.label)
            except Exception: continue
        return unknown("canned", "no model reachable")

    def reply(self, chat, context: str) -> tuple[str, str]:
        """Returns (text, source) where source is gemini | ollama | canned."""
        for m in self._chain():
            try: return self._call(m, "reply", chat, context), m.name
            except Exception: continue
        return self.canned.reply(chat, context), "canned"
