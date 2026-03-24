"""
Domain configuration Pydantic models for the Medici Engine.

Defines the schema for domain configurations including extraction fields,
scoring axes, and prompt templates. Also provides a dynamic model factory
for building OpenAI-compatible Pydantic models from domain config. This
module belongs to the Domains layer.
"""

from pydantic import BaseModel, Field, create_model, model_validator

from src.scoring.models import AxisScore


class ExtractionField(BaseModel):
    """Definition of a single field extracted by the synthesizer.

    Each extraction field becomes a required string field on the
    dynamic ConceptExtraction model sent to the OpenAI API.
    """

    name: str = Field(description="Machine-readable field name (snake_case)")
    label: str = Field(description="Human-readable label for display")
    description: str = Field(
        description="Description passed to the OpenAI API as field guidance",
    )


class ScoringAxis(BaseModel):
    """Definition of a single scoring axis for concept evaluation.

    Each scoring axis becomes a required AxisScore field on the
    dynamic ConceptScoring model sent to the OpenAI API.
    """

    name: str = Field(description="Machine-readable axis name (snake_case)")
    label: str = Field(description="Human-readable label for display")
    description: str = Field(
        description="Description of what this axis measures, passed to the API",
    )


class DomainConfig(BaseModel):
    """Complete configuration for an application domain.

    Defines everything needed to run the Medici Engine pipeline for a
    specific domain: what the synthesizer extracts, how the scorer
    evaluates, and the prompts that drive both. Domain configs are
    Python modules registered at import time.
    """

    name: str = Field(description="Unique domain identifier (kebab-case)")
    label: str = Field(description="Human-readable domain name")
    description: str = Field(description="Short description of the domain")
    extraction_fields: list[ExtractionField] = Field(
        description="Fields the synthesizer extracts from transcripts",
    )
    primary_field: str = Field(
        description="Extraction field used as the primary label in list views",
    )
    scoring_axes: list[ScoringAxis] = Field(
        description="Axes the scorer evaluates concepts on",
    )
    synthesis_prompt: str = Field(
        description="System prompt for the synthesizer agent",
    )
    scoring_prompt: str = Field(
        description="System prompt for the scoring agent",
    )

    @model_validator(mode="after")
    def validate_primary_field_exists(self) -> "DomainConfig":
        """Ensure primary_field references an existing extraction field."""
        field_names = {f.name for f in self.extraction_fields}
        if self.primary_field not in field_names:
            raise ValueError(
                f"primary_field '{self.primary_field}' must be one of: "
                f"{', '.join(sorted(field_names))}"
            )
        return self

    @model_validator(mode="after")
    def validate_minimum_fields_and_axes(self) -> "DomainConfig":
        """Ensure at least one extraction field and one scoring axis."""
        if len(self.extraction_fields) < 1:
            raise ValueError("At least one extraction field is required")
        if len(self.scoring_axes) < 1:
            raise ValueError("At least one scoring axis is required")
        return self


# ── Dynamic Model Factory ────────────────────────────


def _to_pascal_case(name: str) -> str:
    """Convert a kebab-case or snake_case name to PascalCase."""
    return "".join(part.capitalize() for part in name.replace("-", "_").split("_"))


def create_extraction_model(domain: DomainConfig) -> type[BaseModel]:
    """Build a dynamic Pydantic model for OpenAI structured extraction.

    Creates a model with one required string field per extraction field
    in the domain config. The model name is derived from the domain name
    in PascalCase with an 'Extraction' suffix.

    Args:
        domain: The domain configuration to build from.

    Returns:
        A Pydantic model class compatible with OpenAI structured output.
    """
    model_name = f"{_to_pascal_case(domain.name)}Extraction"
    field_definitions: dict[str, tuple[type, Field]] = {}
    for ef in domain.extraction_fields:
        field_definitions[ef.name] = (str, Field(description=ef.description))

    return create_model(model_name, **field_definitions)


def create_scoring_model(domain: DomainConfig) -> type[BaseModel]:
    """Build a dynamic Pydantic model for OpenAI structured scoring.

    Creates a model with one required AxisScore field per scoring axis
    in the domain config. The model name is derived from the domain name
    in PascalCase with a 'Scoring' suffix.

    Args:
        domain: The domain configuration to build from.

    Returns:
        A Pydantic model class compatible with OpenAI structured output.
    """
    model_name = f"{_to_pascal_case(domain.name)}Scoring"
    field_definitions: dict[str, tuple[type, Field]] = {}
    for axis in domain.scoring_axes:
        field_definitions[axis.name] = (
            AxisScore,
            Field(description=axis.description),
        )

    return create_model(model_name, **field_definitions)
