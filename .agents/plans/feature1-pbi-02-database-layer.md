# PBI 2: Database Layer

**Feature**: 1 — Core Conversation Engine
**Tasks**: 6–8 of 28
**Dependencies**: PBI 1 (scaffold + config)
**Estimated Complexity**: Medium

---

## Objective

Create the SQLite schema and typed query layer. This is the storage foundation — every other layer writes to or reads from it. All SQL is isolated here; no raw SQL exists anywhere else in the codebase.

## User Story

As the conversation engine
I want a typed data layer that persists runs and transcripts
So that conversation results are stored reliably and retrievable as Pydantic models

## Preconditions

- PBI 1 complete (`pyproject.toml`, `src/config.py` working)
- `uv sync` passes

## Context References — READ BEFORE IMPLEMENTING

- `CLAUDE.md` — Database access rules: all SQL in `src/db/`, query layer returns Pydantic models, never raw rows
- `CLAUDE.md` — Async patterns: all I/O functions must be `async`
- `CLAUDE.md` — Error handling: specific exception types, logging module per file
- `.agents/DevPlan.md` (lines 154-156) — SQLite decision rationale

### Patterns to Follow

**Row Factory**: Set `db.row_factory = aiosqlite.Row` on the connection (done in lifespan) so rows support column-name access like `row["id"]`.

**UUID Storage**: SQLite has no native UUID type. Store as TEXT, convert to/from `uuid.UUID` at the query layer boundary.

**Transcript Storage**: Store as JSON text in the `runs` table. Deserialize to `list[Turn]` in the mapping function.

**Commit Pattern**: Each write function calls `await db.commit()` internally. For multi-step atomic operations, use an explicit `transaction()` context manager.

---

## TASKS

### Task 6: CREATE `src/db/__init__.py`

- **IMPLEMENT**: Empty file (package marker).
- **VALIDATE**: `test -f src/db/__init__.py && echo "exists"`

---

### Task 7: CREATE `src/db/schema.py`

SQL schema definitions and initialization function.

- **IMPLEMENT**:

```python
"""
Database schema definitions for the Yield Engine.

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
"""


async def init_schema(db: aiosqlite.Connection) -> None:
    """Create all tables and indexes if they don't already exist.

    Called during application startup via the FastAPI lifespan.
    Uses executescript which issues an implicit COMMIT.
    """
    await db.executescript(SCHEMA_SQL)
    logger.info("Database schema initialized")
```

- **GOTCHA**: `executescript()` issues an implicit COMMIT before running. Fine for schema init, but don't use it mid-transaction. `PRAGMA foreign_keys=ON` must be set per-connection (done in lifespan, not here).
- **VALIDATE**: `uv run python -c "from src.db.schema import SCHEMA_SQL; print('Schema loaded:', len(SCHEMA_SQL), 'chars')"`

---

### Task 8: CREATE `src/db/queries.py`

Typed query layer — the only module that touches SQLite. Returns Pydantic models, never raw rows.

- **IMPLEMENT**:

