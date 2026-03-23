"""Tests for the scorer module.

All OpenAI API calls are mocked — no real inference happens in tests.
"""

from unittest.mock import AsyncMock, patch

import pytest
from openai import APIConnectionError

from src.scoring.scorer import SCORING_PROMPT, EvaluationError, Scorer


async def test_scorer_returns_concept_scoring_on_success(
    test_concept_scoring,
    mock_scoring_response,
) -> None:
    """Verify the scorer returns a ConceptScoring with all three axes."""
    scorer = Scorer()
    mock_parse = AsyncMock(
        return_value=mock_scoring_response(scoring=test_concept_scoring),
    )

    with patch.object(scorer._client.beta.chat.completions, "parse", mock_parse):
        result = await scorer.score(
            title="The Architecture of Forgetting",
            premise="Buildings that preserve by decaying.",
            originality="Combines structural failure with information theory.",
        )

    assert result.uniqueness.score == test_concept_scoring.uniqueness.score
    assert result.uniqueness.reasoning == test_concept_scoring.uniqueness.reasoning
    assert result.plausibility.score == test_concept_scoring.plausibility.score
    assert (
        result.compelling_factor.score == test_concept_scoring.compelling_factor.score
    )


async def test_scorer_raises_on_refusal(
    mock_scoring_response,
) -> None:
    """Verify EvaluationError is raised when the model refuses to score."""
    scorer = Scorer()
    mock_parse = AsyncMock(
        return_value=mock_scoring_response(
            scoring=None,
            refusal="Content policy violation",
        ),
    )

    with (
        patch.object(scorer._client.beta.chat.completions, "parse", mock_parse),
        pytest.raises(EvaluationError, match="refused"),
    ):
        await scorer.score(
            title="Test Title",
            premise="Test premise.",
            originality="Test originality.",
        )


async def test_scorer_raises_on_api_connection_error() -> None:
    """Verify EvaluationError is raised when the OpenAI API is unreachable."""
    scorer = Scorer()
    mock_parse = AsyncMock(
        side_effect=APIConnectionError(request=None),
    )

    with (
        patch.object(scorer._client.beta.chat.completions, "parse", mock_parse),
        pytest.raises(EvaluationError),
    ):
        await scorer.score(
            title="Test Title",
            premise="Test premise.",
            originality="Test originality.",
        )


def test_scorer_builds_messages_with_system_and_user() -> None:
    """Verify message structure has a system prompt and user content."""
    scorer = Scorer()
    messages = scorer._build_messages(
        title="The Architecture of Forgetting",
        premise="Buildings that preserve by decaying.",
        originality="Combines structural failure with information theory.",
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "The Architecture of Forgetting" in messages[1]["content"]
    assert "Buildings that preserve by decaying." in messages[1]["content"]
    assert (
        "Combines structural failure with information theory." in messages[1]["content"]
    )


def test_scoring_prompt_contains_evaluation_instructions() -> None:
    """Verify the scoring prompt instructs evaluation across all axes."""
    prompt_lower = SCORING_PROMPT.lower()
    assert "uniqueness" in prompt_lower
    assert "plausibility" in prompt_lower
    assert "compelling factor" in prompt_lower
    assert "0.0" in SCORING_PROMPT
    assert "10.0" in SCORING_PROMPT


def test_scorer_scores_are_within_range(test_concept_scoring) -> None:
    """Verify fixture scores are within the valid 0.0-10.0 range."""
    for axis in [
        test_concept_scoring.uniqueness,
        test_concept_scoring.plausibility,
        test_concept_scoring.compelling_factor,
    ]:
        assert 0.0 <= axis.score <= 10.0, (
            f"{axis.axis} score {axis.score} is outside valid range 0.0-10.0"
        )
