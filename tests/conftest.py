"""
Shared test fixtures for the Medici Engine test suite.

Provides in-memory database connections, mock vLLM responses,
mock synthesis responses, and test persona/shared object data.
All LLM calls are mocked — no real inference happens in tests.
"""

from unittest.mock import MagicMock

import aiosqlite
import pytest
from httpx import ASGITransport, AsyncClient

from src.db.queries import Turn
from src.db.schema import init_schema
from src.main import app
from src.personas.models import Persona, SharedObject
from src.scoring.models import AxisScore, ConceptScoring
from src.synthesis.models import ConceptExtraction


@pytest.fixture
async def db():
    """Provide an in-memory SQLite database with schema initialized."""
    connection = await aiosqlite.connect(":memory:")
    connection.row_factory = aiosqlite.Row
    await connection.execute("PRAGMA foreign_keys=ON")
    await init_schema(connection)
    yield connection
    await connection.close()


@pytest.fixture
async def client(db):
    """Provide an async HTTP client with the FastAPI app and test database."""
    app.state.db = db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def test_persona_a() -> Persona:
    """Provide a test persona for conversation tests."""
    return Persona(
        name="test_physicist",
        title="A test physicist persona",
        worldview="Everything is information.",
        vocabulary_style="Speaks in equations and thought experiments.",
        core_obsessions="The nature of observation.",
        way_of_seeing="Sees patterns in data.",
    )


@pytest.fixture
def test_persona_b() -> Persona:
    """Provide a second test persona for conversation tests."""
    return Persona(
        name="test_builder",
        title="A test builder persona",
        worldview="The world is built by hands.",
        vocabulary_style="Speaks of loads and foundations.",
        core_obsessions="Making things that last.",
        way_of_seeing="Sees every system as a structure.",
    )


@pytest.fixture
def test_shared_object() -> SharedObject:
    """Provide a test shared object for conversation tests."""
    return SharedObject(
        text="A bridge that has stood for a thousand years begins to hum.",
        object_type="scenario",
    )


@pytest.fixture
def mock_openai_response():
    """Create a factory for mock OpenAI chat completion responses."""

    def _make_response(content: str) -> MagicMock:
        response = MagicMock()
        choice = MagicMock()
        choice.message.content = content
        response.choices = [choice]
        return response

    return _make_response


@pytest.fixture
def mock_parse_response():
    """Create a factory for mock OpenAI structured output parse responses."""

    def _make_response(
        extraction: ConceptExtraction | None = None,
        refusal: str | None = None,
    ) -> MagicMock:
        response = MagicMock()
        choice = MagicMock()
        choice.message.parsed = extraction
        choice.message.refusal = refusal
        response.choices = [choice]
        return response

    return _make_response


@pytest.fixture
def test_concept_extraction() -> ConceptExtraction:
    """Provide a sample concept extraction for synthesis tests."""
    return ConceptExtraction(
        title="The Architecture of Forgetting",
        premise=(
            "A civilization discovers that its most enduring structures were "
            "never designed to last — they survived because they encoded a "
            "pattern of deliberate decay that mimics biological adaptation."
        ),
        originality=(
            "Combines structural engineering's concept of load-bearing failure "
            "points with information theory's erasure coding — neither domain "
            "alone would produce the idea of a building that preserves itself "
            "by strategically forgetting parts of its own blueprint."
        ),
    )


@pytest.fixture
def mock_scoring_response():
    """Create a factory for mock OpenAI structured output scoring responses."""

    def _make_response(
        scoring: ConceptScoring | None = None,
        refusal: str | None = None,
    ) -> MagicMock:
        response = MagicMock()
        choice = MagicMock()
        choice.message.parsed = scoring
        choice.message.refusal = refusal
        response.choices = [choice]
        return response

    return _make_response


@pytest.fixture
def test_concept_scoring() -> ConceptScoring:
    """Provide a sample concept scoring for scorer tests."""
    return ConceptScoring(
        uniqueness=AxisScore(
            axis="uniqueness",
            score=8.5,
            reasoning=(
                "The concept of buildings that preserve themselves through "
                "strategic decay is genuinely novel — no published sci-fi "
                "explores erasure coding as an architectural principle."
            ),
        ),
        plausibility=AxisScore(
            axis="plausibility",
            score=6.0,
            reasoning=(
                "The underlying information theory is sound, but the leap "
                "to physical structures encoding redundancy through planned "
                "failure requires generous extrapolation."
            ),
        ),
        compelling_factor=AxisScore(
            axis="compelling_factor",
            score=7.5,
            reasoning=(
                "The idea that forgetting is a form of preservation is "
                "immediately provocative and raises questions a reader "
                "would want answered."
            ),
        ),
    )


@pytest.fixture
def test_transcript() -> list[Turn]:
    """Provide a sample transcript for synthesis tests."""
    return [
        Turn(
            turn_number=1,
            persona_name="test_physicist",
            content=(
                "The interesting question is what information is being preserved here."
            ),
        ),
        Turn(
            turn_number=2,
            persona_name="test_builder",
            content="Show me where the weight goes. A structure stands or it falls.",
        ),
        Turn(
            turn_number=3,
            persona_name="test_physicist",
            content="But what if the collapse itself encodes something?",
        ),
        Turn(
            turn_number=4,
            persona_name="test_builder",
            content="A wall that falls on purpose is not a wall. It is a message.",
        ),
    ]
