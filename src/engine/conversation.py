"""
Conversation runner for the Medici Engine.

Manages turn-taking between two persona agents given a dynamically
generated situation, producing a full conversation transcript. This
module belongs to the Engine layer and communicates with the local
vLLM inference server via an OpenAI-compatible API.
"""

import logging

import httpx
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
)

from src.config import settings
from src.db.queries import Turn
from src.engine.models import ConversationConfig, ConversationRequest
from src.personas.models import Persona, Situation

logger = logging.getLogger(__name__)


class ConversationError(Exception):
    """Raised when the conversation runner encounters a non-recoverable error."""


class InferenceError(ConversationError):
    """Raised when the local vLLM server fails to respond."""


class ConversationRunner:
    """Orchestrates a multi-turn conversation between two persona agents.

    Takes two fully specified personas and a situation, manages
    turn-taking for a configurable number of exchanges, and returns
    the complete transcript. Communicates with the local inference
    server via the OpenAI-compatible client.
    """

    def __init__(self) -> None:
        """Initialize the conversation runner with a vLLM client."""
        # vLLM serves an OpenAI-compatible API, so we use the standard client
        # with a base_url override
        self._client = AsyncOpenAI(
            base_url=settings.vllm_base_url,
            api_key="unused",
            timeout=httpx.Timeout(120.0, connect=5.0),
            max_retries=2,
        )

    async def run(self, request: ConversationRequest) -> list[Turn]:
        """Run a full conversation between two personas on a situation.

        Alternates turns between persona_a and persona_b, building up
        a shared message history. Each agent sees the full conversation
        so far from their own perspective.

        Args:
            request: Complete conversation specification including
                personas, situation, and generation config.

        Returns:
            Ordered list of conversation turns.

        Raises:
            ConversationError: If the conversation cannot be completed.
            InferenceError: If the vLLM server fails to respond.
        """
        persona_a = request.persona_a
        persona_b = request.persona_b
        situation = request.situation
        config = request.config

        logger.info(
            "Starting conversation",
            extra={
                "persona_a": persona_a.name,
                "persona_b": persona_b.name,
                "situation_type": situation.situation_type,
                "turns_per_agent": config.turns_per_agent,
            },
        )

        turns: list[Turn] = []
        total_turns = config.turns_per_agent * 2

        for turn_number in range(1, total_turns + 1):
            # Alternate between personas: odd turns = A, even turns = B
            is_persona_a = turn_number % 2 == 1
            active_persona = persona_a if is_persona_a else persona_b
            other_persona = persona_b if is_persona_a else persona_a

            try:
                content = await self._generate_turn(
                    active_persona=active_persona,
                    other_persona=other_persona,
                    situation=situation,
                    turns=turns,
                    turn_number=turn_number,
                    config=config,
                )
            except InferenceError:
                logger.error(
                    "Aborting conversation due to inference failure",
                    extra={
                        "turn_number": turn_number,
                        "persona": active_persona.name,
                    },
                )
                raise

            turn = Turn(
                turn_number=turn_number,
                persona_name=active_persona.name,
                content=content,
            )
            turns.append(turn)

            logger.debug(
                "Turn completed",
                extra={
                    "turn_number": turn_number,
                    "persona": active_persona.name,
                    "content_length": len(content),
                },
            )

        logger.info(
            "Conversation completed",
            extra={
                "persona_a": persona_a.name,
                "persona_b": persona_b.name,
                "total_turns": len(turns),
            },
        )

        return turns

    async def _generate_turn(
        self,
        active_persona: Persona,
        other_persona: Persona,
        situation: Situation,
        turns: list[Turn],
        turn_number: int,
        config: ConversationConfig,
    ) -> str:
        """Generate a single conversation turn from the vLLM server.

        Builds the message history from the active persona's perspective
        and calls the local inference server.

        Args:
            active_persona: The persona generating this turn.
            other_persona: The other persona in the conversation.
            situation: The situation seeding the conversation.
            turns: All previous turns in the conversation.
            turn_number: Current turn number (1-indexed).
            config: Generation parameters.

        Returns:
            The generated text content for this turn.

        Raises:
            InferenceError: If the vLLM server fails to respond.
        """
        messages = self._build_messages(
            active_persona=active_persona,
            other_persona=other_persona,
            situation=situation,
            turns=turns,
            turn_number=turn_number,
        )

        try:
            response = await self._client.chat.completions.create(
                model=settings.conversation_model,
                messages=messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                extra_body={"repetition_penalty": config.repetition_penalty},
            )
        except APIConnectionError as e:
            raise InferenceError(
                f"Cannot reach vLLM server at {settings.vllm_base_url}: {e}"
            ) from e
        except APITimeoutError as e:
            raise InferenceError(
                f"vLLM request timed out on turn {turn_number}: {e}"
            ) from e
        except APIStatusError as e:
            raise InferenceError(
                f"vLLM returned status {e.status_code} on turn {turn_number}: "
                f"{e.message}"
            ) from e

        content = response.choices[0].message.content
        if not content:
            raise InferenceError(f"vLLM returned empty content on turn {turn_number}")

        return content.strip()

    def _build_messages(
        self,
        active_persona: Persona,
        other_persona: Persona,
        situation: Situation,
        turns: list[Turn],
        turn_number: int,
    ) -> list[dict[str, str]]:
        """Build the chat messages array for a turn.

        Constructs the message history from the active persona's
        perspective: their system prompt, the situation as the
        opening user message, then alternating assistant/user roles
        for previous turns.

        Args:
            active_persona: The persona generating this turn.
            other_persona: The other persona in the conversation.
            situation: The situation seeding the conversation.
            turns: All previous turns in the conversation.
            turn_number: Current turn number.

        Returns:
            List of message dicts ready for the OpenAI chat API.
        """
        messages: list[dict[str, str]] = [
            {"role": "system", "content": active_persona.to_system_prompt()},
        ]

        # Opening context: present the situation and conversation framing
        opening = (
            f"You're in a conversation with someone very different from you — "
            f"{other_persona.title}. One of you has been wrestling with a problem "
            f"and described it like this:\n\n"
            f"---\n{situation.text}\n---\n\n"
        )

        if turn_number == 1:
            # First turn: persona A elaborates on or continues from the situation
            # (the situation was generated from their perspective)
            opening += (
                "This is your problem. You wrote the description above. Now you're "
                "talking to someone outside your field about it. Continue thinking "
                "out loud — what aspects of this are most frustrating? What have "
                "you already tried? Respond naturally as yourself. "
                "Keep it to a short paragraph or two."
            )
            messages.append({"role": "user", "content": opening})
        else:
            if active_persona == other_persona:
                # This branch won't trigger in normal flow, but for clarity:
                # Persona B sees the situation as someone else's problem
                pass

            # For persona B's first turn (turn 2), frame it as encountering
            # someone else's problem
            if turn_number == 2:
                opening += (
                    "Someone from a completely different field just described this "
                    "problem to you. What strikes you about it? What does it remind "
                    "you of from your own work? React honestly — don't pretend to "
                    "be an expert in their area. Respond naturally as yourself. "
                    "Keep it to a short paragraph or two."
                )

            messages.append({"role": "user", "content": opening})

            # Replay conversation history with correct role mapping
            for turn in turns:
                if turn.persona_name == active_persona.name:
                    role = "assistant"
                else:
                    role = "user"
                messages.append({"role": role, "content": turn.content})

        return messages
