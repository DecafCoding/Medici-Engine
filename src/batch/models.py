"""
Data models for batch orchestration.

Defines the request structure for configuring a batch of
conversation runs. This module belongs to the API layer.
"""

from pydantic import BaseModel, Field


class BatchRequest(BaseModel):
    """Specification for a batch of conversation runs.

    Configures how many conversations to run, which persona pairings
    to use, and which shared objects to seed them with. When persona
    pairs or shared objects are not specified, they are selected randomly.
    """

    persona_pairs: list[tuple[str, str]] | None = Field(
        default=None,
        description=(
            "List of (persona_a_name, persona_b_name) tuples. None = random selection."
        ),
    )
    shared_object_indices: list[int] | None = Field(
        default=None,
        description=("List of shared object indices to use. None = random selection."),
    )
    num_conversations: int = Field(
        default=1,
        description="Number of conversations to run",
    )
    turns_per_agent: int = Field(
        default=5,
        description="Turns per agent per conversation",
    )
    use_informed_selection: bool = Field(
        default=False,
        description="Use performance-weighted persona selection instead of random",
    )
