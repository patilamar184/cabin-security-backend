from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Cabin Security Management API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    control_database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/cabin_control"
    tenant_database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
    tenant_password_secret: str = "CHANGE_ME_TO_ANOTHER_LONG_RANDOM_SECRET"
    provision_database_url: str = "postgresql://postgres:postgres@localhost:5432/postgres"

    jwt_secret_key: str = "CHANGE_ME_TO_A_LONG_RANDOM_SECRET"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 720

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    allow_private_lan_origins: bool = True
    allow_owner_registration: bool = False

    device_command_lease_seconds: int = 20
    device_online_window_seconds: int = 45

    @property
    def parsed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache

def get_settings() -> Settings:
    return Settings()


settings = get_settings()
