"""
Scorer for the Medici Engine.

Evaluates concepts extracted by the synthesizer across domain-specific
axes using the OpenAI API with structured output. Each axis receives a
0.0-10.0 score with written reasoning that helps a human reviewer make
faster keep/discard decisions. This module belongs to the Scoring layer
and communicates with the OpenAI API only — no vLLM calls.
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
from src.db.queries import AxisScoreRecord
from src.domains.models import DomainConfig, create_scoring_model

logger = logging.getLogger(__name__)


class ScoringError(Exception):
    """Raised when scoring encounters a non-recoverable error."""


class EvaluationError(ScoringError):
    """Raised when the OpenAI API fails to score a concept."""


class Scorer:
    """Evaluates concepts across domain-specific axes using the OpenAI API.

    Takes a concept's extracted fields, sends them to the scoring model
    with structured output, and returns per-axis scores with written
    reasoning. The scoring axes and prompt are driven by the domain config.
    """

    def __init__(self, domain: DomainConfig) -> None:
        """Initialize the scorer with a domain config and OpenAI client.

        Args:
            domain: Domain configuration defining scoring axes and prompt.
        """
        self._domain = domain
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=httpx.Timeout(60.0, connect=5.0),
            max_retries=3,
        )

    async def score(
        self,
        fields: dict[str, str],
    ) -> list[AxisScoreRecord]:
        """Score a concept across domain-specific evaluation axes.

        Args:
            fields: Dict of extraction field names to values (e.g.,
                {"title": "...", "premise": "...", "originality": "..."}).

        Returns:
            List of AxisScoreRecord objects, one per scoring axis.

        Raises:
            ScoringError: If scoring cannot be completed.
            EvaluationError: If the API fails or refuses to score.
        """
        primary_value = fields.get(self._domain.primary_field, "unknown")
        logger.info(
            "Scoring concept",
            extra={
                "concept_title": primary_value,
                "domain": self._domain.name,
            },
        )

        messages = self._build_messages(fields)

        # Build the response_format model dynamically from domain config
        scoring_model = create_scoring_model(self._domain)

        try:
            response = await self._client.beta.chat.completions.parse(
                model=settings.scoring_model,
                messages=messages,
                response_format=scoring_model,
                temperature=0.3,
            )
        except APIConnectionError as e:
            raise EvaluationError(f"Cannot reach OpenAI API: {e}") from e
        except APITimeoutError as e:
            raise EvaluationError(f"OpenAI API request timed out: {e}") from e
        except APIStatusError as e:
            raise EvaluationError(
                f"OpenAI API returned status {e.status_code}: {e.message}"
            ) from e

        result = response.choices[0].message.parsed
        if result is None:
            refusal = response.choices[0].message.refusal
            raise EvaluationError(f"Model refused to score concept: {refusal}")

        # Map dynamic model fields to AxisScoreRecord objects with labels
        axis_scores: list[AxisScoreRecord] = []
        for axis_def in self._domain.scoring_axes:
            axis_result = getattr(result, axis_def.name)
            axis_scores.append(
                AxisScoreRecord(
                    axis=axis_def.name,
                    label=axis_def.label,
                    score=axis_result.score,
                    reasoning=axis_result.reasoning,
                )
            )

        logger.info(
            "Concept scored",
            extra={
                "concept_title": primary_value,
                "domain": self._domain.name,
                "scores": {s.axis: s.score for s in axis_scores},
            },
        )

        return axis_scores

    def _build_messages(
        self,
        fields: dict[str, str],
    ) -> list[dict[str, str]]:
        """Build the chat messages for the scoring API call.

        Formats each extraction field with its human-readable label
        from the domain config.

        Args:
            fields: Dict of extraction field names to values.

        Returns:
            List of message dicts ready for the OpenAI chat API.
        """
        # Build a lookup from field name to label
        field_labels = {ef.name: ef.label for ef in self._domain.extraction_fields}

        # Format each field as **Label:** value
        lines: list[str] = []
        for name, value in fields.items():
            label = field_labels.get(name, name)
            lines.append(f"**{label}:** {value}")

        user_content = "\n\n".join(lines)

        return [
            {"role": "system", "content": self._domain.scoring_prompt},
            {"role": "user", "content": user_content},
        ]
