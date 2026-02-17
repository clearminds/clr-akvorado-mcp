"""Configuration management for Akvorado MCP Server."""

import logging
import logging.config
from typing import Any, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized configuration for Akvorado MCP Server.

    Configuration precedence: CLI > Environment > .env file > Defaults
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
