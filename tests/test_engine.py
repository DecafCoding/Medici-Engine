"""Tests for the conversation engine.

All vLLM calls are mocked — no real inference happens in tests.
"""

from unittest.mock import AsyncMock, patch

import pytest
from openai import APIConnectionError

from src.db.queries import Turn
from src.engine.conversation import ConversationRunner, InferenceError
from src.engine.models import ConversationConfig, ConversationRequest


async def test_conversation_produces_correct_turn_count(
    test_persona_a,
    test_persona_b,
    test_situation,
    mock_openai_response,
) -> None:
    """Verify a conversation produces the expected number of turns."""
    turns_per_agent = 3
    config = ConversationConfig(turns_per_agent=turns_per_agent)
    request = ConversationRequest(
        persona_a=test_persona_a,
        persona_b=test_persona_b,
        situation=test_situation,
        config=config,
    )

    runner = ConversationRunner()
    mock_create = AsyncMock(
        side_effect=[mock_openai_response(f"Turn {i} response") for i in range(1, 7)],
    )

    with patch.object(runner._client.chat.completions, "create", mock_create):
        turns = await runner.run(request)

    assert len(turns) == turns_per_agent * 2
    assert all(isinstance(t, Turn) for t in turns)


async def test_conversation_alternates_personas(
    test_persona_a,
    test_persona_b,
    test_situation,
    mock_openai_response,
) -> None:
    """Verify personas alternate correctly: A, B, A, B, ..."""
    config = ConversationConfig(turns_per_agent=2)
    request = ConversationRequest(
        persona_a=test_persona_a,
        persona_b=test_persona_b,
        situation=test_situation,
        config=config,
    )

    runner = ConversationRunner()
    mock_create = AsyncMock(
        side_effect=[mock_openai_response(f"Turn {i}") for i in range(1, 5)],
    )

    with patch.object(runner._client.chat.completions, "create", mock_create):
        turns = await runner.run(request)

    assert turns[0].persona_name == test_persona_a.name
    assert turns[1].persona_name == test_persona_b.name
    assert turns[2].persona_name == test_persona_a.name
    assert turns[3].persona_name == test_persona_b.name


async def test_conversation_builds_message_history(
    test_persona_a,
    test_persona_b,
    test_situation,
    mock_openai_response,
) -> None:
    """Verify message history grows with each turn."""
    config = ConversationConfig(turns_per_agent=2)
    request = ConversationRequest(
        persona_a=test_persona_a,
        persona_b=test_persona_b,
        situation=test_situation,
        config=config,
    )

    runner = ConversationRunner()
    mock_create = AsyncMock(
        side_effect=[mock_openai_response(f"Turn {i}") for i in range(1, 5)],
    )

    with patch.object(runner._client.chat.completions, "create", mock_create):
        await runner.run(request)
        call_args_list = mock_create.call_args_list

    # First call: system + opening (2 messages)
    first_messages = call_args_list[0].kwargs.get("messages", [])
    assert len(first_messages) == 2  # system + user/opening

    # Last call should have more messages (system + opening + history)
    last_messages = call_args_list[-1].kwargs.get("messages", [])
    assert len(last_messages) > 2


async def test_conversation_raises_inference_error_on_connection_failure(
    test_persona_a,
    test_persona_b,
    test_situation,
) -> None:
    """Verify InferenceError is raised when vLLM is unreachable."""
    config = ConversationConfig(turns_per_agent=1)
    request = ConversationRequest(
        persona_a=test_persona_a,
        persona_b=test_persona_b,
        situation=test_situation,
        config=config,
    )

    runner = ConversationRunner()
    mock_create = AsyncMock(
        side_effect=APIConnectionError(request=None),
    )

    with (
        patch.object(runner._client.chat.completions, "create", mock_create),
        pytest.raises(InferenceError),
    ):
        await runner.run(request)


async def test_conversation_raises_inference_error_on_empty_response(
    test_persona_a,
    test_persona_b,
    test_situation,
    mock_openai_response,
) -> None:
    """Verify InferenceError is raised when vLLM returns empty content."""
    config = ConversationConfig(turns_per_agent=1)
    request = ConversationRequest(
        persona_a=test_persona_a,
        persona_b=test_persona_b,
        situation=test_situation,
        config=config,
    )

    runner = ConversationRunner()
    empty_response = mock_openai_response("")
    empty_response.choices[0].message.content = ""
    mock_create = AsyncMock(return_value=empty_response)

    with (
        patch.object(runner._client.chat.completions, "create", mock_create),
        pytest.raises(InferenceError),
    ):
        await runner.run(request)
