"""
Situation generator for the Medici Engine.

Generates a dynamic situation by prompting an LLM as Persona A to
describe an unresolved problem in their work. The generated situation
becomes the seed for creative collision when Persona B encounters it.
This module belongs to the Engine layer and communicates with a local
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
from src.personas.models import Persona, Situation

logger = logging.getLogger(__name__)

# Maximum number of retries before giving up on situation generation
_MAX_RETRIES = 2

SITUATION_PROMPT = (
    "You've had a rough week. Something in your work has been nagging at you — "
    "a problem you can't solve, a pattern that doesn't make sense, a result "
    "that contradicts what you expected.\n\n"
    "Describe what's been bothering you. Be specific. Use the language you'd "
    "use talking to a colleague in your field — the real jargon, the real "
    "frustration. Don't simplify it for an outsider. This isn't a presentation; "
    "it's you thinking out loud about something that's genuinely unresolved.\n\n"
    "Keep it to 2-3 paragraphs. Stay concrete — name the specific phenomenon, "
    "dataset, case, mechanism, or observation that has you stuck."
)


class SituationError(Exception):
    """Raised when situation generation fails after all retries."""


class SituationGenerator:
    """Generates a dynamic situation from a persona's perspective.

    Prompts a vLLM-served model with a persona's system prompt and a
    situation generation prompt, producing an authentic description of
    an unresolved problem from the persona's domain. Retries up to
    twice on transient failures before raising.
    """

    def __init__(self) -> None:
        """Initialize the situation generator with a vLLM client."""
        self._client = AsyncOpenAI(
            base_url=settings.situation_model_url,
            api_key="unused",
            timeout=httpx.Timeout(120.0, connect=5.0),
            max_retries=0,
        )

    async def generate(self, persona: Persona) -> Situation:
        """Generate a situation from the given persona's perspective.

        Prompts the model as the persona to describe an unresolved
        problem in their work. Retries up to twice on failure.

        Args:
            persona: The persona whose perspective seeds the situation.

        Returns:
            A Situation containing the generated text.

        Raises:
            SituationError: If generation fails after all retries.
        """
        messages = [
            {"role": "system", "content": persona.to_system_prompt()},
            {"role": "user", "content": SITUATION_PROMPT},
        ]

        last_error: Exception | None = None

        for attempt in range(1, _MAX_RETRIES + 2):
            try:
                response = await self._client.chat.completions.create(
                    model=settings.situation_model,
                    messages=messages,
                    temperature=0.9,
                    max_tokens=768,
                )

                content = response.choices[0].message.content
                if not content or not content.strip():
                    raise SituationError(
                        f"Model returned empty situation on attempt {attempt}"
                    )

                logger.info(
                    "Situation generated",
                    extra={
                        "persona": persona.name,
                        "attempt": attempt,
                        "content_length": len(content.strip()),
                    },
                )

                return Situation(text=content.strip(), situation_type="generated")

            except (APIConnectionError, APITimeoutError, APIStatusError) as e:
                last_error = e
                logger.warning(
                    "Situation generation attempt %d/%d failed: %s",
                    attempt,
                    _MAX_RETRIES + 1,
                    e,
                    extra={"persona": persona.name},
                )

        raise SituationError(
            f"Situation generation failed after {_MAX_RETRIES + 1} attempts "
            f"for persona {persona.name}: {last_error}"
        )
