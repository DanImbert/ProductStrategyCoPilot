"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
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
