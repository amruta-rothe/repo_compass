"""
RepoCompass — application config loaded from environment variables.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = "development"
    app_base_url: str = "http://localhost:8501"
    app_secret_key: str = "change-me"

    # Supabase / Database
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    database_url: str = ""

    # GitHub
    github_token: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""

    # Ollama / AI
    ollama_base_url: str = "http://localhost:11434"
    # NOTE: `qwen3:4b` is a thinking-only model in Ollama -- it ignores `think: false`,
    # so it burns the token budget on a reasoning trace and is both slow and unreliable
    # for structured JSON. `qwen3:4b-instruct` is the non-thinking variant (~4x faster).
    ollama_model: str = "qwen3:4b-instruct"
    # Send `think: false` on every request. Harmless for non-thinking models and it
    # protects the JSON path if the model is later switched to a hybrid one.
    ollama_disable_thinking: bool = True
    # Keep the model resident in RAM between calls to avoid cold reload costs.
    ollama_keep_alive: str = "30m"
    model_timeout_seconds: int = 45
    model_max_retries: int = 2

    # Ingestion limits
    max_repository_files: int = 500
    max_source_file_bytes: int = 250_000
    max_context_chars: int = 30_000

    # Isolated runner
    runner_enabled: bool = False
    runner_base_url: str = ""
    runner_api_key: str = ""
    runner_timeout_seconds: int = 30

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_anon_key)

    @property
    def github_authenticated(self) -> bool:
        return bool(self.github_token)

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
