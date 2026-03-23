"""Tests for the database schema and query layer."""

from uuid import UUID, uuid4

from src.db.queries import (
    BatchCreate,
    ConceptCreate,
    RunCreate,
    ScoreCreate,
    Turn,
    complete_batch,
    complete_run,
    create_batch,
    create_concept,
    create_run,
    create_score,
    fail_run,
    get_batch_by_id,
    get_batches,
    get_concept_by_run_id,
    get_concepts,
    get_concepts_with_scores,
    get_recent_pairings,
    get_run_by_id,
    get_runs,
    get_runs_by_batch_id,
    get_score_by_concept_id,
    increment_batch_completed,
    increment_batch_failed,
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


# ── Batch Query Tests ──────────────────────────────


async def test_create_and_get_batch(db) -> None:
    """Verify a batch can be created and retrieved by ID."""
    batch = await create_batch(db, BatchCreate(total_runs=5))
    assert isinstance(batch.id, UUID)
    assert batch.total_runs == 5
    assert batch.completed_runs == 0
    assert batch.failed_runs == 0
    assert batch.status == "running"
    assert batch.completed_at is None

    fetched = await get_batch_by_id(db, batch.id)
    assert fetched is not None
    assert fetched.id == batch.id


async def test_get_batches(db) -> None:
    """Verify recent batches can be listed."""
    await create_batch(db, BatchCreate(total_runs=3))
    await create_batch(db, BatchCreate(total_runs=5))
    batches = await get_batches(db)
    assert len(batches) == 2


async def test_increment_batch_completed(db) -> None:
    """Verify completed run count increments correctly."""
    batch = await create_batch(db, BatchCreate(total_runs=3))
    updated = await increment_batch_completed(db, batch.id)
    assert updated.completed_runs == 1
    updated2 = await increment_batch_completed(db, batch.id)
    assert updated2.completed_runs == 2


async def test_increment_batch_failed(db) -> None:
    """Verify failed run count increments correctly."""
    batch = await create_batch(db, BatchCreate(total_runs=3))
    updated = await increment_batch_failed(db, batch.id)
    assert updated.failed_runs == 1
    updated2 = await increment_batch_failed(db, batch.id)
    assert updated2.failed_runs == 2


async def test_complete_batch_success(db) -> None:
    """Verify batch completes with 'completed' status when runs succeed."""
    batch = await create_batch(db, BatchCreate(total_runs=2))
    await increment_batch_completed(db, batch.id)
    await increment_batch_completed(db, batch.id)
    completed = await complete_batch(db, batch.id)
    assert completed.status == "completed"
    assert completed.completed_at is not None


async def test_complete_batch_all_failed(db) -> None:
    """Verify batch completes with 'failed' status when all runs fail."""
    batch = await create_batch(db, BatchCreate(total_runs=2))
    await increment_batch_failed(db, batch.id)
    await increment_batch_failed(db, batch.id)
    completed = await complete_batch(db, batch.id)
    assert completed.status == "failed"


async def test_complete_batch_partial_success(db) -> None:
    """Verify batch completes with 'completed' status on partial success."""
    batch = await create_batch(db, BatchCreate(total_runs=3))
    await increment_batch_completed(db, batch.id)
    await increment_batch_failed(db, batch.id)
    completed = await complete_batch(db, batch.id)
    assert completed.status == "completed"


async def test_create_run_with_batch_id(db) -> None:
    """Verify a run can be created with a batch association."""
    batch = await create_batch(db, BatchCreate(total_runs=1))
    run = await create_run(
        db,
        RunCreate(
            persona_a_name="physicist",
            persona_b_name="builder",
            shared_object_text="A test scenario",
            batch_id=batch.id,
        ),
    )
    assert run.batch_id == batch.id


async def test_create_run_without_batch_id(db) -> None:
    """Verify a run created without batch_id has None."""
    run = await create_run(
        db,
        RunCreate(
            persona_a_name="physicist",
            persona_b_name="builder",
            shared_object_text="A test scenario",
        ),
    )
    assert run.batch_id is None


async def test_get_runs_by_batch_id(db) -> None:
    """Verify runs can be fetched by their batch association."""
    batch = await create_batch(db, BatchCreate(total_runs=2))
    await create_run(
        db,
        RunCreate(
            persona_a_name="a",
            persona_b_name="b",
            shared_object_text="test1",
            batch_id=batch.id,
        ),
    )
    await create_run(
        db,
        RunCreate(
            persona_a_name="c",
            persona_b_name="d",
            shared_object_text="test2",
            batch_id=batch.id,
        ),
    )
    # Create a run without batch to verify filtering
    await create_run(
        db,
        RunCreate(
            persona_a_name="e",
            persona_b_name="f",
            shared_object_text="test3",
        ),
    )
    runs = await get_runs_by_batch_id(db, batch.id)
    assert len(runs) == 2


# ── Concept + Score Join Query Tests ──────────────


async def test_get_concepts_with_scores(db) -> None:
    """Verify the join query returns concept data with scores attached."""
    run = await _create_test_run(db)
    concept = await create_concept(
        db,
        ConceptCreate(
            run_id=run.id,
            title="Test Concept",
            premise="Test premise.",
            originality="Test originality.",
        ),
    )
    await create_score(
        db,
        ScoreCreate(
            concept_id=concept.id,
            uniqueness_score=8.0,
            uniqueness_reasoning="Novel.",
            plausibility_score=6.0,
            plausibility_reasoning="Plausible.",
            compelling_factor_score=7.0,
            compelling_factor_reasoning="Compelling.",
        ),
    )
    results = await get_concepts_with_scores(db)
    assert len(results) == 1
    result = results[0]
    assert result.title == "Test Concept"
    assert result.uniqueness_score == 8.0
    assert result.plausibility_score == 6.0
    assert result.compelling_factor_score == 7.0
    assert result.overall_score == 7.0


async def test_get_concepts_with_scores_no_score(db) -> None:
    """Verify concepts without scores have NULL score fields."""
    run = await _create_test_run(db)
    await create_concept(
        db,
        ConceptCreate(
            run_id=run.id,
            title="Unscored Concept",
            premise="Test premise.",
            originality="Test originality.",
        ),
    )
    results = await get_concepts_with_scores(db)
    assert len(results) == 1
    assert results[0].uniqueness_score is None
    assert results[0].overall_score is None


async def test_get_concepts_with_scores_sort_by_score(db) -> None:
    """Verify concepts can be sorted by overall score descending."""
    run1 = await _create_test_run(db)
    concept1 = await create_concept(
        db,
        ConceptCreate(
            run_id=run1.id,
            title="Low Score",
            premise="p",
            originality="o",
        ),
    )
    await create_score(
        db,
        ScoreCreate(
            concept_id=concept1.id,
            uniqueness_score=3.0,
            uniqueness_reasoning="r",
            plausibility_score=3.0,
            plausibility_reasoning="r",
            compelling_factor_score=3.0,
            compelling_factor_reasoning="r",
        ),
    )

    run2 = await _create_test_run(db)
    concept2 = await create_concept(
        db,
        ConceptCreate(
            run_id=run2.id,
            title="High Score",
            premise="p",
            originality="o",
        ),
    )
    await create_score(
        db,
        ScoreCreate(
            concept_id=concept2.id,
            uniqueness_score=9.0,
            uniqueness_reasoning="r",
            plausibility_score=9.0,
            plausibility_reasoning="r",
            compelling_factor_score=9.0,
            compelling_factor_reasoning="r",
        ),
    )

    results = await get_concepts_with_scores(db, sort_by="score_desc")
    assert len(results) == 2
    assert results[0].title == "High Score"
    assert results[1].title == "Low Score"

    results_asc = await get_concepts_with_scores(db, sort_by="score_asc")
    assert results_asc[0].title == "Low Score"
    assert results_asc[1].title == "High Score"
