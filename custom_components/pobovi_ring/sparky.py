"""SparkyFitness client for pushing ring data."""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession

from .const import SPARKY_ENDPOINT_PATH

_LOGGER = logging.getLogger(__name__)


class SparkyError(Exception):
    """Raised when SparkyFitness rejects or cannot accept the data."""


class SparkyClient:
    """Minimal client for the SparkyFitness health-data endpoint."""

    def __init__(self, session: ClientSession, base_url: str, api_key: str) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    @property
    def endpoint(self) -> str:
        """Return the full ingest URL."""
        if self._base_url.endswith(SPARKY_ENDPOINT_PATH):
            return self._base_url
        return f"{self._base_url}{SPARKY_ENDPOINT_PATH}"

    async def async_get(self, path: str) -> Any:
        """GET a SparkyFitness endpoint with the configured key."""
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            async with self._session.get(
                f"{self._base_url}{path}", headers=headers, timeout=20
            ) as response:
                if response.status != 200:
                    return None
                return await response.json()
        except (ClientError, TimeoutError, ValueError):
            return None

    async def async_push_payloads(self, payloads: list[dict[str, Any]]) -> dict[str, Any]:
        """Push already-built health-data payloads and return the response."""
        if not payloads:
            return {}
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with self._session.post(
                self.endpoint, json=payloads, headers=headers, timeout=30
            ) as response:
                if response.status == 401:
                    raise SparkyError("SparkyFitness rejected the API key (401)")
                if response.status >= 400:
                    text = await response.text()
                    raise SparkyError(f"SparkyFitness returned {response.status}: {text[:200]}")
                try:
                    return await response.json()
                except (ValueError, ClientError):
                    return {}
        except ClientResponseError as err:
            raise SparkyError(str(err)) from err
        except ClientError as err:
            raise SparkyError(f"Could not reach SparkyFitness: {err}") from err
        except TimeoutError as err:
            raise SparkyError(f"SparkyFitness timed out: {err}") from err
