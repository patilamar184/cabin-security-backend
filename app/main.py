from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.api.routes import auth,admin,visitors,roles,devices,fingerprints,access,device_comm,logs,dashboard,health,door
from app.models import entities  # register models
@asynccontextmanager
async def lifespan(app:FastAPI):
    yield
app=FastAPI(title=settings.app_name,version='1.0.0',lifespan=lifespan,description='Multi-tenant IoT cabin access management API. No email verification is implemented.')
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.cors_origins.split(',')],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
for router in [auth.router,admin.router,visitors.router,roles.router,devices.router,fingerprints.router,access.router,device_comm.router,logs.router,dashboard.router,health.router,door.router]: app.include_router(router,prefix=settings.api_v1_prefix)
