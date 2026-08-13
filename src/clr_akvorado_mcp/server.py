"""Akvorado MCP Server — FastMCP tools for network flow analysis via the Akvorado Console API."""

import argparse
import logging
import re
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from fastmcp import FastMCP

from clr_akvorado_mcp.api_client import AkvoradoAPIClient
from clr_akvorado_mcp.config import Settings, configure_logging
from clr_akvorado_mcp.middleware import ToolValidationMiddleware


def parse_cli_args() -> tuple[dict[str, Any], bool | None]:
    """Parse CLI arguments for configuration overrides.

    Returns:
        A tuple of (overlay dict, read_only flag).
    """
    parser = argparse.ArgumentParser(description="Akvorado MCP Server")

    parser.add_argument("--akvorado-api-url", type=str, help="Akvorado Console API URL")
    parser.add_argument("--akvorado-api-user", type=str, help="API username")
    parser.add_argument("--akvorado-api-password", type=str, help="API password")
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
    parser.add_argument(
        "--read-only",
        action="store_true",
        default=None,
        help="Run in read-only mode (hide write tools)",
    )

    args = parser.parse_args()

    overlay: dict[str, Any] = {}
    for key in [
        "akvorado_api_url",
        "akvorado_api_user",
        "akvorado_api_password",
        "transport",
        "host",
        "port",
        "log_level",
    ]:
        val = getattr(args, key, None)
        if val is not None:
            overlay[key] = val

    return overlay, args.read_only


mcp = FastMCP("Akvorado")
mcp.add_middleware(ToolValidationMiddleware())
api: AkvoradoAPIClient | None = None

# Imported here (not at the top) on purpose: annotations.py needs ``mcp`` from
# this module, so importing it before the ``mcp = FastMCP(...)`` line above
# would be a circular import. Do not move.
from clr_akvorado_mcp.annotations import read_tool, remove_non_read_tools  # noqa: E402


_REL_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
_REL_WORDS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400, "week": 604800}


def _resolve_time(value: str) -> str:
    """Resolve a relative time expression to an absolute UTC ISO-8601 string.

    The Akvorado console API only accepts absolute timestamps, but these tools
    advertise relative inputs. Handles absolute ISO (passed through), ``now``,
    Grafana-style ``now-1d`` / ``now-6h`` / ``now-30m``, and human ``6 hours ago``.
    """
    low = value.strip().lower()
    now = datetime.now(timezone.utc)
    if low == "now":
        delta = 0
    elif (m := re.fullmatch(r"now\s*-\s*(\d+)\s*([smhdw])", low)) is not None:
        delta = int(m.group(1)) * _REL_UNITS[m.group(2)]
    elif (m := re.fullmatch(r"(\d+)\s*(second|minute|hour|day|week)s?\s+ago", low)) is not None:
        delta = int(m.group(1)) * _REL_WORDS[m.group(2)]
    else:
        return value.strip()  # assume it is already an absolute timestamp
    return (now - timedelta(seconds=delta)).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Time-series graph
# ---------------------------------------------------------------------------


@read_tool
def akvorado_graph(
    dimensions: list[str],
    start: str,
    end: str,
    filter: str = "",
    units: str = "l3bps",
    limit: int = 10,
    bidirectional: bool = False,
    points: int = 100,
) -> dict[str, Any]:
    """Query Akvorado for time-series traffic data (line graph).

    Returns time-series rows with dimension labels, averages, 95th percentile,
    min, and max values. Uses the Akvorado filter language for filtering.

    Args:
        dimensions: Group-by dimensions (e.g. ["SrcAS"], ["SrcAS", "ExporterName"]).
            Valid: SrcAddr, DstAddr, SrcAS, DstAS, SrcCountry, DstCountry,
            SrcPort, DstPort, ExporterName, InIfName, OutIfName, EType, Proto,
            InIfBoundary, OutIfBoundary, InIfProvider, OutIfProvider.
        start: Start time (e.g. "2026-02-15T00:00:00Z", "6 hours ago", "now-1d").
        end: End time (e.g. "now", "2026-02-15T06:00:00Z").
        filter: Akvorado filter expression (e.g. "InIfBoundary = external",
            "SrcAS = 13335 AND DstPort = 443"). Empty string means no filter.
        units: Traffic unit — "l3bps" (L3 bits/s), "l2bps" (L2 bits/s),
            "pps" (packets/s), "inl2%" (inbound L2 %), "outl2%" (outbound L2 %).
        limit: Max number of dimension groups to return (default 10).
        bidirectional: If true, show both directions separately.
        points: Number of time buckets in the series (graph resolution, default 100).

    Returns:
        Graph data with time points, rows (dimension labels), and statistics.
    """
    # The console's graph/line endpoint requires points, limitType, previousPeriod
    # and filter to always be present — omitting any of them returns HTTP 400.
    payload: dict[str, Any] = {
        "start": _resolve_time(start),
        "end": _resolve_time(end),
        "points": points,
        "dimensions": dimensions,
        "limit": limit,
        "limitType": "avg",
        "units": units,
        "bidirectional": bidirectional,
        "previousPeriod": False,
        "filter": filter,
    }
    return api.post("/api/v0/console/graph/line", json=payload)


