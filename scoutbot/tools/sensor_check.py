import argparse,statistics
from scoutbot.settings import load
from scoutbot.hw.base import build

def parser():
 p=argparse.ArgumentParser(description='Read 50 distance samples and print calibration statistics.');p.add_argument('--profile',default='pi');return p
def main(argv=None):
 cfg=load(parser().parse_args(argv).profile);camera,sensors,motors=build(cfg,None);rows=[]
 try:
  for _ in range(50): rows.append(sensors.read())
 finally:
  sensors.close();camera.close();motors.stop();motors.close()
 for i,name in enumerate(('left','center','right')):
  vals=[(r.left,r.center,r.right)[i] for r in rows if r.valid[i] and (r.left,r.center,r.right)[i] is not None]
  print(f'{name}: min={min(vals):.1f} median={statistics.median(vals):.1f} max={max(vals):.1f} no-echo={(1-len(vals)/len(rows))*100:.1f}%')
if __name__=='__main__':main()
