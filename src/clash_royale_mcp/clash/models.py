"""Pydantic models mirroring Supercell Clash Royale API response shapes.

These models capture only the fields our tools currently need. Unknown
fields in responses are silently ignored via `extra="ignore"` — extend
the models when a new tool needs a new field.

JSON payloads from Supercell use camelCase; our Python fields use
snake_case. `alias_generator=to_camel` handles the translation
automatically, and `populate_by_name=True` also lets us construct
models directly using the Python names.
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CRBaseModel(BaseModel):
    """Base class for all Clash Royale API models.

    Every model inherits camelCase-to-snake_case alias generation and
    `extra="ignore"` so Supercell adding new fields never breaks us.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


class Arena(CRBaseModel):
    id: int
    name: str


class IconUrls(CRBaseModel):
    medium: str | None = None


class Card(CRBaseModel):
    """A single card — appears in player collections and in battle decks."""

    id: int
    name: str
    level: int
    max_level: int | None = None
    star_level: int | None = None
    count: int | None = None
    elixir_cost: int | None = None
    icon_urls: IconUrls | None = None


class ClanRef(CRBaseModel):
    """Minimal clan info as embedded in a Player response.

    The `/clans/{tag}` endpoint returns a fuller Clan object with
    members and score — we'll add that as its own model when we need it.
    """

    tag: str
    name: str
    badge_id: int


class Player(CRBaseModel):
    """A Clash Royale player profile from GET /players/{tag}."""

    tag: str
    name: str
    exp_level: int
    trophies: int
    best_trophies: int
    wins: int
    losses: int
    battle_count: int
    three_crown_wins: int
    clan: ClanRef | None = None
    arena: Arena
    current_deck: list[Card] = []
    cards: list[Card] = []


class GameMode(CRBaseModel):
    id: int
    name: str


class BattleParticipant(CRBaseModel):
    """One side of a battle — either the player or their opponent.

    Supercell wraps this in a single-element list even for 1v1 games
    (`team: [...]`, `opponent: [...]`), presumably to accommodate 2v2.
    """

    tag: str
    name: str
    starting_trophies: int | None = None
    trophy_change: int | None = None
    crowns: int
    king_tower_hit_points: int | None = None
    princess_towers_hit_points: list[int] | None = None
    cards: list[Card]


class Battle(CRBaseModel):
    """A single battle from GET /players/{tag}/battlelog."""

    type: str
    battle_time: str  # ISO-ish string like "20260820T163021.000Z" — parse later
    arena: Arena
    game_mode: GameMode
    deck_selection: str
    team: list[BattleParticipant]
    opponent: list[BattleParticipant]