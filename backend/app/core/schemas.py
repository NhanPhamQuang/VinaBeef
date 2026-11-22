from datetime import datetime
from pydantic import BaseModel,Field,ConfigDict
from typing import Literal

class Schema(BaseModel):
    model_config=ConfigDict(from_attributes=True)

class LoginIn(Schema):
    email:str
    password:str

class CattleIn(Schema):
    animal_code:str=Field(min_length=2,max_length=80)
    barn_id:str
    breed:str="Unknown"
    weight_kg:float|None=None
    epc:str|None=None

class CattlePatch(Schema):
    breed:str|None=None
    weight_kg:float|None=None
    status:str|None=None

class TagIn(Schema):
    epc:str=Field(min_length=3,max_length=100)

class FarmIn(Schema):
    name:str=Field(min_length=2,max_length=140)
    location:str=""

class BarnIn(Schema):
    farm_id:str
    code:str
    capacity:int=Field(default=500,gt=0)

class ReaderIn(Schema):
    code:str
    gate_id:str
    model:str="RFID Simulator"

class GateIn(Schema):
    barn_id:str
    name:str
    direction_mode:Literal["IN","OUT","BIDIRECTIONAL"]="BIDIRECTIONAL"

class ReadIn(Schema):
    event_id:str=Field(min_length=4)
    reader_id:str
    tag_epc:str
    direction:Literal["IN","OUT"]
    observed_at:datetime|None=None

class SyncIn(Schema):
    gateway_id:str
    events:list[ReadIn]=Field(max_length=500)

class HealthIn(Schema):
    cattle_id:str
    type:Literal["VACCINATION","ASSESSMENT","TREATMENT","OUTBREAK"]
    description:str=Field(min_length=2)
    vaccine:str|None=None
    status:str|None=None
    event_at:datetime|None=None
    source_id:str|None=None

class TransferIn(Schema):
    cattle_id:str
    target_barn_id:str
    reason:str=""

class UserIn(Schema):
    email:str
    full_name:str
    password:str=Field(min_length=8)
    role:Literal["SYSTEM_ADMIN","FARM_MANAGER","BARN_SUPERVISOR","EXECUTIVE"]
    farm_id:str|None=None
    barn_id:str|None=None

class UserPatch(Schema):
    role:Literal["SYSTEM_ADMIN","FARM_MANAGER","BARN_SUPERVISOR","EXECUTIVE"]|None=None
    farm_id:str|None=None
    barn_id:str|None=None
    active:bool|None=None
