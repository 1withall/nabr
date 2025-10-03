"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Nābr"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, validation_alias="DEBUG")
    environment: Literal["development", "staging", "production"] = "development"

    # API
    api_v1_prefix: str = "/api/v1"
    allowed_hosts: list[str] = Field(default=["*"])
    
    # Security
    secret_key: str = Field(..., min_length=32, validation_alias="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    password_min_length: int = 8
    
    # Database
    postgres_server: str = Field(default="localhost", validation_alias="POSTGRES_SERVER")
    postgres_user: str = Field(default="nabr", validation_alias="POSTGRES_USER")
    postgres_password: str = Field(..., validation_alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="nabr_db", validation_alias="POSTGRES_DB")
    postgres_port: int = Field(default=5432, validation_alias="POSTGRES_PORT")
    database_url: PostgresDsn | None = None

    @field_validator("database_url", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str | None, info) -> str:
        """Construct database URL from components if not provided."""
        if isinstance(v, str):
            return v
        data = info.data
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=data.get("postgres_user"),
                password=data.get("postgres_password"),
                host=data.get("postgres_server"),
                port=data.get("postgres_port"),
                path=data.get("postgres_db"),
            )
        )

    # Temporal
    temporal_host: str = Field(default="localhost:7233", validation_alias="TEMPORAL_HOST")
    temporal_namespace: str = Field(default="default", validation_alias="TEMPORAL_NAMESPACE")
    
    # Task Queues (deprecated single queue, now using dedicated queues)
    temporal_task_queue: str = Field(default="nabr-task-queue", validation_alias="TEMPORAL_TASK_QUEUE")
    
    # Verification
    min_verifiers_required: int = 2
    verification_expiry_days: int = 365
    
    # Matching Algorithm
    max_distance_km: float = 50.0
    skill_match_weight: float = 0.4
    availability_weight: float = 0.3
    rating_weight: float = 0.2
    distance_weight: float = 0.1
    matching_skill_weight: float = 0.4
    matching_availability_weight: float = 0.3
    matching_rating_weight: float = 0.2
    matching_distance_weight: float = 0.1
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # seconds


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
