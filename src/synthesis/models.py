"""
Pydantic models for the synthesis layer.

This module previously contained the ConceptExtraction model used as the
response_format for OpenAI structured output. That model has been replaced
by dynamic models built from domain configuration via
src.domains.models.create_extraction_model(). This module is retained for
the synthesis layer's module structure.
"""
