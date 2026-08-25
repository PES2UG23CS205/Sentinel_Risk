"""
SentinelRisk — Application Configuration

Reads configuration from environment variables / .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Database
    database_url: str = "sqlite:///./sentinelrisk.db"

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Logging
    log_level: str = "INFO"

    # Application metadata
    app_name: str = "SentinelRisk"
    app_version: str = "0.1.0"
    app_description: str = "Defense-only Payment Risk Intelligence"


def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
