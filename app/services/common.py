from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.entities import DeviceCommand
from app.core.config import settings

def utcnow(): return datetime.now(timezone.utc)
def add_command(db:Session, tenant_id, device_id, command_type:str, payload:dict, ttl:int|None=None):
    cmd=DeviceCommand(tenant_id=tenant_id,device_id=device_id,command_type=command_type,payload=payload,status='pending',expires_at=utcnow()+timedelta(seconds=ttl or settings.command_default_ttl_seconds))
    db.add(cmd); db.flush(); return cmd
def tenant_get(db, model, item_id, tenant_id):
    try: parsed_id=UUID(str(item_id))
    except (ValueError, TypeError): raise HTTPException(404,"Resource not found")
    item=db.query(model).filter(model.id==parsed_id,model.tenant_id==tenant_id).first()
    if not item: raise HTTPException(404,"Resource not found")
    return item
