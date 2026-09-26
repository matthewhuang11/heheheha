"""Speaker: one clip at a time from a priority queue; responder messages and greetings jump the queue; the same sentence
is never repeated within dedupe_s. ElevenLabs (eleven_flash_v2_5, streamed) when online and a key is set, otherwise the
local voice: `say` on the Mac, `espeak-ng` on the Pi. provider: fake just prints [SAY] ..."""
from __future__ import annotations
import itertools, os, platform, queue, shutil, subprocess, tempfile, threading, time, wave
import httpx

class FakeVoice:
    name = "fake"
    def speak(self, text: str): print(f"[SAY] {text}", flush=True)

class LocalVoice:
    name = "local"
    def __init__(self):
        self.cmd = None
        if platform.system() == "Darwin" and shutil.which("say"): self.cmd = ["say"]
        elif platform.system() == "Windows" and shutil.which("powershell"): self.cmd = ["powershell", "-NoProfile", "-Command"]
        elif shutil.which("espeak-ng"): self.cmd = ["espeak-ng", "-s", "150"]
        elif shutil.which("espeak"): self.cmd = ["espeak", "-s", "150"]
    def speak(self, text: str):
        if self.cmd is None: print(f"[SAY (no local voice installed)] {text}", flush=True); return
        if platform.system() == "Windows":
            escaped = text.replace("'", "''")
            command = "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('" + escaped + "')"
            subprocess.run(self.cmd + [command], timeout=60, check=False)
        else:
            subprocess.run(self.cmd + [text], timeout=60, check=False)

def pcm_to_wav(pcm: bytes, path: str) -> None:
    """Write ElevenLabs pcm_22050 output as a portable mono WAV file."""
    with wave.open(path, "wb") as out:
        out.setnchannels(1); out.setsampwidth(2); out.setframerate(22050); out.writeframes(pcm)

def play_audio_file(path: str) -> bool:
    """Play a local MP3/WAV using the native player for the current OS."""
    system = platform.system()
    if system == "Darwin" and shutil.which("afplay"):
        command = ["afplay", path]
    elif system == "Windows" and shutil.which("powershell"):
        command = ["powershell", "-NoProfile", "-Command", f"(New-Object Media.SoundPlayer '{path.replace(chr(39), chr(39) * 2)}').PlaySync()"]
    elif system != "Windows" and shutil.which("aplay"):
        command = ["aplay", "-q", path]
    elif shutil.which("mpg123"):
        command = ["mpg123", "-q", path]
    elif shutil.which("ffplay"):
        command = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path]
    else:
        return False
    subprocess.run(command, timeout=60, check=False)
    return True

class ElevenLabsVoice:
    name = "elevenlabs"
    def __init__(self, model: str = "eleven_flash_v2_5"):
        self.key = os.getenv("ELEVENLABS_API_KEY", "").strip(); self.voice = os.getenv("ELEVENLABS_VOICE_ID", "").strip() or "21m00Tcm4TlvDq8ikWAM"
        if not self.key: raise RuntimeError("ELEVENLABS_API_KEY missing in .env")
        self.model = model; self.http = httpx.Client(timeout=15)
        self.stream_player = (["mpg123", "-q", "-"] if shutil.which("mpg123") else
                              ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-"] if shutil.which("ffplay") else None)
    def speak(self, text: str):
        is_windows = platform.system() == "Windows"
        output_format = "pcm_22050" if is_windows else "mp3_44100_128"
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice}/stream?output_format={output_format}"
        body = {"text": text, "model_id": self.model}
        with self.http.stream("POST", url, headers={"xi-api-key": self.key}, json=body) as r:
            r.raise_for_status()
            if self.stream_player:                       # speech starts before the whole clip is made
                p = subprocess.Popen(self.stream_player, stdin=subprocess.PIPE)
                for chunk in r.iter_bytes(): p.stdin.write(chunk)
                p.stdin.close(); p.wait(timeout=60); return
            data = b"".join(r.iter_bytes())
        with tempfile.NamedTemporaryFile(suffix=".wav" if is_windows else ".mp3", delete=False) as f:
            path = f.name
        if is_windows: pcm_to_wav(data, path)
        else:
            with open(path, "wb") as f: f.write(data)
        try:
            if not play_audio_file(path):
                raise RuntimeError("no audio player available")
        finally:
            try: os.unlink(path)
            except OSError: pass

class Speaker:
    def __init__(self, cfg: dict, shared):
        v = cfg["voice"]; self.shared = shared; self.dedupe_s = v.get("dedupe_s", 10)
        self.q: queue.PriorityQueue = queue.PriorityQueue(); self.count = itertools.count(); self.recent: dict[str, float] = {}
        self.fallback = FakeVoice() if v.get("fallback") == "fake" else LocalVoice()
        self.primary = None
        if v.get("provider") == "elevenlabs":
            try: self.primary = ElevenLabsVoice(v.get("model", "eleven_flash_v2_5"))
            except Exception as e: self._status(f"elevenlabs off ({e}); using {self.fallback.name}")
        elif v.get("provider") == "fake": self.primary = FakeVoice(); self.fallback = FakeVoice()
        else: self.primary = None
        if self.primary is not None: self._status(f"{self.primary.name} ready")
        self._stop = threading.Event(); self.spoken: list[tuple[str, str]] = []
    def _status(self, s):
        with self.shared.lock: self.shared.services["voice"] = s
    def say(self, text: str, priority: int = 0, key: str | None = None):
        """key: what counts as 'the same sentence' for de-duplication (default: the text). The talk worker passes
        survivor id + text so two different survivors can both get the same greeting."""
        now = time.monotonic(); self.recent = {old: at for old, at in self.recent.items() if now - at < self.dedupe_s}; k = key or text
        if now - self.recent.get(k, -1e9) < self.dedupe_s: return
        self.recent[k] = now
        self.q.put((-priority, next(self.count), text))
    def _speak_one(self, text: str):
        use_primary = self.primary is not None and (self.primary.name != "elevenlabs" or self.shared.online())
        if use_primary:
            try: self.primary.speak(text); self.spoken.append((self.primary.name, text)); self._status(f"{self.primary.name} ok"); return
            except Exception as e: self._status(f"{self.primary.name} failed ({type(e).__name__}); using {self.fallback.name}")
        try: self.fallback.speak(text); self.spoken.append((self.fallback.name, text))
        except Exception as e: print("[voice] fallback failed:", e, flush=True)
    def run(self):
        while not self._stop.is_set():
            try: _, _, text = self.q.get(timeout=0.5)
            except queue.Empty: continue
            self._speak_one(text)
    def start(self):
        threading.Thread(target=self.run, daemon=True, name="voice").start(); return self
    def stop(self): self._stop.set()
