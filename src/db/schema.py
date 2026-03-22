"""
Database schema definitions for the Medici Engine.

Contains all CREATE TABLE statements and the schema initialization
function. This module belongs to the Data layer and is called during
application startup to ensure all tables exist.
"""

import logging

import aiosqlite

logger = logging.getLogger(__name__)

SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    persona_a_name TEXT NOT NULL,
    persona_b_name TEXT NOT NULL,
    shared_object_text TEXT NOT NULL,
    shared_object_type TEXT NOT NULL DEFAULT 'scenario',
    turns_per_agent INTEGER NOT NULL DEFAULT 5,
    transcript_json TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs(created_at);

CREATE TABLE IF NOT EXISTS pairing_history (
    id TEXT PRIMARY KEY,
    persona_a_name TEXT NOT NULL,
    persona_b_name TEXT NOT NULL,
    run_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (run_id) REFERENCES runs(id)
);

CREATE INDEX IF NOT EXISTS idx_pairing_history_personas
    ON pairing_history(persona_a_name, persona_b_name);

CREATE TABLE IF NOT EXISTS concepts (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    title TEXT NOT NULL,
    premise TEXT NOT NULL,
    originality TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (run_id) REFERENCES runs(id)
);

CREATE INDEX IF NOT EXISTS idx_concepts_run_id ON concepts(run_id);
CREATE INDEX IF NOT EXISTS idx_concepts_status ON concepts(status);

CREATE TABLE IF NOT EXISTS scores (
    id TEXT PRIMARY KEY,
    concept_id TEXT NOT NULL UNIQUE,
    uniqueness_score REAL NOT NULL,
    uniqueness_reasoning TEXT NOT NULL,
    plausibility_score REAL NOT NULL,
    plausibility_reasoning TEXT NOT NULL,
    compelling_factor_score REAL NOT NULL,
    compelling_factor_reasoning TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (concept_id) REFERENCES concepts(id)
);

CREATE INDEX IF NOT EXISTS idx_scores_concept_id ON scores(concept_id);
"""


async def init_schema(db: aiosqlite.Connection) -> None:
    """Create all tables and indexes if they don't already exist.

    Called during application startup via the FastAPI lifespan.
    Uses executescript which issues an implicit COMMIT.
    """
    await db.executescript(SCHEMA_SQL)
    logger.info("Database schema initialized")
