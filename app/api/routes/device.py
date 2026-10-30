from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.api.deps import DeviceContext, get_device_context
from app.core.config import settings
from app.models.tenant import (
    AccessEntry,
    AccessRequest,
    DeviceCommand,
    Fingerprint,
    FingerprintEnrollment,
    Visitor,
)
from app.schemas.access import CommandAckIn, FingerprintEventIn, FingerprintEventOut, HeartbeatIn
from app.schemas.device import DeviceCommandOut, DeviceStatusOut
from app.services.access_control import record_command_result
from app.services.device_commands import enqueue_command

router = APIRouter(prefix="/device", tags=["ESP32 Device"])


@router.post("/heartbeat")
def heartbeat(payload: HeartbeatIn, context: DeviceContext = Depends(get_device_context)):
    now = datetime.now(timezone.utc)
    context.credential.last_seen_at = now
    context.credential.last_ip_address = payload.ip_address
    context.credential.firmware_version = payload.firmware_version
    context.control_db.commit()
    return {"device_id": context.credential.device_id, "status": "online", "server_time": now}


@router.get("/status", response_model=DeviceStatusOut)
def device_status(context: DeviceContext = Depends(get_device_context)):
    last_seen = context.credential.last_seen_at
    if last_seen is not None and last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    online = bool(last_seen and last_seen >= datetime.now(timezone.utc) - timedelta(seconds=settings.device_online_window_seconds))
    return DeviceStatusOut(
        device_id=context.credential.device_id,
        online=online,
        last_seen_at=last_seen,
        firmware_version=context.credential.firmware_version,
    )


