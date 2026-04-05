from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ChirandhAI Resume API"
    environment: str = Field(default="development", description="development | staging | production")

    # Comma-separated API keys (each key is a full secret string)
    api_keys: str = Field(default="dev-insecure-key-change-me", alias="API_KEYS")

    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/app.db",
        alias="DATABASE_URL",
    )

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    llm_model_propose: str = Field(default="gpt-4o-mini", alias="LLM_MODEL_PROPOSE")
    llm_model_score: str = Field(default="gpt-4o-mini", alias="LLM_MODEL_SCORE")
    max_propose_rounds_per_session: int = Field(default=5, alias="MAX_PROPOSE_ROUNDS_PER_SESSION")

    # S3-compatible storage (internal URL for API/worker → MinIO in Docker)
    s3_endpoint_url: str | None = Field(default=None, alias="S3_ENDPOINT_URL")
    # Browser-reachable URL for presigned GETs only (e.g. http://localhost:9000). If unset, uses S3_ENDPOINT_URL.
    s3_presign_endpoint_url: str | None = Field(default=None, alias="S3_PRESIGN_ENDPOINT_URL")
    s3_region: str = Field(default="us-east-1", alias="S3_REGION")
    s3_bucket: str = Field(default="resume-artifacts", alias="S3_BUCKET")
    aws_access_key_id: str | None = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str | None = Field(default=None, alias="AWS_SECRET_ACCESS_KEY")
    artifact_url_ttl_seconds: int = Field(default=3600, alias="ARTIFACT_URL_TTL_SECONDS")
    artifact_retention_days: int = Field(default=14, alias="ARTIFACT_RETENTION_DAYS")

    rate_limit_default: str = Field(default="60/minute", alias="RATE_LIMIT_DEFAULT")

    # Comma-separated origins; empty disables CORS middleware
    cors_origins: str = Field(default="", alias="CORS_ORIGINS")

    tectonic_timeout_seconds: int = Field(default=60, alias="TECTONIC_TIMEOUT_SECONDS")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @field_validator("api_keys", mode="before")
    @classmethod
    def strip_keys(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    def api_key_set(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
