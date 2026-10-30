from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VisitorCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=10, max_length=20)
    department: str = Field(min_length=2, max_length=100)
    role: str = Field(min_length=2, max_length=40)


class VisitorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, min_length=10, max_length=20)
    department: str | None = Field(default=None, min_length=2, max_length=100)
    role: str | None = Field(default=None, min_length=2, max_length=40)


class VisitorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str
    department: str
    role: str
    fingerprint_count: int
    registered_at: datetime


class FingerprintEnrollmentOut(BaseModel):
    enrollment_id: str
    fingerprint_id: str | None = None
    enrolled_at: datetime | None = None
    status: str
    message: str | None = None
