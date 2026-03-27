"""
Data models for the conversation engine.

Defines the structures used by the ConversationRunner to manage
turn-taking and produce transcripts. This module belongs to the
Engine layer.
"""

from pydantic import BaseModel, Field

from src.personas.models import Persona, Situation


class ConversationConfig(BaseModel):
    """Configuration for a single conversation run.

    Controls turn count and inference parameters. Defaults come
    from application settings but can be overridden per-run.
    """

    turns_per_agent: int = Field(default=5, description="Number of turns per agent")
    temperature: float = Field(default=0.9, description="Sampling temperature")
    repetition_penalty: float = Field(
        default=1.15, description="vLLM repetition penalty"
    )
    max_tokens: int = Field(default=150, description="Max tokens per turn")


class ConversationRequest(BaseModel):
    """Complete specification for a conversation run.

    Bundles the two personas, situation, and generation config
    into a single request object.
    """

    persona_a: Persona
    persona_b: Persona
    situation: Situation
    config: ConversationConfig = Field(default_factory=ConversationConfig)
