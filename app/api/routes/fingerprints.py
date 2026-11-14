from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_owner,current_device
from app.models.entities import Visitor,Device,FingerprintEnrollment
from app.schemas.resources import FingerprintStart,FingerprintResult
from app.services.common import tenant_get,add_command
router=APIRouter(tags=['Fingerprint Enrollment'])
@router.post('/fingerprints/enroll')
def enroll(data:FingerprintStart,owner=Depends(current_owner),db:Session=Depends(get_db)):
    device=tenant_get(db,Device,data.device_id,owner.tenant_id)
    visitor=tenant_get(db,Visitor,data.visitor_id,owner.tenant_id)
    existing=db.query(FingerprintEnrollment).filter_by(device_id=device.id,template_id=data.template_id).first()
    if existing: raise HTTPException(409,'Template ID is already assigned on this device')
    if db.query(FingerprintEnrollment).filter_by(visitor_id=visitor.id,tenant_id=owner.tenant_id).first(): raise HTTPException(409,'Visitor already has a fingerprint mapping; delete it before replacement')
    mapping=FingerprintEnrollment(tenant_id=owner.tenant_id,visitor_id=visitor.id,device_id=device.id,template_id=data.template_id,status='pending')
    db.add(mapping)
    cmd=add_command(db,owner.tenant_id,device.id,'fingerprint_enroll',{'visitor_id':str(visitor.id),'template_id':data.template_id})
    db.commit(); return {'command_id':str(cmd.id),'status':'queued','message':'Device enrollment command queued. Complete visitor mapping when enrollment succeeds.'}
@router.post('/device/fingerprints/result')
def enrollment_result(data:FingerprintResult,device=Depends(current_device),db:Session=Depends(get_db)):
    visitor=tenant_get(db,Visitor,data.visitor_id,device.tenant_id)
    rec=db.query(FingerprintEnrollment).filter_by(tenant_id=device.tenant_id,visitor_id=visitor.id,device_id=device.id,template_id=data.template_id).first()
    if not rec: raise HTTPException(404,'Pending fingerprint enrollment was not found')
    rec.status='active' if data.success else 'failed'
    db.commit()
    return {'status':rec.status,'visitor_id':str(visitor.id)}
@router.delete('/fingerprints/{visitor_id}')
def delete_fingerprint(visitor_id:str,owner=Depends(current_owner),db:Session=Depends(get_db)):
    rec=db.query(FingerprintEnrollment).filter_by(visitor_id=visitor_id,tenant_id=owner.tenant_id).first()
    if not rec: raise HTTPException(404,'Fingerprint mapping not found')
    add_command(db,owner.tenant_id,rec.device_id,'fingerprint_delete',{'template_id':rec.template_id}); db.delete(rec); db.commit(); return {'message':'Fingerprint deletion queued'}
@router.get('/fingerprints')
def list_fingerprints(owner=Depends(current_owner),db:Session=Depends(get_db)):
    rows=db.query(FingerprintEnrollment).filter_by(tenant_id=owner.tenant_id).all(); return [{'id':str(x.id),'visitor_id':str(x.visitor_id),'device_id':str(x.device_id),'template_id':x.template_id,'status':x.status} for x in rows]
