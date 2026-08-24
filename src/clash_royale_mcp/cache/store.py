"""SQLite-backed cache for Supercell API responses.

Stores raw JSON payloads keyed by resource type and identifier.
"""

import json
import time
from pathlib import Path
from typing import Any

import aiosqlite

from clash_royale_mcp.config import settings


# Resolve schema.sql relative to this file so the path is stable
# regardless of the working directory when the server is launched.
_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class CacheStore:
    """Async SQLite cache with per-call TTL freshness checks.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or settings.cache_db_path
        self._db: aiosqlite.Connection | None = None

    async def __aenter__(self) -> "CacheStore":
        self._db = await aiosqlite.connect(self._db_path)
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._apply_schema()
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None

    async def _apply_schema(self) -> None:
        """Create tables and indexes if they don't already exist."""
        assert self._db is not None
        schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
        await self._db.executescript(schema_sql)
        await self._db.commit()

    async def get(self, resource_type: str, resource_key: str, ttl_seconds: float, ) -> dict[str, Any] | None:
        """Return the cached payload if it's newer than ttl_seconds, else None."""
        assert self._db is not None
        cursor = await self._db.execute(
            "SELECT fetched_at, payload FROM cache_entries "
            "WHERE resource_type = ? AND resource_key = ?",
            (resource_type, resource_key),
        )
        row = await cursor.fetchone()
        await cursor.close()

        if row is None:
            return None

        fetched_at, payload = row
        age = time.time() - fetched_at
        if age >= ttl_seconds:
            return None  # Stale — treat as miss

        return json.loads(payload)

    async def set(self, resource_type: str, resource_key: str, payload: dict[str, Any],) -> None:
        """Store a payload, overwriting any existing entry for the same key."""
        assert self._db is not None
        await self._db.execute(
            "INSERT OR REPLACE INTO cache_entries "
            "(resource_type, resource_key, fetched_at, payload) "
            "VALUES (?, ?, ?, ?)",
            (resource_type, resource_key, time.time(), json.dumps(payload)),
        )
        await self._db.commit()

    async def invalidate(self, resource_type: str, resource_key: str) -> None:
        """Delete a specific cache entry and forces a refetch on next get."""
        assert self._db is not None
        await self._db.execute(
            "DELETE FROM cache_entries "
            "WHERE resource_type = ? AND resource_key = ?",
            (resource_type, resource_key),
        )
        await self._db.commit()