"""Tests for the configuration module."""

from src.config import Settings


def test_default_settings_load() -> None:
    """Verify default settings are valid without any env vars."""
    s = Settings()
    assert s.vllm_base_url == "http://localhost:8000/v1"
    assert s.conversation_model == "MythoMax-L2-13B"
    assert s.default_turns == 5
    assert s.database_path == "data/yield_engine.db"


def test_settings_types() -> None:
    """Verify settings fields have correct types."""
    s = Settings()
    assert isinstance(s.conversation_temperature, float)
    assert isinstance(s.conversation_max_tokens, int)
    assert isinstance(s.default_turns, int)


def test_active_domain_default() -> None:
    """Verify the active_domain setting defaults to sci-fi-concepts."""
    s = Settings()
    assert s.active_domain == "sci-fi-concepts"
