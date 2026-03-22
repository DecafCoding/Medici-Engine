"""Tests for the database schema and query layer."""

from uuid import UUID, uuid4

from src.db.queries import (
    RunCreate,
    Turn,
    complete_run,
    create_run,
    fail_run,
    get_recent_pairings,
    get_run_by_id,
    get_runs,
    record_pairing,
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
