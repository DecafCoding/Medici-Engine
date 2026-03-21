# PBI 6: Tests & Validation

**Feature**: 1 — Core Conversation Engine
**Tasks**: 20–28 of 28
**Dependencies**: PBIs 1–5 (all application code complete)
**Estimated Complexity**: Medium

---

## Objective

Build the complete test suite: shared fixtures, unit tests for every module, architectural boundary verification, and API integration tests. Run full lint and format validation. This PBI is the quality gate — Feature 1 is not done until everything here passes.

## User Story

As a developer
I want comprehensive tests with mocked LLM calls and boundary verification
So that I can confidently build Features 2-7 without regressions

## Preconditions

- PBIs 1–5 complete (all application code exists and imports cleanly)
- No vLLM server required — all LLM calls are mocked

## Context References — READ BEFORE IMPLEMENTING

- `CLAUDE.md` — Testing conventions: pytest + pytest-asyncio, mirror source structure, mock all LLM calls, use httpx.AsyncClient for API tests
- `CLAUDE.md` — Boundary verification: tests that inspect imports via `ast`
- `CLAUDE.md` — Test naming: describe behavior being verified, not implementation

### Testing Patterns

**Async tests**: With `asyncio_mode = "auto"` in pyproject.toml, every `async def test_*` is automatically treated as an async test. No `@pytest.mark.asyncio` needed.

**Database fixtures**: In-memory SQLite (`:memory:`) for test isolation. Schema initialized per test.

**Mock vLLM**: Use `unittest.mock.AsyncMock` with `patch.object` on `runner._client.chat.completions.create`. Factory fixture creates mock OpenAI responses.

**API testing**: Use `httpx.AsyncClient` with `ASGITransport(app=app)` — not the deprecated `app=` kwarg.

---

## TASKS

### Task 20: CREATE `tests/__init__.py`

- **IMPLEMENT**: Empty file (package marker).
- **VALIDATE**: `test -f tests/__init__.py && echo "exists"`

---

### Task 21: CREATE `tests/conftest.py`

Shared test fixtures for all test modules.

- **IMPLEMENT**:

```python
"""
Shared test fixtures for the Yield Engine test suite.

Provides in-memory database connections, mock vLLM responses,
and test persona/shared object data. All LLM calls are mocked —
no real inference happens in tests.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

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
```

- **PATTERN**: In-memory SQLite for isolation. Mock factory for vLLM responses. `ASGITransport` for FastAPI testing.
- **VALIDATE**: `uv run pytest --collect-only 2>&1 | head -20`

---

### Task 22: CREATE `tests/test_config.py`

- **IMPLEMENT**:

```python
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
```

- **VALIDATE**: `uv run pytest tests/test_config.py -v`

---

### Task 23: CREATE `tests/test_db.py`

- **IMPLEMENT**:

```python
"""Tests for the database schema and query layer."""

from uuid import UUID

from src.db.queries import (
    Run,
    RunCreate,
    Turn,
    complete_run,
    create_run,
    fail_run,
    get_recent_pairings,
    get_run_by_id,
    get_runs,
    record_pairing,
)


async def test_create_run(db) -> None:
    """Verify a run can be created and retrieved."""
    run = await create_run(
        db,
        RunCreate(
            persona_a_name="physicist",
            persona_b_name="builder",
            shared_object_text="A test scenario",
            turns_per_agent=5,
        ),
    )
    assert isinstance(run.id, UUID)
    assert run.status == "pending"
    assert run.persona_a_name == "physicist"
    assert run.transcript is None


async def test_get_run_by_id(db) -> None:
    """Verify a run can be fetched by its ID."""
    created = await create_run(
        db,
        RunCreate(
            persona_a_name="physicist",
            persona_b_name="builder",
            shared_object_text="A test scenario",
        ),
    )
    fetched = await get_run_by_id(db, created.id)
    assert fetched is not None
    assert fetched.id == created.id


async def test_get_run_by_id_returns_none_for_missing(db) -> None:
    """Verify None is returned for a nonexistent run ID."""
    from uuid import uuid4

    result = await get_run_by_id(db, uuid4())
    assert result is None


async def test_complete_run_stores_transcript(db) -> None:
    """Verify completing a run stores the transcript and updates status."""
    run = await create_run(
        db,
        RunCreate(
            persona_a_name="physicist",
            persona_b_name="builder",
            shared_object_text="A test scenario",
        ),
    )
    turns = [
        Turn(turn_number=1, persona_name="physicist", content="Hello from physics"),
        Turn(turn_number=2, persona_name="builder", content="Hello from building"),
    ]
    completed = await complete_run(db, run.id, turns)
    assert completed.status == "completed"
    assert completed.transcript is not None
    assert len(completed.transcript) == 2
    assert completed.transcript[0].content == "Hello from physics"
    assert completed.completed_at is not None


async def test_fail_run_stores_error(db) -> None:
    """Verify failing a run stores the error message and updates status."""
    run = await create_run(
        db,
        RunCreate(
            persona_a_name="physicist",
            persona_b_name="builder",
            shared_object_text="A test scenario",
        ),
    )
    failed = await fail_run(db, run.id, "Connection timeout")
    assert failed.status == "failed"
    assert failed.error_message == "Connection timeout"


async def test_get_runs_filters_by_status(db) -> None:
    """Verify runs can be filtered by status."""
    await create_run(
        db,
        RunCreate(
            persona_a_name="a",
            persona_b_name="b",
            shared_object_text="test",
        ),
    )
    run2 = await create_run(
        db,
        RunCreate(
            persona_a_name="c",
            persona_b_name="d",
            shared_object_text="test2",
        ),
    )
    await fail_run(db, run2.id, "error")

    pending = await get_runs(db, status="pending")
    failed = await get_runs(db, status="failed")
    assert len(pending) == 1
    assert len(failed) == 1


async def test_pairing_history_tracks_pairings(db) -> None:
    """Verify pairing history records and retrieves pairings."""
    run = await create_run(
        db,
        RunCreate(
            persona_a_name="physicist",
            persona_b_name="builder",
            shared_object_text="test",
        ),
    )
    await record_pairing(db, "physicist", "builder", run.id)
    recent = await get_recent_pairings(db, limit=5)
    assert len(recent) == 1
    # Names are sorted in record_pairing
    assert recent[0] == ("builder", "physicist")
```

