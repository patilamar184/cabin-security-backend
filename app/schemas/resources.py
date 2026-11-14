from pydantic import BaseModel, Field
from app.schemas.common import ORMModel
class RoleCreate(BaseModel): name:str=Field(min_length=2,max_length=80)
class RoleOut(ORMModel): id:object; name:str; is_active:bool
class VisitorCreate(BaseModel): name:str=Field(min_length=2,max_length=160); phone:str=Field(min_length=7,max_length=30); department:str=Field(min_length=2,max_length=120); role_id:str
class VisitorUpdate(BaseModel): name:str|None=None; phone:str|None=None; department:str|None=None; role_id:str|None=None; is_active:bool|None=None
class VisitorOut(ORMModel): id:object; name:str; phone:str; department:str; role_id:object; is_active:bool; created_at:object
class DeviceCreate(BaseModel): name:str=Field(min_length=2,max_length=120)
class DeviceOut(ORMModel): id:object; name:str; status:str; last_heartbeat_at:object|None=None; firmware_version:str|None=None; is_active:bool
class DeviceConfig(BaseModel): firmware_version:str|None=None
class FingerprintStart(BaseModel): device_id:str; visitor_id:str; template_id:int=Field(ge=1,le=200)
class FingerprintResult(BaseModel): visitor_id:str; template_id:int=Field(ge=1,le=200); success:bool
class AccessDecision(BaseModel): duration_minutes:int|None=Field(default=None, ge=1, le=60)
class DisplayDuration(BaseModel): duration_minutes:int=Field(ge=1,le=180)
class AuthEvent(BaseModel): method:str; pin:str|None=None; template_id:int|None=None
class CommandAck(BaseModel): status:str; result:dict|None=None