```python
"""
Typed query layer for the Yield Engine.

All database access flows through this module. Functions accept an
aiosqlite connection and return Pydantic models — never raw rows or
dicts. This module belongs to the Data layer.
"""

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID, uuid4

import aiosqlite
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ── Models ────────────────────────────────────────────


class Turn(BaseModel):
    """A single turn in a conversation transcript."""

    turn_number: int
    persona_name: str
    content: str


class Run(BaseModel):
    """A complete conversation run with metadata."""

    id: UUID
    persona_a_name: str
    persona_b_name: str
    shared_object_text: str
    shared_object_type: str
    turns_per_agent: int
    transcript: list[Turn] | None = None
    status: str = Field(default="pending")
    error_message: str | None = None
    created_at: str
    completed_at: str | None = None


class RunCreate(BaseModel):
    """Input model for creating a new run."""

    persona_a_name: str
    persona_b_name: str
    shared_object_text: str
    shared_object_type: str = "scenario"
    turns_per_agent: int = 5


class PairingRecord(BaseModel):
    """Record of a persona pairing used in a run."""

    id: UUID
    persona_a_name: str
    persona_b_name: str
    run_id: UUID
    created_at: str


# ── Helpers ───────────────────────────────────────────


def _row_to_run(row: aiosqlite.Row) -> Run:
    """Map a database row to a Run model."""
    transcript = None
    if row["transcript_json"]:
        transcript = [Turn(**t) for t in json.loads(row["transcript_json"])]

    return Run(
        id=UUID(row["id"]),
        persona_a_name=row["persona_a_name"],
        persona_b_name=row["persona_b_name"],
        shared_object_text=row["shared_object_text"],
        shared_object_type=row["shared_object_type"],
        turns_per_agent=row["turns_per_agent"],
        transcript=transcript,
        status=row["status"],
        error_message=row["error_message"],
        created_at=row["created_at"],
        completed_at=row["completed_at"],
    )


@asynccontextmanager
async def transaction(db: aiosqlite.Connection):
    """Explicit transaction with rollback on failure."""
    await db.execute("BEGIN")
    try:
        yield db
        await db.commit()
    except Exception:
        await db.rollback()
        raise


# ── Run Queries ───────────────────────────────────────


async def create_run(db: aiosqlite.Connection, run: RunCreate) -> Run:
    """Insert a new run record and return the hydrated model."""
    run_id = str(uuid4())
    await db.execute(
        "INSERT INTO runs (id, persona_a_name, persona_b_name, "
        "shared_object_text, shared_object_type, turns_per_agent) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            run_id,
            run.persona_a_name,
            run.persona_b_name,
            run.shared_object_text,
            run.shared_object_type,
            run.turns_per_agent,
        ),
    )
    await db.commit()
    result = await get_run_by_id(db, UUID(run_id))
    if result is None:
        raise RuntimeError(f"Failed to retrieve run after insert: {run_id}")
    return result


async def get_run_by_id(db: aiosqlite.Connection, run_id: UUID) -> Run | None:
    """Fetch a single run by its ID."""
    cursor = await db.execute("SELECT * FROM runs WHERE id = ?", (str(run_id),))
    row = await cursor.fetchone()
    return _row_to_run(row) if row else None


async def get_runs(
    db: aiosqlite.Connection,
    status: str | None = None,
    limit: int = 20,
) -> list[Run]:
    """Fetch runs, optionally filtered by status."""
    if status:
        cursor = await db.execute(
            "SELECT * FROM runs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
            (status, limit),
        )
    else:
        cursor = await db.execute(
            "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
    rows = await cursor.fetchall()
    return [_row_to_run(row) for row in rows]


async def complete_run(
    db: aiosqlite.Connection,
    run_id: UUID,
    transcript: list[Turn],
) -> Run:
    """Mark a run as completed and store the transcript."""
    transcript_json = json.dumps([t.model_dump() for t in transcript])
    now = datetime.now().isoformat()
    await db.execute(
        "UPDATE runs SET status = 'completed', transcript_json = ?, "
        "completed_at = ? WHERE id = ?",
        (transcript_json, now, str(run_id)),
    )
    await db.commit()
    result = await get_run_by_id(db, run_id)
    if result is None:
        raise RuntimeError(f"Run not found after update: {run_id}")
    return result


async def fail_run(
    db: aiosqlite.Connection,
    run_id: UUID,
    error_message: str,
) -> Run:
    """Mark a run as failed with an error message."""
    now = datetime.now().isoformat()
    await db.execute(
        "UPDATE runs SET status = 'failed', error_message = ?, "
        "completed_at = ? WHERE id = ?",
        (error_message, now, str(run_id)),
    )
    await db.commit()
    result = await get_run_by_id(db, run_id)
    if result is None:
        raise RuntimeError(f"Run not found after update: {run_id}")
    return result


# ── Pairing History Queries ───────────────────────────


async def record_pairing(
    db: aiosqlite.Connection,
    persona_a_name: str,
    persona_b_name: str,
    run_id: UUID,
) -> None:
    """Record a persona pairing for history tracking.

    Stores names in sorted order so (A, B) and (B, A) are the same pairing.
    """
    sorted_names = sorted([persona_a_name, persona_b_name])
    await db.execute(
        "INSERT INTO pairing_history (id, persona_a_name, persona_b_name, run_id) "
        "VALUES (?, ?, ?, ?)",
        (str(uuid4()), sorted_names[0], sorted_names[1], str(run_id)),
    )
    await db.commit()


async def get_recent_pairings(
    db: aiosqlite.Connection,
    limit: int = 10,
) -> list[tuple[str, str]]:
    """Fetch the most recent persona pairings to avoid repeats."""
    cursor = await db.execute(
        "SELECT DISTINCT persona_a_name, persona_b_name "
        "FROM pairing_history ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    rows = await cursor.fetchall()
    return [(row["persona_a_name"], row["persona_b_name"]) for row in rows]
```

- **PATTERN**: Every public function returns a Pydantic model or typed collection. UUIDs stored as TEXT. Transcripts stored as JSON text. `commit()` inside each write function.
- **GOTCHA**: `aiosqlite.Row` must be set as `row_factory` on the connection (done in lifespan) for column-name access. `record_pairing` sorts names so (A,B) and (B,A) match.
- **VALIDATE**: `uv run python -c "from src.db.queries import Run, Turn; print('Query models loaded')"`

---

## FILES CREATED

| File | Purpose |
|------|---------|
| `src/db/__init__.py` | Package marker |
| `src/db/schema.py` | SQL CREATE TABLE statements, `init_schema()` |
| `src/db/queries.py` | Typed query functions returning Pydantic models |

## VALIDATION COMMANDS

```bash
# Modules import cleanly
uv run python -c "from src.db.schema import init_schema; print('schema ok')"
uv run python -c "from src.db.queries import create_run, get_runs; print('queries ok')"

# Lint
uv run ruff check src/db/
uv run ruff format --check src/db/
```

## DONE WHEN

- [ ] `src/db/schema.py` defines `runs` and `pairing_history` tables
- [ ] `src/db/queries.py` provides CRUD for runs and pairing history
- [ ] All query functions return Pydantic models, never raw rows
- [ ] No raw SQL exists outside `src/db/`
- [ ] Ruff passes on `src/db/`