- **VALIDATE**: `uv run pytest tests/test_db.py -v`

---

### Task 24: CREATE `tests/test_personas.py`

- **IMPLEMENT**:

```python
"""Tests for the persona library and selection logic."""

from src.personas.library import (
    get_all_personas,
    get_all_shared_objects,
    get_persona_by_name,
    get_persona_pair,
    get_random_shared_object,
)
from src.personas.models import Persona, SharedObject


def test_library_has_minimum_personas() -> None:
    """Verify the library contains at least 4 personas for Feature 1."""
    personas = get_all_personas()
    assert len(personas) >= 4


def test_all_personas_fully_specified() -> None:
    """Verify every persona has all four dimensions filled in."""
    for persona in get_all_personas():
        assert persona.name, f"Persona missing name"
        assert persona.title, f"{persona.name} missing title"
        assert len(persona.worldview) > 50, f"{persona.name} worldview too short"
        assert len(persona.vocabulary_style) > 50, f"{persona.name} vocabulary too short"
        assert len(persona.core_obsessions) > 50, f"{persona.name} obsessions too short"
        assert len(persona.way_of_seeing) > 50, f"{persona.name} way_of_seeing too short"


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
        for b in personas[i + 1:]:
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
```

- **VALIDATE**: `uv run pytest tests/test_personas.py -v`

---

### Task 25: CREATE `tests/test_engine.py`

- **IMPLEMENT**:

