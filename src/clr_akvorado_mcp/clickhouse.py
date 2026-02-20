"""ClickHouse query client via SSH to Akvorado's Docker container."""

import json
import logging
import os
import subprocess
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class ClickHouseClient:
    """Execute read-only ClickHouse queries via SSH."""

    def __init__(
        self,
        ssh_host: str,
        ssh_user: str,
        ssh_key: str,
        docker_container: str,
    ) -> None:
        self.ssh_host = ssh_host
        self.ssh_user = ssh_user
        self.ssh_key = os.path.expanduser(ssh_key)
        self.docker_container = docker_container

    def query(self, sql: str) -> str:
        """Execute a ClickHouse query and return raw text output.

        Args:
            sql: The SQL query string to execute.

        Returns:
            The trimmed stdout from the ClickHouse client.

        Raises:
            RuntimeError: If the query exits with a non-zero return code.
        """
        logger.debug("Executing query: %s", sql[:200])
        result = subprocess.run(
            [
                "ssh",
                "-o",
                "ConnectTimeout=15",
                "-o",
                "StrictHostKeyChecking=accept-new",
                "-i",
                self.ssh_key,
                f"{self.ssh_user}@{self.ssh_host}",
                f"sudo docker exec -i {self.docker_container} clickhouse-client",
            ],
            input=sql,
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Filter out harmless chdir warning
        stderr = "\n".join(
            line for line in result.stderr.splitlines() if "Could not chdir" not in line
        ).strip()

        if result.returncode != 0 and stderr:
            raise RuntimeError(f"ClickHouse query failed: {stderr}")

        return result.stdout.strip()

    def query_json(self, sql: str) -> list[dict[str, Any]]:
        """Execute a query and return parsed JSON rows.

        Appends FORMAT JSONEachRow if no FORMAT clause present.

        Args:
            sql: The SQL query string to execute.

        Returns:
            A list of dictionaries, one per result row.
        """
        if "FORMAT" not in sql.upper():
            sql = sql.rstrip().rstrip(";") + "\nFORMAT JSONEachRow"

        raw = self.query(sql)
        if not raw:
            return []

        rows = []
        for line in raw.splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        return rows


def auto_select_table(start: str, end: str) -> str:
    """Select the best ClickHouse table based on time range.

    - <= 7 days: flows (raw)
    - 7-90 days: flows_5m0s
    - > 90 days: flows_1h0m0s

    Args:
        start: Start timestamp in ISO format.
        end: End timestamp in ISO format.

    Returns:
        The ClickHouse table name appropriate for the time span.
    """
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
        days = (end_dt - start_dt).days
        if days > 90:
            return "flows_1h0m0s"
        elif days > 7:
            return "flows_5m0s"
    except (ValueError, TypeError):
        pass
    return "flows"


def format_ipv4(ip: str) -> str:
    """Convert IPv4 address to ClickHouse IPv4-mapped IPv6 format.

    Args:
        ip: An IPv4 or IPv6 address string.

    Returns:
        The address in ``::ffff:x.x.x.x`` format, or unchanged if already IPv6.
    """
    if ":" in ip:
        return ip  # Already IPv6
    return f"::ffff:{ip}"
