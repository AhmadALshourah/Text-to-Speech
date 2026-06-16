"""Application configuration loaded from environment variables / .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized, typed application settings.

    Values are read from the environment or the local `.env` file.
    """

    # Security
    secret_key: str = "dev-only-insecure-secret-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15   # short-lived; client refreshes via cookie
    refresh_token_expire_days: int = 7

    # Database
    database_url: str = "sqlite:///./app.db"

    # Audio output directory
    audio_output_dir: str = "audio_output"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# A single shared settings instance used across the app.
settings = Settings()
