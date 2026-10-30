from collections.abc import Iterator
from contextlib import contextmanager
from threading import RLock
import hashlib
import hmac

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class TenantBase(DeclarativeBase):
    pass


_engine_cache: dict[str, object] = {}
_session_cache: dict[str, sessionmaker] = {}
_cache_lock = RLock()


def tenant_role_name(owner_id: str) -> str:
    return f"cabin_user_{owner_id.replace('-', '')[:24]}"


def tenant_role_password(owner_id: str) -> str:
    # Deterministic per-owner database password. It is never stored in plaintext
    # or in the central DB; keep TENANT_PASSWORD_SECRET stable and backed up.
    return hmac.new(
        settings.tenant_password_secret.encode("utf-8"),
        owner_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def get_tenant_engine(database_name: str, owner_id: str):
    with _cache_lock:
        if database_name not in _engine_cache:
            url = make_url(settings.tenant_database_url).set(
                database=database_name,
                username=tenant_role_name(owner_id),
                password=tenant_role_password(owner_id),
            )
            _engine_cache[database_name] = create_engine(
                url,
                pool_pre_ping=True,
                pool_recycle=1800,
            )
        return _engine_cache[database_name]


def get_tenant_session_factory(database_name: str, owner_id: str) -> sessionmaker:
    with _cache_lock:
        if database_name not in _session_cache:
            _session_cache[database_name] = sessionmaker(
                bind=get_tenant_engine(database_name, owner_id),
                autoflush=False,
                expire_on_commit=False,
            )
        return _session_cache[database_name]


@contextmanager
def tenant_session(database_name: str, owner_id: str) -> Iterator[Session]:
    factory = get_tenant_session_factory(database_name, owner_id)
    db = factory()
    try:
        yield db
    finally:
        db.close()


def init_tenant_db(database_name: str, owner_id: str) -> None:
    from app.models.tenant import (  # noqa: F401
        AccessEntry,
        AccessRequest,
        DeviceCommand,
        Fingerprint,
        FingerprintEnrollment,
        Visitor,
    )

    TenantBase.metadata.create_all(bind=get_tenant_engine(database_name, owner_id))


def dispose_tenant_engine(database_name: str) -> None:
    with _cache_lock:
        engine = _engine_cache.pop(database_name, None)
        _session_cache.pop(database_name, None)
        if engine is not None:
            engine.dispose()


def dispose_tenant_engines() -> None:
    with _cache_lock:
        for engine in _engine_cache.values():
            engine.dispose()
        _engine_cache.clear()
        _session_cache.clear()
