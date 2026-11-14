from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_owner
from app.models.entities import Device
from app.services.common import tenant_get, add_command

router = APIRouter(prefix='/door', tags=['Door Control'])

@router.post('/unlock')
def unlock(device_id: str, duration_minutes: int = 5, owner=Depends(current_owner), db: Session=Depends(get_db)):
    if duration_minutes not in (5, 10, 30):
        raise HTTPException(422, 'Duration must be 5, 10, or 30 minutes')
    device = tenant_get(db, Device, device_id, owner.tenant_id)
    if not device.is_active:
        raise HTTPException(409, 'Device is inactive')
    command = add_command(db, owner.tenant_id, device.id, 'unlock_door', {'duration_minutes': duration_minutes, 'source': 'owner_manual'})
    db.commit()
    return {'message': 'Door unlock command queued', 'command_id': str(command.id), 'duration_minutes': duration_minutes}
