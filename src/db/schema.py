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
CREATE TABLE IF NOT EXISTS batches (
    id TEXT PRIMARY KEY,
    total_runs INTEGER NOT NULL,
    completed_runs INTEGER NOT NULL DEFAULT 0,
    failed_runs INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'running',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_batches_status ON batches(status);

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
    batch_id TEXT REFERENCES batches(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT
);

-- NOTE: batch_id added in Milestone 2. Existing databases created before this
-- change won't have the column (CREATE TABLE IF NOT EXISTS won't alter them).
-- Pre-v1.0, users can delete data/yield_engine.db to recreate.

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

-- BREAKING CHANGE: concepts and scores tables now use JSON storage for
-- domain-agnostic fields. Delete data/yield_engine.db to recreate.
CREATE TABLE IF NOT EXISTS concepts (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    title TEXT NOT NULL,
    fields_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (run_id) REFERENCES runs(id)
);

CREATE INDEX IF NOT EXISTS idx_concepts_run_id ON concepts(run_id);
CREATE INDEX IF NOT EXISTS idx_concepts_status ON concepts(status);

CREATE TABLE IF NOT EXISTS scores (
    id TEXT PRIMARY KEY,
    concept_id TEXT NOT NULL UNIQUE,
    axes_json TEXT NOT NULL,
    overall_score REAL,
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
