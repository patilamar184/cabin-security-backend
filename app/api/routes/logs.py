from fastapi import APIRouter,Depends,Query
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_owner
from app.models.entities import EntryLog,Visitor
router=APIRouter(prefix='/entry-logs',tags=['Entry Logs'])
@router.get('')
def logs(owner=Depends(current_owner),db:Session=Depends(get_db),visitor_id:str|None=None,department:str|None=None,role_id:str|None=None,method:str|None=None,result:str|None=None,access_decision:str|None=None,start:datetime|None=None,end:datetime|None=None,skip:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=200)):
    q=db.query(EntryLog).filter(EntryLog.tenant_id==owner.tenant_id)
    if visitor_id:
        try: q=q.filter(EntryLog.visitor_id==UUID(visitor_id))
        except ValueError: return []
    if role_id:
        try: parsed_role=UUID(role_id)
        except ValueError: return []
        q=q.join(Visitor,EntryLog.visitor_id==Visitor.id).filter(Visitor.role_id==parsed_role,Visitor.tenant_id==owner.tenant_id)
    if method: q=q.filter(EntryLog.authentication_method==method.lower())
    if result: q=q.filter(EntryLog.authentication_result==result.lower())
    if access_decision: q=q.filter(EntryLog.access_decision==access_decision.lower())
    if start: q=q.filter(EntryLog.created_at>=start)
    if end: q=q.filter(EntryLog.created_at<=end)
    if department: q=q.join(Visitor,EntryLog.visitor_id==Visitor.id).filter(Visitor.department==department,Visitor.tenant_id==owner.tenant_id)
    rows=q.order_by(EntryLog.created_at.desc()).offset(skip).limit(limit).all()
    return [{'id':str(x.id),'visitor_id':str(x.visitor_id) if x.visitor_id else None,'device_id':str(x.device_id) if x.device_id else None,'authentication_method':x.authentication_method,'authentication_result':x.authentication_result,'access_decision':x.access_decision,'metadata':x.metadata_json,'created_at':x.created_at} for x in rows]
