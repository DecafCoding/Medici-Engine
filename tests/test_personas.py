"""Tests for the persona library and selection logic."""

from src.personas.library import (
    get_all_personas,
    get_all_shared_objects,
    get_persona_by_name,
    get_persona_pair,
    get_random_shared_object,
)
from src.personas.models import SharedObject


def test_library_has_minimum_personas() -> None:
    """Verify the library contains at least 4 personas for Feature 1."""
    personas = get_all_personas()
    assert len(personas) >= 4


def test_all_personas_fully_specified() -> None:
    """Verify every persona has all four dimensions filled in."""
    for persona in get_all_personas():
        assert persona.name, "Persona missing name"
        assert persona.title, f"{persona.name} missing title"
        assert len(persona.worldview) > 50, f"{persona.name} worldview too short"
        assert len(persona.vocabulary_style) > 50, (
            f"{persona.name} vocabulary too short"
        )
        assert len(persona.core_obsessions) > 50, f"{persona.name} obsessions too short"
        assert len(persona.way_of_seeing) > 50, (
            f"{persona.name} way_of_seeing too short"
        )


def test_persona_names_are_unique() -> None:
    """Verify no two personas share a name."""
    names = [p.name for p in get_all_personas()]
    assert len(names) == len(set(names))


def test_get_persona_by_name_found() -> None:
    """Verify a persona can be retrieved by name."""
    personas = get_all_personas()
    result = get_persona_by_name(personas[0].name)
    assert result is not None
    assert result.name == personas[0].name


def test_get_persona_by_name_not_found() -> None:
    """Verify None is returned for an unknown persona name."""
    result = get_persona_by_name("nonexistent_persona")
    assert result is None


def test_get_persona_pair_returns_two_distinct() -> None:
    """Verify pair selection returns two different personas."""
    a, b = get_persona_pair()
    assert a.name != b.name


def test_get_persona_pair_avoids_recent() -> None:
    """Verify pair selection avoids recently used pairings."""
    # Get all possible pairings except one
    personas = get_all_personas()
    all_pairs = []
    for i, a in enumerate(personas):
        for b in personas[i + 1 :]:
            all_pairs.append(tuple(sorted([a.name, b.name])))

    # Mark all but one pairing as recent
    recent = all_pairs[:-1]
    remaining = all_pairs[-1]

    a, b = get_persona_pair(recent_pairings=recent)
    selected = tuple(sorted([a.name, b.name]))
    assert selected == remaining


def test_persona_generates_system_prompt() -> None:
    """Verify system prompt includes all persona dimensions."""
    persona = get_all_personas()[0]
    prompt = persona.to_system_prompt()
    assert persona.title in prompt
    assert "WORLDVIEW" in prompt
    assert "VOCABULARY" in prompt
    assert "CORE OBSESSIONS" in prompt
    assert "WAY OF SEEING" in prompt


def test_shared_objects_pool_not_empty() -> None:
    """Verify the shared objects pool has entries."""
    objects = get_all_shared_objects()
    assert len(objects) >= 3


def test_get_random_shared_object_returns_valid() -> None:
    """Verify random selection returns a complete shared object."""
    obj = get_random_shared_object()
    assert isinstance(obj, SharedObject)
    assert len(obj.text) > 20
    assert obj.object_type in ("scenario", "question", "problem", "image_description")
