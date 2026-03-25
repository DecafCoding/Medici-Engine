"""Tests for the scorer module.

All OpenAI API calls are mocked — no real inference happens in tests.
"""

from unittest.mock import AsyncMock, patch

import pytest
from openai import APIConnectionError

from src.db.queries import AxisScoreRecord
from src.domains.sci_fi_concepts import SCI_FI_CONCEPTS
from src.scoring.scorer import EvaluationError, Scorer


async def test_scorer_returns_axis_score_records_on_success(
    test_scoring_result,
    mock_scoring_parse_response,
) -> None:
    """Verify the scorer returns a list of AxisScoreRecord with all axes."""
    scorer = Scorer(SCI_FI_CONCEPTS)
    mock_parse = AsyncMock(
        return_value=mock_scoring_parse_response(scores=test_scoring_result),
    )

    with patch.object(scorer._client.beta.chat.completions, "parse", mock_parse):
        result = await scorer.score(
            fields={
                "title": "The Architecture of Forgetting",
                "premise": "Buildings that preserve by decaying.",
                "originality": "Combines structural failure with information theory.",
            },
        )

    assert isinstance(result, list)
    assert len(result) == 3
    axes = {r.axis for r in result}
    assert axes == {"uniqueness", "plausibility", "compelling_factor"}
    for record in result:
        assert isinstance(record, AxisScoreRecord)
        assert record.reasoning


async def test_scorer_raises_on_refusal(
    mock_scoring_parse_response,
) -> None:
    """Verify EvaluationError is raised when the model refuses to score."""
    scorer = Scorer(SCI_FI_CONCEPTS)
    mock_parse = AsyncMock(
        return_value=mock_scoring_parse_response(
            scores=None,
            refusal="Content policy violation",
        ),
    )

    with (
        patch.object(scorer._client.beta.chat.completions, "parse", mock_parse),
        pytest.raises(EvaluationError, match="refused"),
    ):
        await scorer.score(
            fields={
                "title": "Test Title",
                "premise": "Test premise.",
                "originality": "Test originality.",
            },
        )


async def test_scorer_raises_on_api_connection_error() -> None:
    """Verify EvaluationError is raised when the OpenAI API is unreachable."""
    scorer = Scorer(SCI_FI_CONCEPTS)
    mock_parse = AsyncMock(
        side_effect=APIConnectionError(request=None),
    )

    with (
        patch.object(scorer._client.beta.chat.completions, "parse", mock_parse),
        pytest.raises(EvaluationError),
    ):
        await scorer.score(
            fields={
                "title": "Test Title",
                "premise": "Test premise.",
                "originality": "Test originality.",
            },
        )


def test_scorer_builds_messages_with_system_and_user() -> None:
    """Verify message structure has a system prompt and user content."""
    scorer = Scorer(SCI_FI_CONCEPTS)
    messages = scorer._build_messages(
        fields={
            "title": "The Architecture of Forgetting",
            "premise": "Buildings that preserve by decaying.",
            "originality": "Combines structural failure with information theory.",
        },
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == SCI_FI_CONCEPTS.scoring_prompt
    assert messages[1]["role"] == "user"
    assert "The Architecture of Forgetting" in messages[1]["content"]
    assert "Buildings that preserve by decaying." in messages[1]["content"]
    assert (
        "Combines structural failure with information theory." in messages[1]["content"]
    )


def test_scoring_prompt_contains_evaluation_instructions() -> None:
    """Verify the scoring prompt instructs evaluation across all axes."""
    prompt_lower = SCI_FI_CONCEPTS.scoring_prompt.lower()
    assert "uniqueness" in prompt_lower
    assert "plausibility" in prompt_lower
    assert "compelling factor" in prompt_lower
    assert "0.0" in SCI_FI_CONCEPTS.scoring_prompt
    assert "10.0" in SCI_FI_CONCEPTS.scoring_prompt


def test_scorer_scores_are_within_range(test_scoring_result) -> None:
    """Verify fixture scores are within the valid 0.0-10.0 range."""
    for record in test_scoring_result:
        assert 0.0 <= record.score <= 10.0, (
            f"{record.axis} score {record.score} is outside valid range 0.0-10.0"
        )
