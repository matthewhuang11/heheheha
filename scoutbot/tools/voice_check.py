"""Manual local and ElevenLabs voice check. Never prints keys."""
from __future__ import annotations
import time
from scoutbot.voice.speaker import ElevenLabsVoice, LocalVoice

def _check(voice, label):
    started = time.monotonic()
    try:
        voice.speak("Scoutbot voice check. Can you hear me?")
        print(f"PASS {label} completed in {time.monotonic() - started:.2f}s")
    except Exception as exc: print(f"FAIL {label}: {type(exc).__name__}")

def main():
    try: _check(ElevenLabsVoice(), "ElevenLabs")
    except Exception as exc: print(f"SKIP ElevenLabs: {type(exc).__name__}")
    _check(LocalVoice(), "local")
if __name__ == "__main__": main()
