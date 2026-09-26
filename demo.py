import argparse,json,threading,time,cv2
from pathlib import Path
from dotenv import load_dotenv
from robot.types import Sensors,SceneReport
from robot.brain import decide
from robot.vlm import describe
load_dotenv()

def canned(i):
 d=[("clear","flat",[],False),("blocked","flat",[],False),("clear","flat",[{"type":"fire","where":"center","distance":"near"}],False),("clear","flat",[],True),("partially_blocked","rubble",[],False),("clear","stairs_or_drop",[],False)]
 p,t,h,person=d[i%6]; return SceneReport(path_ahead=p,best_direction="left",terrain=t,hazards=h,people={"visible":person,"where":"center" if person else "none","distance":"near" if person else "none"},objects=["canned"],confidence=1,notes="fake VLM")
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--fake-vlm",action="store_true"); ap.add_argument("--image"); ap.add_argument("--once",action="store_true"); args=ap.parse_args()
 cap=None; image=cv2.imread(args.image) if args.image else None
 if image is None and not args.image: cap=cv2.VideoCapture(0)
 if image is None and cap is None: raise SystemExit("could not open image")
 sensors=Sensors(updated_at=time.monotonic()); selected=0; scene=None; scene_at=None; failures=0; force=True; fake_index=0; busy=False
 def call(frame):
  nonlocal scene,scene_at,failures,busy
  try: scene=canned(fake_index) if args.fake_vlm else describe(frame); scene_at=time.monotonic(); failures=0
  except Exception: failures+=1
  finally: busy=False
 while True:
  frame=image.copy() if image is not None else cap.read()[1]
  if frame is None: break
  now=time.monotonic()
  if force and not busy:
   force=False; busy=True; threading.Thread(target=call,args=(frame.copy(),),daemon=True).start()
  sensors.updated_at=now; sensors.vlm_online=not (failures>=3)
  action,rule,reason=decide(sensors,scene,now,scene_at)
  Path("logs").mkdir(exist_ok=True)
  with open("logs/run.jsonl","a") as f:f.write(json.dumps({"time":time.time(),"sensors":sensors.model_dump(),"scene":scene.model_dump() if scene else None,"scene_age":now-scene_at if scene_at else None,"action":action,"rule":rule})+"\n")
  if args.once and scene: print(scene.model_dump_json(indent=2)); return
  lines=[f"L/C/R: {sensors.left}/{sensors.center}/{sensors.right} selected {selected+1}",f"VLM: {'offline' if not sensors.vlm_online else 'online'} age {now-scene_at:.1f}s" if scene_at else "VLM: waiting",f"{scene.path_ahead if scene else 'unknown'} {scene.terrain if scene else ''}",f"ACTION {action} rule {rule}: {reason}"]
  for n,line in enumerate(lines):cv2.putText(frame,line,(15,30+n*30),cv2.FONT_HERSHEY_SIMPLEX,.7,(0,255,0),2)
  cv2.imshow("robot brain",frame); key=cv2.waitKey(100)&255
  if key==ord('q'):break
  if key in map(ord,'123'):selected=key-ord('1')
  if key in (ord('='),ord('-')):
   names=['left','center','right']; setattr(sensors,names[selected],max(0,getattr(sensors,names[selected])+(10 if key==ord('=') else -10)))
  if key==ord('0'):
   v=list(sensors.valid);v[selected]=not v[selected];sensors.valid=tuple(v)
  if key==ord('r'):sensors=Sensors(updated_at=now)
  if key==ord('v'):failures=3 if failures<3 else 0
  if key==ord(' '):force=True
  if args.fake_vlm and key in map(ord,'456789'):fake_index=key-ord('4');force=True
  if now-(scene_at or 0)>=2:force=True
 if cap:cap.release()
 cv2.destroyAllWindows()
if __name__=='__main__':main()
