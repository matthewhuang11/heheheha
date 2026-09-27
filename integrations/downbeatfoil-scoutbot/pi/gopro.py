"""GoPro Hero 12/13 as the robot's camera, over USB.

Over USB the GoPro shows up as a small network link, not a normal webcam: the Pi gets an
address like 172.2X.1YZ.5x and the camera sits at .51 on the same subnet. We turn on wired
control, start webcam mode through the Open GoPro HTTP API, and the camera then streams
MPEG-TS video to udp port 8554 on the Pi, which OpenCV reads through ffmpeg.

On the camera: Preferences > Connections > USB Connection = GoPro Connect.
"""
import re
import subprocess

import httpx

STREAM_URL = "udp://@0.0.0.0:8554?overrun_nonfatal=1&fifo_size=50000000"
RES_720P = 7


def camera_ip():
    out = subprocess.run(["ip", "-4", "-o", "addr"], capture_output=True, text=True).stdout
    m = re.search(r"inet (172\.2\d\.1\d\d)\.\d+/", out)
    return f"{m.group(1)}.51" if m else None


def start():
    """Returns the stream url once webcam mode is running, or None if no gopro is attached."""
    ip = camera_ip()
    if not ip:
        return None
    base = f"http://{ip}:8080/gopro"
    try:
        httpx.get(f"{base}/camera/control/wired_usb", params={"p": 1}, timeout=4)
        httpx.get(f"{base}/webcam/stop", timeout=4)
        r = httpx.get(f"{base}/webcam/start", params={"res": RES_720P, "fov": 0}, timeout=6)
        if r.status_code != 200:
            print(f"[gopro] webcam start refused: {r.status_code} {r.text[:120]}")
            return None
    except httpx.HTTPError as e:
        print(f"[gopro] not answering at {ip}: {e}")
        return None
    print(f"[gopro] webcam streaming from {ip}")
    return STREAM_URL
