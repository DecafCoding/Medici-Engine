"""
Typed query layer for the Medici Engine.

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


class Concept(BaseModel):
    """A structured concept extracted by the synthesizer from a conversation."""

    id: UUID
    run_id: UUID
    title: str
    premise: str
    originality: str
    status: str = Field(default="pending", description="pending | kept | discarded")
    created_at: str


class ConceptCreate(BaseModel):
    """Input model for creating a new concept."""

    run_id: UUID
    title: str
    premise: str
    originality: str


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


def _row_to_concept(row: aiosqlite.Row) -> Concept:
    """Map a database row to a Concept model."""
    return Concept(
        id=UUID(row["id"]),
        run_id=UUID(row["run_id"]),
        title=row["title"],
        premise=row["premise"],
        originality=row["originality"],
        status=row["status"],
        created_at=row["created_at"],
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


# ── Concept Queries ──────────────────────────────────


async def create_concept(db: aiosqlite.Connection, concept: ConceptCreate) -> Concept:
    """Insert a new concept record and return the hydrated model."""
    concept_id = str(uuid4())
    await db.execute(
        "INSERT INTO concepts (id, run_id, title, premise, originality) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            concept_id,
            str(concept.run_id),
            concept.title,
            concept.premise,
            concept.originality,
        ),
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM concepts WHERE id = ?", (concept_id,))
    row = await cursor.fetchone()
    if row is None:
        raise RuntimeError(f"Failed to retrieve concept after insert: {concept_id}")
    return _row_to_concept(row)


async def get_concepts(
    db: aiosqlite.Connection,
    status: str | None = None,
    limit: int = 20,
) -> list[Concept]:
    """Fetch concepts, optionally filtered by review status."""
    if status:
        cursor = await db.execute(
            "SELECT * FROM concepts WHERE status = ? ORDER BY created_at DESC LIMIT ?",
            (status, limit),
        )
    else:
        cursor = await db.execute(
            "SELECT * FROM concepts ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
    rows = await cursor.fetchall()
    return [_row_to_concept(row) for row in rows]


async def get_concept_by_run_id(
    db: aiosqlite.Connection,
    run_id: UUID,
) -> Concept | None:
    """Fetch the concept extracted from a specific run."""
    cursor = await db.execute("SELECT * FROM concepts WHERE run_id = ?", (str(run_id),))
    row = await cursor.fetchone()
    return _row_to_concept(row) if row else None


async def update_concept_status(
    db: aiosqlite.Connection,
    concept_id: UUID,
    status: str,
) -> Concept:
    """Update a concept's review status (kept or discarded)."""
    await db.execute(
        "UPDATE concepts SET status = ? WHERE id = ?",
        (status, str(concept_id)),
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM concepts WHERE id = ?", (str(concept_id),))
    row = await cursor.fetchone()
    if row is None:
        raise RuntimeError(f"Concept not found after update: {concept_id}")
    return _row_to_concept(row)
