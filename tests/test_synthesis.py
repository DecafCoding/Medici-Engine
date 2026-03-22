"""Tests for the synthesizer module.

All OpenAI API calls are mocked — no real inference happens in tests.
"""

from unittest.mock import AsyncMock, patch

import pytest
from openai import APIConnectionError

from src.synthesis.synthesizer import SYNTHESIS_PROMPT, ExtractionError, Synthesizer


async def test_synthesizer_extracts_concept_from_transcript(
    test_transcript,
    test_concept_extraction,
    mock_parse_response,
) -> None:
    """Verify the synthesizer returns a ConceptExtraction on success."""
    synthesizer = Synthesizer()
    mock_parse = AsyncMock(
        return_value=mock_parse_response(extraction=test_concept_extraction),
    )

    with patch.object(synthesizer._client.beta.chat.completions, "parse", mock_parse):
        result = await synthesizer.synthesize(
            transcript=test_transcript,
            persona_a_name="test_physicist",
            persona_b_name="test_builder",
            shared_object_text="A bridge that hums.",
        )

    assert result.title == test_concept_extraction.title
    assert result.premise == test_concept_extraction.premise
    assert result.originality == test_concept_extraction.originality


async def test_synthesizer_raises_on_refusal(
    test_transcript,
    mock_parse_response,
) -> None:
    """Verify ExtractionError is raised when the model refuses extraction."""
    synthesizer = Synthesizer()
    mock_parse = AsyncMock(
        return_value=mock_parse_response(
            extraction=None,
            refusal="Content policy violation",
        ),
    )

    with (
        patch.object(synthesizer._client.beta.chat.completions, "parse", mock_parse),
        pytest.raises(ExtractionError, match="refused"),
    ):
        await synthesizer.synthesize(
            transcript=test_transcript,
            persona_a_name="test_physicist",
            persona_b_name="test_builder",
            shared_object_text="A bridge that hums.",
        )


async def test_synthesizer_raises_on_api_connection_error(
    test_transcript,
) -> None:
    """Verify ExtractionError is raised when the OpenAI API is unreachable."""
    synthesizer = Synthesizer()
    mock_parse = AsyncMock(
        side_effect=APIConnectionError(request=None),
    )

    with (
        patch.object(synthesizer._client.beta.chat.completions, "parse", mock_parse),
        pytest.raises(ExtractionError),
    ):
        await synthesizer.synthesize(
            transcript=test_transcript,
            persona_a_name="test_physicist",
            persona_b_name="test_builder",
            shared_object_text="A bridge that hums.",
        )


def test_synthesizer_formats_transcript_correctly(test_transcript) -> None:
    """Verify _format_transcript produces readable labeled text."""
    synthesizer = Synthesizer()
    formatted = synthesizer._format_transcript(test_transcript)

    assert "[Turn 1] test_physicist:" in formatted
    assert "[Turn 2] test_builder:" in formatted
    assert "information is being preserved" in formatted
    assert "Show me where the weight goes" in formatted


def test_synthesizer_builds_messages_with_system_and_user(
    test_transcript,
) -> None:
    """Verify message structure has a system prompt and user transcript."""
    synthesizer = Synthesizer()
    formatted = synthesizer._format_transcript(test_transcript)
    messages = synthesizer._build_messages(
        formatted_transcript=formatted,
        persona_a_name="test_physicist",
        persona_b_name="test_builder",
        shared_object_text="A bridge that hums.",
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "test_physicist" in messages[1]["content"]
    assert "test_builder" in messages[1]["content"]
    assert "A bridge that hums." in messages[1]["content"]


def test_synthesis_prompt_contains_extraction_instructions() -> None:
    """Verify the synthesis prompt instructs concept extraction."""
    assert "transferable principles" in SYNTHESIS_PROMPT.lower()
    assert "reframing" in SYNTHESIS_PROMPT.lower()
    assert "novel compound concepts" in SYNTHESIS_PROMPT.lower()
    assert "title" in SYNTHESIS_PROMPT.lower()
    assert "premise" in SYNTHESIS_PROMPT.lower()
    assert "originality" in SYNTHESIS_PROMPT.lower()
