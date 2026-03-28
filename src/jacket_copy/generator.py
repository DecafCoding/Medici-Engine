"""
Jacket copy generator for the Medici Engine.

Takes a concept's raw premise and transforms it into a polished
back-cover blurb via the OpenAI API. Uses plain text completion
(not structured output) since the result is creative prose rather
than structured data. This module belongs to the Jacket Copy layer
and communicates with the remote OpenAI API only.
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
from src.jacket_copy.prompt import build_jacket_copy_messages

logger = logging.getLogger(__name__)


class JacketCopyError(Exception):
    """Raised when jacket copy generation encounters a non-recoverable error."""


class GenerationError(JacketCopyError):
    """Raised when the OpenAI API fails to generate a jacket copy."""


class JacketCopyGenerator:
    """Generates back-cover blurb text from a concept's premise.

    Takes the premise extracted by the synthesizer and expands it into
    a polished jacket copy via the OpenAI API. The prompt enforces strict
    constraints on structure, tone, and length to produce consistent output.
    """

    def __init__(self) -> None:
        """Initialize the generator with an OpenAI client."""
        client_kwargs: dict = {
            "api_key": settings.openai_api_key,
            "timeout": httpx.Timeout(90.0, connect=5.0),
            "max_retries": 3,
        }
        if settings.jacket_copy_base_url:
            client_kwargs["base_url"] = settings.jacket_copy_base_url
        self._client = AsyncOpenAI(**client_kwargs)

    async def generate(self, premise: str) -> str:
        """Generate a jacket copy from a concept premise.

        Args:
            premise: The raw premise text to expand into a jacket copy.

        Returns:
            The generated jacket copy text.

        Raises:
            GenerationError: If the API call fails or returns no content.
        """
        logger.info(
            "Generating jacket copy",
            extra={"premise_length": len(premise)},
        )

        messages = build_jacket_copy_messages(premise)

        # Some models only accept their default temperature
        optional_params: dict = {}
        if settings.jacket_copy_temperature is not None:
            optional_params["temperature"] = settings.jacket_copy_temperature

        try:
            response = await self._client.chat.completions.create(
                model=settings.jacket_copy_model,
                messages=messages,
                **optional_params,
            )
        except APIConnectionError as e:
            raise GenerationError(f"Cannot reach OpenAI API: {e}") from e
        except APITimeoutError as e:
            raise GenerationError(f"OpenAI API request timed out: {e}") from e
        except APIStatusError as e:
            raise GenerationError(
                f"OpenAI API returned status {e.status_code}: {e.message}"
            ) from e

        content = response.choices[0].message.content
        if not content:
            raise GenerationError("Model returned empty jacket copy")

        logger.info(
            "Jacket copy generated",
            extra={"output_length": len(content)},
        )

        return content.strip()
