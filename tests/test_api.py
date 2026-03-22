"""Tests for the API endpoints."""


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
