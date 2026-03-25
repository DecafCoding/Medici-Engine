"""Tests for the web UI routes (batch setup and concept review)."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.db.queries import (
    AxisScoreRecord,
    BatchCreate,
    ConceptCreate,
    RunCreate,
    ScoreCreate,
    Turn,
    complete_run,
    create_batch,
    create_concept,
    create_run,
    create_score,
)
from src.domains.sci_fi_concepts import SCI_FI_CONCEPTS


async def _seed_review_data(db):
    """Create a batch, run, concept, and score for review UI tests."""
    batch = await create_batch(db, BatchCreate(total_runs=1))
    run = await create_run(
        db,
        RunCreate(
            persona_a_name="test_physicist",
            persona_b_name="test_builder",
            shared_object_text="A test scenario",
            batch_id=batch.id,
        ),
    )
    transcript = [
        Turn(
            turn_number=1,
            persona_name="test_physicist",
            content="The interesting question is what information is preserved.",
        ),
        Turn(
            turn_number=2,
            persona_name="test_builder",
            content="Show me where the weight goes.",
        ),
    ]
    await complete_run(db, run.id, transcript)
    concept = await create_concept(
        db,
        ConceptCreate(
            run_id=run.id,
            domain="sci-fi-concepts",
            title="Test Concept",
            fields={
                "title": "Test Concept",
                "premise": "Test premise for review.",
                "originality": "Test originality statement.",
            },
        ),
    )
    score = await create_score(
        db,
        ScoreCreate(
            concept_id=concept.id,
            axes=[
                AxisScoreRecord(
                    axis="uniqueness",
                    label="Uniqueness",
                    score=8.5,
                    reasoning="Novel approach.",
                ),
                AxisScoreRecord(
                    axis="plausibility",
                    label="Scientific Plausibility",
                    score=6.0,
                    reasoning="Plausible with extrapolation.",
                ),
                AxisScoreRecord(
                    axis="compelling_factor",
                    label="Compelling Factor",
                    score=7.5,
                    reasoning="Compelling and provocative.",
                ),
            ],
        ),
    )
    return batch, run, concept, score


# ── Root Redirect ────────────────────────────────────


async def test_root_redirects_to_review(client) -> None:
    """Verify the root URL redirects to the review page."""
    response = await client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/ui/review"


# ── Batch UI Tests ───────────────────────────────────


async def test_batch_page_renders(client) -> None:
    """Verify the batch setup page returns HTML with expected elements."""
    response = await client.get("/ui/batch")
    assert response.status_code == 200
    assert "Batch Setup" in response.text


async def test_batch_page_contains_personas(client) -> None:
    """Verify all persona names appear in the batch setup dropdowns."""
    response = await client.get("/ui/batch")
    assert response.status_code == 200
    assert "quantum_information_theorist" in response.text
    assert "medieval_master_builder" in response.text
    assert "jazz_improviser" in response.text
    assert "deep_sea_ecologist" in response.text


async def test_batch_page_contains_shared_objects(client) -> None:
    """Verify shared objects appear in the batch setup dropdown."""
    response = await client.get("/ui/batch")
    assert response.status_code == 200
    # Check for a snippet from the first shared object
    assert "oldest building" in response.text
    assert "scenario" in response.text


async def test_batch_form_submission(client, db) -> None:
    """Verify batch form submission creates a batch and returns status HTML."""
    with patch("src.ui.routes.BatchRunner") as mock_runner_cls:
        mock_instance = mock_runner_cls.return_value
        mock_instance.run_batch = AsyncMock()

        response = await client.post(
            "/ui/batch",
            data={
                "num_conversations": "1",
                "turns_per_agent": "3",
                "persona_a": "",
                "persona_b": "",
                "shared_object": "",
            },
        )

    assert response.status_code == 200
    # Response should contain batch status HTML
    assert "batch-status" in response.text or "Batch" in response.text


async def test_batch_status_endpoint(client, db) -> None:
    """Verify the batch status polling endpoint returns progress HTML."""
    batch = await create_batch(db, BatchCreate(total_runs=3))

    response = await client.get(f"/ui/batch/{batch.id}/status")
    assert response.status_code == 200
    assert "0/3" in response.text
    assert "running" in response.text


# ── Review UI Tests ──────────────────────────────────


async def test_review_page_renders_empty(client) -> None:
    """Verify the review page renders correctly with no data."""
    with patch("src.ui.routes.get_active_domain", return_value=SCI_FI_CONCEPTS):
        response = await client.get("/ui/review")
    assert response.status_code == 200
    assert "concept-table-body" in response.text
    assert "No concepts found" in response.text


async def test_review_page_renders_with_data(client, db) -> None:
    """Verify the review page shows concept data when seeded."""
    await _seed_review_data(db)

    with patch("src.ui.routes.get_active_domain", return_value=SCI_FI_CONCEPTS):
        response = await client.get("/ui/review")
    assert response.status_code == 200
    assert "Test Concept" in response.text


async def test_review_rows_fragment(client, db) -> None:
    """Verify the rows fragment returns concept data without full page layout."""
    await _seed_review_data(db)

    response = await client.get("/ui/review/rows")
    assert response.status_code == 200
    assert "Test Concept" in response.text
    # Fragment should not contain the full page layout
    assert "<!DOCTYPE" not in response.text


async def test_review_filter_by_status(client, db) -> None:
    """Verify filtering review rows by status works correctly."""
    await _seed_review_data(db)

    # Pending concept should appear
    response = await client.get("/ui/review/rows?status=pending")
    assert response.status_code == 200
    assert "Test Concept" in response.text

    # Kept filter should show no concepts (none are kept yet)
    response = await client.get("/ui/review/rows?status=kept")
    assert response.status_code == 200
    assert "No concepts found" in response.text


async def test_review_sort_by_score(client, db) -> None:
    """Verify sorting by score orders concepts correctly."""
    # Create first concept with low score
    run1 = await create_run(
        db,
        RunCreate(
            persona_a_name="a",
            persona_b_name="b",
            shared_object_text="test",
        ),
    )
    concept1 = await create_concept(
        db,
        ConceptCreate(
            run_id=run1.id,
            domain="sci-fi-concepts",
            title="Low Score Concept",
            fields={"title": "Low Score Concept", "premise": "p", "originality": "o"},
        ),
    )
    await create_score(
        db,
        ScoreCreate(
            concept_id=concept1.id,
            axes=[
                AxisScoreRecord(
                    axis="uniqueness", label="Uniqueness", score=2.0, reasoning="r"
                ),
                AxisScoreRecord(
                    axis="plausibility", label="Plausibility", score=2.0, reasoning="r"
                ),
                AxisScoreRecord(
                    axis="compelling_factor",
                    label="Compelling Factor",
                    score=2.0,
                    reasoning="r",
                ),
            ],
        ),
    )

    # Create second concept with high score
    run2 = await create_run(
        db,
        RunCreate(
            persona_a_name="c",
            persona_b_name="d",
            shared_object_text="test2",
        ),
    )
    concept2 = await create_concept(
        db,
        ConceptCreate(
            run_id=run2.id,
            domain="sci-fi-concepts",
            title="High Score Concept",
            fields={
                "title": "High Score Concept",
                "premise": "p",
                "originality": "o",
            },
        ),
    )
    await create_score(
        db,
        ScoreCreate(
            concept_id=concept2.id,
            axes=[
                AxisScoreRecord(
                    axis="uniqueness", label="Uniqueness", score=9.0, reasoning="r"
                ),
                AxisScoreRecord(
                    axis="plausibility", label="Plausibility", score=9.0, reasoning="r"
                ),
                AxisScoreRecord(
                    axis="compelling_factor",
                    label="Compelling Factor",
                    score=9.0,
                    reasoning="r",
                ),
            ],
        ),
    )

    response = await client.get("/ui/review/rows?sort=score_desc")
    assert response.status_code == 200
    text = response.text
    # High score concept should appear before low score concept
    high_pos = text.find("High Score Concept")
    low_pos = text.find("Low Score Concept")
    assert high_pos < low_pos


# ── Concept Detail Tests ─────────────────────────────


async def test_concept_detail_page(client, db) -> None:
    """Verify the concept detail page shows all expected content."""
    _batch, _run, concept, _score = await _seed_review_data(db)

    with patch("src.ui.routes.get_active_domain", return_value=SCI_FI_CONCEPTS):
        response = await client.get(f"/ui/review/{concept.id}")
    assert response.status_code == 200
    assert "Test Concept" in response.text
    assert "Test premise for review." in response.text
    assert "Test originality statement." in response.text
    assert "8.5" in response.text
    assert "6.0" in response.text
    assert "7.5" in response.text
    assert "Novel approach." in response.text
    assert "Plausible with extrapolation." in response.text


async def test_concept_detail_not_found(client) -> None:
    """Verify a 404 is returned for a nonexistent concept ID."""
    response = await client.get(f"/ui/review/{uuid4()}")
    assert response.status_code == 404


async def test_transcript_lazy_load(client, db) -> None:
    """Verify the transcript fragment returns turn content."""
    _batch, _run, concept, _score = await _seed_review_data(db)

    response = await client.get(f"/ui/review/{concept.id}/transcript")
    assert response.status_code == 200
    assert "test_physicist" in response.text
    assert "what information is preserved" in response.text
    assert "where the weight goes" in response.text


async def test_transcript_not_found(client) -> None:
    """Verify transcript endpoint returns 404 for nonexistent concept."""
    response = await client.get(f"/ui/review/{uuid4()}/transcript")
    assert response.status_code == 404


async def test_transcript_no_transcript(client, db) -> None:
    """Verify transcript fragment shows fallback when run has no transcript."""
    run = await create_run(
        db,
        RunCreate(
            persona_a_name="a",
            persona_b_name="b",
            shared_object_text="test",
        ),
    )
    concept = await create_concept(
        db,
        ConceptCreate(
            run_id=run.id,
            domain="sci-fi-concepts",
            title="No Transcript",
            fields={"title": "No Transcript", "premise": "p", "originality": "o"},
        ),
    )

    response = await client.get(f"/ui/review/{concept.id}/transcript")
    assert response.status_code == 200
    assert "No transcript available" in response.text


# ── Status Toggle Tests ──────────────────────────────


async def test_status_toggle_keep(client, db) -> None:
    """Verify toggling status to 'kept' updates the concept."""
    _batch, _run, concept, _score = await _seed_review_data(db)

    response = await client.patch(
        f"/ui/review/{concept.id}/status",
        data={"status": "kept"},
    )
    assert response.status_code == 200
    assert "kept" in response.text


async def test_status_toggle_discard(client, db) -> None:
    """Verify toggling status to 'discarded' updates the concept."""
    _batch, _run, concept, _score = await _seed_review_data(db)

    response = await client.patch(
        f"/ui/review/{concept.id}/status",
        data={"status": "discarded"},
    )
    assert response.status_code == 200
    assert "discarded" in response.text


# ── Insights UI Tests ───────────────────────────────


async def test_insights_page_renders_empty(client) -> None:
    """Verify the insights page renders correctly with no data."""
    response = await client.get("/ui/insights")
    assert response.status_code == 200
    assert "Pairing Performance" in response.text
    assert "Shared Object Performance" in response.text
    assert "No pairing data available." in response.text
    assert "No shared object data available." in response.text


async def test_insights_page_renders_with_data(client, db) -> None:
    """Verify the insights page shows performance data when seeded."""
    await _seed_review_data(db)

    response = await client.get("/ui/insights")
    assert response.status_code == 200
    assert "test_builder" in response.text
    assert "test_physicist" in response.text
    assert "A test scenario" in response.text


async def test_insights_pairing_fragment(client, db) -> None:
    """Verify the pairing fragment returns data without full page layout."""
    await _seed_review_data(db)

    response = await client.get("/ui/insights/pairings")
    assert response.status_code == 200
    assert "test_builder" in response.text
    assert "<!DOCTYPE" not in response.text


async def test_insights_shared_object_fragment(client, db) -> None:
    """Verify the shared object fragment returns data without full page layout."""
    await _seed_review_data(db)

    response = await client.get("/ui/insights/shared-objects")
    assert response.status_code == 200
    assert "A test scenario" in response.text
    assert "<!DOCTYPE" not in response.text


async def test_insights_domain_filter(client, db) -> None:
    """Verify domain filter returns only matching domain data."""
    await _seed_review_data(db)

    # Filter by domain that has data
    response = await client.get("/ui/insights/pairings?domain=sci-fi-concepts")
    assert response.status_code == 200
    assert "test_builder" in response.text

    # Filter by domain with no data
    response = await client.get("/ui/insights/pairings?domain=product-design")
    assert response.status_code == 200
    assert "No pairing data available." in response.text


async def test_insights_nav_link_present(client) -> None:
    """Verify the Insights nav link appears on all pages."""
    response = await client.get("/ui/batch")
    assert response.status_code == 200
    assert 'href="/ui/insights"' in response.text
