"""Anything that talks cannot move: the talk, voice and sync code must never import motor or safety code."""
import subprocess, sys

def test_talk_voice_sync_never_import_motors_or_safety():
    code = ("import sys; import scoutbot.talk.worker, scoutbot.talk.router, scoutbot.talk.models, scoutbot.voice.speaker, "
            "scoutbot.sync.outbox, scoutbot.sync.mongo, scoutbot.sync.tiger; "
            "bad=[m for m in sys.modules if m.startswith(('scoutbot.hw', 'scoutbot.safety', 'scoutbot.runtime'))]; print(bad); sys.exit(1 if bad else 0)")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
