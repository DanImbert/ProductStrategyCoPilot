"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Product Strategy Copilot"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_allow_origins: str = "*"

    llm_provider: Literal["mock", "openai", "local"] = "mock"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_base_url: str = "https://api.openai.com/v1"

    local_api_base: str = "http://localhost:11434/v1"
    local_model: str = "llama3.1:8b-instruct"

    planner_temperature: float = 0.3
    critic_temperature: float = 0.1
    request_timeout_seconds: float = 45.0
    llm_max_retries: int = 3

    input_token_cost_usd_per_million: float = Field(default=0.40, ge=0.0)
    output_token_cost_usd_per_million: float = Field(default=1.60, ge=0.0)

    log_level: str = "INFO"
    enable_file_logging: bool = True
    log_file_path: str = "logs/product_strategy_copilot.log"

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug(cls, value: object) -> object:
        """Tolerate common environment strings that imply non-debug mode."""

        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"release", "prod", "production"}:
                return False
            if lowered in {"dev", "development", "debug"}:
                return True
        return value

    @property
    def cors_origins(self) -> list[str]:
        """Return normalized CORS origins from the environment string."""

        origins = [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]
        return origins or ["*"]

    @property
    def cors_allow_credentials(self) -> bool:
        """Disable credentialed wildcard CORS, which browsers reject."""

        return "*" not in self.cors_origins

    @property
    def active_model_name(self) -> str:
        """Model name selected for the current provider."""

        if self.llm_provider == "local":
            return self.local_model
        if self.llm_provider == "openai":
            return self.openai_model
        return "mock-heuristic-v1"


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings object."""

    return Settings()
