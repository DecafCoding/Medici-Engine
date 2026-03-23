"""
Scorer for the Medici Engine.

Evaluates concepts extracted by the synthesizer across three domain-specific
axes — uniqueness, scientific plausibility, and compelling factor — using
the OpenAI o3 model with structured output. Each axis receives a 0.0-10.0
score with written reasoning that helps a human reviewer make faster
keep/discard decisions. This module belongs to the Scoring layer and
communicates with the OpenAI API only — no vLLM calls.
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
from src.scoring.models import ConceptScoring

logger = logging.getLogger(__name__)

SCORING_PROMPT = """\
You are an evaluator for the Medici Engine — a system that collides radically \
different worldviews to surface novel sci-fi book concepts.

You will receive a concept consisting of a title, premise, and originality \
statement. Your job is to evaluate this concept across three axes. For each \
axis, provide a score from 0.0 to 10.0 and written reasoning that explains \
the score.

Your reasoning should help a human reviewer make a faster, better-informed \
keep/discard decision. Be specific and honest — a well-reasoned 4 is more \
useful than an inflated 8.

**Evaluation Axes:**

1. **Uniqueness** — How novel and unprecedented is this concept? Has something \
structurally similar been explored in published sci-fi? A high score means the core \
idea breaks genuinely new ground, not just a fresh coat of paint on a familiar trope. \
A low score means it closely echoes existing work, even if well-executed.

2. **Scientific Plausibility** — Could the underlying science or speculative \
framework work, even in a generous reading? A high score means the concept is \
grounded in real principles extended thoughtfully, or builds a self-consistent \
speculative framework. A low score means the concept relies on handwaving or \
contradicts well-established science without justification.

3. **Compelling Factor** — Would someone want to read a book built on this concept? \
A high score means the idea provokes genuine curiosity, raises questions the reader \
needs answered, or reframes something familiar in a way that demands exploration. \
A low score means the idea is intellectually interesting but inert — it doesn't \
pull the reader forward.\
"""


class ScoringError(Exception):
    """Raised when scoring encounters a non-recoverable error."""


class EvaluationError(ScoringError):
    """Raised when the OpenAI API fails to score a concept."""


class Scorer:
    """Evaluates concepts across domain-specific axes using OpenAI o3.

    Takes a concept's title, premise, and originality statement, sends
    them to the scoring model with structured output, and returns
    per-axis scores with written reasoning. Communicates with the
    remote OpenAI API only.
    """

    def __init__(self) -> None:
        """Initialize the scorer with an OpenAI API client."""
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=httpx.Timeout(60.0, connect=5.0),
            max_retries=3,
        )

    async def score(
        self,
        title: str,
        premise: str,
        originality: str,
    ) -> ConceptScoring:
        """Score a concept across uniqueness, plausibility, and compelling factor.

        Args:
            title: Working title of the concept.
            premise: Core premise — the central idea.
            originality: What makes the concept novel.

        Returns:
            Structured scoring result with per-axis scores and reasoning.

        Raises:
            ScoringError: If scoring cannot be completed.
            EvaluationError: If the API fails or refuses to score.
        """
        logger.info(
            "Scoring concept",
            extra={"concept_title": title},
        )

        messages = self._build_messages(
            title=title,
            premise=premise,
            originality=originality,
        )

        try:
            response = await self._client.beta.chat.completions.parse(
                model=settings.scoring_model,
                messages=messages,
                response_format=ConceptScoring,
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

        logger.info(
            "Concept scored",
            extra={
                "concept_title": title,
                "uniqueness": result.uniqueness.score,
                "plausibility": result.plausibility.score,
                "compelling_factor": result.compelling_factor.score,
            },
        )

        return result

    def _build_messages(
        self,
        title: str,
        premise: str,
        originality: str,
    ) -> list[dict[str, str]]:
        """Build the chat messages for the scoring API call.

        Args:
            title: Working title of the concept.
            premise: Core premise of the concept.
            originality: What makes the concept novel.

        Returns:
            List of message dicts ready for the OpenAI chat API.
        """
        user_content = (
            f"**Title:** {title}\n\n"
            f"**Premise:** {premise}\n\n"
            f"**Originality:** {originality}"
        )

        return [
            {"role": "system", "content": SCORING_PROMPT},
            {"role": "user", "content": user_content},
        ]
