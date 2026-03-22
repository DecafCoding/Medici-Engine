"""
Shared test fixtures for the Medici Engine test suite.

Provides in-memory database connections, mock vLLM responses,
and test persona/shared object data. All LLM calls are mocked —
no real inference happens in tests.
"""

from unittest.mock import MagicMock

import aiosqlite
import pytest
from httpx import ASGITransport, AsyncClient

from src.db.schema import init_schema
from src.main import app
from src.personas.models import Persona, SharedObject


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
