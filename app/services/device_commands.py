from uuid import uuid4

from app.models.tenant import DeviceCommand


def enqueue_command(db, device_id: str, command_type: str, payload: dict) -> DeviceCommand:
    command = DeviceCommand(
        id=str(uuid4()),
        device_id=device_id,
        command_type=command_type,
        payload=payload,
        status="queued",
    )
    db.add(command)
    db.flush()
    return command
