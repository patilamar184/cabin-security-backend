from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_owner, get_tenant_db
from app.db.control import get_control_db
from app.models.control import Owner
from app.models.tenant import Fingerprint, FingerprintEnrollment, Visitor
from app.schemas.visitor import FingerprintEnrollmentOut, VisitorCreate, VisitorOut, VisitorUpdate
from app.services.access_control import get_owner_device, get_owner_device_id
from app.services.device_commands import enqueue_command

router = APIRouter(prefix="/visitors", tags=["Visitors"])


def visitor_to_dict(db: Session, visitor: Visitor) -> dict:
    count = db.scalar(
        select(func.count(Fingerprint.id)).where(
            Fingerprint.visitor_id == visitor.id,
            Fingerprint.status == "active",
        )
    ) or 0
    return {
        "id": visitor.id,
        "name": visitor.name,
        "phone": visitor.phone,
        "department": visitor.department,
        "role": visitor.role,
        "fingerprint_count": int(count),
        "registered_at": visitor.created_at,
    }


@router.get("")
def list_visitors(
    search: str | None = None,
    department: str | None = None,
    role: str | None = None,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_tenant_db),
):
    query = select(Visitor)
    count_query = select(func.count(Visitor.id))
    filters = []
    if search:
        term = f"%{search.strip()}%"
        filters.append(or_(Visitor.name.ilike(term), Visitor.phone.ilike(term), Visitor.department.ilike(term), cast(Visitor.id, String).ilike(term)))
    if department:
        filters.append(Visitor.department == department)
    if role:
        filters.append(Visitor.role == role)
    if filters:
        query = query.where(*filters)
        count_query = count_query.where(*filters)

    total = db.scalar(count_query) or 0
    visitors = list(db.scalars(query.order_by(Visitor.created_at.desc(), Visitor.id.desc()).offset((page - 1) * pageSize).limit(pageSize)))
    return {"items": [visitor_to_dict(db, visitor) for visitor in visitors], "total": int(total)}


@router.post("", response_model=VisitorOut, status_code=status.HTTP_201_CREATED)
def create_visitor(payload: VisitorCreate, db: Session = Depends(get_tenant_db)):
    phone = payload.phone.strip()
    existing = db.scalar(select(Visitor).where(Visitor.phone == phone))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A visitor with this phone number is already registered.")

    visitor = Visitor(
        name=payload.name.strip(),
        phone=phone,
        department=payload.department.strip(),
        role=payload.role.strip(),
    )
    db.add(visitor)
    db.commit()
    db.refresh(visitor)
    return visitor_to_dict(db, visitor)


@router.get("/{visitor_id}", response_model=VisitorOut)
def get_visitor(visitor_id: int, db: Session = Depends(get_tenant_db)):
    visitor = db.get(Visitor, visitor_id)
    if visitor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visitor not found.")
    return visitor_to_dict(db, visitor)


@router.put("/{visitor_id}", response_model=VisitorOut)
def update_visitor(visitor_id: int, payload: VisitorUpdate, db: Session = Depends(get_tenant_db)):
    visitor = db.get(Visitor, visitor_id)
    if visitor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visitor not found.")

    changes = payload.model_dump(exclude_unset=True)
    if "phone" in changes and changes["phone"]:
        changes["phone"] = changes["phone"].strip()
        duplicate = db.scalar(select(Visitor).where(Visitor.phone == changes["phone"], Visitor.id != visitor_id))
        if duplicate:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Another visitor already uses this phone number.")

    for field, value in changes.items():
        if value is not None:
            setattr(visitor, field, value.strip() if isinstance(value, str) else value)
    visitor.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(visitor)
    return visitor_to_dict(db, visitor)


@router.delete("/{visitor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_visitor(
    visitor_id: int,
    owner: Owner = Depends(get_current_owner),
    db: Session = Depends(get_tenant_db),
    control_db: Session = Depends(get_control_db),
):
    visitor = db.get(Visitor, visitor_id)
    if visitor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visitor not found.")

    pending_enrollment = db.scalar(
        select(FingerprintEnrollment).where(
            FingerprintEnrollment.visitor_id == visitor_id,
            FingerprintEnrollment.status == "pending",
        )
    )
    if pending_enrollment:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot delete this visitor while fingerprint enrollment is still pending.")

    fingerprints = list(db.scalars(select(Fingerprint).where(Fingerprint.visitor_id == visitor_id, Fingerprint.status == "active")))
    if fingerprints:
        device_id = get_owner_device_id(control_db, owner.id)
        for fingerprint in fingerprints:
            enqueue_command(
                db,
                device_id,
                "DELETE_FINGERPRINT",
                {"sensor_slot": fingerprint.sensor_slot, "visitor_id": visitor_id},
            )

    db.delete(visitor)
    db.commit()
    return None


@router.post("/{visitor_id}/fingerprints", response_model=FingerprintEnrollmentOut, status_code=status.HTTP_202_ACCEPTED)
def start_fingerprint_enrollment(
    visitor_id: int,
    owner: Owner = Depends(get_current_owner),
    db: Session = Depends(get_tenant_db),
    control_db: Session = Depends(get_control_db),
):
    visitor = db.get(Visitor, visitor_id)
    if visitor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visitor not found.")

    device = get_owner_device(control_db, owner.id)
    now = datetime.now(timezone.utc)
    last_seen = device.last_seen_at
    if last_seen is not None and last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    if last_seen is None or (now - last_seen).total_seconds() > 45:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ESP32 device is offline. Bring the device online before starting fingerprint enrollment.")
    device_id = device.device_id
    if db.scalar(select(FingerprintEnrollment).where(
        FingerprintEnrollment.visitor_id == visitor_id,
        FingerprintEnrollment.status == "pending",
    )):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A fingerprint enrollment is already pending for this visitor.")

    enrollment_id = str(uuid4())
    command = enqueue_command(
        db,
        device_id,
        "ENROLL_FINGERPRINT",
        {
            "enrollment_id": enrollment_id,
            "visitor_id": visitor_id,
            "visitor_name": visitor.name,
            "sensor": "R307",
            "prompt": "Place finger on the fingerprint sensor",
        },
    )
    command_id = command.id
    db.add(
        FingerprintEnrollment(
            id=enrollment_id,
            visitor_id=visitor_id,
            device_id=device_id,
            command_id=command_id,
            status="pending",
        )
    )
    db.commit()
    return FingerprintEnrollmentOut(
        enrollment_id=enrollment_id,
        status="pending",
        message="Enrollment command queued. Waiting for the ESP32 and R307 fingerprint sensor.",
    )

