from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_device_api_key, hash_device_api_key, hash_password
from app.db.control import ControlSessionLocal
from app.models.control import DeviceCredential, Owner
from app.services.tenant_provisioning import make_tenant_database_name, provision_tenant_database


def register_owner(
    db: Session,
    *,
    full_name: str,
    username: str,
    email: str,
    password: str,
    phone: str,
    department: str,
) -> tuple[Owner, str, str]:
    username = username.strip().lower()
    email = email.strip().lower()

    existing = db.scalar(select(Owner).where((Owner.username == username) | (Owner.email == email)))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email is already registered.")

    owner_id = str(uuid4())
    database_name = make_tenant_database_name(owner_id)
    device_id = f"esp32-{uuid4().hex[:12]}"
    device_api_key = create_device_api_key()

    provision_tenant_database(database_name, owner_id)
    try:
        owner = Owner(
            id=owner_id,
            full_name=full_name.strip(),
            username=username,
            email=email,
            phone=phone.strip(),
            department=department.strip(),
            password_hash=hash_password(password),
            tenant_database=database_name,
            role="Cabin Owner",
            is_active=True,
        )
        device = DeviceCredential(
            owner_id=owner_id,
            device_id=device_id,
            api_key_hash=hash_device_api_key(device_api_key),
            is_active=True,
        )
        db.add(owner)
        db.add(device)
        db.commit()
        db.refresh(owner)
        return owner, device_id, device_api_key
    except Exception:
        db.rollback()
        from app.services.tenant_provisioning import drop_tenant_database

        drop_tenant_database(database_name, owner_id)
        raise
