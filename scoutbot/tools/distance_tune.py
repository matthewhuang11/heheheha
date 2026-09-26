"""Measure YOLO person box heights at known distances and suggest perception.yolo near_frac / mid_frac (R1 / A4).

    python -m scoutbot.tools.distance_tune                      # interactive: stand at each distance, press Enter
    python -m scoutbot.tools.distance_tune --distances 0.7 1.0 1.5 2.5 4.0 --frames 20

For each distance it grabs frames, keeps the largest person box per frame, and records its height as a fraction of the
image height. At the end it prints a table (median / min / max) and suggested cut-offs:
  near_frac = midpoint between the 1.0 m median and the 1.5 m median   (near = closer than ~1 m)
  mid_frac  = midpoint between the 2.5 m median and the 4.0 m median   (mid  = ~1 to 2.5 m, far beyond)
Extra poses (lying down, partly hidden) can be added with --extra "lying 1.5" "hidden 1.5"."""
from __future__ import annotations
import argparse, json, statistics, sys, time
from pathlib import Path

def parser():
    p = argparse.ArgumentParser(prog="python -m scoutbot.tools.distance_tune", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--profile", default="laptop")
    p.add_argument("--distances", type=float, nargs="+", default=[0.7, 1.0, 1.5, 2.5, 4.0], help="metres")
    p.add_argument("--extra", nargs="*", default=["lying 1.5", "hidden 1.5"], help='extra poses: "name metres"')
    p.add_argument("--frames", type=int, default=20)
    p.add_argument("--model", help="override perception.yolo.model (e.g. yolov8n_ncnn_model)")
    p.add_argument("--imgsz", type=int, default=None)
    p.add_argument("--out", default="data/distance_tune.json")
    p.add_argument("--no-wait", action="store_true", help="don't wait for Enter between distances (for testing)")
    return p

def suggest(rows: dict[str, list[float]]) -> tuple[float | None, float | None]:
    """rows: label -> list of height fractions. Labels are distances in metres as strings."""
    med = {}
    for k, v in rows.items():
        try: med[float(k)] = statistics.median(v) if v else None
        except ValueError: continue
    def mid(a, b):
        return round((med[a] + med[b]) / 2, 3) if med.get(a) and med.get(b) else None
    return mid(1.0, 1.5), mid(2.5, 4.0)

def summarize(rows: dict[str, list[float]], seen: dict[str, int], frames: int) -> str:
    lines = ["| position | detected frames | median height | min | max |", "| --- | --- | --- | --- | --- |"]
    for k, v in rows.items():
        if v: lines.append(f"| {k} | {seen[k]}/{frames} | {statistics.median(v):.3f} | {min(v):.3f} | {max(v):.3f} |")
        else: lines.append(f"| {k} | 0/{frames} | - | - | - |")
    return "\n".join(lines)

def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        try: s.reconfigure(errors="replace")
        except Exception: pass
    a = parser().parse_args(argv)
    from scoutbot.settings import get, load
    from scoutbot.hw.camera_opencv import open_best_camera
    from scoutbot.perception.yolo import YoloDetector
    cfg = load(a.profile); ycfg = dict(get(cfg, "perception.yolo", {}))
    if a.model: ycfg["model"] = a.model
    if a.imgsz: ycfg["imgsz"] = a.imgsz
    det = YoloDetector(ycfg)
    cam = open_best_camera(get(cfg, "hw.camera_index", 0))
    if not cam.ok: raise SystemExit("no camera available")
    plan = [(f"{d:g}", f"stand facing the camera {d:g} m away") for d in a.distances]
    for e in a.extra:
        name, _, m = e.partition(" "); plan.append((f"{name} {m}", f"{name} at {m} m"))
    rows: dict[str, list[float]] = {}; seen: dict[str, int] = {}
    try:
        for label, what in plan:
            if not a.no_wait:
                try: input(f"\n==> {what}, then press Enter ")
                except EOFError: pass
            hs = []; n = 0
            for _ in range(a.frames):
                f = cam.read()
                if f is None: time.sleep(0.05); continue
                boxes = [d.bbox for d in det.detect(f, time.monotonic()) if d.bbox]
                if boxes: n += 1; hs.append(max(b[3] - b[1] for b in boxes))
            rows[label] = [round(h, 4) for h in hs]; seen[label] = n
            print(f"    {label}: person in {n}/{a.frames} frames" + (f", median height {statistics.median(hs):.3f}" if hs else ""), flush=True)
    finally:
        cam.close()
    near, mid = suggest(rows)
    print("\n" + summarize(rows, seen, a.frames))
    print(f"\nsuggested: near_frac={near}  mid_frac={mid}   (current: near_frac={ycfg.get('near_frac')} mid_frac={ycfg.get('mid_frac')})")
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"model": ycfg.get("model"), "imgsz": ycfg.get("imgsz"), "rows": rows, "seen": seen,
                               "frames": a.frames, "suggest": {"near_frac": near, "mid_frac": mid}}, indent=1), encoding="utf-8")
    print(f"saved {out}")

if __name__ == "__main__":
    main()
