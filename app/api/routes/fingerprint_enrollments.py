from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.tenant import get_tenant_session_factory
from app.api.deps import get_current_owner
from app.models.control import Owner
from app.models.tenant import Fingerprint, FingerprintEnrollment
from app.schemas.visitor import FingerprintEnrollmentOut

router = APIRouter(prefix="/fingerprint-enrollments", tags=["Fingerprint Enrollment"])


@router.get("/{enrollment_id}", response_model=FingerprintEnrollmentOut)
def get_enrollment_status(
    enrollment_id: str,
    owner: Owner = Depends(get_current_owner),
):
    factory = get_tenant_session_factory(owner.tenant_database, owner.id)
    with factory() as db:
        enrollment = db.get(FingerprintEnrollment, enrollment_id)
        if enrollment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fingerprint enrollment not found.")

        fingerprint_id = enrollment.fingerprint_id
        return FingerprintEnrollmentOut(
            enrollment_id=enrollment.id,
            fingerprint_id=fingerprint_id,
            enrolled_at=enrollment.enrolled_at,
            status=enrollment.status,
            message=enrollment.error_message,
        )
