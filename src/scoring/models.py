"""
Pydantic models for the scoring layer.

Defines the structured output models used by the OpenAI API to return
concept evaluations with per-axis scores and reasoning. These are pure
data structures with no LLM-related imports. This module belongs to the
Scoring layer.
"""

from pydantic import BaseModel, Field


class AxisScore(BaseModel):
    """A single axis evaluation with score and reasoning.

    This model represents one dimension of concept evaluation. The score
    is on a 0.0-10.0 scale, and the reasoning explains the score in a
    way that helps a human reviewer make a faster decision.
    """

    axis: str = Field(description="Name of the evaluation axis")
    score: float = Field(description="Score from 0.0 to 10.0")
    reasoning: str = Field(
        description="Written reasoning explaining the score",
    )


class ConceptScoring(BaseModel):
    """Complete scoring result for a concept across all evaluation axes.

    This model is passed as the response_format to the OpenAI API's
    structured output endpoint. All fields are required to satisfy
    strict mode — the API guarantees all fields are populated. Uses
    named fields (not a list) so each axis is always present.
    """

    uniqueness: AxisScore = Field(
        description="How novel and unprecedented the concept is",
    )
    plausibility: AxisScore = Field(
        description="Whether the underlying science could work, even speculatively",
    )
    compelling_factor: AxisScore = Field(
        description="Whether someone would want to read a book built on this concept",
    )
