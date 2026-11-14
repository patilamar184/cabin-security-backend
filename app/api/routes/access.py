from datetime import timedelta
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_owner
from app.models.entities import AccessRequest,Device,EntryLog,Visitor
from app.schemas.resources import AccessDecision,DisplayDuration
from app.services.common import tenant_get,add_command,utcnow
router=APIRouter(prefix='/access-requests',tags=['Access Requests'])
@router.get('')
def list_requests(owner=Depends(current_owner),db:Session=Depends(get_db),status:str|None=None):
    expired=db.query(AccessRequest).filter(AccessRequest.tenant_id==owner.tenant_id,AccessRequest.status=='pending',AccessRequest.expires_at<=utcnow()).all()
    for item in expired: item.status='expired'
    if expired: db.commit()
    q=db.query(AccessRequest).filter_by(tenant_id=owner.tenant_id)
    if status: q=q.filter_by(status=status.lower())
    return [{'id':str(a.id),'visitor_id':str(a.visitor_id) if a.visitor_id else None,'device_id':str(a.device_id) if a.device_id else None,'authentication_method':a.authentication_method,'status':a.status,'created_at':a.created_at,'expires_at':a.expires_at} for a in q.order_by(AccessRequest.created_at.desc()).limit(200).all()]
@router.post('/{request_id}/approve')
def approve(request_id:str,data:AccessDecision,owner=Depends(current_owner),db:Session=Depends(get_db)):
    a=tenant_get(db,AccessRequest,request_id,owner.tenant_id)
    if a.status!='pending' or a.expires_at<=utcnow(): raise HTTPException(409,'Request is no longer pending')
    if not a.device_id: raise HTTPException(409,'Request has no associated device')
    duration=data.duration_minutes or 5
    if duration not in (5, 10, 30): raise HTTPException(422,'Duration must be 5, 10, or 30 minutes')
    a.status='approved'; a.decided_at=utcnow(); add_command(db,owner.tenant_id,a.device_id,'unlock_door',{'access_request_id':str(a.id),'duration_minutes':duration})
    log=db.query(EntryLog).filter_by(tenant_id=owner.tenant_id,visitor_id=a.visitor_id,device_id=a.device_id).order_by(EntryLog.created_at.desc()).first()
    if log: log.access_decision='approved'
    db.commit(); return {'message':'Access approved','duration_minutes':duration}
@router.post('/{request_id}/deny')
def deny(request_id:str,owner=Depends(current_owner),db:Session=Depends(get_db)):
    a=tenant_get(db,AccessRequest,request_id,owner.tenant_id)
    if a.status!='pending': raise HTTPException(409,'Request is no longer pending')
    a.status='denied'; a.decided_at=utcnow()
    if a.device_id: add_command(db,owner.tenant_id,a.device_id,'deny_access',{'access_request_id':str(a.id)})
    log=db.query(EntryLog).filter_by(tenant_id=owner.tenant_id,visitor_id=a.visitor_id,device_id=a.device_id).order_by(EntryLog.created_at.desc()).first()
    if log: log.access_decision='denied'
    db.commit(); return {'message':'Access denied'}
@router.post('/display-duration')
def display_duration(data:DisplayDuration,device_id:str,owner=Depends(current_owner),db:Session=Depends(get_db)):
    device=tenant_get(db,Device,device_id,owner.tenant_id); cmd=add_command(db,owner.tenant_id,device.id,'display_return_after',{'duration_minutes':data.duration_minutes,'message':f'Please come back after {data.duration_minutes} minutes'})
    db.commit(); return {'message':'Display command queued','command_id':str(cmd.id)}
