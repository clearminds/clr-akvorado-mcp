"""Akvorado MCP Server — FastMCP tools for network flow analysis via ClickHouse."""

import argparse
import logging
import sys
from typing import Any

from fastmcp import FastMCP

from clr_akvorado_mcp.clickhouse import (
    ClickHouseClient,
    auto_select_table,
    format_ipv4,
)
from clr_akvorado_mcp.config import Settings, configure_logging


def parse_cli_args() -> dict[str, Any]:
    """Parse CLI arguments for configuration overrides."""
    parser = argparse.ArgumentParser(description="Akvorado MCP Server")

    parser.add_argument("--akvorado-ssh-host", type=str, help="SSH host for ClickHouse")
    parser.add_argument("--akvorado-ssh-user", type=str, help="SSH username")
    parser.add_argument("--akvorado-ssh-key", type=str, help="SSH key path")
    parser.add_argument(
        "--akvorado-docker-container", type=str, help="Docker container name"
    )
    parser.add_argument(
        "--akvorado-default-exporter", type=str, help="Default exporter name"
    )
    parser.add_argument(
        "--akvorado-default-limit", type=int, help="Default result limit"
    )
    parser.add_argument(
        "--transport", type=str, choices=["stdio", "http"], help="MCP transport"
    )
    parser.add_argument("--host", type=str, help="HTTP host")
    parser.add_argument("--port", type=int, help="HTTP port")
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Log level",
    )

    args = parser.parse_args()

    overlay: dict[str, Any] = {}
    for key in [
        "akvorado_ssh_host",
        "akvorado_ssh_user",
        "akvorado_ssh_key",
        "akvorado_docker_container",
        "akvorado_default_exporter",
        "akvorado_default_limit",
        "transport",
        "host",
        "port",
        "log_level",
    ]:
        val = getattr(args, key, None)
        if val is not None:
            overlay[key] = val

    return overlay


mcp = FastMCP("Akvorado")
ch: ClickHouseClient | None = None
default_exporter: str = ""
default_limit: int = 20


# ---------------------------------------------------------------------------
# DMCA Investigation
# ---------------------------------------------------------------------------


@mcp.tool
def akvorado_dmca_lookup(
    port: int,
    start_time: str,
    end_time: str,
    exporter: str = "",
    limit: int = 0,
) -> list[dict[str, Any]]:
    """Investigate a DMCA notice by looking up flows matching a source port in a time window.

    Use this for abuse investigations — finds the internal IP that was using a
    specific port during a specific time. If the exporter sees pre-NAT flows,
    SrcAddr shows the internal customer IP.

    Args:
        port: Source port from the DMCA notice.
        start_time: Start of time window (ISO format, e.g. "2026-02-15 14:00:00").
        end_time: End of time window (ISO format, e.g. "2026-02-15 14:30:00").
        exporter: Exporter name (uses AKVORADO_DEFAULT_EXPORTER if not set).
        limit: Max results (default: 20).
    """
    exp = exporter or default_exporter
    lim = limit or default_limit
    table = auto_select_table(start_time, end_time)

    return ch.query_json(f"""
SELECT TimeReceived, SrcAddr, DstAddr, SrcPort, DstPort, Proto, Bytes,
       InIfName, InIfDescription
FROM {table}
WHERE ExporterName = '{exp}'
  AND SrcPort = {port}
  AND TimeReceived >= '{start_time}'
  AND TimeReceived <= '{end_time}'
ORDER BY TimeReceived
LIMIT {lim}
""")


# ---------------------------------------------------------------------------
# Top Bandwidth Users
# ---------------------------------------------------------------------------


@mcp.tool
def akvorado_top_users(
    start_time: str,
    end_time: str,
    exporter: str = "",
    limit: int = 0,
) -> list[dict[str, Any]]:
    """Find top bandwidth users in a time window.

    Returns source IPs sorted by total bytes transferred, with interface info.

    Args:
        start_time: Start of time window (ISO format).
        end_time: End of time window (ISO format).
        exporter: Exporter name (uses AKVORADO_DEFAULT_EXPORTER if not set).
        limit: Max results (default: 20).
    """
    exp = exporter or default_exporter
    lim = limit or default_limit
    table = auto_select_table(start_time, end_time)

    return ch.query_json(f"""
SELECT SrcAddr, InIfName, InIfDescription,
       sum(Bytes) AS total_bytes, count() AS flow_count
FROM {table}
WHERE ExporterName = '{exp}'
  AND TimeReceived >= '{start_time}'
  AND TimeReceived <= '{end_time}'
GROUP BY SrcAddr, InIfName, InIfDescription
ORDER BY total_bytes DESC
LIMIT {lim}
""")


# ---------------------------------------------------------------------------
# Top ASNs
# ---------------------------------------------------------------------------


