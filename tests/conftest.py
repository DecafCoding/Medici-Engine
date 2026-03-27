"""
Shared test fixtures for the Medici Engine test suite.

Provides in-memory database connections, mock vLLM responses,
mock synthesis responses, and test persona/situation data.
All LLM calls are mocked — no real inference happens in tests.
"""

from unittest.mock import MagicMock

import aiosqlite
import pytest
from httpx import ASGITransport, AsyncClient

from src.db.queries import AxisScoreRecord, Turn
from src.db.schema import init_schema
from src.domains.models import (
    DomainConfig,
    create_extraction_model,
    create_scoring_model,
)
from src.domains.sci_fi_concepts import SCI_FI_CONCEPTS
from src.main import app
from src.personas.models import Persona, Situation
from src.scoring.models import AxisScore


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
def test_situation() -> Situation:
    """Provide a test situation for conversation tests."""
    return Situation(
        text="A bridge that has stood for a thousand years begins to hum.",
        situation_type="generated",
    )


@pytest.fixture
def test_domain() -> DomainConfig:
    """Provide the sci-fi domain configuration for tests."""
    return SCI_FI_CONCEPTS


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
def test_extraction_result() -> dict[str, str]:
    """Provide a sample extraction result dict for synthesis tests."""
    return {
        "title": "The Architecture of Forgetting",
        "premise": (
            "A civilization discovers that its most enduring structures were "
            "never designed to last — they survived because they encoded a "
            "pattern of deliberate decay that mimics biological adaptation."
        ),
        "originality": (
            "Combines structural engineering's concept of load-bearing failure "
            "points with information theory's erasure coding — neither domain "
            "alone would produce the idea of a building that preserves itself "
            "by strategically forgetting parts of its own blueprint."
        ),
    }


@pytest.fixture
def mock_parse_response(test_domain):
    """Create a factory for mock OpenAI structured output parse responses.

    Returns responses whose .parsed is a dynamic model instance built
    from the domain's extraction fields.
    """
    extraction_model = create_extraction_model(test_domain)

    def _make_response(
        extraction: dict[str, str] | None = None,
        refusal: str | None = None,
    ) -> MagicMock:
        response = MagicMock()
        choice = MagicMock()
        if extraction is not None:
            choice.message.parsed = extraction_model(**extraction)
        else:
            choice.message.parsed = None
        choice.message.refusal = refusal
        response.choices = [choice]
        return response

    return _make_response


@pytest.fixture
def test_scoring_result() -> list[AxisScoreRecord]:
    """Provide a sample scoring result for scorer tests."""
    return [
        AxisScoreRecord(
            axis="uniqueness",
            label="Uniqueness",
            score=8.5,
            reasoning=(
                "The concept of buildings that preserve themselves through "
                "strategic decay is genuinely novel — no published sci-fi "
                "explores erasure coding as an architectural principle."
            ),
        ),
        AxisScoreRecord(
            axis="plausibility",
            label="Scientific Plausibility",
            score=6.0,
            reasoning=(
                "The underlying information theory is sound, but the leap "
                "to physical structures encoding redundancy through planned "
                "failure requires generous extrapolation."
            ),
        ),
        AxisScoreRecord(
            axis="compelling_factor",
            label="Compelling Factor",
            score=7.5,
            reasoning=(
                "The idea that forgetting is a form of preservation is "
                "immediately provocative and raises questions a reader "
                "would want answered."
            ),
        ),
    ]


@pytest.fixture
def mock_scoring_parse_response(test_domain):
    """Create a factory for mock OpenAI structured scoring parse responses.

    Returns responses whose .parsed is a dynamic scoring model instance
    built from the domain's scoring axes.
    """
    scoring_model = create_scoring_model(test_domain)

    def _make_response(
        scores: list[AxisScoreRecord] | None = None,
        refusal: str | None = None,
    ) -> MagicMock:
        response = MagicMock()
        choice = MagicMock()
        if scores is not None:
            # Build kwargs: {axis_name: AxisScore(axis=..., score=..., reasoning=...)}
            kwargs = {}
            for s in scores:
                kwargs[s.axis] = AxisScore(
                    axis=s.axis,
                    score=s.score,
                    reasoning=s.reasoning,
                )
            choice.message.parsed = scoring_model(**kwargs)
        else:
            choice.message.parsed = None
        choice.message.refusal = refusal
        response.choices = [choice]
        return response

    return _make_response


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
