"""Tests for the API endpoints."""

from src.db.queries import (
    ConceptCreate,
    RunCreate,
    ScoreCreate,
    create_concept,
    create_run,
    create_score,
)


async def test_health_endpoint(client) -> None:
    """Verify the health endpoint returns ok status."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_list_runs_empty(client) -> None:
    """Verify listing runs returns empty list when none exist."""
    response = await client.get("/api/runs")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_concepts_empty(client) -> None:
    """Verify listing concepts returns empty list when none exist."""
    response = await client.get("/api/concepts")
    assert response.status_code == 200
    assert response.json() == []


async def test_get_run_concept(client, db) -> None:
    """Verify a concept can be fetched via the run's concept endpoint."""
    run = await create_run(
        db,
        RunCreate(
            persona_a_name="physicist",
            persona_b_name="builder",
            shared_object_text="A test scenario",
        ),
    )
    concept = await create_concept(
        db,
        ConceptCreate(
            run_id=run.id,
            title="Test Concept",
            premise="Test premise.",
            originality="Test originality.",
        ),
    )

    response = await client.get(f"/api/runs/{run.id}/concept")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Concept"
    assert data["id"] == str(concept.id)


async def _seed_score(db):
    """Helper to create a run, concept, and score for API tests."""
    run = await create_run(
        db,
        RunCreate(
            persona_a_name="physicist",
            persona_b_name="builder",
            shared_object_text="A test scenario",
        ),
    )
    concept = await create_concept(
        db,
        ConceptCreate(
            run_id=run.id,
            title="Scored Concept",
            premise="Test premise.",
            originality="Test originality.",
        ),
    )
    score = await create_score(
        db,
        ScoreCreate(
            concept_id=concept.id,
            uniqueness_score=8.5,
            uniqueness_reasoning="Highly novel.",
            plausibility_score=6.0,
            plausibility_reasoning="Requires extrapolation.",
            compelling_factor_score=7.5,
            compelling_factor_reasoning="Provocative idea.",
        ),
    )
    return run, concept, score


async def test_get_concept_scores(client, db) -> None:
    """Verify scores can be fetched via the concept scores endpoint."""
    _run, concept, _score = await _seed_score(db)

    response = await client.get(f"/api/concepts/{concept.id}/scores")
    assert response.status_code == 200
    data = response.json()
    assert data["uniqueness_score"] == 8.5
    assert data["plausibility_score"] == 6.0
    assert data["compelling_factor_score"] == 7.5
    assert data["concept_id"] == str(concept.id)


async def test_list_scores(client, db) -> None:
    """Verify the scores list endpoint returns seeded data."""
    await _seed_score(db)

    response = await client.get("/api/scores")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["uniqueness_score"] == 8.5
