"""Tests for the API endpoints."""

from src.db.queries import ConceptCreate, RunCreate, create_concept, create_run


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
