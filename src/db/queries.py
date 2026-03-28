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
    situation_text: str
    situation_type: str
    turns_per_agent: int
    transcript: list[Turn] | None = None
    status: str = Field(default="pending")
    error_message: str | None = None
    batch_id: UUID | None = None
    created_at: str
    completed_at: str | None = None


class RunCreate(BaseModel):
    """Input model for creating a new run."""

    persona_a_name: str
    persona_b_name: str
    situation_text: str
    situation_type: str = "generated"
    turns_per_agent: int = 5
    batch_id: UUID | None = None


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
    domain: str
    title: str
    fields: dict[str, str]
    status: str = Field(
        default="pending",
        description="pending | kept | discarded | jacket_copy",
    )
    created_at: str


class ConceptCreate(BaseModel):
    """Input model for creating a new concept."""

    run_id: UUID
    domain: str
    title: str
    fields: dict[str, str]


class AxisScoreRecord(BaseModel):
    """A single axis score with reasoning, stored as part of a Score."""

    axis: str
    label: str
    score: float
    reasoning: str


class Score(BaseModel):
    """Per-axis scores and reasoning for a concept evaluation."""

    id: UUID
    concept_id: UUID
    axes: list[AxisScoreRecord]
    overall_score: float | None
    created_at: str


class ScoreCreate(BaseModel):
    """Input model for creating a new score."""

    concept_id: UUID
    axes: list[AxisScoreRecord]


class Batch(BaseModel):
    """A batch of conversation runs."""

    id: UUID
    total_runs: int
    completed_runs: int
    failed_runs: int
    status: str
    created_at: str
    completed_at: str | None = None


class BatchCreate(BaseModel):
    """Input model for creating a new batch."""

    total_runs: int


class ConceptWithScore(BaseModel):
    """A concept joined with its score data for the review table."""

    id: UUID
    run_id: UUID
    domain: str
    title: str
    fields: dict[str, str]
    status: str
    created_at: str
    overall_score: float | None = None
    axes: list[AxisScoreRecord] | None = None


class PairingPerformance(BaseModel):
    """Aggregated performance metrics for a persona pairing."""

    persona_a_name: str
    persona_b_name: str
    total_runs: int
    completed_runs: int
    concepts_kept: int
    concepts_discarded: int
    concepts_pending: int
    avg_score: float | None
    max_score: float | None
    kept_rate: float | None


class SituationPerformance(BaseModel):
    """Aggregated performance metrics for a situation."""

    situation_text: str
    situation_type: str
    total_runs: int
    completed_runs: int
    concepts_kept: int
    concepts_discarded: int
    avg_score: float | None
    max_score: float | None
    kept_rate: float | None


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
        situation_text=row["situation_text"],
        situation_type=row["situation_type"],
        turns_per_agent=row["turns_per_agent"],
        transcript=transcript,
        status=row["status"],
        error_message=row["error_message"],
        batch_id=UUID(row["batch_id"]) if row["batch_id"] else None,
        created_at=row["created_at"],
        completed_at=row["completed_at"],
    )


def _row_to_concept(row: aiosqlite.Row) -> Concept:
    """Map a database row to a Concept model."""
    return Concept(
        id=UUID(row["id"]),
        run_id=UUID(row["run_id"]),
        domain=row["domain"],
        title=row["title"],
        fields=json.loads(row["fields_json"]),
        status=row["status"],
        created_at=row["created_at"],
    )


def _row_to_batch(row: aiosqlite.Row) -> Batch:
    """Map a database row to a Batch model."""
    return Batch(
        id=UUID(row["id"]),
        total_runs=row["total_runs"],
        completed_runs=row["completed_runs"],
        failed_runs=row["failed_runs"],
        status=row["status"],
        created_at=row["created_at"],
        completed_at=row["completed_at"],
    )


