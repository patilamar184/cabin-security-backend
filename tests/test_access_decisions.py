from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.tenant import TenantBase
from app.models.tenant import AccessEntry, AccessRequest, DeviceCommand
from app.services.access_control import decide_requests, delay_request, record_command_result


def make_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TenantBase.metadata.create_all(engine)
    return Session(engine, expire_on_commit=False)


def test_allow_decision_queues_unlock_and_records_acknowledged_entry():
    with make_session() as db:
        request = AccessRequest(
            visitor_id=41,
            device_id="esp32-test",
            visitor_name="Test Visitor",
            department="Engineering",
            role="Employee",
            status="pending",
        )
        db.add(request)
        db.commit()
        db.refresh(request)

        decided = decide_requests(db, request_ids=[request.id], decision="allowed")
        assert decided[0].status == "allowed"

        command = db.scalar(select(DeviceCommand).where(DeviceCommand.command_type == "UNLOCK_DOOR"))
        assert command is not None
        assert command.payload["access_request_id"] == request.id
        assert "relay_pulse_ms" in command.payload

        record_command_result(db, command, success=True)
        db.commit()
        entry = db.scalar(select(AccessEntry).where(AccessEntry.access_request_id == request.id))
        assert entry is not None
        assert entry.result == "allowed"


def test_delay_queues_oled_message_and_never_unlocks():
    with make_session() as db:
        request = AccessRequest(
            visitor_id=42,
            device_id="esp32-test",
            visitor_name="Another Visitor",
            department="IT",
            role="Visitor",
            status="pending",
        )
        db.add(request)
        db.commit()
        db.refresh(request)

        command = delay_request(db, request, 10)
        assert request.status == "delayed"
        assert request.duration_minutes == 10
        assert command.command_type == "DISPLAY_MESSAGE"
        assert command.payload["keep_locked"] is True
        assert command.payload["unlock"] is False
        assert command.payload["oled_lines"] == ["Come back later", "after 10 minutes"]

        assert db.scalar(select(DeviceCommand).where(DeviceCommand.command_type == "UNLOCK_DOOR")) is None
