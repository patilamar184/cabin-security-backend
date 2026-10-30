from datetime import datetime

from pydantic import BaseModel


class DeviceCommandOut(BaseModel):
    command_id: str
    command_type: str
    payload: dict
    created_at: datetime


class DeviceStatusOut(BaseModel):
    device_id: str
    online: bool
    last_seen_at: datetime | None = None
    firmware_version: str | None = None
