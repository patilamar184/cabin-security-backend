import hashlib, secrets
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(value: str) -> str:
    return pwd_context.hash(value)

def verify_password(value: str, hashed: str) -> bool:
    return pwd_context.verify(value, hashed)

def create_access_token(subject: str, role: str, tenant_id: str | None = None) -> str:
    now=datetime.now(timezone.utc)
    payload={"sub":subject,"role":role,"tenant_id":tenant_id,"type":"access","iat":now,"exp":now+timedelta(minutes=settings.access_token_minutes)}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def create_refresh_token(subject: str) -> tuple[str, datetime]:
    now=datetime.now(timezone.utc); expires=now+timedelta(days=settings.refresh_token_days)
    return jwt.encode({"sub":subject,"type":"refresh","iat":now,"exp":expires,"jti":secrets.token_urlsafe(16)}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm), expires

def decode_token(token: str) -> dict:
    try: return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc: raise ValueError("Invalid or expired token") from exc

def hash_secret(value: str) -> str:
    return hashlib.sha256((settings.device_api_key_pepper + value).encode()).hexdigest()

def generate_pin() -> str:
    return ''.join(str(secrets.randbelow(10)) for _ in range(settings.pin_length))

def generate_device_key() -> str:
    return secrets.token_urlsafe(36)
