"""
Pydantic models for the synthesis layer.

Defines the structured output models used by the OpenAI API to return
concept extractions from conversation transcripts. These are pure data
structures with no LLM-related imports. This module belongs to the
Synthesis layer.
"""

from pydantic import BaseModel, Field


class ConceptExtraction(BaseModel):
    """A single concept extracted from a conversation transcript.

    This model is passed as the response_format to the OpenAI API's
    structured output endpoint. All fields are required to satisfy
    strict mode — the API guarantees all fields are populated.
    """

    title: str = Field(description="Working title for the concept")
    premise: str = Field(
        description="Core premise of the concept — the central idea",
    )
    originality: str = Field(
        description="What makes this concept original — why it is novel",
    )
