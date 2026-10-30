from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.control import DeviceCredential
from app.models.tenant import AccessEntry, AccessRequest
from app.services.device_commands import enqueue_command


def get_owner_device(control_db: Session, owner_id: str) -> DeviceCredential:
    device = control_db.scalar(
        select(DeviceCredential)
        .where(DeviceCredential.owner_id == owner_id, DeviceCredential.is_active.is_(True))
        .order_by(DeviceCredential.id.asc())
    )
    if device is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No active ESP32 device is registered for this cabin.")
    return device


def get_owner_device_id(control_db: Session, owner_id: str) -> str:
    return get_owner_device(control_db, owner_id).device_id


def decide_requests(
    db: Session,
    *,
    request_ids: list[int],
    decision: str,
) -> list[AccessRequest]:
    unique_ids = list(dict.fromkeys(request_ids))
    requests = list(db.scalars(select(AccessRequest).where(AccessRequest.id.in_(unique_ids))))
    found_ids = {request.id for request in requests}
    if found_ids != set(unique_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more access requests were not found.")
    if any(request.status != "pending" for request in requests):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only pending requests can be allowed or denied.")

    now = datetime.now(timezone.utc)
    for request in requests:
        request.status = decision
        request.resolved_at = now
        if decision == "allowed":
            enqueue_command(
                db,
                request.device_id,
                "UNLOCK_DOOR",
                {
                    "access_request_id": request.id,
                    "visitor_id": request.visitor_id,
                    "visitor_name": request.visitor_name,
                    "relay_pulse_ms": 3000,
                },
            )
        else:
            enqueue_command(
                db,
                request.device_id,
                "KEEP_LOCKED",
                {
                    "access_request_id": request.id,
                    "visitor_id": request.visitor_id,
                    "visitor_name": request.visitor_name,
                    "message": "Access denied",
                    "keep_locked": True,
                },
            )
    db.commit()
    for request in requests:
        db.refresh(request)
    return requests


def delay_request(db: Session, request: AccessRequest, duration_minutes: int):
    if request.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only pending requests can be delayed.")

    request.status = "delayed"
    request.duration_minutes = duration_minutes
    request.resolved_at = datetime.now(timezone.utc)
    message = f"Come back later after {duration_minutes} minutes"
    command = enqueue_command(
        db,
        request.device_id,
        "DISPLAY_MESSAGE",
        {
            "access_request_id": request.id,
            "visitor_id": request.visitor_id,
            "visitor_name": request.visitor_name,
            "duration_minutes": duration_minutes,
            "message": message,
            "oled_lines": ["Come back later", f"after {duration_minutes} minutes"],
            "keep_locked": True,
            "unlock": False,
        },
    )
    db.commit()
    db.refresh(request)
    return command


def record_command_result(db: Session, command, success: bool, error_message: str | None = None) -> None:
    """Create a Previous Entries row once the ESP32 acknowledges the physical action."""
    access_request_id = (command.payload or {}).get("access_request_id")
    if not access_request_id:
        return

    request = db.get(AccessRequest, int(access_request_id))
    if request is None:
        return

    existing = db.scalar(select(AccessEntry).where(AccessEntry.access_request_id == request.id))
    if existing:
        return

    # A delayed visit is a denied entry for the current attempt; the OLED message
    # does not schedule or trigger an automatic unlock later.
    result = "allowed" if success and command.command_type == "UNLOCK_DOOR" else "denied"
    reason = None if result == "allowed" else (error_message or request.status)

    db.add(
        AccessEntry(
            visitor_id=request.visitor_id,
            access_request_id=request.id,
            visitor_name=request.visitor_name,
            department=request.department,
            role=request.role,
            method="Fingerprint",
            result=result,
            reason=reason,
        )
    )
