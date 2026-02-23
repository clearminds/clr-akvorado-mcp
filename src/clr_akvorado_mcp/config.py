"""Configuration management for Akvorado MCP Server."""

import json
import logging
import logging.config
from pathlib import Path
from typing import Any, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

CREDS_PATH = Path.home() / ".config" / "akvorado" / "credentials.json"


class Settings(BaseSettings):
    """Centralized configuration for Akvorado MCP Server.

    Configuration precedence: CLI > credentials.json > Environment > .env file > Defaults

    Priority order for credentials:
    1. ~/.config/akvorado/credentials.json
    2. Environment variables (AKVORADO_API_URL, AKVORADO_API_USER, AKVORADO_API_PASSWORD) - override
    """

    # HTTP Console API
    akvorado_api_url: str = ""
    akvorado_api_user: str = ""
    akvorado_api_password: str = ""

    # Default query settings
    akvorado_read_only: bool = False

    @field_validator("akvorado_read_only", mode="before")
    @classmethod
    def _empty_str_to_false(cls, v: Any) -> Any:
        if v == "":
            return False
        return v

    transport: Literal["stdio", "http"] = "stdio"
    host: str = "127.0.0.1"
    port: int = 8000

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    def load_credentials(self) -> dict[str, Any]:
        """Load credentials with config-file-first, env-override pattern.

        Returns:
            Dict with api_url, api_user, api_password.
        """
        creds: dict[str, Any] = {}

        # 1. FIRST: Load from environment variables (base/fallback)
        if self.akvorado_api_url:
            creds["api_url"] = self.akvorado_api_url
        if self.akvorado_api_user:
            creds["api_user"] = self.akvorado_api_user
        if self.akvorado_api_password:
            creds["api_password"] = self.akvorado_api_password

        # 2. THEN: Override with credentials.json file (takes priority)
        if CREDS_PATH.exists():
            try:
                file_creds: dict[str, Any] = json.loads(CREDS_PATH.read_text())

                if "api_url" in file_creds:
                    creds["api_url"] = file_creds["api_url"]
                if "api_user" in file_creds:
                    creds["api_user"] = file_creds["api_user"]
                if "api_password" in file_creds:
                    creds["api_password"] = file_creds["api_password"]

                logger.info("Loaded Akvorado credentials from %s", CREDS_PATH)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Failed to load %s: %s", CREDS_PATH, e)

        if not (creds.get("api_url") and creds.get("api_user")):
            logger.warning(
                "No Akvorado API credentials configured. Set AKVORADO_API_URL/AKVORADO_API_USER "
                "env vars or create %s",
                CREDS_PATH,
            )

        return creds


def configure_logging(
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
) -> None:
    """Configure structured logging with console output to stderr.

    Args:
        log_level: The minimum severity level for log messages.
    """
    config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "console": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console",
                "stream": "ext://sys.stderr",
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console"],
        },
    }
    logging.config.dictConfig(config)
