"""Tests for analytics queries (pairing and shared object performance)."""

import pytest

from src.db.queries import (
    AxisScoreRecord,
    ConceptCreate,
    PairingPerformance,
    RunCreate,
    ScoreCreate,
    SharedObjectPerformance,
    Turn,
    complete_run,
    create_concept,
    create_run,
    create_score,
    get_pairing_performance,
    get_shared_object_performance,
    update_concept_status,
)

# ── Helpers ──────────────────────────────────────────


async def _seed_run(
    db,
    persona_a: str = "physicist",
    persona_b: str = "builder",
    shared_object_text: str = "A test scenario",
    shared_object_type: str = "scenario",
    turns_per_agent: int = 5,
):
    """Create a run, complete it, and return the run record."""
    run = await create_run(
        db,
        RunCreate(
            persona_a_name=persona_a,
            persona_b_name=persona_b,
            shared_object_text=shared_object_text,
            shared_object_type=shared_object_type,
            turns_per_agent=turns_per_agent,
        ),
    )
    transcript = [
        Turn(turn_number=1, persona_name=persona_a, content="Turn 1"),
        Turn(turn_number=2, persona_name=persona_b, content="Turn 2"),
    ]
    return await complete_run(db, run.id, transcript)


def _make_axes(score: float = 7.0) -> list[AxisScoreRecord]:
    """Build a uniform test score across three axes."""
    return [
        AxisScoreRecord(
            axis="uniqueness",
            label="Uniqueness",
            score=score,
            reasoning="Test.",
        ),
        AxisScoreRecord(
            axis="plausibility",
            label="Plausibility",
            score=score,
            reasoning="Test.",
        ),
        AxisScoreRecord(
            axis="compelling_factor",
            label="Compelling Factor",
            score=score,
            reasoning="Test.",
        ),
    ]


async def _seed_full_pipeline(
    db,
    persona_a: str = "physicist",
    persona_b: str = "builder",
    shared_object_text: str = "A test scenario",
    domain: str = "sci-fi-concepts",
    score_value: float = 7.0,
    concept_status: str = "pending",
):
    """Seed a run -> concept -> score and optionally review the concept."""
    run = await _seed_run(
        db,
        persona_a=persona_a,
        persona_b=persona_b,
        shared_object_text=shared_object_text,
    )
    concept = await create_concept(
        db,
        ConceptCreate(
            run_id=run.id,
            domain=domain,
            title=f"Concept from {persona_a} + {persona_b}",
            fields={"title": "Test", "premise": "Test", "originality": "Test"},
        ),
    )
    await create_score(
        db,
        ScoreCreate(concept_id=concept.id, axes=_make_axes(score_value)),
    )
    if concept_status != "pending":
        await update_concept_status(db, concept.id, concept_status)
    return run, concept


# ── Pairing Performance Tests ──────────────────────


async def test_pairing_performance_empty_db(db) -> None:
    """Returns empty list when no runs exist."""
    results = await get_pairing_performance(db)
    assert results == []


async def test_pairing_performance_single_kept_concept(db) -> None:
    """Returns correct counts and score for a single kept concept."""
    await _seed_full_pipeline(db, concept_status="kept", score_value=8.0)

    results = await get_pairing_performance(db)
    assert len(results) == 1
    r = results[0]
    assert isinstance(r, PairingPerformance)
    assert r.total_runs == 1
    assert r.completed_runs == 1
    assert r.concepts_kept == 1
    assert r.concepts_discarded == 0
    assert r.concepts_pending == 0
    assert r.avg_score == 8.0
    assert r.max_score == 8.0


async def test_pairing_performance_multiple_runs_same_pairing(db) -> None:
    """Aggregates correctly across multiple runs for the same pairing."""
    await _seed_full_pipeline(
        db,
        score_value=6.0,
        concept_status="kept",
    )
    await _seed_full_pipeline(
        db,
        score_value=8.0,
        concept_status="discarded",
    )

    results = await get_pairing_performance(db)
    assert len(results) == 1
    r = results[0]
    assert r.total_runs == 2
    assert r.concepts_kept == 1
    assert r.concepts_discarded == 1
    assert r.avg_score == 7.0


