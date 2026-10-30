from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import access_requests, auth, device, entries, fingerprint_enrollments, visitors
from app.core.config import settings
from app.db.control import init_control_db
from app.db.tenant import dispose_tenant_engines


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.environment.lower() == "production":
        if settings.jwt_secret_key.startswith("CHANGE_ME") or settings.tenant_password_secret.startswith("CHANGE_ME"):
            raise RuntimeError("Set strong JWT_SECRET_KEY and TENANT_PASSWORD_SECRET values before production startup.")
    init_control_db()
    yield
    dispose_tenant_engines()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Multi-tenant cabin security API. Each cabin owner has a separate PostgreSQL database. "
        "ESP32 devices poll authenticated commands; fingerprint templates remain on the R307 sensor."
    ),
    lifespan=lifespan,
)

private_lan_origin_regex = (
    r"^http://(localhost|127\.0\.0\.1|10\.(?:\d{1,3}\.){2}\d{1,3}|"
    r"192\.168\.(?:\d{1,3}\.)\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.(?:\d{1,3}\.)\d{1,3}):5173$"
    if settings.allow_private_lan_origins
    else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_origins,
    allow_origin_regex=private_lan_origin_regex,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Device-ID", "X-Device-Key"],
)

app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(visitors.router, prefix=settings.api_v1_prefix)
app.include_router(fingerprint_enrollments.router, prefix=settings.api_v1_prefix)
app.include_router(access_requests.router, prefix=settings.api_v1_prefix)
app.include_router(entries.router, prefix=settings.api_v1_prefix)
app.include_router(device.router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": settings.app_name}


@app.get(f"{settings.api_v1_prefix}/health", tags=["Health"])
def api_health_check():
    return {"status": "ok", "service": settings.app_name}
