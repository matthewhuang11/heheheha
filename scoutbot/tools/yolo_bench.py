import argparse,time
from pathlib import Path
import cv2
from scoutbot.settings import load,get

def parser():
 p=argparse.ArgumentParser(description='Benchmark YOLO person detection on 50 frames.');p.add_argument('--profile',default='mac');p.add_argument('--folder');p.add_argument('--imgsz',type=int,choices=[320,640],default=320);p.add_argument('--export-ncnn',action='store_true');return p
def main(argv=None):
 a=parser().parse_args(argv);cfg=load(a.profile);ycfg=dict(get(cfg,'perception.yolo',{}),imgsz=a.imgsz)
 from scoutbot.perception.yolo import YoloDetector
 d=YoloDetector(ycfg)
 if a.export_ncnn: d.model.export(format='ncnn');return
 files=sorted(Path(a.folder).glob('*')) if a.folder else [] ;cap=None if files else cv2.VideoCapture(get(cfg,'hw.camera_index',0));times=[]
 try:
  for i in range(50):
   frame=cv2.imread(str(files[i%len(files)])) if files else cap.read()[1]
   if frame is None: raise SystemExit('no frame available')
   t=time.monotonic();d.detect(frame,t);times.append(time.monotonic()-t)
 finally:
  if cap:cap.release()
 fps=len(times)/sum(times);print(f'YOLO: {fps:.2f} FPS ({a.imgsz}px)')
 if fps<3: print('use perception.yolo.where=remote')
if __name__=='__main__':main()
