"""JobInterview — centralised application settings.

All configuration is loaded from environment variables and the .env file.
Import the shared ``settings`` singleton anywhere you need a config value:

    from config import settings
    key = settings.groq_api_key
"""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings for JobInterview.

    Values are read from environment variables (case-insensitive) and from
    a ``.env`` file in the project root, with environment variables taking
    priority.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Required — the app will not start without this.
    # ------------------------------------------------------------------
    groq_api_key: str = Field(..., description="Groq API key for the LLM.")

    # ------------------------------------------------------------------
    # Groq / LLM
    # ------------------------------------------------------------------
    groq_base_url: str = Field(
        default="https://api.groq.com/openai/v1",
        description="Groq OpenAI-compatible API base URL.",
    )
    groq_model: str = Field(
        default="llama-3.3-70b-versatile",
        description="Groq model identifier.",
    )

    # ------------------------------------------------------------------
    # Local dev server
    # ------------------------------------------------------------------
    host: str = Field(default="127.0.0.1", description="Bind address for the dev server.")
    port: int = Field(default=8000, description="Port for the dev server.")
    reload: bool = Field(default=True, description="Enable auto-reload in development.")


# Single shared instance — import this rather than constructing a new Settings().
settings = Settings()
