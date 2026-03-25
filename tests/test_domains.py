"""Tests for the domain configuration system.

Validates domain models, the registry, dynamic model creation,
and field/axis validation rules.
"""

import pytest
from pydantic import ValidationError

from src.domains.models import (
    DomainConfig,
    ExtractionField,
    ScoringAxis,
    create_extraction_model,
    create_scoring_model,
)
from src.domains.product_design import PRODUCT_DESIGN
from src.domains.registry import get_all_domains, get_domain
from src.domains.sci_fi_concepts import SCI_FI_CONCEPTS


def test_sci_fi_domain_has_required_fields() -> None:
    """Validate sci-fi config has 3 extraction fields and 3 scoring axes."""
    assert len(SCI_FI_CONCEPTS.extraction_fields) == 3
    assert len(SCI_FI_CONCEPTS.scoring_axes) == 3
    field_names = {f.name for f in SCI_FI_CONCEPTS.extraction_fields}
    assert field_names == {"title", "premise", "originality"}
    axis_names = {a.name for a in SCI_FI_CONCEPTS.scoring_axes}
    assert axis_names == {"uniqueness", "plausibility", "compelling_factor"}


def test_product_design_domain_has_required_fields() -> None:
    """Validate product design config has 3 extraction fields and 3 scoring axes."""
    assert len(PRODUCT_DESIGN.extraction_fields) == 3
    assert len(PRODUCT_DESIGN.scoring_axes) == 3
    field_names = {f.name for f in PRODUCT_DESIGN.extraction_fields}
    assert field_names == {"product_name", "value_proposition", "target_insight"}
    axis_names = {a.name for a in PRODUCT_DESIGN.scoring_axes}
    assert axis_names == {"novelty", "feasibility", "market_potential"}


def test_domain_registry_returns_all_domains() -> None:
    """Verify at least 2 domains are registered in the global registry."""
    domains = get_all_domains()
    assert len(domains) >= 2
    names = {d.name for d in domains}
    assert "sci-fi-concepts" in names
    assert "product-design" in names


def test_get_domain_raises_for_unknown() -> None:
    """Verify ValueError is raised for an unregistered domain name."""
    with pytest.raises(ValueError, match="nonexistent"):
        get_domain("nonexistent")


def test_create_extraction_model_produces_valid_schema() -> None:
    """Verify the dynamic extraction model has all fields from config."""
    model = create_extraction_model(SCI_FI_CONCEPTS)
    schema = model.model_json_schema()
    required = schema.get("required", [])
    properties = schema.get("properties", {})

    for ef in SCI_FI_CONCEPTS.extraction_fields:
        assert ef.name in properties, f"Missing field: {ef.name}"
        assert ef.name in required, f"Field not required: {ef.name}"


def test_create_scoring_model_produces_valid_schema() -> None:
    """Verify the dynamic scoring model has AxisScore fields per axis."""
    model = create_scoring_model(SCI_FI_CONCEPTS)
    schema = model.model_json_schema()
    required = schema.get("required", [])
    properties = schema.get("properties", {})

    for axis in SCI_FI_CONCEPTS.scoring_axes:
        assert axis.name in properties, f"Missing axis: {axis.name}"
        assert axis.name in required, f"Axis not required: {axis.name}"


def test_domain_config_validates_primary_field() -> None:
    """Verify primary_field must reference an existing extraction field."""
    with pytest.raises(ValidationError, match="primary_field"):
        DomainConfig(
            name="test",
            label="Test",
            description="Test domain",
            extraction_fields=[
                ExtractionField(name="title", label="Title", description="The title"),
            ],
            primary_field="nonexistent",
            scoring_axes=[
                ScoringAxis(
                    name="quality", label="Quality", description="Overall quality"
                ),
            ],
            synthesis_prompt="Test prompt",
            scoring_prompt="Test prompt",
        )


def test_domain_config_requires_at_least_one_field() -> None:
    """Verify empty extraction_fields raises ValidationError."""
    with pytest.raises(ValidationError):
        DomainConfig(
            name="test",
            label="Test",
            description="Test domain",
            extraction_fields=[],
            primary_field="title",
            scoring_axes=[
                ScoringAxis(
                    name="quality", label="Quality", description="Overall quality"
                ),
            ],
            synthesis_prompt="Test prompt",
            scoring_prompt="Test prompt",
        )
