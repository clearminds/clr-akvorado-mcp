"""Configuration management for Akvorado MCP Server."""

import json
import logging
import logging.config
from pathlib import Path
from typing import Any, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

CREDS_PATH = Path.home() / ".config" / "akvorado" / "credentials.json"


class Settings(BaseSettings):
    """Centralized configuration for Akvorado MCP Server.

    Configuration precedence: CLI > Environment > credentials.json > .env file > Defaults

    Priority order for credentials:
    1. Environment variables (AKVORADO_SSH_HOST, AKVORADO_SSH_USER, AKVORADO_SSH_KEY)
    2. ~/.config/akvorado/credentials.json
    """

    # SSH access to ClickHouse
    akvorado_ssh_host: str = ""
    akvorado_ssh_user: str = ""
    akvorado_ssh_key: str = "~/.ssh/id_ed25519"
    akvorado_docker_container: str = "akvorado-clickhouse-1"

    # Default query settings
    akvorado_default_exporter: str = ""
    akvorado_default_limit: int = 20

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
        """Load credentials with env-first, config-file-fallback pattern.

        Returns:
            Dict with ssh_host, ssh_user, ssh_key, and optional docker_container.
        """
        creds: dict[str, Any] = {}

        # 1. FIRST: Check environment variables
        if self.akvorado_ssh_host:
            creds["ssh_host"] = self.akvorado_ssh_host
        if self.akvorado_ssh_user:
            creds["ssh_user"] = self.akvorado_ssh_user
        if self.akvorado_ssh_key:
            creds["ssh_key"] = self.akvorado_ssh_key
        if self.akvorado_docker_container:
            creds["docker_container"] = self.akvorado_docker_container

        # If we have all required creds from env, return early
        if creds.get("ssh_host") and creds.get("ssh_user"):
            logger.info("Using Akvorado credentials from environment variables")
            return creds

        # 2. FALLBACK: Check credentials.json file
        if CREDS_PATH.exists():
            try:
                file_creds: dict[str, Any] = json.loads(CREDS_PATH.read_text())

                # Only use file values if NOT already set by env vars
                if "ssh_host" in file_creds and not creds.get("ssh_host"):
                    creds["ssh_host"] = file_creds["ssh_host"]
                if "ssh_user" in file_creds and not creds.get("ssh_user"):
                    creds["ssh_user"] = file_creds["ssh_user"]
                if "ssh_key" in file_creds and not creds.get("ssh_key"):
                    creds["ssh_key"] = file_creds["ssh_key"]
                if "docker_container" in file_creds and not creds.get("docker_container"):
                    creds["docker_container"] = file_creds["docker_container"]

                logger.info(f"Loaded Akvorado credentials from {CREDS_PATH}")
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load {CREDS_PATH}: {e}")

        # Set defaults
        if not creds.get("ssh_key"):
            creds["ssh_key"] = "~/.ssh/id_ed25519"
        if not creds.get("docker_container"):
            creds["docker_container"] = "akvorado-clickhouse-1"

        if not (creds.get("ssh_host") and creds.get("ssh_user")):
            logger.warning(
                "No Akvorado credentials configured. Set AKVORADO_SSH_HOST/AKVORADO_SSH_USER "
                f"env vars or create {CREDS_PATH}"
            )

        return creds


def configure_logging(
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
) -> None:
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