# ---------------------------------------------------------------------------
# Sankey diagram
# ---------------------------------------------------------------------------


@read_tool
def akvorado_sankey(
    dimensions: list[str],
    start: str,
    end: str,
    filter: str = "",
    units: str = "l3bps",
    limit: int = 10,
) -> dict[str, Any]:
    """Query Akvorado for Sankey flow diagram data.

    Requires 2 or more dimensions to show traffic flow between them
    (e.g. SrcAS -> DstAS, SrcCountry -> DstCountry -> DstPort).

    Args:
        dimensions: Group-by dimensions (must be 2+, e.g. ["SrcAS", "DstAS"]).
        start: Start time (e.g. "6 hours ago").
        end: End time (e.g. "now").
        filter: Akvorado filter expression. Empty string means no filter.
        units: Traffic unit — "l3bps", "l2bps", "pps", "inl2%", "outl2%".
        limit: Max number of flows to return (default 10).

    Returns:
        Sankey data with nodes and links for flow visualization.
    """
    payload: dict[str, Any] = {
        "start": start,
        "end": end,
        "dimensions": dimensions,
        "limit": limit,
        "units": units,
    }
    if filter:
        payload["filter"] = filter
    return api.post("/api/v0/console/graph/sankey", json=payload)


# ---------------------------------------------------------------------------
# Top-N widget
# ---------------------------------------------------------------------------


@read_tool
def akvorado_top(
    dimension: str,
) -> list[dict[str, Any]]:
    """Get top-5 by a single dimension from the Akvorado dashboard widget.

    Quick summary — does not require time range. Shows the current top talkers.

    Args:
        dimension: Dimension to rank by. Valid values: "src-as", "dst-as",
            "src-country", "dst-country", "src-port", "dst-port", "exporter",
            "etype", "protocol".

    Returns:
        A list of top entries with name and percentage.
    """
    return api.get(f"/api/v0/console/widget/top/{dimension}")


# ---------------------------------------------------------------------------
# Exporters
# ---------------------------------------------------------------------------


@read_tool
def akvorado_exporters() -> list[dict[str, Any]]:
    """List all flow exporters known to Akvorado.

    Returns:
        A list of exporter objects with name and IP information.
    """
    return api.get("/api/v0/console/widget/exporters")


# ---------------------------------------------------------------------------
# Status (dashboard overview)
# ---------------------------------------------------------------------------


@read_tool
def akvorado_status() -> dict[str, Any]:
    """Get Akvorado dashboard status: flow rate, last flow, and exporters.

    Combines multiple widget endpoints into a single overview.

    Returns:
        A dict with flow_rate, last_flow, and exporters.
    """
    flow_rate = api.get("/api/v0/console/widget/flow-rate")
    flow_last = api.get("/api/v0/console/widget/flow-last")
    exporters = api.get("/api/v0/console/widget/exporters")
    return {
        "flow_rate": flow_rate,
        "last_flow": flow_last,
        "exporters": exporters,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Main entry point for the Akvorado MCP server."""
    global api

    cli_overlay, cli_read_only = parse_cli_args()

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
        "Config: api_url=%s user=%s transport=%s",
        creds.get("api_url", ""),
        creds.get("api_user", ""),
        settings.transport,
    )

    if creds.get("api_url") and creds.get("api_user"):
        api = AkvoradoAPIClient(
            base_url=creds["api_url"],
            username=creds["api_user"],
            password=creds.get("api_password", ""),
        )
    else:
        logger.error(
            "Akvorado API credentials required. Set AKVORADO_API_URL, "
            "AKVORADO_API_USER, AKVORADO_API_PASSWORD or configure %s",
            "~/.config/akvorado/credentials.json",
        )
        sys.exit(1)

    read_only = cli_read_only if cli_read_only is not None else settings.akvorado_read_only
    if read_only:
        removed = remove_non_read_tools(mcp)
        logger.info("Read-only mode: %d non-read tools removed", removed)

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
