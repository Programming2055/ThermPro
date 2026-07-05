"""Application settings loaded from environment variables."""
from __future__ import annotations

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="THERMPRO_",
        env_file=".env",
        case_sensitive=False,
    )

    # Database
    database_url: PostgresDsn = Field(
        default="postgresql+psycopg://thermpro:thermpro@localhost:5432/thermpro",
        description="PostgreSQL connection string (psycopg3 dialect).",
    )

    # Object storage
    s3_endpoint_url: str = Field(
        default="http://localhost:9000",
        description="S3-compatible endpoint (MinIO in development).",
    )
    s3_access_key_id: str = Field(default="minioadmin")
    s3_secret_access_key: str = Field(default="minioadmin")
    s3_bucket_artifacts: str = Field(default="thermpro-artifacts")
    s3_region: str = Field(default="us-east-1")

    # Application
    app_name: str = Field(default="ThermPro API")
    app_version: str = Field(default="0.1.0")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    # Auth (development identity provider)
    dev_auth_enabled: bool = Field(
        default=True,
        description=(
            "When True, uses the development identity provider (DevAuthProvider). "
            "Set to False and configure JWT_SECRET for production."
        ),
    )
    jwt_secret: str = Field(default="dev-secret-change-in-production")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_minutes: int = Field(default=60)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return upper


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
