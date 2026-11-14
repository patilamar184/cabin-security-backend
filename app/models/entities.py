import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Text, JSON, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

def uid(): return uuid.uuid4()
def now(): return datetime.now(timezone.utc)

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now, nullable=False)

class Tenant(Base, TimestampMixin):
    __tablename__='tenants'
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uid)
    name: Mapped[str]=mapped_column(String(160),nullable=False)
    location: Mapped[str]=mapped_column(String(255),nullable=False)
    status: Mapped[str]=mapped_column(String(20),default='active',nullable=False)

class CabinOwner(Base, TimestampMixin):
    __tablename__='cabin_owners'
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uid)
    tenant_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey('tenants.id',ondelete='CASCADE'),unique=True,index=True)
    full_name: Mapped[str]=mapped_column(String(160),nullable=False)
    email: Mapped[str]=mapped_column(String(255),unique=True,index=True,nullable=False)
    password_hash: Mapped[str]=mapped_column(String(255),nullable=False)
    phone: Mapped[str]=mapped_column(String(30),nullable=False)
    is_active: Mapped[bool]=mapped_column(Boolean,default=True,nullable=False)

class PlatformAdmin(Base):
    __tablename__='platform_admins'
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uid)
    email: Mapped[str]=mapped_column(String(255),unique=True,nullable=False)
    password_hash: Mapped[str]=mapped_column(String(255),nullable=False)
    is_active: Mapped[bool]=mapped_column(Boolean,default=True,nullable=False)

class VisitorRole(Base, TimestampMixin):
    __tablename__='visitor_roles'; __table_args__=(UniqueConstraint('tenant_id','name',name='uq_role_tenant_name'),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uid)
    tenant_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey('tenants.id',ondelete='CASCADE'),index=True)
    name: Mapped[str]=mapped_column(String(80),nullable=False)
    is_active: Mapped[bool]=mapped_column(Boolean,default=True,nullable=False)

class Visitor(Base, TimestampMixin):
    __tablename__='visitors'; __table_args__=(Index('ix_visitors_tenant_name','tenant_id','name'),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uid)
    tenant_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey('tenants.id',ondelete='CASCADE'),index=True)
    role_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey('visitor_roles.id',ondelete='RESTRICT'))
    name: Mapped[str]=mapped_column(String(160),nullable=False)
    phone: Mapped[str]=mapped_column(String(30),nullable=False)
    department: Mapped[str]=mapped_column(String(120),nullable=False)
    is_active: Mapped[bool]=mapped_column(Boolean,default=True,nullable=False)

class VisitorCredential(Base, TimestampMixin):
    __tablename__='visitor_credentials'
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uid)
    tenant_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey('tenants.id',ondelete='CASCADE'),index=True)
    visitor_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey('visitors.id',ondelete='CASCADE'),unique=True)
    pin_hash: Mapped[str]=mapped_column(String(255),nullable=False)

class Device(Base, TimestampMixin):
    __tablename__='devices'
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uid)
    tenant_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey('tenants.id',ondelete='CASCADE'),index=True)
    name: Mapped[str]=mapped_column(String(120),nullable=False)
    api_key_hash: Mapped[str]=mapped_column(String(64),nullable=False)
    status: Mapped[str]=mapped_column(String(20),default='offline',nullable=False)
    last_heartbeat_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    firmware_version: Mapped[str|None]=mapped_column(String(40))
    is_active: Mapped[bool]=mapped_column(Boolean,default=True,nullable=False)

class FingerprintEnrollment(Base, TimestampMixin):
    __tablename__='fingerprint_enrollments'; __table_args__=(UniqueConstraint('device_id','template_id',name='uq_device_template'),UniqueConstraint('visitor_id',name='uq_fingerprint_visitor'))
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uid)
    tenant_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey('tenants.id',ondelete='CASCADE'),index=True)
    visitor_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey('visitors.id',ondelete='CASCADE'))
    device_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey('devices.id',ondelete='CASCADE'))
    template_id: Mapped[int]=mapped_column(Integer,nullable=False)
    status: Mapped[str]=mapped_column(String(20),default='pending',nullable=False)

class AccessRequest(Base, TimestampMixin):
    __tablename__='access_requests'
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uid)
    tenant_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey('tenants.id',ondelete='CASCADE'),index=True)
    visitor_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey('visitors.id',ondelete='SET NULL'),nullable=True)
    device_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey('devices.id',ondelete='SET NULL'),nullable=True)
    authentication_method: Mapped[str]=mapped_column(String(20),nullable=False)
    status: Mapped[str]=mapped_column(String(20),default='pending',nullable=False,index=True)
    decided_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)

class DeviceCommand(Base):
    __tablename__='device_commands'
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uid)
    tenant_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey('tenants.id',ondelete='CASCADE'),index=True)
    device_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey('devices.id',ondelete='CASCADE'),index=True)
    command_type: Mapped[str]=mapped_column(String(60),nullable=False)
    payload: Mapped[dict]=mapped_column(JSON,default=dict,nullable=False)
    status: Mapped[str]=mapped_column(String(20),default='pending',nullable=False,index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,nullable=False)
    expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    acknowledged_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    result: Mapped[dict|None]=mapped_column(JSON)

class EntryLog(Base):
    __tablename__='entry_logs'
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uid)
    tenant_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey('tenants.id',ondelete='CASCADE'),index=True)
    visitor_id: Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True),ForeignKey('visitors.id',ondelete='SET NULL'))
    device_id: Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True),ForeignKey('devices.id',ondelete='SET NULL'))
    authentication_method: Mapped[str]=mapped_column(String(20),nullable=False)
    authentication_result: Mapped[str]=mapped_column(String(20),nullable=False)
    access_decision: Mapped[str]=mapped_column(String(20),default='pending',nullable=False)
    metadata_json: Mapped[dict]=mapped_column('metadata',JSON,default=dict,nullable=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,nullable=False,index=True)

class RefreshToken(Base):
    __tablename__='refresh_tokens'
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uid)
    owner_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey('cabin_owners.id',ondelete='CASCADE'),index=True)
    token_hash: Mapped[str]=mapped_column(String(64),unique=True,nullable=False)
    expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    revoked_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,nullable=False)
