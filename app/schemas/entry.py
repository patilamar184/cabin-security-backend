from datetime import datetime

from pydantic import BaseModel


class AccessEntryOut(BaseModel):
    id: int
    visitor_id: int | None = None
    visitor_name: str
    department: str
    role: str
    entry_at: datetime
    method: str
    result: str
    reason: str | None = None
