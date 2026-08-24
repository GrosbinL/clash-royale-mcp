-- Cache table: stores raw JSON payloads from the Supercell API,
-- keyed by (resource_type, resource_key), with a fetched_at timestamp
-- so callers can decide if the row is still fresh enough to use.

CREATE TABLE IF NOT EXISTS cache_entries (
    resource_type TEXT NOT NULL,
    resource_key  TEXT NOT NULL,
    fetched_at    REAL NOT NULL,      -- Unix timestamp (float seconds since epoch)
    payload       TEXT NOT NULL,
    PRIMARY KEY (resource_type, resource_key)
);