@router.get("/commands/next", response_model=DeviceCommandOut | None)
def get_next_command(context: DeviceContext = Depends(get_device_context)):
    now = datetime.now(timezone.utc)
    lease_expired_before = now - timedelta(seconds=settings.device_command_lease_seconds)
    command = context.db.scalar(
        select(DeviceCommand)
        .where(
            DeviceCommand.device_id == context.credential.device_id,
            or_(
                DeviceCommand.status == "queued",
                and_(DeviceCommand.status == "delivered", DeviceCommand.delivered_at <= lease_expired_before),
            ),
        )
        .order_by(DeviceCommand.created_at.asc())
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if command is None:
        return None

    command.status = "delivered"
    command.delivered_at = now
    command.attempt_count += 1
    context.db.commit()
    return DeviceCommandOut(
        command_id=command.id,
        command_type=command.command_type,
        payload=command.payload,
        created_at=command.created_at,
    )


@router.post("/commands/{command_id}/ack")
def acknowledge_command(
    command_id: str,
    payload: CommandAckIn,
    context: DeviceContext = Depends(get_device_context),
):
    command = context.db.scalar(
        select(DeviceCommand).where(
            DeviceCommand.id == command_id,
            DeviceCommand.device_id == context.credential.device_id,
        )
    )
    if command is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device command not found.")
    if command.status == "acknowledged":
        return {"acknowledged": True, "already_acknowledged": True}
    if command.status == "failed":
        return {"acknowledged": True, "already_acknowledged": True, "status": "failed"}

    now = datetime.now(timezone.utc)
    success = payload.status == "succeeded"
    command.status = "acknowledged" if success else "failed"
    command.acknowledged_at = now
    command.error_message = payload.error_message

    if not success:
        access_request_id = (command.payload or {}).get("access_request_id")
        if access_request_id:
            access_request = context.db.get(AccessRequest, int(access_request_id))
            if access_request is not None:
                access_request.status = "failed"
                access_request.resolved_at = now

    if command.command_type == "ENROLL_FINGERPRINT":
        enrollment = context.db.scalar(
            select(FingerprintEnrollment).where(FingerprintEnrollment.command_id == command.id)
        )
        if enrollment:
            if success:
                sensor_slot = payload.result.get("sensor_slot", payload.result.get("template_id"))
                try:
                    sensor_slot = int(sensor_slot)
                except (TypeError, ValueError):
                    sensor_slot = 0
                existing = context.db.scalar(
                    select(Fingerprint).where(
                        Fingerprint.device_id == context.credential.device_id,
                        Fingerprint.sensor_slot == sensor_slot,
                        Fingerprint.status == "active",
                    )
                ) if 1 <= sensor_slot <= 255 else None
                if not 1 <= sensor_slot <= 255:
                    success = False
                    command.status = "failed"
                    command.error_message = "ESP32 acknowledgement did not include a valid sensor_slot (1-255)."
                elif existing:
                    success = False
                    command.status = "failed"
                    command.error_message = f"R307 sensor slot {sensor_slot} is already assigned to another fingerprint."
                else:
                    fingerprint = Fingerprint(
                        visitor_id=enrollment.visitor_id,
                        device_id=context.credential.device_id,
                        sensor_slot=sensor_slot,
                        status="active",
                    )
                    context.db.add(fingerprint)
                    context.db.flush()
                    enrollment.status = "completed"
                    enrollment.sensor_slot = sensor_slot
                    enrollment.fingerprint_id = f"R307-{sensor_slot:03d}"
                    enrollment.enrolled_at = now
            if not success:
                enrollment.status = "failed"
                enrollment.error_message = command.error_message or payload.error_message or "Fingerprint enrollment failed on the device."

    elif command.command_type == "DELETE_FINGERPRINT" and success:
        sensor_slot = (command.payload or {}).get("sensor_slot")
        if sensor_slot is not None:
            fingerprint = context.db.scalar(
                select(Fingerprint).where(
                    Fingerprint.device_id == context.credential.device_id,
                    Fingerprint.sensor_slot == int(sensor_slot),
                )
            )
            if fingerprint:
                fingerprint.status = "deleted"

    else:
        record_command_result(context.db, command, success, command.error_message)

    context.db.commit()
    return {
        "acknowledged": True,
        "status": command.status,
        "command_id": command.id,
    }


@router.post("/fingerprint-events", response_model=FingerprintEventOut, status_code=status.HTTP_201_CREATED)
def fingerprint_event(payload: FingerprintEventIn, context: DeviceContext = Depends(get_device_context)):
    fingerprint = context.db.scalar(
        select(Fingerprint).where(
            Fingerprint.device_id == context.credential.device_id,
            Fingerprint.sensor_slot == payload.sensor_slot,
            Fingerprint.status == "active",
        )
    )

    if fingerprint is None:
        enqueue_command(
            context.db,
            context.credential.device_id,
            "DISPLAY_MESSAGE",
            {
                "message": "Fingerprint not recognized",
                "oled_lines": ["Fingerprint not", "recognized"],
                "keep_locked": True,
                "unlock": False,
            },
        )
        context.db.add(
            AccessEntry(
                visitor_id=None,
                access_request_id=None,
                visitor_name="Unknown Visitor",
                department="—",
                role="—",
                method="Fingerprint",
                result="denied",
                reason=f"Unregistered R307 sensor slot: {payload.sensor_slot}",
            )
        )
        context.db.commit()
        return FingerprintEventOut(accepted=False, status="denied", message="Fingerprint is not registered. Door remains locked.")

    visitor = context.db.get(Visitor, fingerprint.visitor_id)
    if visitor is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Fingerprint mapping has no active visitor record.")

    existing_pending = context.db.scalar(
        select(AccessRequest).where(
            AccessRequest.visitor_id == visitor.id,
            AccessRequest.device_id == context.credential.device_id,
            AccessRequest.status == "pending",
        )
    )
    if existing_pending:
        return FingerprintEventOut(
            accepted=True,
            access_request_id=existing_pending.id,
            status="pending",
            message="This visitor already has a pending access request.",
        )

    request = AccessRequest(
        visitor_id=visitor.id,
        device_id=context.credential.device_id,
        visitor_name=visitor.name,
        department=visitor.department,
        role=visitor.role,
        method="Fingerprint",
        status="pending",
    )
    context.db.add(request)
    context.db.commit()
    context.db.refresh(request)
    return FingerprintEventOut(
        accepted=True,
        access_request_id=request.id,
        status="pending",
        message="Fingerprint verified. Waiting for cabin owner approval.",
    )
