"""Measure how accurate Gemini's scene reports are on YOUR frames.
Step 1  python3 eval_vlm.py --label     Gemini pre-fills labels for each frame in dataset/, you correct them in dataset/labels.json
                                        (open the file, fix any wrong field; the image name is the key).  Delete "_check" when a label is verified.
Step 2  python3 eval_vlm.py --score [--repeats 3]   asks Gemini again (several times) and compares with your labels.
Reports: per-field accuracy, hazard recall, person recall, FALSE-CLEAR rate (said clear when you labelled blocked/hazard = the dangerous error),
self-consistency across repeats, latency."""
import argparse, json, statistics, time
from pathlib import Path
import cv2
from dotenv import load_dotenv
load_dotenv(override=True)
from robot.vlm import describe

D = Path("dataset"); LAB = D / "labels.json"
def frames(): return sorted(D.glob("*.jpg"))

def label():
    labels = json.loads(LAB.read_text()) if LAB.exists() else {}
    for p in frames():
        if p.name in labels: continue
        try: r = describe(cv2.imread(str(p))).model_dump()
        except Exception as e: print("skip", p.name, e); continue
        r.pop("notes", None); r["_check"] = "verify these labels, then delete this key"; labels[p.name] = r; print("prefilled", p.name, flush=True)
        LAB.write_text(json.dumps(labels, indent=1))
    print(f"Now open {LAB}, correct any wrong values (path_ahead, terrain, hazards, people), delete the _check keys.")

def haz(r, kinds=None): return {(h["type"], h["where"]) for h in r["hazards"] if kinds is None or h["type"] in kinds}
def score(repeats):
    labels = json.loads(LAB.read_text()); unverified = [k for k, v in labels.items() if "_check" in v]
    if unverified: print(f"WARNING: {len(unverified)} labels still marked _check (not verified): scores are not trustworthy yet")
    n = 0; field = {"path_ahead": 0, "terrain": 0, "best_direction": 0}; person_tp = person_fn = person_fp = 0; haz_tp = haz_fn = haz_fp = 0
    false_clear = danger_frames = 0; lat = []; cons = []; fails = 0
    for name, gt in labels.items():
        img = cv2.imread(str(D / name)); outs = []
        for _ in range(repeats):
            t = time.time()
            try: outs.append(describe(img).model_dump()); lat.append(time.time() - t)
            except Exception as e: fails += 1; print("fail", name, e)
        if not outs: continue
        for r in outs:
            n += 1
            for f in field: field[f] += r[f] == gt[f]
            gp, rp = gt["people"]["visible"], r["people"]["visible"]
            person_tp += gp and rp; person_fn += gp and not rp; person_fp += (not gp) and rp
            g, h = haz(gt, {"fire", "smoke", "drop_off"}), haz(r, {"fire", "smoke", "drop_off"})
            haz_tp += len(g & h); haz_fn += len(g - h); haz_fp += len(h - g)
            if gt["path_ahead"] in ("blocked", "partially_blocked") or g or gt["terrain"] == "stairs_or_drop":
                danger_frames += 1; false_clear += r["path_ahead"] == "clear" and not h and r["terrain"] != "stairs_or_drop"
        cons.append(statistics.mean(o["path_ahead"] == outs[0]["path_ahead"] for o in outs))
    if not n: print("no results"); return
    pct = lambda a, b: "n/a" if b == 0 else f"{100 * a / b:.0f}%"
    print(f"\nreplies scored: {n}  failed calls: {fails}")
    for f, v in field.items(): print(f"  {f:15s} accuracy {pct(v, n)}")
    print(f"  person recall {pct(person_tp, person_tp + person_fn)}   person false alarms {person_fp}")
    print(f"  fire/smoke/drop recall {pct(haz_tp, haz_tp + haz_fn)}   false alarms {haz_fp}")
    print(f"  FALSE-CLEAR rate {pct(false_clear, danger_frames)}  (said clear when it was blocked/hazard; lower is better, target ~0)")
    print(f"  self-consistency across repeats {pct(sum(cons), len(cons)) if cons else 'n/a'}   (path_ahead identical each time)")
    if lat: print(f"  latency p50 {statistics.median(lat):.2f}s  max {max(lat):.2f}s")

ap = argparse.ArgumentParser(); ap.add_argument("--label", action="store_true"); ap.add_argument("--score", action="store_true"); ap.add_argument("--repeats", type=int, default=1)
a = ap.parse_args()
if a.label: label()
elif a.score: score(a.repeats)
else: ap.print_help()
