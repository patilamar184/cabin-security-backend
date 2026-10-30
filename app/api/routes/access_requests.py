from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_owner, get_tenant_db
from app.db.control import get_control_db
from app.models.control import Owner
from app.models.tenant import AccessRequest
from app.schemas.access import (
    AccessDecisionOut,
    AccessDecisionRequest,
    AccessRequestOut,
    DelayOut,
    DelayRequest,
)
from app.services.access_control import decide_requests, delay_request

router = APIRouter(prefix="/access-requests", tags=["Access Control"])


def access_request_to_dict(request: AccessRequest) -> dict:
    return {
        "id": request.id,
        "visitor_id": request.visitor_id,
        "visitor_name": request.visitor_name,
        "department": request.department,
        "role": request.role,
        "method": request.method,
        "status": request.status,
        "requested_at": request.requested_at,
        "duration_minutes": request.duration_minutes,
    }


@router.get("")
def list_access_requests(db: Session = Depends(get_tenant_db)):
    requests = list(
        db.scalars(
            select(AccessRequest)
            .order_by(AccessRequest.requested_at.desc(), AccessRequest.id.desc())
            .limit(100)
        )
    )
    return {"items": [access_request_to_dict(request) for request in requests], "total": len(requests)}


@router.post("/decision", response_model=AccessDecisionOut)
def decide_access_requests(
    payload: AccessDecisionRequest,
    owner: Owner = Depends(get_current_owner),
    db: Session = Depends(get_tenant_db),
):
    updated = decide_requests(db, request_ids=payload.ids, decision=payload.decision)
    return AccessDecisionOut(
        updated=len(updated),
        items=[AccessRequestOut(**access_request_to_dict(request)) for request in updated],
        message=f"{len(updated)} access request(s) marked {payload.decision} and command(s) queued for the ESP32.",
    )


@router.post("/{request_id}/delay", response_model=DelayOut, status_code=status.HTTP_202_ACCEPTED)
def delay_access_request(
    request_id: int,
    payload: DelayRequest,
    db: Session = Depends(get_tenant_db),
):
    request = db.get(AccessRequest, request_id)
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access request not found.")

    command = delay_request(db, request, payload.duration_minutes)
    db.refresh(request)
    return DelayOut(
        request=AccessRequestOut(**access_request_to_dict(request)),
        command_id=command.id,
        message=f"OLED message queued: come back later after {payload.duration_minutes} minutes. Door remains locked.",
    )
