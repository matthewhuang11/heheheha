"""Offline speech: espeak-ng for the robot's voice, arecord for the survivor's answer.

Everything here works with no network. Spoken lines are cached as wav files, so you can
drop in nicer recordings (e.g. made with ElevenLabs) under data/tts/ with the same name.
"""
import hashlib
import subprocess

import config

TTS_DIR = config.DATA_DIR / "tts"
TTS_DIR.mkdir(exist_ok=True)
AUDIO_DIR = config.DATA_DIR / "audio"
AUDIO_DIR.mkdir(exist_ok=True)


def _dev(flag_dev):
    return ["-D", flag_dev] if flag_dev else []


def tts_file(text):
    wav = TTS_DIR / (hashlib.sha1(text.encode()).hexdigest()[:10] + ".wav")
    if not wav.exists():
        subprocess.run(["espeak-ng", "-s", "150", "-w", str(wav), text], check=True, timeout=20)
    return wav


def say(text):
    """Speak and block until done. Returns False if there's no speaker."""
    try:
        subprocess.run(["aplay", "-q", *_dev(config.AUDIO_OUT), str(tts_file(text))], check=True, timeout=60)
        return True
    except Exception as e:
        print(f"[voice] say failed: {e}")
        return False


def record(name, seconds):
    """Record from the mic into data/audio/<name>.wav. Returns the path, or None if there's no mic."""
    path = AUDIO_DIR / f"{name}.wav"
    try:
        subprocess.run(
            ["arecord", "-q", *_dev(config.AUDIO_IN), "-f", "S16_LE", "-r", "16000", "-c", "1",
             "-d", str(int(seconds)), str(path)],
            check=True, timeout=seconds + 10,
        )
        return path
    except Exception as e:
        print(f"[voice] record failed: {e}")
        return None