async def test_pairing_performance_normalizes_persona_order(db) -> None:
    """(A,B) and (B,A) aggregate together as the same pairing."""
    await _seed_full_pipeline(
        db,
        persona_a="physicist",
        persona_b="builder",
        score_value=6.0,
        concept_status="kept",
    )
    # Reversed order
    await _seed_full_pipeline(
        db,
        persona_a="builder",
        persona_b="physicist",
        score_value=8.0,
        concept_status="kept",
    )

    results = await get_pairing_performance(db)
    assert len(results) == 1
    r = results[0]
    assert r.total_runs == 2
    assert r.concepts_kept == 2
    # Sorted names
    assert r.persona_a_name == "builder"
    assert r.persona_b_name == "physicist"


async def test_pairing_performance_filters_by_domain(db) -> None:
    """Domain filter only includes concepts from the specified domain."""
    await _seed_full_pipeline(
        db,
        domain="sci-fi-concepts",
        score_value=9.0,
        concept_status="kept",
    )
    await _seed_full_pipeline(
        db,
        persona_a="chef",
        persona_b="dancer",
        domain="product-design",
        score_value=5.0,
        concept_status="kept",
    )

    results = await get_pairing_performance(db, domain="sci-fi-concepts")
    assert len(results) == 1
    assert results[0].avg_score == 9.0

    results_pd = await get_pairing_performance(db, domain="product-design")
    assert len(results_pd) == 1
    assert results_pd[0].avg_score == 5.0


async def test_pairing_performance_min_runs_filter(db) -> None:
    """Pairings below the min_runs threshold are excluded."""
    await _seed_full_pipeline(db, score_value=7.0)
    # Only 1 run for this pairing
    await _seed_full_pipeline(
        db,
        persona_a="chef",
        persona_b="dancer",
        score_value=9.0,
    )
    await _seed_full_pipeline(
        db,
        persona_a="chef",
        persona_b="dancer",
        score_value=8.0,
    )

    results = await get_pairing_performance(db, min_runs=2)
    assert len(results) == 1
    assert results[0].persona_a_name == "chef"


async def test_pairing_performance_kept_rate_calculation(db) -> None:
    """kept_rate = kept / (kept + discarded)."""
    await _seed_full_pipeline(db, concept_status="kept", score_value=8.0)
    await _seed_full_pipeline(db, concept_status="kept", score_value=7.0)
    await _seed_full_pipeline(db, concept_status="discarded", score_value=3.0)

    results = await get_pairing_performance(db)
    assert len(results) == 1
    # 2 kept, 1 discarded -> 2/3
    assert results[0].kept_rate == pytest.approx(2 / 3, abs=0.001)


async def test_pairing_performance_no_reviewed_concepts_null_kept_rate(db) -> None:
    """kept_rate is None when all concepts are still pending."""
    await _seed_full_pipeline(db, concept_status="pending")

    results = await get_pairing_performance(db)
    assert len(results) == 1
    assert results[0].kept_rate is None


# ── Shared Object Performance Tests ──────────────────


async def test_shared_object_performance_empty_db(db) -> None:
    """Returns empty list when no runs exist."""
    results = await get_shared_object_performance(db)
    assert results == []


async def test_shared_object_performance_aggregates_correctly(db) -> None:
    """Returns correct counts and scores for a shared object."""
    shared = "A bridge hums at midnight"
    await _seed_full_pipeline(
        db,
        shared_object_text=shared,
        score_value=8.0,
        concept_status="kept",
    )
    await _seed_full_pipeline(
        db,
        persona_a="chef",
        persona_b="dancer",
        shared_object_text=shared,
        score_value=6.0,
        concept_status="discarded",
    )

    results = await get_shared_object_performance(db)
    assert len(results) == 1
    r = results[0]
    assert isinstance(r, SharedObjectPerformance)
    assert r.shared_object_text == shared
    assert r.total_runs == 2
    assert r.completed_runs == 2
    assert r.concepts_kept == 1
    assert r.concepts_discarded == 1
    assert r.avg_score == 7.0
    assert r.max_score == 8.0
    assert r.kept_rate == pytest.approx(0.5)


async def test_shared_object_performance_filters_by_domain(db) -> None:
    """Domain filter only includes concepts from the specified domain."""
    shared = "A signal from deep space"
    await _seed_full_pipeline(
        db,
        shared_object_text=shared,
        domain="sci-fi-concepts",
        score_value=9.0,
        concept_status="kept",
    )
    await _seed_full_pipeline(
        db,
        persona_a="chef",
        persona_b="dancer",
        shared_object_text=shared,
        domain="product-design",
        score_value=4.0,
        concept_status="kept",
    )

    results = await get_shared_object_performance(db, domain="sci-fi-concepts")
    assert len(results) == 1
    assert results[0].avg_score == 9.0
