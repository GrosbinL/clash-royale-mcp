"""Application configuration loaded from environment variables."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed configuration for the Clash Royale MCP server.

    Values are loaded from a .env file at the project root, or from
    real environment variables (which override .env if both are set).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    clash_royale_api_token: str = Field(
        ...,
        description="Supercell developer API token",
    )

    cache_db_path: Path = Field(
        default=Path("./cache.db"),
        description="Filesystem path to the SQLite cache database",
    )

    clash_royale_api_base_url: str = Field(
        default="https://api.clashroyale.com/v1",
        description="Base URL for the Supercell API",
    )


settings = Settings()  # type: ignore[call-arg]