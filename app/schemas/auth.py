from pydantic import BaseModel, EmailStr, Field
from app.schemas.common import ORMModel
class OwnerRegister(BaseModel): full_name:str=Field(min_length=2,max_length=160); email:EmailStr; password:str=Field(min_length=8,max_length=128); phone:str=Field(min_length=7,max_length=30); cabin_name:str=Field(min_length=2,max_length=160); cabin_location:str=Field(min_length=2,max_length=255)
class Login(BaseModel): email:EmailStr; password:str
class TokenPair(BaseModel): access_token:str; refresh_token:str; token_type:str='bearer'
class RefreshInput(BaseModel): refresh_token:str
class OwnerOut(ORMModel): id:str|None=None; full_name:str; email:str; phone:str; tenant_id:str; is_active:bool