```python
"""Tests for the conversation engine.

All vLLM calls are mocked — no real inference happens in tests.
"""

from unittest.mock import AsyncMock, patch

from src.db.queries import Turn
from src.engine.conversation import ConversationRunner, InferenceError
from src.engine.models import ConversationConfig, ConversationRequest


async def test_conversation_produces_correct_turn_count(
    test_persona_a, test_persona_b, test_shared_object, mock_openai_response
) -> None:
    """Verify a conversation produces the expected number of turns."""
    turns_per_agent = 3
    config = ConversationConfig(turns_per_agent=turns_per_agent)
    request = ConversationRequest(
        persona_a=test_persona_a,
        persona_b=test_persona_b,
        shared_object=test_shared_object,
        config=config,
    )

    runner = ConversationRunner()
    mock_create = AsyncMock(
        side_effect=[
            mock_openai_response(f"Turn {i} response") for i in range(1, 7)
        ]
    )

    with patch.object(runner._client.chat.completions, "create", mock_create):
        turns = await runner.run(request)

    assert len(turns) == turns_per_agent * 2
    assert all(isinstance(t, Turn) for t in turns)


async def test_conversation_alternates_personas(
    test_persona_a, test_persona_b, test_shared_object, mock_openai_response
) -> None:
    """Verify personas alternate correctly: A, B, A, B, ..."""
    config = ConversationConfig(turns_per_agent=2)
    request = ConversationRequest(
        persona_a=test_persona_a,
        persona_b=test_persona_b,
        shared_object=test_shared_object,
        config=config,
    )

    runner = ConversationRunner()
    mock_create = AsyncMock(
        side_effect=[mock_openai_response(f"Turn {i}") for i in range(1, 5)]
    )

    with patch.object(runner._client.chat.completions, "create", mock_create):
        turns = await runner.run(request)

    assert turns[0].persona_name == test_persona_a.name
    assert turns[1].persona_name == test_persona_b.name
    assert turns[2].persona_name == test_persona_a.name
    assert turns[3].persona_name == test_persona_b.name


async def test_conversation_builds_message_history(
    test_persona_a, test_persona_b, test_shared_object, mock_openai_response
) -> None:
    """Verify message history grows with each turn."""
    config = ConversationConfig(turns_per_agent=2)
    request = ConversationRequest(
        persona_a=test_persona_a,
        persona_b=test_persona_b,
        shared_object=test_shared_object,
        config=config,
    )

    runner = ConversationRunner()
    call_args_list = []
    mock_create = AsyncMock(
        side_effect=[mock_openai_response(f"Turn {i}") for i in range(1, 5)]
    )

    with patch.object(runner._client.chat.completions, "create", mock_create):
        await runner.run(request)
        call_args_list = mock_create.call_args_list

    # First call: system + opening (2 messages)
    first_messages = call_args_list[0].kwargs.get(
        "messages", call_args_list[0][1].get("messages", [])
    )
    assert len(first_messages) == 2  # system + user/opening

    # Last call should have more messages (system + opening + history)
    last_messages = call_args_list[-1].kwargs.get(
        "messages", call_args_list[-1][1].get("messages", [])
    )
    assert len(last_messages) > 2


async def test_conversation_raises_inference_error_on_connection_failure(
    test_persona_a, test_persona_b, test_shared_object
) -> None:
    """Verify InferenceError is raised when vLLM is unreachable."""
    from openai import APIConnectionError

    config = ConversationConfig(turns_per_agent=1)
    request = ConversationRequest(
        persona_a=test_persona_a,
        persona_b=test_persona_b,
        shared_object=test_shared_object,
        config=config,
    )

    runner = ConversationRunner()
    mock_create = AsyncMock(
        side_effect=APIConnectionError(request=None)
    )

    with patch.object(runner._client.chat.completions, "create", mock_create):
        try:
            await runner.run(request)
            assert False, "Expected InferenceError"
        except InferenceError:
            pass  # Expected


async def test_conversation_raises_inference_error_on_empty_response(
    test_persona_a, test_persona_b, test_shared_object, mock_openai_response
) -> None:
    """Verify InferenceError is raised when vLLM returns empty content."""
    config = ConversationConfig(turns_per_agent=1)
    request = ConversationRequest(
        persona_a=test_persona_a,
        persona_b=test_persona_b,
        shared_object=test_shared_object,
        config=config,
    )

    runner = ConversationRunner()
    empty_response = mock_openai_response("")
    empty_response.choices[0].message.content = ""
    mock_create = AsyncMock(return_value=empty_response)

    with patch.object(runner._client.chat.completions, "create", mock_create):
        try:
            await runner.run(request)
            assert False, "Expected InferenceError"
        except InferenceError:
            pass  # Expected
```

- **VALIDATE**: `uv run pytest tests/test_engine.py -v`

---

### Task 26: CREATE `tests/test_boundaries.py`

Architectural boundary verification tests.

- **IMPLEMENT**:

```python
"""Architectural boundary verification tests.

These tests ensure that module boundaries defined in CLAUDE.md
are respected. They inspect source files for forbidden imports
to catch boundary violations at test time.
"""

import ast
from pathlib import Path


def _get_imports(file_path: Path) -> set[str]:
    """Extract all imported module names from a Python file."""
    source = file_path.read_text()
    tree = ast.parse(source)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
    return imports


def _get_all_imports_in_dir(dir_path: Path) -> set[str]:
    """Collect all imports from all Python files in a directory."""
    all_imports: set[str] = set()
    for py_file in dir_path.rglob("*.py"):
        all_imports.update(_get_imports(py_file))
    return all_imports


def test_engine_has_no_anthropic_imports() -> None:
    """Verify the engine module does not import the Anthropic SDK.

    The engine layer communicates with vLLM only — never the Anthropic API.
    """
    engine_dir = Path("src/engine")
    if not engine_dir.exists():
        return
    imports = _get_all_imports_in_dir(engine_dir)
    assert "anthropic" not in imports, (
        "src/engine/ must not import anthropic — it communicates with vLLM only"
    )


def test_personas_has_no_llm_imports() -> None:
    """Verify the persona module makes no LLM calls.

    The persona layer is pure data and selection logic.
    """
    personas_dir = Path("src/personas")
    if not personas_dir.exists():
        return
    imports = _get_all_imports_in_dir(personas_dir)
    assert "openai" not in imports, (
        "src/personas/ must not import openai — it is pure data"
    )
    assert "anthropic" not in imports, (
        "src/personas/ must not import anthropic — it is pure data"
    )


def test_db_has_no_llm_imports() -> None:
    """Verify the database module makes no LLM calls.

    The data layer handles storage only.
    """
    db_dir = Path("src/db")
    if not db_dir.exists():
        return
    imports = _get_all_imports_in_dir(db_dir)
    assert "openai" not in imports, (
        "src/db/ must not import openai — it handles storage only"
    )
    assert "anthropic" not in imports, (
        "src/db/ must not import anthropic — it handles storage only"
    )
```

