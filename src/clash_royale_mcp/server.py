"""MCP server entrypoint. Registers get_player/get_battle_log as tools,
opens the cache and API client once at startup, reuses them for every call.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server import MCPServer
from mcp.server.mcpserver import Context

from clash_royale_mcp.cache.store import CacheStore
from clash_royale_mcp.clash.client import (
    AuthError,
    ClashAPIError,
    ClashClient,
    PlayerNotFound,
    RateLimited,
)
from clash_royale_mcp.tools.fetch import fetch_battle_log, fetch_player


@dataclass
class AppContext:
    """Resources shared across every tool call for the process's lifetime."""
    cache: CacheStore
    client: ClashClient


@asynccontextmanager
async def lifespan(server: MCPServer) -> AsyncGenerator[AppContext, None]:
    """Open the cache and API client at startup, close them at shutdown."""
    async with CacheStore() as cache, ClashClient() as client:
        yield AppContext(cache=cache, client=client)


mcp = MCPServer("clash-royale-mcp", lifespan=lifespan)


@mcp.tool()
async def get_player(tag: str, ctx: Context) -> str:
    """Fetch a Clash Royale player's profile by tag. Returns a summary with
    level, arena, trophies, win/loss record, and clan."""
    app: AppContext = ctx.request_context.lifespan_context

    try:
        player = await fetch_player(tag, app.cache, app.client)
    except PlayerNotFound:
        return (
            f"No player found with tag {tag!r}. Double-check the tag — "
            "Clash Royale tags are case-sensitive and easy to mistype "
            "('O' vs '0', 'I' vs 'l' vs '1')."
        )
    except AuthError as e:
        return f"Auth error contacting Supercell: {e}"
    except RateLimited:
        return "Rate limited by Supercell. Please try again in a moment."
    except ClashAPIError as e:
        return f"Supercell API error: {e}"

    clan_line = (
        f"Clan: {player.clan.name} ({player.clan.tag})"
        if player.clan else "Clan: none"
    )

    return (
        f"**{player.name}** ({player.tag})\n"
        f"Level {player.exp_level} — {player.arena.name}\n"
        f"Trophies: {player.trophies} (best: {player.best_trophies})\n"
        f"Record: {player.wins}W / {player.losses}L "
        f"across {player.battle_count} battles\n"
        f"Three-crown wins: {player.three_crown_wins}\n"
        f"{clan_line}"
    )


@mcp.tool()
async def get_battle_log(tag: str, ctx: Context) -> str:
    """Fetch a Clash Royale player's recent battle log by tag. Supercell caps
    this at 25 battles. Returns each battle with mode, arena, result, and
    opponent."""
    app: AppContext = ctx.request_context.lifespan_context

    try:
        battles = await fetch_battle_log(tag, app.cache, app.client)
    except PlayerNotFound:
        return f"No player found with tag {tag!r}."
    except AuthError as e:
        return f"Auth error contacting Supercell: {e}"
    except RateLimited:
        return "Rate limited by Supercell. Please try again in a moment."
    except ClashAPIError as e:
        return f"Supercell API error: {e}"

    if not battles:
        return f"No recent battles for {tag}."

    lines = [f"Recent battles for {tag} ({len(battles)} total):", ""]
    for i, battle in enumerate(battles, start=1):
        me = battle.team[0]
        opp = battle.opponent[0]

        if me.crowns > opp.crowns:
            result = "WIN"
        elif me.crowns < opp.crowns:
            result = "LOSS"
        else:
            result = "DRAW"

        lines.append(
            f"{i}. {battle.game_mode.name} in {battle.arena.name} — {result} "
            f"({me.crowns}-{opp.crowns} vs {opp.name})"
        )

    return "\n".join(lines)


def main() -> None:
    """Entry point invoked by Claude Desktop."""
    try:
        mcp.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()