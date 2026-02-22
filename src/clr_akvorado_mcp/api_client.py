"""HTTP client for the Akvorado Console API."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class AkvoradoAPIClient:
    """Akvorado Console API client with HTTP Basic auth.

    Wraps the ``/api/v0/console`` endpoints for graph queries, widgets,
    filters, and configuration.

    Attributes:
        base_url: Base URL of the Akvorado instance (trailing slash stripped).
    """

    def __init__(self, base_url: str, username: str, password: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(
            base_url=self.base_url,
            auth=(username, password),
            timeout=60.0,
            headers={"Accept": "application/json"},
        )

        # Verify connectivity
        resp = self._http.get("/api/v0/console/configuration")
        resp.raise_for_status()
        logger.info("Connected to Akvorado at %s", self.base_url)

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._http.close()

    def get(self, path: str, params: dict[str, str] | None = None) -> Any:
        """Send a GET request and return parsed JSON.

        Args:
            path: API path (e.g. ``"/api/v0/console/widget/exporters"``).
            params: Optional query parameters.

        Returns:
            Parsed JSON response body.

        Raises:
            httpx.HTTPStatusError: On non-2xx response.
        """
        resp = self._http.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    def post(self, path: str, json: dict[str, Any] | None = None) -> Any:
        """Send a POST request and return parsed JSON.

        Args:
            path: API path (e.g. ``"/api/v0/console/graph/line"``).
            json: JSON-serializable request body.

        Returns:
            Parsed JSON response body.

        Raises:
            httpx.HTTPStatusError: On non-2xx response.
        """
        resp = self._http.post(path, json=json or {})
        resp.raise_for_status()
        return resp.json()
