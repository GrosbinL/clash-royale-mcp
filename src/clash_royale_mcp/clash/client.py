"""Async HTTP client for the Supercell Clash Royale API.

Wraps httpx with everything specific to Supercell: base URL, auth header,
player/clan tag normalization, and mapping HTTP errors to typed exceptions.
The rest of the codebase talks to Supercell exclusively through this class.
"""

from typing import Any
from urllib.parse import quote

import httpx

from clash_royale_mcp.clash.models import Battle, Player
from clash_royale_mcp.config import settings
from clash_royale_mcp.tags import canonical_tag


class ClashAPIError(Exception):
    """Base class for all Supercell API errors we raise."""


class PlayerNotFound(ClashAPIError):
    """The requested player tag doesn't exist (HTTP 404)."""


class RateLimited(ClashAPIError):
    """We've been rate-limited by Supercell (HTTP 429)."""


class AuthError(ClashAPIError):
    """Our API token is missing, invalid, or the IP isn't whitelisted (HTTP 401/403)."""


class ServerError(ClashAPIError):
    """Supercell returned a 5xx — their problem, not ours."""


def normalize_tag(tag: str) -> str:
    """Canonicalize a tag and percent-encode it for a URL path ('#' -> '%23')."""
    return quote(canonical_tag(tag), safe="")


class ClashClient:
    """Async client for the Supercell Clash Royale API.
    """

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(
            base_url=settings.clash_royale_api_base_url,
            headers={
                "Authorization": f"Bearer {settings.clash_royale_api_token}",
                "Accept": "application/json",
            },
            timeout=httpx.Timeout(10.0, connect=5.0),
        )

    async def __aenter__(self) -> "ClashClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._http.aclose()

    async def _get(self, path: str) -> dict[str, Any]:
        """Send a GET request and return the parsed JSON body.

        Maps HTTP error responses to our typed exception hierarchy so
        callers work with meaningful errors, not raw HTTP status codes.
        """
        response = await self._http.get(path)

        if response.status_code == 200:
            return response.json()
        if response.status_code == 404:
            raise PlayerNotFound(f"Not found: {path}")
        if response.status_code in (401, 403):
            raise AuthError(
                f"Auth failed ({response.status_code}). Check API token and IP whitelist."
            )
        if response.status_code == 429:
            raise RateLimited("Rate limited by Supercell — back off and retry.")
        if 500 <= response.status_code < 600:
            raise ServerError(f"Supercell server error: {response.status_code}")
        raise ClashAPIError(
            f"Unexpected status {response.status_code}: {response.text[:200]}"
        )

    async def get_player(self, tag: str) -> Player:
        """Fetch a player profile by tag."""
        data = await self._get(f"/players/{normalize_tag(tag)}")
        return Player.model_validate(data)

    async def get_battle_log(self, tag: str) -> list[Battle]:
        """Fetch a player's recent battles (Supercell returns up to 25)."""
        data = await self._get(f"/players/{normalize_tag(tag)}/battlelog")
        return [Battle.model_validate(item) for item in data]