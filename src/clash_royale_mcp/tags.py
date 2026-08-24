"""Player and clan tag normalization — shared across the codebase.

Clash Royale tags come from users in many forms: '#ABC123', 'abc123',
'#abc123', '  ABC123 '. This module owns the canonical form used
throughout the codebase — uppercase, leading '#', no whitespace — so
cache keys, log messages, and comparisons stay consistent regardless
of how the user typed the tag.
"""


def canonical_tag(tag: str) -> str:
    """Normalize any tag form ('abc123', '#ABC123', ' abc123 ') to '#ABC123'."""
    stripped = tag.strip().lstrip("#").upper()
    if not stripped:
        raise ValueError(f"Tag is empty after normalization: {tag!r}")
    return f"#{stripped}"