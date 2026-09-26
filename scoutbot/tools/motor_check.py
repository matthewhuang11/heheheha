import argparse,time
from robot.types import Action
from scoutbot.settings import load
from scoutbot.hw.base import build

def parser():
 p=argparse.ArgumentParser(description='WHEELS OFF GROUND: step each motor action.');p.add_argument('--profile',default='pi');return p
def main(argv=None):
 cfg=load(parser().parse_args(argv).profile)
 if input('WHEELS OFF THE GROUND. Type yes to continue: ').strip().lower()!='yes': return print('Cancelled.')
 camera,sensors,motors=build(cfg,None)
 try:
  for action in Action:
   print(action.value);motors.apply(action);time.sleep(1);motors.stop();time.sleep(1)
 finally:
  motors.stop();sensors.close();camera.close();motors.close()
if __name__=='__main__':main()
