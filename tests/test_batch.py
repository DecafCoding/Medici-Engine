"""
Tests for the batch runner service.

Verifies that BatchRunner correctly orchestrates the full pipeline
(conversation -> synthesis -> scoring), handles failures gracefully,
and tracks batch progress. All LLM calls are mocked.
"""

from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from src.batch.models import BatchRequest
from src.batch.runner import BatchRunner
from src.db.queries import (
    BatchCreate,
    create_batch,
    get_batch_by_id,
    get_concepts,
    get_runs_by_batch_id,
    get_scores,
)
from src.engine.conversation import ConversationError


@pytest.fixture
def mock_conversation_runner(test_transcript):
    """Mock ConversationRunner.run to return a fixed transcript."""
    with patch("src.batch.runner.ConversationRunner") as mock_cls:
        instance = mock_cls.return_value
        instance.run = AsyncMock(return_value=test_transcript)
        yield instance


@pytest.fixture
def mock_synthesizer(test_concept_extraction):
    """Mock Synthesizer.synthesize to return a fixed extraction."""
    with patch("src.batch.runner.Synthesizer") as mock_cls:
        instance = mock_cls.return_value
        instance.synthesize = AsyncMock(return_value=test_concept_extraction)
        yield instance


@pytest.fixture
def mock_scorer(test_concept_scoring):
    """Mock Scorer.score to return a fixed scoring result."""
    with patch("src.batch.runner.Scorer") as mock_cls:
        instance = mock_cls.return_value
        instance.score = AsyncMock(return_value=test_concept_scoring)
        yield instance


@pytest.fixture
def api_key_set():
    """Ensure settings.openai_api_key is set for synthesis/scoring."""
    with patch("src.batch.runner.settings") as mock_settings:
        mock_settings.openai_api_key = "test-key"
        mock_settings.conversation_temperature = 0.9
        mock_settings.conversation_repetition_penalty = 1.15
        mock_settings.conversation_max_tokens = 512
        yield mock_settings


@pytest.fixture
def api_key_empty():
    """Ensure settings.openai_api_key is empty to skip synthesis/scoring."""
    with patch("src.batch.runner.settings") as mock_settings:
        mock_settings.openai_api_key = ""
        mock_settings.conversation_temperature = 0.9
        mock_settings.conversation_repetition_penalty = 1.15
        mock_settings.conversation_max_tokens = 512
        yield mock_settings


async def _create_test_batch(db, num_runs: int) -> UUID:
    """Create a batch record and return its ID."""
    batch = await create_batch(db, BatchCreate(total_runs=num_runs))
    return batch.id


async def test_single_conversation_batch(
    db,
    mock_conversation_runner,
    mock_synthesizer,
    mock_scorer,
    api_key_set,
):
    """A batch with 1 conversation creates run, concept, score, and completes."""
    batch_id = await _create_test_batch(db, 1)
    request = BatchRequest(
        persona_pairs=[("quantum_information_theorist", "medieval_master_builder")],
        num_conversations=1,
        turns_per_agent=5,
    )

    runner = BatchRunner(db)
    await runner.run_batch(request, batch_id)

    batch = await get_batch_by_id(db, batch_id)
    assert batch is not None
    assert batch.status == "completed"
    assert batch.completed_runs == 1
    assert batch.failed_runs == 0

    runs = await get_runs_by_batch_id(db, batch_id)
    assert len(runs) == 1
    assert runs[0].status == "completed"

    concepts = await get_concepts(db)
    assert len(concepts) == 1

    scores = await get_scores(db)
    assert len(scores) == 1


async def test_multi_conversation_batch(
    db,
    mock_conversation_runner,
    mock_synthesizer,
    mock_scorer,
    api_key_set,
):
    """A batch with 3 conversations creates 3 runs and completes all."""
    batch_id = await _create_test_batch(db, 3)
    request = BatchRequest(
        persona_pairs=[("quantum_information_theorist", "medieval_master_builder")],
        num_conversations=3,
        turns_per_agent=5,
    )

    runner = BatchRunner(db)
    await runner.run_batch(request, batch_id)

    batch = await get_batch_by_id(db, batch_id)
    assert batch is not None
    assert batch.completed_runs == 3
    assert batch.failed_runs == 0
    assert batch.status == "completed"

    runs = await get_runs_by_batch_id(db, batch_id)
    assert len(runs) == 3


