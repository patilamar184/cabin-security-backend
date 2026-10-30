from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AccessRequestOut(BaseModel):
    id: int
    visitor_id: int | None = None
    visitor_name: str
    method: str = "Fingerprint"
    status: str
    requested_at: datetime
    duration_minutes: int | None = None


class AccessDecisionRequest(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=50)
    decision: Literal["allowed", "denied"]


class AccessDecisionOut(BaseModel):
    updated: int
    items: list[AccessRequestOut]
    message: str


class DelayRequest(BaseModel):
    duration_minutes: Literal[5, 10, 30]


class DelayOut(BaseModel):
    request: AccessRequestOut
    command_id: str
    message: str


class FingerprintEventIn(BaseModel):
    sensor_slot: int = Field(ge=1, le=255)


class FingerprintEventOut(BaseModel):
    accepted: bool
    access_request_id: int | None = None
    status: str
    message: str


class CommandAckIn(BaseModel):
    status: Literal["succeeded", "failed"]
    result: dict = Field(default_factory=dict)
    error_message: str | None = Field(default=None, max_length=500)


class HeartbeatIn(BaseModel):
    firmware_version: str | None = Field(default=None, max_length=40)
    ip_address: str | None = Field(default=None, max_length=64)
    rssi: int | None = None
