"""Tests for the database schema and query layer."""

from uuid import UUID, uuid4

from src.db.queries import (
    ConceptCreate,
    RunCreate,
    ScoreCreate,
    Turn,
    complete_run,
    create_concept,
    create_run,
    create_score,
    fail_run,
    get_concept_by_run_id,
    get_concepts,
    get_recent_pairings,
    get_run_by_id,
    get_runs,
    get_score_by_concept_id,
    record_pairing,
    update_concept_status,
)


async def test_create_run(db) -> None:
    """Verify a run can be created and retrieved."""
    run = await create_run(
        db,
        RunCreate(
            persona_a_name="physicist",
            persona_b_name="builder",
            shared_object_text="A test scenario",
            turns_per_agent=5,
        ),
    )
    assert isinstance(run.id, UUID)
    assert run.status == "pending"
    assert run.persona_a_name == "physicist"
    assert run.transcript is None


async def test_get_run_by_id(db) -> None:
    """Verify a run can be fetched by its ID."""
    created = await create_run(
        db,
        RunCreate(
            persona_a_name="physicist",
            persona_b_name="builder",
            shared_object_text="A test scenario",
        ),
    )
    fetched = await get_run_by_id(db, created.id)
    assert fetched is not None
    assert fetched.id == created.id


async def test_get_run_by_id_returns_none_for_missing(db) -> None:
    """Verify None is returned for a nonexistent run ID."""
    result = await get_run_by_id(db, uuid4())
    assert result is None


async def test_complete_run_stores_transcript(db) -> None:
    """Verify completing a run stores the transcript and updates status."""
    run = await create_run(
        db,
        RunCreate(
            persona_a_name="physicist",
            persona_b_name="builder",
            shared_object_text="A test scenario",
        ),
    )
    turns = [
        Turn(turn_number=1, persona_name="physicist", content="Hello from physics"),
        Turn(turn_number=2, persona_name="builder", content="Hello from building"),
    ]
    completed = await complete_run(db, run.id, turns)
    assert completed.status == "completed"
    assert completed.transcript is not None
    assert len(completed.transcript) == 2
    assert completed.transcript[0].content == "Hello from physics"
    assert completed.completed_at is not None


async def test_fail_run_stores_error(db) -> None:
    """Verify failing a run stores the error message and updates status."""
    run = await create_run(
        db,
        RunCreate(
            persona_a_name="physicist",
            persona_b_name="builder",
            shared_object_text="A test scenario",
        ),
    )
    failed = await fail_run(db, run.id, "Connection timeout")
    assert failed.status == "failed"
    assert failed.error_message == "Connection timeout"


async def test_get_runs_filters_by_status(db) -> None:
    """Verify runs can be filtered by status."""
    await create_run(
        db,
        RunCreate(
            persona_a_name="a",
            persona_b_name="b",
            shared_object_text="test",
        ),
    )
    run2 = await create_run(
        db,
        RunCreate(
            persona_a_name="c",
            persona_b_name="d",
            shared_object_text="test2",
        ),
    )
    await fail_run(db, run2.id, "error")

    pending = await get_runs(db, status="pending")
    failed = await get_runs(db, status="failed")
    assert len(pending) == 1
    assert len(failed) == 1


async def test_pairing_history_tracks_pairings(db) -> None:
    """Verify pairing history records and retrieves pairings."""
    run = await create_run(
        db,
        RunCreate(
            persona_a_name="physicist",
            persona_b_name="builder",
            shared_object_text="test",
        ),
    )
    await record_pairing(db, "physicist", "builder", run.id)
    recent = await get_recent_pairings(db, limit=5)
    assert len(recent) == 1
    # Names are sorted in record_pairing
    assert recent[0] == ("builder", "physicist")


# ── Concept Query Tests ──────────────────────────────


async def _create_test_run(db):
    """Helper to create a run for concept tests."""
    return await create_run(
        db,
        RunCreate(
            persona_a_name="physicist",
            persona_b_name="builder",
            shared_object_text="A test scenario",
        ),
    )