async def test_batch_continues_on_conversation_failure(
    db,
    mock_synthesizer,
    mock_scorer,
    api_key_set,
    test_transcript,
):
    """Batch continues past a failed conversation and tracks failures."""
    batch_id = await _create_test_batch(db, 3)
    request = BatchRequest(
        persona_pairs=[("quantum_information_theorist", "medieval_master_builder")],
        num_conversations=3,
        turns_per_agent=5,
    )

    # Fail on 2nd call, succeed on 1st and 3rd
    with patch("src.batch.runner.ConversationRunner") as mock_cls:
        instance = mock_cls.return_value
        instance.run = AsyncMock(
            side_effect=[
                test_transcript,
                ConversationError("vLLM timeout"),
                test_transcript,
            ]
        )

        runner = BatchRunner(db)
        await runner.run_batch(request, batch_id)

    batch = await get_batch_by_id(db, batch_id)
    assert batch is not None
    assert batch.completed_runs == 2
    assert batch.failed_runs == 1
    assert batch.status == "completed"


async def test_batch_with_specified_personas(
    db,
    mock_conversation_runner,
    mock_synthesizer,
    mock_scorer,
    api_key_set,
):
    """Specified persona pairs are used in the created runs."""
    batch_id = await _create_test_batch(db, 1)
    request = BatchRequest(
        persona_pairs=[("jazz_improviser", "deep_sea_ecologist")],
        num_conversations=1,
        turns_per_agent=5,
    )

    runner = BatchRunner(db)
    await runner.run_batch(request, batch_id)

    runs = await get_runs_by_batch_id(db, batch_id)
    assert len(runs) == 1
    assert runs[0].persona_a_name == "jazz_improviser"
    assert runs[0].persona_b_name == "deep_sea_ecologist"


async def test_batch_with_random_personas(
    db,
    mock_conversation_runner,
    mock_synthesizer,
    mock_scorer,
    api_key_set,
):
    """Random persona selection is used when no pairs are specified."""
    batch_id = await _create_test_batch(db, 1)
    request = BatchRequest(
        num_conversations=1,
        turns_per_agent=5,
    )

    with patch("src.batch.runner.get_persona_pair") as mock_pair:
        from src.personas.library import PERSONAS

        mock_pair.return_value = (PERSONAS[0], PERSONAS[1])

        runner = BatchRunner(db)
        await runner.run_batch(request, batch_id)

        mock_pair.assert_called_once()


async def test_batch_skips_synthesis_without_api_key(
    db,
    mock_conversation_runner,
    api_key_empty,
):
    """Synthesis and scoring are skipped when OpenAI API key is empty."""
    batch_id = await _create_test_batch(db, 1)
    request = BatchRequest(
        persona_pairs=[("quantum_information_theorist", "medieval_master_builder")],
        num_conversations=1,
        turns_per_agent=5,
    )

    runner = BatchRunner(db)
    await runner.run_batch(request, batch_id)

    batch = await get_batch_by_id(db, batch_id)
    assert batch is not None
    assert batch.completed_runs == 1
    assert batch.status == "completed"

    concepts = await get_concepts(db)
    assert len(concepts) == 0

    scores = await get_scores(db)
    assert len(scores) == 0


