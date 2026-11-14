import hashlib
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.entities import Tenant,CabinOwner,RefreshToken,VisitorRole
from app.schemas.auth import OwnerRegister,Login,TokenPair,RefreshInput
from app.core.security import hash_password,verify_password,create_access_token,create_refresh_token,decode_token
from app.api.deps import current_owner
router=APIRouter(prefix='/auth',tags=['Authentication'])
def pair(owner,db):
    access=create_access_token(str(owner.id),'owner',str(owner.tenant_id)); refresh,expires=create_refresh_token(str(owner.id))
    db.add(RefreshToken(owner_id=owner.id,token_hash=hashlib.sha256(refresh.encode()).hexdigest(),expires_at=expires)); db.commit()
    return TokenPair(access_token=access,refresh_token=refresh)
@router.post('/register',response_model=TokenPair,status_code=201)
def register(data:OwnerRegister,db:Session=Depends(get_db)):
    email=data.email.lower()
    if db.query(CabinOwner).filter(CabinOwner.email==email).first(): raise HTTPException(409,'Email is already registered')
    tenant=Tenant(name=data.cabin_name,location=data.cabin_location,status='active'); db.add(tenant); db.flush()
    owner=CabinOwner(tenant_id=tenant.id,full_name=data.full_name,email=email,password_hash=hash_password(data.password),phone=data.phone,is_active=True); db.add(owner); db.flush()
    for name in ['Student','Teacher','Employee','Guest']: db.add(VisitorRole(tenant_id=tenant.id,name=name))
    db.commit(); db.refresh(owner); return pair(owner,db)
@router.post('/login',response_model=TokenPair)
def login(data:Login,db:Session=Depends(get_db)):
    owner=db.query(CabinOwner).filter(CabinOwner.email==data.email.lower()).first()
    if not owner or not verify_password(data.password,owner.password_hash): raise HTTPException(401,'Incorrect email or password')
    if not owner.is_active: raise HTTPException(403,'Owner account is inactive')
    return pair(owner,db)
@router.post('/refresh',response_model=TokenPair)
def refresh(data:RefreshInput,db:Session=Depends(get_db)):
    try: claims=decode_token(data.refresh_token)
    except ValueError: raise HTTPException(401,'Invalid refresh token')
    if claims.get('type')!='refresh': raise HTTPException(401,'Invalid refresh token')
    digest=hashlib.sha256(data.refresh_token.encode()).hexdigest(); record=db.query(RefreshToken).filter(RefreshToken.token_hash==digest,RefreshToken.revoked_at.is_(None),RefreshToken.expires_at>datetime.now(timezone.utc)).first()
    if not record: raise HTTPException(401,'Refresh token revoked or expired')
    record.revoked_at=datetime.now(timezone.utc); owner=db.get(CabinOwner,record.owner_id)
    if not owner or not owner.is_active: raise HTTPException(403,'Owner account inactive')
    db.commit(); return pair(owner,db)
@router.post('/logout')
def logout(data:RefreshInput,owner=Depends(current_owner),db:Session=Depends(get_db)):
    digest=hashlib.sha256(data.refresh_token.encode()).hexdigest(); rec=db.query(RefreshToken).filter(RefreshToken.owner_id==owner.id,RefreshToken.token_hash==digest,RefreshToken.revoked_at.is_(None)).first()
    if rec: rec.revoked_at=datetime.now(timezone.utc); db.commit()
    return {'message':'Logged out'}
@router.get('/me')
def me(owner=Depends(current_owner)):
    return {'id':str(owner.id),'tenant_id':str(owner.tenant_id),'full_name':owner.full_name,'email':owner.email,'phone':owner.phone,'is_active':owner.is_active}