def _row_to_concept_with_score(row: aiosqlite.Row) -> ConceptWithScore:
    """Map a joined concept+score row to a ConceptWithScore model."""
    axes = None
    axes_json = row["axes_json"]
    if axes_json:
        axes = [AxisScoreRecord(**a) for a in json.loads(axes_json)]

    return ConceptWithScore(
        id=UUID(row["id"]),
        run_id=UUID(row["run_id"]),
        domain=row["domain"],
        title=row["title"],
        fields=json.loads(row["fields_json"]),
        status=row["status"],
        created_at=row["created_at"],
        overall_score=row["overall_score"],
        axes=axes,
    )


def _row_to_score(row: aiosqlite.Row) -> Score:
    """Map a database row to a Score model."""
    axes = [AxisScoreRecord(**a) for a in json.loads(row["axes_json"])]
    return Score(
        id=UUID(row["id"]),
        concept_id=UUID(row["concept_id"]),
        axes=axes,
        overall_score=row["overall_score"],
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
        "situation_text, situation_type, turns_per_agent, batch_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            run_id,
            run.persona_a_name,
            run.persona_b_name,
            run.situation_text,
            run.situation_type,
            run.turns_per_agent,
            str(run.batch_id) if run.batch_id else None,
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
    fields_json = json.dumps(concept.fields)
    await db.execute(
        "INSERT INTO concepts (id, run_id, domain, title, fields_json) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            concept_id,
            str(concept.run_id),
            concept.domain,
            concept.title,
            fields_json,
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


async def get_concept_by_id(
    db: aiosqlite.Connection,
    concept_id: UUID,
) -> Concept | None:
    """Fetch a single concept by its ID."""
    cursor = await db.execute("SELECT * FROM concepts WHERE id = ?", (str(concept_id),))
    row = await cursor.fetchone()
    return _row_to_concept(row) if row else None


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


async def update_concept_fields(
    db: aiosqlite.Connection,
    concept_id: UUID,
    fields: dict[str, str],
) -> Concept:
    """Update a concept's fields_json and return the updated concept."""
    fields_json = json.dumps(fields)
    await db.execute(
        "UPDATE concepts SET fields_json = ? WHERE id = ?",
        (fields_json, str(concept_id)),
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM concepts WHERE id = ?", (str(concept_id),))
    row = await cursor.fetchone()
    if row is None:
        raise RuntimeError(f"Concept not found after update: {concept_id}")
    return _row_to_concept(row)


# ── Score Queries ───────────────────────────────────


async def create_score(db: aiosqlite.Connection, score: ScoreCreate) -> Score:
    """Insert a new score record and return the hydrated model."""
    score_id = str(uuid4())
    axes_json = json.dumps([a.model_dump() for a in score.axes])
    overall = (
        round(sum(a.score for a in score.axes) / len(score.axes), 2)
        if score.axes
        else None
    )
    await db.execute(
        "INSERT INTO scores (id, concept_id, axes_json, overall_score) "
        "VALUES (?, ?, ?, ?)",
        (
            score_id,
            str(score.concept_id),
            axes_json,
            overall,
        ),
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM scores WHERE id = ?", (score_id,))
    row = await cursor.fetchone()
    if row is None:
        raise RuntimeError(f"Failed to retrieve score after insert: {score_id}")
    return _row_to_score(row)


async def get_score_by_concept_id(
    db: aiosqlite.Connection,
    concept_id: UUID,
) -> Score | None:
    """Fetch the score for a specific concept."""
    cursor = await db.execute(
        "SELECT * FROM scores WHERE concept_id = ?", (str(concept_id),)
    )
    row = await cursor.fetchone()
    return _row_to_score(row) if row else None


async def get_scores(
    db: aiosqlite.Connection,
    limit: int = 20,
) -> list[Score]:
    """Fetch recent scores."""
    cursor = await db.execute(
        "SELECT * FROM scores ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    rows = await cursor.fetchall()
    return [_row_to_score(row) for row in rows]


# ── Batch Queries ──────────────────────────────────


async def create_batch(db: aiosqlite.Connection, batch: BatchCreate) -> Batch:
    """Insert a new batch record and return the hydrated model."""
    batch_id = str(uuid4())
    await db.execute(
        "INSERT INTO batches (id, total_runs) VALUES (?, ?)",
        (batch_id, batch.total_runs),
    )
    await db.commit()
    result = await get_batch_by_id(db, UUID(batch_id))
    if result is None:
        raise RuntimeError(f"Failed to retrieve batch after insert: {batch_id}")
    return result


async def get_batch_by_id(db: aiosqlite.Connection, batch_id: UUID) -> Batch | None:
    """Fetch a single batch by its ID."""
    cursor = await db.execute("SELECT * FROM batches WHERE id = ?", (str(batch_id),))
    row = await cursor.fetchone()
    return _row_to_batch(row) if row else None


async def get_batches(
    db: aiosqlite.Connection,
    limit: int = 20,
) -> list[Batch]:
    """Fetch recent batches ordered by creation date."""
    cursor = await db.execute(
        "SELECT * FROM batches ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    rows = await cursor.fetchall()
    return [_row_to_batch(row) for row in rows]


async def increment_batch_completed(
    db: aiosqlite.Connection,
    batch_id: UUID,
) -> Batch:
    """Increment the completed run count for a batch."""
    await db.execute(
        "UPDATE batches SET completed_runs = completed_runs + 1 WHERE id = ?",
        (str(batch_id),),
    )
    await db.commit()
    result = await get_batch_by_id(db, batch_id)
    if result is None:
        raise RuntimeError(f"Batch not found after update: {batch_id}")
    return result


async def increment_batch_failed(
    db: aiosqlite.Connection,
    batch_id: UUID,
) -> Batch:
    """Increment the failed run count for a batch."""
    await db.execute(
        "UPDATE batches SET failed_runs = failed_runs + 1 WHERE id = ?",
        (str(batch_id),),
    )
    await db.commit()
    result = await get_batch_by_id(db, batch_id)
    if result is None:
        raise RuntimeError(f"Batch not found after update: {batch_id}")
    return result


async def complete_batch(
    db: aiosqlite.Connection,
    batch_id: UUID,
) -> Batch:
    """Mark a batch as completed or failed based on run outcomes.

    Sets status to 'completed' if any runs succeeded, 'failed' if all
    runs failed. Sets completed_at timestamp.
    """
    batch = await get_batch_by_id(db, batch_id)
    if batch is None:
        raise RuntimeError(f"Batch not found: {batch_id}")

    # All runs failed = 'failed', otherwise 'completed' (partial success counts)
    status = "failed" if batch.completed_runs == 0 else "completed"
    now = datetime.now().isoformat()

    await db.execute(
        "UPDATE batches SET status = ?, completed_at = ? WHERE id = ?",
        (status, now, str(batch_id)),
    )
    await db.commit()
    result = await get_batch_by_id(db, batch_id)
    if result is None:
        raise RuntimeError(f"Batch not found after update: {batch_id}")
    return result


# ── Run-Batch Queries ─────────────────────────────


async def get_runs_by_batch_id(
    db: aiosqlite.Connection,
    batch_id: UUID,
    limit: int = 100,
) -> list[Run]:
    """Fetch runs associated with a specific batch."""
    cursor = await db.execute(
        "SELECT * FROM runs WHERE batch_id = ? ORDER BY created_at DESC LIMIT ?",
        (str(batch_id), limit),
    )
    rows = await cursor.fetchall()
    return [_row_to_run(row) for row in rows]


# ── Concept + Score Join Queries ──────────────────


async def get_concepts_with_scores(
    db: aiosqlite.Connection,
    status: str | None = None,
    sort_by: str = "date_desc",
    limit: int = 20,
) -> list[ConceptWithScore]:
    """Fetch concepts joined with their scores for the review table.

    Args:
        db: Database connection.
        status: Optional filter by concept review status.
        sort_by: Sort order — 'score_desc', 'score_asc', 'date_desc', 'date_asc'.
        limit: Maximum number of results.

    Returns:
        List of concepts with their score data attached.
    """
    base_query = (
        "SELECT c.*, s.overall_score, s.axes_json "
        "FROM concepts c "
        "LEFT JOIN scores s ON s.concept_id = c.id"
    )

    params: list[str | int] = []
    if status:
        base_query += " WHERE c.status = ?"
        params.append(status)

    # Sort order with NULLs last for score-based sorting
    order_clauses = {
        "score_desc": "ORDER BY (s.overall_score IS NULL), s.overall_score DESC",
        "score_asc": "ORDER BY (s.overall_score IS NULL), s.overall_score ASC",
        "date_desc": "ORDER BY c.created_at DESC",
        "date_asc": "ORDER BY c.created_at ASC",
    }
    base_query += f" {order_clauses.get(sort_by, order_clauses['date_desc'])}"
    base_query += " LIMIT ?"
    params.append(limit)

    cursor = await db.execute(base_query, params)
    rows = await cursor.fetchall()
    return [_row_to_concept_with_score(row) for row in rows]


# ── Analytics Queries ────────────────────────────────


def _compute_kept_rate(kept: int, discarded: int) -> float | None:
    """Compute kept rate from review counts, returning None if none reviewed."""
    reviewed = kept + discarded
    if reviewed == 0:
        return None
    return round(kept / reviewed, 4)


def _row_to_pairing_performance(row: aiosqlite.Row) -> PairingPerformance:
    """Map an aggregated row to a PairingPerformance model."""
    kept = row["concepts_kept"]
    discarded = row["concepts_discarded"]
    return PairingPerformance(
        persona_a_name=row["persona_a_name"],
        persona_b_name=row["persona_b_name"],
        total_runs=row["total_runs"],
        completed_runs=row["completed_runs"],
        concepts_kept=kept,
        concepts_discarded=discarded,
        concepts_pending=row["concepts_pending"],
        avg_score=row["avg_score"],
        max_score=row["max_score"],
        kept_rate=_compute_kept_rate(kept, discarded),
    )


async def get_pairing_performance(
    db: aiosqlite.Connection,
    domain: str | None = None,
    min_runs: int = 1,
    limit: int = 50,
) -> list[PairingPerformance]:
    """Aggregate concept outcomes and scores by persona pairing.

    Normalizes persona order so (A,B) and (B,A) are treated as the
    same pairing. Joins runs -> concepts -> scores.

    Args:
        db: Database connection.
        domain: Optional filter by concept domain.
        min_runs: Minimum number of runs to include a pairing.
        limit: Maximum number of results.

    Returns:
        List of pairing performance records sorted by avg score descending.
    """
    query = (
        "SELECT "
        "  MIN(r.persona_a_name, r.persona_b_name) AS persona_a_name, "
        "  MAX(r.persona_a_name, r.persona_b_name) AS persona_b_name, "
        "  COUNT(DISTINCT r.id) AS total_runs, "
        "  COUNT(DISTINCT CASE WHEN r.status = 'completed' "
        "    THEN r.id END) AS completed_runs, "
        "  SUM(CASE WHEN c.status = 'kept' THEN 1 ELSE 0 END) AS concepts_kept, "
        "  SUM(CASE WHEN c.status = 'discarded' "
        "    THEN 1 ELSE 0 END) AS concepts_discarded, "
        "  SUM(CASE WHEN c.status = 'pending' "
        "    THEN 1 ELSE 0 END) AS concepts_pending, "
        "  ROUND(AVG(s.overall_score), 2) AS avg_score, "
        "  MAX(s.overall_score) AS max_score "
        "FROM runs r "
        "LEFT JOIN concepts c ON c.run_id = r.id "
        "LEFT JOIN scores s ON s.concept_id = c.id"
    )

    params: list[str | int] = []
    if domain:
        query += " WHERE c.domain = ?"
        params.append(domain)

    query += (
        " GROUP BY MIN(r.persona_a_name, r.persona_b_name), "
        "MAX(r.persona_a_name, r.persona_b_name)"
    )
    query += " HAVING COUNT(DISTINCT r.id) >= ?"
    params.append(min_runs)

    query += " ORDER BY (avg_score IS NULL), avg_score DESC LIMIT ?"
    params.append(limit)

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    return [_row_to_pairing_performance(row) for row in rows]


async def get_pairing_scores(
    db: aiosqlite.Connection,
    domain: str | None = None,
) -> dict[tuple[str, str], float]:
    """Fetch average scores per persona pairing as a simple dict.

    Returns a dict mapping sorted (name_a, name_b) tuples to their
    average overall score. Only includes pairings that have at least
    one scored concept. Used by the informed selection logic.

    Args:
        db: Database connection.
        domain: Optional filter by concept domain.

    Returns:
        Dict of {(persona_a, persona_b): avg_score}.
    """
    query = (
        "SELECT "
        "  MIN(r.persona_a_name, r.persona_b_name) AS persona_a_name, "
        "  MAX(r.persona_a_name, r.persona_b_name) AS persona_b_name, "
        "  ROUND(AVG(s.overall_score), 2) AS avg_score "
        "FROM runs r "
        "JOIN concepts c ON c.run_id = r.id "
        "JOIN scores s ON s.concept_id = c.id"
    )

    params: list[str] = []
    if domain:
        query += " WHERE c.domain = ?"
        params.append(domain)

    query += (
        " GROUP BY MIN(r.persona_a_name, r.persona_b_name), "
        "MAX(r.persona_a_name, r.persona_b_name)"
    )

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    return {
        (row["persona_a_name"], row["persona_b_name"]): row["avg_score"] for row in rows
    }


def _row_to_situation_performance(
    row: aiosqlite.Row,
) -> SituationPerformance:
    """Map an aggregated row to a SituationPerformance model."""
    kept = row["concepts_kept"]
    discarded = row["concepts_discarded"]
    return SituationPerformance(
        situation_text=row["situation_text"],
        situation_type=row["situation_type"],
        total_runs=row["total_runs"],
        completed_runs=row["completed_runs"],
        concepts_kept=kept,
        concepts_discarded=discarded,
        avg_score=row["avg_score"],
        max_score=row["max_score"],
        kept_rate=_compute_kept_rate(kept, discarded),
    )


async def get_situation_performance(
    db: aiosqlite.Connection,
    domain: str | None = None,
    min_runs: int = 1,
    limit: int = 50,
) -> list[SituationPerformance]:
    """Aggregate concept outcomes and scores by situation.

    Joins runs -> concepts -> scores grouped by situation text and type.

    Args:
        db: Database connection.
        domain: Optional filter by concept domain.
        min_runs: Minimum number of runs to include a situation.
        limit: Maximum number of results.

    Returns:
        List of situation performance records sorted by avg score descending.
    """
    query = (
        "SELECT "
        "  r.situation_text, "
        "  r.situation_type, "
        "  COUNT(DISTINCT r.id) AS total_runs, "
        "  COUNT(DISTINCT CASE WHEN r.status = 'completed' "
        "    THEN r.id END) AS completed_runs, "
        "  SUM(CASE WHEN c.status = 'kept' THEN 1 ELSE 0 END) AS concepts_kept, "
        "  SUM(CASE WHEN c.status = 'discarded' "
        "    THEN 1 ELSE 0 END) AS concepts_discarded, "
        "  ROUND(AVG(s.overall_score), 2) AS avg_score, "
        "  MAX(s.overall_score) AS max_score "
        "FROM runs r "
        "LEFT JOIN concepts c ON c.run_id = r.id "
        "LEFT JOIN scores s ON s.concept_id = c.id"
    )

    params: list[str | int] = []
    if domain:
        query += " WHERE c.domain = ?"
        params.append(domain)

    query += " GROUP BY r.situation_text, r.situation_type"
    query += " HAVING COUNT(DISTINCT r.id) >= ?"
    params.append(min_runs)

    query += " ORDER BY (avg_score IS NULL), avg_score DESC LIMIT ?"
    params.append(limit)

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    return [_row_to_situation_performance(row) for row in rows]
