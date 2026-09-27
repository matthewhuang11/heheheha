"""All tunables in one place. Override any of these in pi/.env."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")


def _f(name, default):
    return float(os.getenv(name, default))


# camera: "picam" (camera module 3 on the csi port), an index (0 = first usb webcam), a url/path,
# or "gopro" (hero 12/13 over usb, see gopro.py)
CAMERA_SRC = os.getenv("CAMERA_SRC", "picam")
CAMERA_W = int(os.getenv("CAMERA_W", 640))
CAMERA_H = int(os.getenv("CAMERA_H", 360))               # 16:9, so the wide lens isn't cropped to 4:3
CAMERA_FPS = int(os.getenv("CAMERA_FPS", 15))
CAMERA_ROTATE = int(os.getenv("CAMERA_ROTATE", 0))       # 180 if the camera is mounted upside down
CAMERA_HFOV_DEG = _f("CAMERA_HFOV_DEG", 102)  # camera module 3 wide (imx708_wide); standard lens is 66

# detection
MODEL_PATH = os.getenv("MODEL_PATH", str(ROOT / "models" / "yolov8n-320.onnx"))
MODEL_SIZE = int(os.getenv("MODEL_SIZE", 320))
CONF_THRESHOLD = _f("CONF_THRESHOLD", 0.45)
DETECT_FPS = _f("DETECT_FPS", 3)  # max yolo runs per second; more just heats the pi
PERSON_LENGTH_M = _f("PERSON_LENGTH_M", 1.7)  # longest body dimension, standing or lying

# victims: a detection must persist this many inference cycles before it becomes a victim
CONFIRM_HITS = int(os.getenv("CONFIRM_HITS", 3))
SAME_VICTIM_RADIUS_M = _f("SAME_VICTIM_RADIUS_M", 1.0)

# motors (bcm pin numbers). works for tb6612 (in1/in2/pwm) or l298n (in1/in2/en).
LEFT_PINS = tuple(int(p) for p in os.getenv("LEFT_PINS", "5,6,12").split(","))
RIGHT_PINS = tuple(int(p) for p in os.getenv("RIGHT_PINS", "23,24,13").split(","))
LEFT_INVERT = os.getenv("LEFT_INVERT", "0") == "1"    # flip a side that spins backwards
RIGHT_INVERT = os.getenv("RIGHT_INVERT", "0") == "1"
MIN_DUTY = _f("MIN_DUTY", 0.4)  # tt motors on an l298n stall below ~40% pwm
MAX_SPEED_MPS =_f("MAX_SPEED_MPS", 0.4)   # calibrate: drive full speed for 2s, measure
MAX_TURN_DPS = _f("MAX_TURN_DPS", 120)     # calibrate: spin full speed for 2s, measure
DRIVE_TIMEOUT_S = _f("DRIVE_TIMEOUT_S", 0.5)  # motors stop if no command arrives in this window

# hc-sr04 ultrasonic sensors: name:trig:echo (bcm). echo goes through a 1k/2k divider (5v -> 3.3v).
# drop any you don't have, e.g. SONARS=front:5:6
# layout: camera dead ahead, one sonar angled ~30 deg left of forward and one ~30 deg right
SONARS = [
    (n, int(t), int(e))
    for n, t, e in (s.split(":") for s in os.getenv("SONARS", "left:17:27,right:22:10").split(",") if s)
]
# sonars that look ahead: the closest of these is "what's in front of us"
FRONT_SONARS = [n for n in os.getenv("FRONT_SONARS", "front,left,right").split(",") if n]

# other senses (bcm pins; blank disables)
SOUND_PIN = int(os.getenv("SOUND_PIN", 25) or -1)       # sound sensor D0
SOUND_ACTIVE_LOW = os.getenv("SOUND_ACTIVE_LOW", "1") == "1"  # most lm393 modules pull D0 low on a loud sound
BUZZER_PIN = int(os.getenv("BUZZER_PIN", 8) or -1)      # active buzzer
# idle level is the opposite of this. a bare passive buzzer from the pin to gnd must idle LOW,
# or the pin pushes dc through the coil the whole time the service runs
BUZZER_ACTIVE_LOW = os.getenv("BUZZER_ACTIVE_LOW", "0") == "1"
BUZZER_PASSIVE = os.getenv("BUZZER_PASSIVE", "1") == "1"  # passive buzzer: driven with a tone, not a dc level
BUZZER_HZ = int(_f("BUZZER_HZ", 2500))                    # beep pitch; passive buzzers are loudest ~2-3 khz
DHT_PIN = int(os.getenv("DHT_PIN", 4) or -1)            # dht11 data
HOT_C = _f("HOT_C", 40)                                  # flag heat as a hazard above this

# autonomy
CRUISE = _f("CRUISE", 0.45)             # explore throttle
APPROACH_SPEED = _f("APPROACH_SPEED", 0.35)
TURN_SPEED = _f("TURN_SPEED", 0.7)      # spin speed when avoiding
AVOID_DIST_M = _f("AVOID_DIST_M", 0.35)  # obstacle closer than this -> turn away
# an hc-sr04 transmits a 200us burst, so any echo shorter than that is the sensor
# hearing itself, not a reflection. below this the reading is discarded as no-echo.
SONAR_MIN_M = _f("SONAR_MIN_M", 0.06)
CLEAR_DIST_M = _f("CLEAR_DIST_M", 0.6)   # keep turning until front is this clear
STOP_NEAR_PERSON_M = _f("STOP_NEAR_PERSON_M", 1.0)
MISSION_S = _f("MISSION_S", 150)        # auto-return after this long
LISTEN_S = _f("LISTEN_S", 8)            # how long to record a survivor's answer

# audio (alsa device names; blank = system default). `aplay -l` / `arecord -l` to list.
AUDIO_OUT = os.getenv("AUDIO_OUT", "")
AUDIO_IN = os.getenv("AUDIO_IN", "")
GREETING = os.getenv("GREETING", "I am a rescue robot. Help is coming. If you can hear me, tell me your name, "
                                  "if you are hurt, and if anyone is with you.")
SIGNOFF = os.getenv("SIGNOFF", "Thank you. I have marked your location. Stay where you are, rescuers are on the way.")

# brain
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
GEMINI_TIMEOUT_S = _f("GEMINI_TIMEOUT_S", 12)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://172.20.10.10:11434")  # base-station laptop
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_TIMEOUT_S = _f("OLLAMA_TIMEOUT_S", 90)

DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
