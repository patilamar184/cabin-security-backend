from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.tenant import TenantBase


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Visitor(TenantBase):
    __tablename__ = "visitors"
    __table_args__ = (UniqueConstraint("phone", name="uq_visitors_phone"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    fingerprints: Mapped[list["Fingerprint"]] = relationship(
        back_populates="visitor", cascade="all, delete-orphan", passive_deletes=True
    )


class Fingerprint(TenantBase):
    __tablename__ = "fingerprints"
    __table_args__ = (
        UniqueConstraint("device_id", "sensor_slot", name="uq_fingerprint_device_slot"),
        Index("ix_fingerprints_visitor_status", "visitor_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    visitor_id: Mapped[int] = mapped_column(ForeignKey("visitors.id", ondelete="CASCADE"), nullable=False)
    device_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    sensor_slot: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    visitor: Mapped[Visitor] = relationship(back_populates="fingerprints")


class FingerprintEnrollment(TenantBase):
    __tablename__ = "fingerprint_enrollments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    visitor_id: Mapped[int] = mapped_column(ForeignKey("visitors.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    command_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    fingerprint_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sensor_slot: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enrolled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AccessRequest(TenantBase):
    __tablename__ = "access_requests"
    __table_args__ = (Index("ix_access_requests_status_requested", "status", "requested_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visitor_id: Mapped[int | None] = mapped_column(ForeignKey("visitors.id", ondelete="SET NULL"), nullable=True, index=True)
    device_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    visitor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    department: Mapped[str] = mapped_column(String(100), default="—", nullable=False)
    role: Mapped[str] = mapped_column(String(40), default="—", nullable=False)
    method: Mapped[str] = mapped_column(String(30), default="Fingerprint", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)


class AccessEntry(TenantBase):
    __tablename__ = "access_entries"
    __table_args__ = (UniqueConstraint("access_request_id", name="uq_entry_access_request"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visitor_id: Mapped[int | None] = mapped_column(ForeignKey("visitors.id", ondelete="SET NULL"), nullable=True, index=True)
    access_request_id: Mapped[int | None] = mapped_column(ForeignKey("access_requests.id", ondelete="SET NULL"), nullable=True)
    visitor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    department: Mapped[str] = mapped_column(String(100), default="—", nullable=False)
    role: Mapped[str] = mapped_column(String(40), default="—", nullable=False)
    entry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(30), default="Fingerprint", nullable=False)
    result: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)


class DeviceCommand(TenantBase):
    __tablename__ = "device_commands"
    __table_args__ = (Index("ix_device_commands_poll", "device_id", "status", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    device_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    command_type: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
