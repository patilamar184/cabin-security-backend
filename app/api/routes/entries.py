from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select, String, cast
from sqlalchemy.orm import Session

from app.api.deps import get_tenant_db
from app.models.tenant import AccessEntry

router = APIRouter(prefix="/entries", tags=["Previous Entries"])


@router.get("")
def list_entries(
    search: str | None = None,
    department: str | None = None,
    role: str | None = None,
    result: str | None = None,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_tenant_db),
):
    query = select(AccessEntry)
    count_query = select(func.count(AccessEntry.id))
    filters = []
    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                AccessEntry.visitor_name.ilike(term),
                AccessEntry.department.ilike(term),
                cast(AccessEntry.id, String).ilike(term),
            )
        )
    if department:
        filters.append(AccessEntry.department == department)
    if role:
        filters.append(AccessEntry.role == role)
    if result:
        filters.append(AccessEntry.result == result)
    if filters:
        query = query.where(*filters)
        count_query = count_query.where(*filters)

    total = int(db.scalar(count_query) or 0)
    rows = list(
        db.scalars(
            query.order_by(AccessEntry.entry_at.desc(), AccessEntry.id.desc())
            .offset((page - 1) * pageSize)
            .limit(pageSize)
        )
    )
    return {
        "items": [
            {
                "id": row.id,
                "visitor_id": row.visitor_id,
                "visitor_name": row.visitor_name,
                "department": row.department,
                "role": row.role,
                "entry_at": row.entry_at,
                "method": row.method,
                "result": row.result,
                "reason": row.reason,
            }
            for row in rows
        ],
        "total": total,
    }
