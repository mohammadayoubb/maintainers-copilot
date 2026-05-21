"""Application configuration module.

This file centralizes all environment-based configuration for the project.

Important rule:
Other files should not call os.getenv() directly.
Instead, they should import get_settings() from this file.

For now, this file reads basic local development settings.
Later, Vault will load real secrets during startup, and those secrets
will be attached to this settings object.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings loaded from environment variables.

    BaseSettings automatically reads values from:
    - environment variables
    - the .env file
    - default values defined below

    This gives us one clean place for configuration.
    """

    # Tell Pydantic Settings to read from .env.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Project metadata.
    app_name: str = "Maintainer's Copilot"
    environment: str = "local"

    # Service ports.
    api_port: int = Field(default=8000, alias="API_PORT")
    model_server_port: int = Field(default=8001, alias="MODEL_SERVER_PORT")
    streamlit_port: int = Field(default=8501, alias="STREAMLIT_PORT")
    # Infrastructure ports.
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    minio_port: int = Field(default=9000, alias="MINIO_PORT")
    minio_console_port: int = Field(default=9001, alias="MINIO_CONSOLE_PORT")
    vault_port: int = Field(default=8200, alias="VAULT_PORT")
    vault_host: str = Field(default="localhost", alias="VAULT_HOST")
    # Vault configuration.
    # For local dev, this comes from .env.
    # Later, the app will use this token only to read real secrets from Vault.
    vault_root_token: str = Field(default="root", alias="VAULT_ROOT_TOKEN")

    # These secrets are intentionally empty by default.
    # Later, Vault startup loading will fill them.
    jwt_signing_key: str | None = None
    llm_api_key: str | None = None
    minio_secret_key: str | None = None
    database_password: str | None = None
    database_url: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings object.

    The cache prevents re-reading and reparsing the .env file every time
    another part of the application asks for settings.
    """
    return Settings()