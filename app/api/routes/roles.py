from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_owner
from app.models.entities import VisitorRole
from app.schemas.resources import RoleCreate
from app.services.common import tenant_get
router=APIRouter(prefix='/visitor-roles',tags=['Visitor Roles'])
@router.post('',status_code=201)
def create(data:RoleCreate,owner=Depends(current_owner),db:Session=Depends(get_db)):
    if db.query(VisitorRole).filter_by(tenant_id=owner.tenant_id,name=data.name).first(): raise HTTPException(409,'Role already exists')
    r=VisitorRole(tenant_id=owner.tenant_id,name=data.name); db.add(r); db.commit(); db.refresh(r); return {'id':str(r.id),'name':r.name,'is_active':r.is_active}
@router.get('')
def list_roles(owner=Depends(current_owner),db:Session=Depends(get_db),include_inactive:bool=False):
    q=db.query(VisitorRole).filter_by(tenant_id=owner.tenant_id)
    if not include_inactive: q=q.filter(VisitorRole.is_active.is_(True))
    return [{'id':str(r.id),'name':r.name,'is_active':r.is_active} for r in q.order_by(VisitorRole.name).all()]
@router.patch('/{role_id}')
def update(role_id:str,data:RoleCreate,owner=Depends(current_owner),db:Session=Depends(get_db)):
    r=tenant_get(db,VisitorRole,role_id,owner.tenant_id); r.name=data.name; db.commit(); return {'message':'Role updated'}
@router.delete('/{role_id}')
def deactivate(role_id:str,owner=Depends(current_owner),db:Session=Depends(get_db)):
    r=tenant_get(db,VisitorRole,role_id,owner.tenant_id); r.is_active=False; db.commit(); return {'message':'Role deactivated'}
