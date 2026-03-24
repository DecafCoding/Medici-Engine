"""
Synthesizer for the Medici Engine.

Reads a full conversation transcript between two persona agents and
extracts a structured concept — the novel idea that emerged from the
collision between radically different worldviews. Communicates with
the OpenAI API via structured output. This module belongs to the
Synthesis layer.
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
from src.domains.models import DomainConfig, create_extraction_model

logger = logging.getLogger(__name__)


class SynthesisError(Exception):
    """Raised when synthesis encounters a non-recoverable error."""


class ExtractionError(SynthesisError):
    """Raised when the OpenAI API fails to extract concepts."""


class Synthesizer:
    """Extracts structured concepts from conversation transcripts.

    Reads the full transcript of a persona collision, identifies the
    most interesting friction points, and distills them into a single
    structured concept via the OpenAI API with structured output.
    The extraction fields and prompt are driven by the domain config.
    """

    def __init__(self, domain: DomainConfig) -> None:
        """Initialize the synthesizer with a domain config and OpenAI client.

        Args:
            domain: Domain configuration defining extraction fields and prompt.
        """
        self._domain = domain
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=httpx.Timeout(60.0, connect=5.0),
            max_retries=3,
        )

    async def synthesize(
        self,
        transcript: list[Turn],
        persona_a_name: str,
        persona_b_name: str,
        shared_object_text: str,
    ) -> dict[str, str]:
        """Extract a structured concept from a conversation transcript.

        Args:
            transcript: Ordered list of conversation turns.
            persona_a_name: Name of the first persona.
            persona_b_name: Name of the second persona.
            shared_object_text: The shared object that seeded the conversation.

        Returns:
            A dict mapping extraction field names to their values.

        Raises:
            SynthesisError: If synthesis cannot be completed.
            ExtractionError: If the API fails or refuses to extract.
        """
        logger.info(
            "Synthesizing concept from transcript",
            extra={
                "persona_a": persona_a_name,
                "persona_b": persona_b_name,
                "turn_count": len(transcript),
                "domain": self._domain.name,
            },
        )

        formatted = self._format_transcript(transcript)
        messages = self._build_messages(
            formatted_transcript=formatted,
            persona_a_name=persona_a_name,
            persona_b_name=persona_b_name,
            shared_object_text=shared_object_text,
        )

        # Build the response_format model dynamically from domain config
        extraction_model = create_extraction_model(self._domain)

        try:
            response = await self._client.beta.chat.completions.parse(
                model=settings.synthesis_model,
                messages=messages,
                response_format=extraction_model,
                temperature=0.4,
            )
        except APIConnectionError as e:
            raise ExtractionError(f"Cannot reach OpenAI API: {e}") from e
        except APITimeoutError as e:
            raise ExtractionError(f"OpenAI API request timed out: {e}") from e
        except APIStatusError as e:
            raise ExtractionError(
                f"OpenAI API returned status {e.status_code}: {e.message}"
            ) from e

        result = response.choices[0].message.parsed
        if result is None:
            refusal = response.choices[0].message.refusal
            raise ExtractionError(f"Model refused to extract concept: {refusal}")

        # Convert the dynamic model to a plain dict of field values
        extraction = result.model_dump()

        logger.info(
            "Concept extracted",
            extra={
                "title": extraction.get(self._domain.primary_field, ""),
                "persona_a": persona_a_name,
                "persona_b": persona_b_name,
                "domain": self._domain.name,
            },
        )

        return extraction

    def _format_transcript(self, transcript: list[Turn]) -> str:
        """Convert a list of turns into a readable transcript string."""
        lines: list[str] = []
        for turn in transcript:
            lines.append(f"[Turn {turn.turn_number}] {turn.persona_name}:")
            lines.append(turn.content)
            lines.append("")
        return "\n".join(lines)

    def _build_messages(
        self,
        formatted_transcript: str,
        persona_a_name: str,
        persona_b_name: str,
        shared_object_text: str,
    ) -> list[dict[str, str]]:
        """Build the chat messages for the synthesis API call.

        Args:
            formatted_transcript: Human-readable transcript text.
            persona_a_name: Name of the first persona.
            persona_b_name: Name of the second persona.
            shared_object_text: The shared object that seeded the conversation.

        Returns:
            List of message dicts ready for the OpenAI chat API.
        """
        user_content = (
            f"Conversation between **{persona_a_name}** and **{persona_b_name}**.\n\n"
            f"Shared object they were reacting to:\n"
            f"---\n{shared_object_text}\n---\n\n"
            f"Full transcript:\n\n{formatted_transcript}"
        )

        return [
            {"role": "system", "content": self._domain.synthesis_prompt},
            {"role": "user", "content": user_content},
        ]
