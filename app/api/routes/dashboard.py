from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.api.deps import current_owner
from app.models.entities import Visitor,AccessRequest,EntryLog,Device
router=APIRouter(prefix='/dashboard',tags=['Dashboard Statistics'])
@router.get('/stats')
def stats(owner=Depends(current_owner),db:Session=Depends(get_db)):
    tenant=owner.tenant_id
    count=lambda model,*filters: db.query(func.count(model.id)).filter(model.tenant_id==tenant,*filters).scalar() or 0
    return {'visitors':{'total':count(Visitor),'active':count(Visitor,Visitor.is_active.is_(True)),'inactive':count(Visitor,Visitor.is_active.is_(False))},'access_requests':{'pending':count(AccessRequest,AccessRequest.status=='pending'),'approved':count(AccessRequest,AccessRequest.status=='approved'),'denied':count(AccessRequest,AccessRequest.status=='denied')},'entry_attempts':count(EntryLog),'devices':{'online':count(Device,Device.status=='online'),'offline':count(Device,Device.status=='offline')}}
