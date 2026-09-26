"""Quick Gemini check. Run: python check_gemini.py   (add --write to save a working model to .env)"""
import os, sys, re
import cv2, numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types, errors

load_dotenv(override=True)
key = os.environ.get("GEMINI_API_KEY", "").strip().strip('"').strip("'")
if not key:
    sys.exit("FAIL: GEMINI_API_KEY is empty or missing in .env")
print("Key loaded.")
client = genai.Client(api_key=key)

try:
    models = [m for m in client.models.list()]
except errors.APIError as e:
    sys.exit(f"FAIL listing models -> HTTP {e.code}: {e.message}\n"
             "  400/403 usually means the key is invalid, restricted, or from the wrong project. Make a new key at https://aistudio.google.com/apikey")
names = []
for m in models:
    n = m.name.replace("models/", "")
    acts = getattr(m, "supported_actions", None) or []
    if "generateContent" in acts and n.startswith("gemini") and not re.search(r"embed|tts|image|live|audio|robotics|computer", n):
        names.append(n)
print(f"Key works. {len(names)} usable Gemini models found.")
flash = sorted([n for n in names if "flash" in n], reverse=True)
want = [os.getenv("GEMINI_MODEL", "").strip(), "gemini-flash-latest", "gemini-flash-lite-latest"] + flash
seen, cands = set(), []
for n in want:
    if n and n not in seen and (n in names or n.endswith("-latest")):
        seen.add(n); cands.append(n)

img = np.zeros((120, 160, 3), np.uint8); cv2.rectangle(img, (40, 30), (120, 90), (0, 0, 255), -1)
jpg = cv2.imencode(".jpg", img)[1].tobytes()
cfg = types.GenerateContentConfig(response_mime_type="application/json")
good = None
for n in cands[:8]:
    try:
        r = client.models.generate_content(model=n, contents=['Return JSON {"color": <main color of the shape>}.', types.Part.from_bytes(data=jpg, mime_type="image/jpeg")], config=cfg)
        print(f"  OK   {n} -> {r.text.strip()[:60]}")
        good = good or n
    except errors.APIError as e:
        print(f"  FAIL {n} -> HTTP {e.code}: {str(e.message)[:100]}")
if not good:
    sys.exit("No model worked. See the errors above (429 = quota/billing, 404 = model name, 403 = key/project).")
print(f"\nUse: GEMINI_MODEL={good}")
if "--write" in sys.argv:
    lines = [l for l in open(".env").read().splitlines() if not l.startswith("GEMINI_MODEL=")]
    open(".env", "w").write("\n".join(lines) + f"\nGEMINI_MODEL={good}\n"); print("Saved to .env")
