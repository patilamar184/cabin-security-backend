from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Cabin Security Management API"
    environment: str = "development"
    api_v1_prefix: str = "/api"
    database_url: str = "postgresql+psycopg://postgres:postgres@db:5432/cabin_security"
    jwt_secret_key: str = "CHANGE_ME_TO_A_LONG_RANDOM_SECRET"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 14
    device_api_key_pepper: str = "CHANGE_ME_DEVICE_PEPPER"
    pin_length: int = 6
    command_default_ttl_seconds: int = 120
    device_offline_after_seconds: int = 60
    cors_origins: str = "http://localhost:5173"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