@mcp.tool
def akvorado_top_asns(
    interval: str = "1 HOUR",
    exporter: str = "",
    limit: int = 0,
) -> list[dict[str, Any]]:
    """Get top Autonomous Systems by traffic volume.

    Args:
        interval: ClickHouse interval (e.g. "1 HOUR", "24 HOUR", "7 DAY").
        exporter: Filter by exporter name (default: all exporters).
        limit: Max results (default: 20).
    """
    lim = limit or default_limit
    exp_filter = f"AND ExporterName = '{exporter}'" if exporter else ""

    return ch.query_json(f"""
SELECT SrcAS, a.name AS asn_name, SrcCountry,
       sum(Bytes) AS total_bytes, count() AS flow_count
FROM flows
LEFT JOIN asns a ON flows.SrcAS = a.asn
WHERE TimeReceived >= now() - INTERVAL {interval}
  {exp_filter}
GROUP BY SrcAS, a.name, SrcCountry
ORDER BY total_bytes DESC
LIMIT {lim}
""")


# ---------------------------------------------------------------------------
# Top Countries
# ---------------------------------------------------------------------------


@mcp.tool
def akvorado_top_countries(
    interval: str = "1 HOUR",
    exporter: str = "",
    limit: int = 0,
) -> list[dict[str, Any]]:
    """Get top source countries by traffic volume.

    Args:
        interval: ClickHouse interval (e.g. "1 HOUR", "24 HOUR").
        exporter: Filter by exporter name (default: all).
        limit: Max results (default: 20).
    """
    lim = limit or default_limit
    exp_filter = f"AND ExporterName = '{exporter}'" if exporter else ""

    return ch.query_json(f"""
SELECT SrcCountry, sum(Bytes) AS total_bytes, count() AS flows
FROM flows
WHERE TimeReceived >= now() - INTERVAL {interval}
  AND SrcCountry <> ''
  {exp_filter}
GROUP BY SrcCountry
ORDER BY total_bytes DESC
LIMIT {lim}
""")


# ---------------------------------------------------------------------------
# Interface Traffic
# ---------------------------------------------------------------------------


@mcp.tool
def akvorado_interface_traffic(
    interval: str = "1 HOUR",
    exporter: str = "",
) -> list[dict[str, Any]]:
    """Get traffic breakdown by network interface.

    Returns all interfaces sorted by total bytes, showing exporter,
    interface name, description, boundary (external/internal), and flow count.

    Args:
        interval: ClickHouse interval (e.g. "1 HOUR", "24 HOUR").
        exporter: Filter by exporter name (default: all).
    """
    exp_filter = f"AND ExporterName = '{exporter}'" if exporter else ""

    return ch.query_json(f"""
SELECT ExporterName, InIfName, InIfDescription, InIfBoundary,
       sum(Bytes) AS total_bytes, count() AS flow_count
FROM flows
WHERE TimeReceived >= now() - INTERVAL {interval}
  {exp_filter}
GROUP BY ExporterName, InIfName, InIfDescription, InIfBoundary
ORDER BY total_bytes DESC
""")


# ---------------------------------------------------------------------------
# BitTorrent / P2P Detection
# ---------------------------------------------------------------------------


@mcp.tool
def akvorado_detect_bittorrent(
    start_time: str,
    end_time: str,
    exporter: str = "",
    min_peers: int = 50,
    limit: int = 0,
) -> list[dict[str, Any]]:
    """Detect BitTorrent/P2P activity by finding IPs with many unique peers.

    High unique_peers (>50 distinct destinations) with many small flows
    indicates P2P activity like BitTorrent.

    Args:
        start_time: Start of time window (ISO format).
        end_time: End of time window (ISO format).
        exporter: Exporter name (uses AKVORADO_DEFAULT_EXPORTER if not set).
        min_peers: Minimum unique peers to flag (default: 50).
        limit: Max results (default: 20).
    """
    exp = exporter or default_exporter
    lim = limit or default_limit
    table = auto_select_table(start_time, end_time)

    return ch.query_json(f"""
SELECT SrcAddr, InIfName, InIfDescription,
       count(DISTINCT DstAddr) AS unique_peers,
       sum(Bytes) AS total_bytes, count() AS flow_count
FROM {table}
WHERE ExporterName = '{exp}'
  AND TimeReceived >= '{start_time}'
  AND TimeReceived <= '{end_time}'
  AND Proto IN (6, 17)
GROUP BY SrcAddr, InIfName, InIfDescription
HAVING unique_peers > {min_peers}
ORDER BY unique_peers DESC
LIMIT {lim}
""")


# ---------------------------------------------------------------------------
# IP Traffic Lookup
# ---------------------------------------------------------------------------


