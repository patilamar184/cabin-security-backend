from collections.abc import Generator
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token, verify_device_api_key
from app.db.control import get_control_db
from app.db.tenant import get_tenant_session_factory
from app.models.control import DeviceCredential, Owner

_bearer = HTTPBearer(auto_error=False)


def get_current_owner(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    control_db: Session = Depends(get_control_db),
) -> Owner:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    owner_id = decode_access_token(credentials.credentials)
    if not owner_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token.")

    owner = control_db.get(Owner, owner_id)
    if owner is None or not owner.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Owner account is inactive or unavailable.")
    return owner


def get_tenant_db(owner: Owner = Depends(get_current_owner)) -> Generator[Session, None, None]:
    factory = get_tenant_session_factory(owner.tenant_database, owner.id)
    db = factory()
    try:
        yield db
    finally:
        db.close()


@dataclass
class DeviceContext:
    credential: DeviceCredential
    owner: Owner
    db: Session
    control_db: Session


def get_device_context(
    x_device_id: str | None = Header(default=None, alias="X-Device-ID"),
    x_device_key: str | None = Header(default=None, alias="X-Device-Key"),
    control_db: Session = Depends(get_control_db),
) -> Generator[DeviceContext, None, None]:
    if not x_device_id or not x_device_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Device credentials are required.")

    credential = control_db.scalar(
        select(DeviceCredential).where(
            DeviceCredential.device_id == x_device_id,
            DeviceCredential.is_active.is_(True),
        )
    )
    if credential is None or not verify_device_api_key(x_device_key, credential.api_key_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device credentials.")

    owner = control_db.get(Owner, credential.owner_id)
    if owner is None or not owner.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The cabin owner account is inactive.")

    factory = get_tenant_session_factory(owner.tenant_database, owner.id)
    tenant_db = factory()
    try:
        yield DeviceContext(credential=credential, owner=owner, db=tenant_db, control_db=control_db)
    finally:
        tenant_db.close()