async def test_batch_handles_synthesis_failure(
    db,
    mock_conversation_runner,
    mock_scorer,
    api_key_set,
):
    """Synthesis failure skips scoring but the run still counts as completed."""
    from src.synthesis.synthesizer import SynthesisError

    batch_id = await _create_test_batch(db, 1)
    request = BatchRequest(
        persona_pairs=[("quantum_information_theorist", "medieval_master_builder")],
        num_conversations=1,
        turns_per_agent=5,
    )

    with patch("src.batch.runner.Synthesizer") as mock_cls:
        instance = mock_cls.return_value
        instance.synthesize = AsyncMock(side_effect=SynthesisError("API error"))

        runner = BatchRunner(db)
        await runner.run_batch(request, batch_id)

    batch = await get_batch_by_id(db, batch_id)
    assert batch is not None
    assert batch.completed_runs == 1
    assert batch.failed_runs == 0
    assert batch.status == "completed"

    concepts = await get_concepts(db)
    assert len(concepts) == 0

    # Scorer should not have been called
    mock_scorer.score.assert_not_called()


async def test_batch_handles_scoring_failure(
    db,
    mock_conversation_runner,
    mock_synthesizer,
    api_key_set,
):
    """Scoring failure still creates the concept and completes the run."""
    from src.scoring.scorer import ScoringError

    batch_id = await _create_test_batch(db, 1)
    request = BatchRequest(
        persona_pairs=[("quantum_information_theorist", "medieval_master_builder")],
        num_conversations=1,
        turns_per_agent=5,
    )

    with patch("src.batch.runner.Scorer") as mock_cls:
        instance = mock_cls.return_value
        instance.score = AsyncMock(side_effect=ScoringError("API error"))

        runner = BatchRunner(db)
        await runner.run_batch(request, batch_id)

    batch = await get_batch_by_id(db, batch_id)
    assert batch is not None
    assert batch.completed_runs == 1
    assert batch.failed_runs == 0

    concepts = await get_concepts(db)
    assert len(concepts) == 1

    scores = await get_scores(db)
    assert len(scores) == 0


async def test_batch_with_zero_conversations(
    db,
    mock_conversation_runner,
    mock_synthesizer,
    mock_scorer,
    api_key_set,
):
    """A batch with 0 conversations completes immediately with no runs."""
    batch_id = await _create_test_batch(db, 0)
    request = BatchRequest(
        num_conversations=0,
        turns_per_agent=5,
    )

    runner = BatchRunner(db)
    await runner.run_batch(request, batch_id)

    batch = await get_batch_by_id(db, batch_id)
    assert batch is not None
    assert batch.completed_runs == 0
    assert batch.failed_runs == 0
    # No runs succeeded, so complete_batch marks it "failed"
    assert batch.status == "failed"

    runs = await get_runs_by_batch_id(db, batch_id)
    assert len(runs) == 0

    mock_conversation_runner.run.assert_not_called()


async def test_batch_all_conversations_fail(
    db,
    mock_synthesizer,
    mock_scorer,
    api_key_set,
):
    """Batch with all conversations failing sets status to 'failed'."""
    batch_id = await _create_test_batch(db, 2)
    request = BatchRequest(
        persona_pairs=[("quantum_information_theorist", "medieval_master_builder")],
        num_conversations=2,
        turns_per_agent=5,
    )

    with patch("src.batch.runner.ConversationRunner") as mock_cls:
        instance = mock_cls.return_value
        instance.run = AsyncMock(
            side_effect=ConversationError("vLLM unreachable"),
        )

        runner = BatchRunner(db)
        await runner.run_batch(request, batch_id)

    batch = await get_batch_by_id(db, batch_id)
    assert batch is not None
    assert batch.status == "failed"
    assert batch.completed_runs == 0
    assert batch.failed_runs == 2


async def test_batch_with_specified_shared_objects(
    db,
    mock_conversation_runner,
    mock_synthesizer,
    mock_scorer,
    api_key_set,
):
    """Specified shared object indices select the correct objects."""
    batch_id = await _create_test_batch(db, 1)
    request = BatchRequest(
        persona_pairs=[("quantum_information_theorist", "medieval_master_builder")],
        shared_object_indices=[2],
        num_conversations=1,
        turns_per_agent=5,
    )

    runner = BatchRunner(db)
    await runner.run_batch(request, batch_id)

    runs = await get_runs_by_batch_id(db, batch_id)
    assert len(runs) == 1
    # Index 2 is the third shared object: the ancient library scenario
    assert "ancient library" in runs[0].shared_object_text.lower()
