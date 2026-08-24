"""Cached fetch tools that back the MCP tool handlers.

Each function does a two-tier lookup: check the SQLite cache first, and
only call Supercell on a miss. Fresh API responses get written back into
the cache so reads (within the TTL) are free.

The cache and client are passed in as arguments rather than constructed
here, the MCP server owns their lifetime, opening them once at startup
and reusing them across every tool call.
"""

from clash_royale_mcp.cache.store import CacheStore
from clash_royale_mcp.clash.client import ClashClient
from clash_royale_mcp.tags import canonical_tag
from clash_royale_mcp.clash.models import Battle, Player


# Cache lifetimes, in seconds. These are the freshness
# guarantees the MCP tools promise their callers — tweak here, not in
# individual tool functions.

PLAYER_TTL = 300      # 5 minutes  — trophies, level, clan change slowly
BATTLE_LOG_TTL = 90   # 1.5 minutes — new matches finish every few min


async def fetch_player(tag: str, cache: CacheStore, client: ClashClient,) -> Player:
    """Fetch a player profile, using the cache to respect rate limits."""
    key = canonical_tag(tag)

    cached = await cache.get("player", key, ttl_seconds=PLAYER_TTL)
    if cached is not None:
        return Player.model_validate(cached)

    fresh = await client.get_player(tag)
    await cache.set("player", key, fresh.model_dump(mode="json", by_alias=True))
    return fresh


async def fetch_battle_log(tag: str, cache: CacheStore, client: ClashClient,) -> list[Battle]:
    """Fetch a player's recent battle log, using the cache to respect rate limits.

    Battle logs are stored as a list wrapped in a dict, since the cache
    only stores dict payloads. On read, we unwrap; on write, we wrap.
    """
    key = canonical_tag(tag)

    cached = await cache.get("battle_log", key, ttl_seconds=BATTLE_LOG_TTL)
    if cached is not None:
        return [Battle.model_validate(b) for b in cached["battles"]]

    fresh = await client.get_battle_log(tag)
    payload = {"battles": [b.model_dump(mode="json", by_alias=True) for b in fresh]}
    await cache.set("battle_log", key, payload)
    return fresh