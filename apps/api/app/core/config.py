from functools import lru_cache
import os

from pydantic import BaseModel, Field


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _split_csv(value: str | None, default: list[str] | None = None) -> list[str]:
    if value is None:
        return list(default or [])
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseModel):
    app_name: str = "HuntFlow vNext API"
    app_version: str = "0.1.0"
    secret_key: str = Field(default_factory=lambda: os.getenv("APP_SECRET", "change-me"))
    app_env: str = Field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    enable_demo_seed: bool = Field(
        default_factory=lambda: _to_bool(os.getenv("ENABLE_DEMO_SEED"), default=os.getenv("APP_ENV", "development") != "production")
    )
    store_backend: str = Field(default_factory=lambda: os.getenv("STORE_BACKEND", "memory"))
    store_file_path: str = Field(default_factory=lambda: os.getenv("STORE_FILE_PATH", "data/store.json"))
    database_url: str | None = Field(default_factory=lambda: os.getenv("DATABASE_URL"))
    database_schema: str = Field(default_factory=lambda: os.getenv("DATABASE_SCHEMA", "public"))
    runtime_backend: str = Field(default_factory=lambda: os.getenv("RUNTIME_BACKEND", "memory"))
    redis_url: str | None = Field(default_factory=lambda: os.getenv("REDIS_URL"))
    allowed_origins: list[str] = Field(
        default_factory=lambda: _split_csv(
            os.getenv("ALLOWED_ORIGINS"),
            default=["http://localhost:3000", "http://127.0.0.1:3000"],
        )
    )
    session_cookie_name: str = Field(default_factory=lambda: os.getenv("SESSION_COOKIE_NAME", "huntflow_session"))
    session_cookie_secure: bool = Field(
        default_factory=lambda: _to_bool(os.getenv("SESSION_COOKIE_SECURE"), default=os.getenv("APP_ENV", "development") == "production")
    )
    session_cookie_samesite: str = Field(default_factory=lambda: os.getenv("SESSION_COOKIE_SAMESITE", "lax"))
    session_cookie_domain: str | None = Field(default_factory=lambda: os.getenv("SESSION_COOKIE_DOMAIN"))
    enable_experimental_sourcing: bool = Field(
        default_factory=lambda: _to_bool(os.getenv("ENABLE_EXPERIMENTAL_SOURCING"), default=False)
    )
    primary_model: str = Field(default_factory=lambda: os.getenv("QWEN_MODEL", "qwen-max"))
    fallback_model: str = Field(default_factory=lambda: os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
