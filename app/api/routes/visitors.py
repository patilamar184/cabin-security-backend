from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_owner
from app.models.entities import Visitor,VisitorRole,VisitorCredential
from app.schemas.resources import VisitorCreate,VisitorUpdate
from app.core.security import generate_pin,hash_password
from app.services.common import tenant_get
router=APIRouter(prefix='/visitors',tags=['Visitor Management'])
@router.post('',status_code=201)
def create(data:VisitorCreate,owner=Depends(current_owner),db:Session=Depends(get_db)):
    role=tenant_get(db,VisitorRole,data.role_id,owner.tenant_id)
    if not role.is_active: raise HTTPException(400,'Visitor role is inactive')
    visitor=Visitor(tenant_id=owner.tenant_id,role_id=role.id,name=data.name,phone=data.phone,department=data.department); db.add(visitor); db.flush()
    pin=generate_pin(); db.add(VisitorCredential(tenant_id=owner.tenant_id,visitor_id=visitor.id,pin_hash=hash_password(pin))); db.commit(); db.refresh(visitor)
    return {'visitor':{'id':str(visitor.id),'name':visitor.name,'phone':visitor.phone,'department':visitor.department,'role_id':str(visitor.role_id),'is_active':visitor.is_active,'created_at':visitor.created_at},'pin':pin,'warning':'Store this PIN now. It will not be returned again.'}
@router.get('')
def list_visitors(owner=Depends(current_owner),db:Session=Depends(get_db),q:str|None=None,active:bool|None=None,skip:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=200)):
    query=db.query(Visitor).filter(Visitor.tenant_id==owner.tenant_id)
    if q: query=query.filter(Visitor.name.ilike(f'%{q}%'))
    if active is not None: query=query.filter(Visitor.is_active==active)
    rows=query.order_by(Visitor.created_at.desc()).offset(skip).limit(limit).all()
    return [{'id':str(v.id),'name':v.name,'phone':v.phone,'department':v.department,'role_id':str(v.role_id),'is_active':v.is_active,'created_at':v.created_at} for v in rows]
@router.get('/{visitor_id}')
def get_visitor(visitor_id:str,owner=Depends(current_owner),db:Session=Depends(get_db)):
    v=tenant_get(db,Visitor,visitor_id,owner.tenant_id); return {'id':str(v.id),'name':v.name,'phone':v.phone,'department':v.department,'role_id':str(v.role_id),'is_active':v.is_active}
@router.patch('/{visitor_id}')
def update(visitor_id:str,data:VisitorUpdate,owner=Depends(current_owner),db:Session=Depends(get_db)):
    v=tenant_get(db,Visitor,visitor_id,owner.tenant_id)
    for key,value in data.model_dump(exclude_unset=True).items():
        if key=='role_id': tenant_get(db,VisitorRole,value,owner.tenant_id)
        setattr(v,key,value)
    db.commit(); db.refresh(v); return {'message':'Visitor updated','id':str(v.id)}
@router.post('/{visitor_id}/reset-pin')
def reset_pin(visitor_id:str,owner=Depends(current_owner),db:Session=Depends(get_db)):
    v=tenant_get(db,Visitor,visitor_id,owner.tenant_id); cred=db.query(VisitorCredential).filter_by(visitor_id=v.id,tenant_id=owner.tenant_id).first(); pin=generate_pin()
    if not cred: cred=VisitorCredential(tenant_id=owner.tenant_id,visitor_id=v.id,pin_hash=hash_password(pin)); db.add(cred)
    else: cred.pin_hash=hash_password(pin)
    db.commit(); return {'visitor_id':str(v.id),'pin':pin,'warning':'Store this PIN now. It will not be returned again.'}
