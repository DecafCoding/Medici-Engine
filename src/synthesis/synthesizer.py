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
from src.synthesis.models import ConceptExtraction

logger = logging.getLogger(__name__)

SYNTHESIS_PROMPT = """\
You are the synthesizer for the Medici Engine — a system that collides radically \
different worldviews to surface novel ideas.

You will receive a conversation transcript between two persona agents who were given \
a shared object to react to. The personas come from completely different domains and \
epistemologies. Your job is NOT to summarize the conversation. Your job is to mine it \
for the novel idea that lives in the gap between the two perspectives.

Look for:
- **Transferable principles**: A concept from one domain that maps structurally onto \
the other domain in a way neither participant recognized.
- **Unexpected reframings**: Moments where one persona's description accidentally \
redefines the other's problem — bypassing assumptions the expert didn't know they had.
- **Novel compound concepts**: Ideas that exist in neither domain alone but emerge \
from their intersection — concepts that have no name yet because they required both \
lenses to see.

Focus on the productive friction — the points where the two personas fundamentally \
talked past each other in interesting ways. Agreement is less valuable than creative \
misunderstanding.

Extract a single sci-fi book concept from this collision:
- **Title**: A working title that captures the core idea. Evocative, not generic.
- **Premise**: The central concept — the idea so structurally original it could anchor \
a book. Not a plot summary. Not characters. The idea itself.
- **Originality**: What makes this concept genuinely novel — why it could not have \
come from either domain alone, and what assumption it breaks.

The concept must stand on its own — readable and compelling without needing \
to read the transcript. Do not reference the personas or the conversation \
directly in the output.\
"""


class SynthesisError(Exception):
    """Raised when synthesis encounters a non-recoverable error."""


class ExtractionError(SynthesisError):
    """Raised when the OpenAI API fails to extract concepts."""


class Synthesizer:
    """Extracts structured concepts from conversation transcripts.

    Reads the full transcript of a persona collision, identifies the
    most interesting friction points, and distills them into a single
    structured concept via the OpenAI API with structured output.
    """

    def __init__(self) -> None:
        """Initialize the synthesizer with an OpenAI API client."""
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
    ) -> ConceptExtraction:
        """Extract a structured concept from a conversation transcript.

        Args:
            transcript: Ordered list of conversation turns.
            persona_a_name: Name of the first persona.
            persona_b_name: Name of the second persona.
            shared_object_text: The shared object that seeded the conversation.

        Returns:
            A structured concept extraction with title, premise, and originality.

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
            },
        )

        formatted = self._format_transcript(transcript)
        messages = self._build_messages(
            formatted_transcript=formatted,
            persona_a_name=persona_a_name,
            persona_b_name=persona_b_name,
            shared_object_text=shared_object_text,
        )

        try:
            response = await self._client.beta.chat.completions.parse(
                model=settings.synthesis_model,
                messages=messages,
                response_format=ConceptExtraction,
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

        logger.info(
            "Concept extracted",
            extra={
                "title": result.title,
                "persona_a": persona_a_name,
                "persona_b": persona_b_name,
            },
        )

        return result

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
            {"role": "system", "content": SYNTHESIS_PROMPT},
            {"role": "user", "content": user_content},
        ]
