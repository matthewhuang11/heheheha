import os
import wave
from scoutbot.sync import resolve_sinks
from scoutbot.sync.tiger import ssl_required
from scoutbot.voice.speaker import pcm_to_wav
from scoutbot.talk.models import SAFE_FALLBACK_REPLY, clean_reply

def test_pcm_to_wav(tmp_path):
    path = tmp_path / "voice.wav"; pcm_to_wav(b"\x00\x00\x01\x00", str(path))
    with wave.open(str(path), "rb") as got:
        assert (got.getnchannels(), got.getsampwidth(), got.getframerate(), got.getnframes()) == (1, 2, 22050, 2)

def test_auto_sinks_ignore_empty_values(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "  "); monkeypatch.setenv("TIGER_DATABASE_URL", "'postgres://x'")
    assert resolve_sinks({"sync": {"sinks": "auto"}}) == ["tiger"]
    assert resolve_sinks({"sync": {"sinks": ["mongo"]}}) == ["mongo"]

def test_tiger_url_adds_tls_requirement():
    assert "sslmode=require" in ssl_required("postgresql://user:pass@host/db")
    assert "sslmode=verify-full" in ssl_required("postgresql://host/db?sslmode=verify-full")

def test_reply_filter_replaces_promises_and_unsafe_medical_advice():
    assert clean_reply("Rescue will arrive in 5 minutes. Take this medicine.") == SAFE_FALLBACK_REPLY
    assert clean_reply("Stay calm. Can you tell me where it hurts? A third sentence.") == "Stay calm. Can you tell me where it hurts?"
