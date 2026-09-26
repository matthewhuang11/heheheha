import time
from robot.types import Sensors,SceneReport,Action
from robot.brain import decide

def scene(**x):
 d=dict(path_ahead="clear",best_direction="left",terrain="flat",hazards=[],people={"visible":False,"where":"none","distance":"none"},objects=[],confidence=1,notes="") ;d.update(x);return SceneReport(**d)
def run(s=Sensors(updated_at=10),sc=None):return decide(s,sc,10,10 if sc else None)[0]
def test_rules():
 assert run(Sensors(updated_at=0))==Action.STOP
 assert run(Sensors(updated_at=10,valid=(False,False,False)))==Action.STOP
 assert run(Sensors(center=20,left=30,right=30,updated_at=10))==Action.BACK_UP
 assert run(Sensors(left=10,updated_at=10))==Action.TURN_RIGHT
 assert run(Sensors(updated_at=10),scene(hazards=[{"type":"fire","where":"center","distance":"near"}]))==Action.BACK_UP
 assert run(Sensors(updated_at=10),scene(people={"visible":True,"where":"center","distance":"near"}))==Action.STOP
 assert run(Sensors(updated_at=10),scene(path_ahead="blocked",best_direction="right"))==Action.TURN_RIGHT
 assert run(Sensors(center=50,updated_at=10),scene())==Action.FORWARD_SLOW
 assert run(Sensors(updated_at=10),scene())==Action.FORWARD
def test_priority_and_offline():
 s=Sensors(center=10,left=10,right=200,updated_at=10);assert run(s,scene(path_ahead="blocked"))==Action.TURN_RIGHT
 assert run(Sensors(updated_at=10,vlm_online=False))==Action.FORWARD_SLOW
 assert decide(Sensors(updated_at=20),scene(),20,10)[0]==Action.FORWARD_SLOW
