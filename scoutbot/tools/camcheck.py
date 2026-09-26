import argparse,time
from pathlib import Path
import cv2
from scoutbot.settings import load,get

def parser():
 p=argparse.ArgumentParser(description='Save 20 camera frames and report resolution/FPS.');p.add_argument('--profile',default='mac');return p
def main(argv=None):
 a=parser().parse_args(argv);cfg=load(a.profile)
 from scoutbot.hw.camera_opencv import OpenCVCamera
 cam=OpenCVCamera(get(cfg,'hw.camera_index',0));out=Path('data/camcheck');out.mkdir(parents=True,exist_ok=True);ts=[];means=[]
 try:
  for i in range(20):
   t=time.monotonic();f=cam.read()
   if f is None: raise SystemExit('camera returned no frame')
   ts.append(time.monotonic()-t);means.append(float(f.mean()));cv2.imwrite(str(out/f'{i:02d}.jpg'),f)
   if i==0: h,w=f.shape[:2]
 finally: cam.close()
 print(f'{w}x{h}, {len(ts)/max(sum(ts),.001):.1f} FPS, saved {out}')
 if sum(means)/len(means)<8: print('WARNING: frames appear black')
if __name__=='__main__':main()
