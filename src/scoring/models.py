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
    way that helps a human reviewer make a faster decision. Used as a
    field type in dynamic scoring models built from domain config.
    """

    axis: str = Field(description="Name of the evaluation axis")
    score: float = Field(description="Score from 0.0 to 10.0")
    reasoning: str = Field(
        description="Written reasoning explaining the score",
    )
