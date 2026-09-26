from __future__ import annotations
from enum import Enum
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class Action(str, Enum):
    STOP="STOP"; FORWARD="FORWARD"; FORWARD_SLOW="FORWARD_SLOW"; TURN_LEFT="TURN_LEFT"; TURN_RIGHT="TURN_RIGHT"; BACK_UP="BACK_UP"

class Hazard(BaseModel):
    model_config=ConfigDict(extra="forbid")
    type: Literal["fire","smoke","water","wire","glass","drop_off","unstable_debris","other"]
    where: Literal["left","center","right"]
    distance: Literal["near","mid","far"]
class People(BaseModel):
    model_config=ConfigDict(extra="forbid")
    visible: bool
    where: Literal["left","center","right","none"]
    distance: Literal["near","mid","far","none"]
    @model_validator(mode="after")
    def consistent(self):
        if self.visible and (self.where=="none" or self.distance=="none"): raise ValueError("visible people need location and distance")
        if not self.visible and (self.where,self.distance)!=("none","none"): raise ValueError("invisible people must be none")
        return self
class SceneReport(BaseModel):
    model_config=ConfigDict(extra="forbid")
    path_ahead: Literal["clear","partially_blocked","blocked","unknown"]
    best_direction: Literal["left","center","right","none"]
    terrain: Literal["flat","rubble","uneven","stairs_or_drop","water","unknown"]
    hazards: list[Hazard]=Field(max_length=12)
    people: People
    objects: list[str]=Field(max_length=20)
    confidence: float=Field(ge=0,le=1)
    notes: str=Field(max_length=240)
class Sensors(BaseModel):
    left: float|None=200; center: float|None=200; right: float|None=200
    updated_at: float=0
    valid: tuple[bool,bool,bool]=(True,True,True)
    vlm_online: bool=True
    def fresh(self, now: float, max_age: float=0.5)->bool: return now-self.updated_at<=max_age
    def values(self): return self.left if self.valid[0] else None, self.center if self.valid[1] else None, self.right if self.valid[2] else None
