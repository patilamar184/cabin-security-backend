from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_owner
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.db.control import get_control_db
from app.models.control import Owner
from app.schemas.auth import (
    LoginRequest,
    OwnerOut,
    OwnerRegisterOut,
    OwnerRegisterRequest,
    TokenOut,
)
from app.services.owner_registration import register_owner

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenOut)
def login(payload: LoginRequest, db: Session = Depends(get_control_db)):
    username = payload.username.strip().lower()
    owner = db.scalar(select(Owner).where(Owner.username == username))
    if owner is None or not owner.is_active or not verify_password(payload.password, owner.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password.")

    return TokenOut(access_token=create_access_token(owner.id))


@router.get("/me", response_model=OwnerOut)
def get_me(owner: Owner = Depends(get_current_owner)):
    return owner


@router.post("/register", response_model=OwnerRegisterOut, status_code=status.HTTP_201_CREATED)
def register(payload: OwnerRegisterRequest, db: Session = Depends(get_control_db)):
    if not settings.allow_owner_registration:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner self-registration is disabled.")

    owner, device_id, device_api_key = register_owner(
        db,
        full_name=payload.full_name,
        username=payload.username,
        email=str(payload.email),
        password=payload.password,
        phone=payload.phone,
        department=payload.department,
    )
    return OwnerRegisterOut(
        owner=OwnerOut.model_validate(owner),
        device_id=device_id,
        device_api_key=device_api_key,
        message="Owner account and isolated tenant database created. Store the device API key securely; it is shown only once.",
    )
