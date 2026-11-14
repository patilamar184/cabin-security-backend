from fastapi import Depends, Header, HTTPException
from fastapi.security import OAuth2PasswordBearer
from uuid import UUID
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import decode_token, hash_secret
from app.models.entities import CabinOwner, PlatformAdmin, Device, Tenant

oauth2=OAuth2PasswordBearer(tokenUrl="/api/auth/login")
def current_claims(token: str=Depends(oauth2)):
    try:
        data=decode_token(token)
        if data.get('type')!='access': raise ValueError()
        return data
    except ValueError: raise HTTPException(401,"Invalid or expired access token",headers={"WWW-Authenticate":"Bearer"})

def current_owner(claims=Depends(current_claims), db: Session=Depends(get_db)):
    if claims.get('role')!='owner': raise HTTPException(403,"Cabin owner access required")
    
    try: owner_id=UUID(claims.get('sub'))
    except (ValueError, TypeError): raise HTTPException(401,"Invalid token subject")
    owner=db.get(CabinOwner,owner_id)
    if not owner or not owner.is_active: raise HTTPException(403,"Owner account is inactive")
    tenant=db.get(Tenant,owner.tenant_id)
    if not tenant or tenant.status!='active': raise HTTPException(403,"Tenant is inactive")
    return owner

def current_admin(claims=Depends(current_claims), db: Session=Depends(get_db)):
    if claims.get('role')!='admin': raise HTTPException(403,"Platform admin access required")
    
    try: admin_id=UUID(claims.get('sub'))
    except (ValueError, TypeError): raise HTTPException(401,"Invalid token subject")
    admin=db.get(PlatformAdmin,admin_id)
    if not admin or not admin.is_active: raise HTTPException(403,"Admin account inactive")
    return admin

def current_device(x_device_key: str=Header(...), db: Session=Depends(get_db)):
    device=db.query(Device).filter(Device.api_key_hash==hash_secret(x_device_key),Device.is_active.is_(True)).first()
    if not device: raise HTTPException(401,"Invalid device credentials")
    tenant=db.get(Tenant,device.tenant_id)
    if not tenant or tenant.status!='active': raise HTTPException(403,"Device tenant is inactive")
    return device
