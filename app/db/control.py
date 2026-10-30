from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class ControlBase(DeclarativeBase):
    pass


control_engine = create_engine(
    settings.control_database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
)
ControlSessionLocal = sessionmaker(bind=control_engine, autoflush=False, expire_on_commit=False)


def get_control_db() -> Generator[Session, None, None]:
    db = ControlSessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_control_db() -> None:
    # Import model metadata before create_all.
    from app.models.control import DeviceCredential, Owner  # noqa: F401

    ControlBase.metadata.create_all(bind=control_engine)