async def test_create_concept(db) -> None:
    """Verify a concept can be created and linked to a run."""
    run = await _create_test_run(db)
    concept = await create_concept(
        db,
        ConceptCreate(
            run_id=run.id,
            title="The Architecture of Forgetting",
            premise="Buildings that preserve by decaying.",
            originality="Combines structural failure with information theory.",
        ),
    )
    assert concept.title == "The Architecture of Forgetting"
    assert concept.run_id == run.id
    assert concept.status == "pending"
    assert concept.created_at is not None


async def test_get_concepts_filters_by_status(db) -> None:
    """Verify concepts can be filtered by review status."""
    run = await _create_test_run(db)
    concept1 = await create_concept(
        db,
        ConceptCreate(
            run_id=run.id,
            title="Concept One",
            premise="Premise one.",
            originality="Original one.",
        ),
    )
    run2 = await _create_test_run(db)
    await create_concept(
        db,
        ConceptCreate(
            run_id=run2.id,
            title="Concept Two",
            premise="Premise two.",
            originality="Original two.",
        ),
    )
    await update_concept_status(db, concept1.id, "kept")

    kept = await get_concepts(db, status="kept")
    pending = await get_concepts(db, status="pending")
    assert len(kept) == 1
    assert kept[0].title == "Concept One"
    assert len(pending) == 1
    assert pending[0].title == "Concept Two"


async def test_get_concept_by_run_id(db) -> None:
    """Verify a concept can be fetched by its associated run ID."""
    run = await _create_test_run(db)
    created = await create_concept(
        db,
        ConceptCreate(
            run_id=run.id,
            title="Test Concept",
            premise="Test premise.",
            originality="Test originality.",
        ),
    )
    fetched = await get_concept_by_run_id(db, run.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.title == "Test Concept"


async def test_update_concept_status(db) -> None:
    """Verify a concept's status can be changed from pending to kept/discarded."""
    run = await _create_test_run(db)
    concept = await create_concept(
        db,
        ConceptCreate(
            run_id=run.id,
            title="Status Test",
            premise="Test premise.",
            originality="Test originality.",
        ),
    )
    assert concept.status == "pending"

    updated = await update_concept_status(db, concept.id, "kept")
    assert updated.status == "kept"

    discarded = await update_concept_status(db, concept.id, "discarded")
    assert discarded.status == "discarded"


# ── Score Query Tests ────────────────────────────────


async def _create_test_concept(db):
    """Helper to create a run and concept for score tests."""
    run = await _create_test_run(db)
    concept = await create_concept(
        db,
        ConceptCreate(
            run_id=run.id,
            title="Score Test Concept",
            premise="Test premise for scoring.",
            originality="Test originality for scoring.",
        ),
    )
    return concept


async def test_create_score(db) -> None:
    """Verify a score can be created and linked to a concept."""
    concept = await _create_test_concept(db)
    score = await create_score(
        db,
        ScoreCreate(
            concept_id=concept.id,
            uniqueness_score=8.5,
            uniqueness_reasoning="Highly novel concept.",
            plausibility_score=6.0,
            plausibility_reasoning="Requires generous extrapolation.",
            compelling_factor_score=7.5,
            compelling_factor_reasoning="Immediately provocative.",
        ),
    )
    assert score.concept_id == concept.id
    assert score.uniqueness_score == 8.5
    assert score.uniqueness_reasoning == "Highly novel concept."
    assert score.plausibility_score == 6.0
    assert score.compelling_factor_score == 7.5
    assert score.created_at is not None


async def test_get_score_by_concept_id(db) -> None:
    """Verify a score can be fetched by its associated concept ID."""
    concept = await _create_test_concept(db)
    created = await create_score(
        db,
        ScoreCreate(
            concept_id=concept.id,
            uniqueness_score=9.0,
            uniqueness_reasoning="Unprecedented.",
            plausibility_score=5.0,
            plausibility_reasoning="Speculative.",
            compelling_factor_score=8.0,
            compelling_factor_reasoning="Page-turner potential.",
        ),
    )
    fetched = await get_score_by_concept_id(db, concept.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.uniqueness_score == 9.0


async def test_get_score_by_concept_id_returns_none_for_missing(db) -> None:
    """Verify None is returned for a nonexistent concept ID."""
    result = await get_score_by_concept_id(db, uuid4())
    assert result is None