@mcp.tool
def akvorado_ip_traffic(
    ip: str,
    interval: str = "1 HOUR",
    exporter: str = "",
    limit: int = 0,
) -> list[dict[str, Any]]:
    """Get all traffic for a specific IP address (source or destination).

    Automatically handles IPv4-to-IPv6 mapping for ClickHouse.

    Args:
        ip: IP address to look up (IPv4 or IPv6).
        interval: ClickHouse interval (e.g. "1 HOUR", "24 HOUR").
        exporter: Filter by exporter name (default: all).
        limit: Max results (default: 20).
    """
    lim = limit or default_limit
    ip_formatted = format_ipv4(ip)
    exp_filter = f"AND ExporterName = '{exporter}'" if exporter else ""

    return ch.query_json(f"""
SELECT TimeReceived, SrcAddr, DstAddr, SrcPort, DstPort, Proto, Bytes
FROM flows
WHERE (SrcAddr = '{ip_formatted}' OR DstAddr = '{ip_formatted}')
  AND TimeReceived >= now() - INTERVAL {interval}
  {exp_filter}
ORDER BY TimeReceived DESC
LIMIT {lim}
""")


# ---------------------------------------------------------------------------
# IP Summary (aggregated)
# ---------------------------------------------------------------------------


@mcp.tool
def akvorado_ip_summary(
    ip: str,
    interval: str = "1 HOUR",
    exporter: str = "",
) -> dict[str, Any]:
    """Get a traffic summary for an IP: total bytes, flow count, top destinations.

    Args:
        ip: IP address to look up.
        interval: ClickHouse interval (e.g. "1 HOUR", "24 HOUR").
        exporter: Filter by exporter name (default: all).
    """
    ip_formatted = format_ipv4(ip)
    exp_filter = f"AND ExporterName = '{exporter}'" if exporter else ""

    totals = ch.query_json(f"""
SELECT sum(Bytes) AS total_bytes, count() AS flow_count,
       min(TimeReceived) AS first_seen, max(TimeReceived) AS last_seen
FROM flows
WHERE (SrcAddr = '{ip_formatted}' OR DstAddr = '{ip_formatted}')
  AND TimeReceived >= now() - INTERVAL {interval}
  {exp_filter}
""")

    top_dst = ch.query_json(f"""
SELECT DstAddr, sum(Bytes) AS bytes, count() AS flows
FROM flows
WHERE SrcAddr = '{ip_formatted}'
  AND TimeReceived >= now() - INTERVAL {interval}
  {exp_filter}
GROUP BY DstAddr
ORDER BY bytes DESC
LIMIT 10
""")

    return {
        "ip": ip,
        "interval": interval,
        "totals": totals[0] if totals else {},
        "top_destinations": top_dst,
    }


# ---------------------------------------------------------------------------
# Raw Query
# ---------------------------------------------------------------------------


@mcp.tool
def akvorado_raw_query(sql: str) -> str:
    """Execute a raw ClickHouse SQL query against Akvorado flow data.

    The ClickHouse user has read-only access. Use this for custom queries
    not covered by the other tools.

    Key tables: flows, flows_1m0s, flows_5m0s, flows_1h0m0s
    Lookup tables: asns (asn, name), protocols (proto, name), exporters (ip, name)

    IPv4 addresses are stored as IPv6-mapped: use ::ffff:1.2.3.4 format.

    Args:
        sql: Full ClickHouse SQL query. Append FORMAT if desired
             (default: Pretty for text, or use FORMAT JSONEachRow for JSON).

    Returns the raw query output as text.
    """
    return ch.query(sql)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Main entry point for the Akvorado MCP server."""
    global ch, default_exporter, default_limit

    cli_overlay = parse_cli_args()

    try:
        settings = Settings(**cli_overlay)
    except Exception as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)

    creds = settings.load_credentials()

    logger.info("Starting Akvorado MCP Server")
    logger.info(
        "Config: ssh=%s@%s container=%s transport=%s",
        creds.get("ssh_user", ""),
        creds.get("ssh_host", ""),
        creds.get("docker_container", ""),
        settings.transport,
    )

    default_exporter = settings.akvorado_default_exporter
    default_limit = settings.akvorado_default_limit

    ch = ClickHouseClient(
        ssh_host=creds.get("ssh_host", ""),
        ssh_user=creds.get("ssh_user", ""),
        ssh_key=creds.get("ssh_key", "~/.ssh/id_ed25519"),
        docker_container=creds.get("docker_container", "akvorado-clickhouse-1"),
    )

    try:
        if settings.transport == "stdio":
            logger.info("Starting stdio transport")
            mcp.run(transport="stdio")
        elif settings.transport == "http":
            logger.info(
                "Starting HTTP transport on %s:%s", settings.host, settings.port
            )
            mcp.run(transport="http", host=settings.host, port=settings.port)
    except Exception as e:
        logger.error("Failed to start MCP server: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
