from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from app.db.session import get_db
from app.api.deps import current_admin
from app.models.entities import Tenant,CabinOwner,PlatformAdmin
from app.core.security import verify_password,create_access_token
from app.schemas.auth import Login
router=APIRouter(prefix='/admin',tags=['Platform Administration'])
@router.post('/login')
def admin_login(data:Login,db:Session=Depends(get_db)):
    admin=db.query(PlatformAdmin).filter(PlatformAdmin.email==data.email.lower()).first()
    if not admin or not verify_password(data.password,admin.password_hash): raise HTTPException(401,'Incorrect credentials')
    if not admin.is_active: raise HTTPException(403,'Admin inactive')
    return {'access_token':create_access_token(str(admin.id),'admin'),'token_type':'bearer'}
@router.get('/owners')
def owners(admin=Depends(current_admin),db:Session=Depends(get_db)):
    return [{'id':str(o.id),'name':o.full_name,'email':o.email,'tenant_id':str(o.tenant_id),'is_active':o.is_active} for o in db.query(CabinOwner).all()]
@router.patch('/owners/{owner_id}/status')
def owner_status(owner_id:str,active:bool,admin=Depends(current_admin),db:Session=Depends(get_db)):
    try: parsed_id=UUID(owner_id)
    except ValueError: raise HTTPException(404,'Owner not found')
    owner=db.get(CabinOwner,parsed_id)
    if not owner: raise HTTPException(404,'Owner not found')
    owner.is_active=active; db.commit(); return {'message':'Owner status updated','is_active':active}
@router.get('/stats')
def stats(admin=Depends(current_admin),db:Session=Depends(get_db)):
    return {'owners':db.query(CabinOwner).count(),'active_owners':db.query(CabinOwner).filter(CabinOwner.is_active.is_(True)).count(),'tenants':db.query(Tenant).count()}