- **VALIDATE**: `uv run pytest tests/test_boundaries.py -v`

---

### Task 27: CREATE `tests/test_api.py`

- **IMPLEMENT**:

```python
"""Tests for the API endpoints."""


async def test_health_endpoint(client) -> None:
    """Verify the health endpoint returns ok status."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_list_runs_empty(client) -> None:
    """Verify listing runs returns empty list when none exist."""
    response = await client.get("/api/runs")
    assert response.status_code == 200
    assert response.json() == []
```

- **VALIDATE**: `uv run pytest tests/test_api.py -v`

---

### Task 28: VALIDATE full test suite and linting

Run the complete validation suite to confirm everything passes.

- **VALIDATE**:

```bash
# Level 1: Lint and format
uv run ruff check .
uv run ruff format --check .

# Level 2: Full test suite
uv run pytest -v

# Level 3: Quick smoke test
uv run python scripts/run_conversation.py --list-personas
uv run python scripts/run_conversation.py --list-objects
uv run python -c "from src.config import settings; print(settings.model_dump())"
```

- **EXPECTED**: All commands pass with exit code 0. All tests pass. No lint or format errors.

---

## FILES CREATED

| File | Purpose |
|------|---------|
| `tests/__init__.py` | Package marker |
| `tests/conftest.py` | Shared fixtures (db, client, personas, mock factory) |
| `tests/test_config.py` | Config default values and types |
| `tests/test_db.py` | CRUD, transcript storage, pairing history |
| `tests/test_personas.py` | Library completeness, selection, avoidance |
| `tests/test_engine.py` | Turn count, alternation, history, errors |
| `tests/test_boundaries.py` | No cross-layer imports |
| `tests/test_api.py` | Health endpoint, run listing |

## VALIDATION COMMANDS

```bash
# All tests
uv run pytest -v

# Individual test files (for debugging)
uv run pytest tests/test_config.py -v
uv run pytest tests/test_db.py -v
uv run pytest tests/test_personas.py -v
uv run pytest tests/test_engine.py -v
uv run pytest tests/test_boundaries.py -v
uv run pytest tests/test_api.py -v

# Lint everything
uv run ruff check .
uv run ruff format --check .
```

## DONE WHEN

- [ ] All test files created and passing
- [ ] `uv run pytest -v` — all tests green
- [ ] `uv run ruff check .` — zero errors
- [ ] `uv run ruff format --check .` — zero errors
- [ ] Boundary tests verify: engine has no anthropic, personas has no LLM imports, db has no LLM imports
- [ ] All LLM calls mocked — no real inference in tests
- [ ] CLI smoke tests pass (--list-personas, --list-objects)

---

## FEATURE 1 COMPLETE CHECKLIST

When this PBI passes, Feature 1 is done. Verify all acceptance criteria:

- [ ] Project scaffolded with uv, pyproject.toml, and all dependencies
- [ ] Configuration module loads all settings from environment variables
- [ ] SQLite schema creates runs and pairing_history tables
- [ ] Typed query layer returns Pydantic models for all operations
- [ ] 4 fully specified personas with all four dimensions
- [ ] 5 curated shared objects (scenarios, questions, problems)
- [ ] Persona pair selection avoids recent repeats
- [ ] ConversationRunner manages turn-taking via vLLM (OpenAI-compatible API)
- [ ] System prompts enforce persona voice across all four dimensions
- [ ] Transcripts stored as JSON in SQLite with full metadata
- [ ] CLI runner supports listing personas/objects and running conversations
- [ ] FastAPI app with health endpoint and run listing API
- [ ] All tests pass with mocked LLM calls
- [ ] Architectural boundary tests verify no cross-layer imports
- [ ] Ruff lint and format pass with zero errors
- [ ] No `print()` in application code — logging only (CLI script excepted)
- [ ] All functions have type hints and docstrings
