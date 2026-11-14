from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_owner
from app.models.entities import Device
from app.schemas.resources import DeviceCreate
from app.core.security import generate_device_key,hash_secret
from app.core.config import settings
from app.services.common import utcnow
from app.services.common import tenant_get
router=APIRouter(prefix='/devices',tags=['Device Management'])
@router.post('',status_code=201)
def register(data:DeviceCreate,owner=Depends(current_owner),db:Session=Depends(get_db)):
    key=generate_device_key(); d=Device(tenant_id=owner.tenant_id,name=data.name,api_key_hash=hash_secret(key),status='offline'); db.add(d); db.commit(); db.refresh(d)
    return {'id':str(d.id),'name':d.name,'device_api_key':key,'status':d.status,'warning':'Copy this key now. It cannot be retrieved later.'}
@router.get('')
def list_devices(owner=Depends(current_owner),db:Session=Depends(get_db)):
    stale=db.query(Device).filter(Device.tenant_id==owner.tenant_id,Device.is_active.is_(True),Device.last_heartbeat_at.is_not(None),Device.last_heartbeat_at < utcnow()-__import__('datetime').timedelta(seconds=settings.device_offline_after_seconds)).all()
    for item in stale: item.status='offline'
    if stale: db.commit()
    return [{'id':str(d.id),'name':d.name,'status':d.status,'last_heartbeat_at':d.last_heartbeat_at,'firmware_version':d.firmware_version,'is_active':d.is_active} for d in db.query(Device).filter_by(tenant_id=owner.tenant_id).all()]
@router.patch('/{device_id}/status')
def status(device_id:str,active:bool,owner=Depends(current_owner),db:Session=Depends(get_db)):
    d=tenant_get(db,Device,device_id,owner.tenant_id); d.is_active=active; d.status='inactive' if not active else 'offline'; db.commit(); return {'message':'Device status updated'}
