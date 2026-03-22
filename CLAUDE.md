# CLAUDE.md — Medici Engine Development Guide

This file provides the conventions, rules, and architectural guidelines for AI-assisted development on the Medici Engine project. It is the authoritative source for how code should be written, structured, and documented.

For the development plan and resolved decisions, see `.agents/DevPlan.md`. For the project summary and design rationale, see `.agents/Summary.md`.

---

## Claude Soul

Be honest in all reviews of code, comments, plans, and suggestions. If something is missed or something is not a good idea, let me know. Do not compliment unless it is truly deserved.

## Project Overview

The Medici Engine is a multi-agent creative collision system. It pairs AI agents embodying radically different personas, gives them a shared object to react to, and mines the productive misunderstandings for novel ideas. A synthesizer agent extracts structured output from the conversation, a scoring model rates it with reasoning, and a human makes the final keep/discard call.

**Tech stack summary:** Python 3.12, uv (package manager), FastAPI, Pydantic AI, SQLite (aiosqlite), vLLM (local inference), Anthropic API (synthesis + scoring), Ruff, Pytest.

**Infrastructure:** 4x NVIDIA 5060Ti GPUs for local conversation model inference via vLLM.

---

## Documentation Requirements

### File and Class Descriptions

Every Python file must begin with a module-level docstring describing the file's purpose, its role in the system, and what layer it belongs to.

```python
"""
Conversation runner for the Medici Engine.

Manages turn-taking between two persona agents given a shared object,
producing a full conversation transcript. This module belongs to the
Engine layer and communicates with the local vLLM inference server
via an OpenAI-compatible API.
"""
```

Every class must have a class-level docstring describing its responsibility and how it fits into the broader architecture.

```python
class ConversationRunner:
    """Orchestrates a multi-turn conversation between two persona agents.

    Takes two fully specified personas and a shared object, manages
    turn-taking for a configurable number of exchanges, and returns
    the complete transcript. Communicates with the local inference
    server via the OpenAI-compatible client.
    """
```

### Method and Function Comments

Every method and function must have a short docstring (one to two sentences) describing what it does, not how it does it. Use Google-style docstrings when parameters or return values are non-obvious.

```python
async def run_conversation(
    persona_a: Persona,
    persona_b: Persona,
    shared_object: SharedObject,
    turns: int = 5,
) -> Transcript:
    """Run a full conversation between two personas on a shared object.

    Args:
        persona_a: First persona specification.
        persona_b: Second persona specification.
        shared_object: The seed object both personas react to.
        turns: Number of turns per agent.

    Returns:
        Complete conversation transcript with metadata.
    """
```

Inline comments should explain *why*, not *what*. If the code needs a comment to explain what it does, the code should be rewritten to be clearer.

```python
# vLLM serves an OpenAI-compatible API, so we use the standard client with a base_url override
client = AsyncOpenAI(base_url=settings.vllm_base_url, api_key="unused")
```

---

## Python Style and Conventions

### Foundational Standards

This project follows **PEP 8** as enforced by **Ruff**. Ruff replaces flake8, black, and isort. The canonical configuration lives in `pyproject.toml`.

- **Line length:** 88 characters (black default).
- **Python target:** 3.12.
- **String quotes:** Double quotes preferred.
- **Trailing commas:** Always use trailing commas in multi-line structures (tuples, lists, dicts, function signatures). This produces cleaner diffs.

### Naming Conventions

Follow PEP 8 naming strictly:

| Element | Convention | Example |
|---------|-----------|---------|
| Modules | `snake_case` | `conversation.py`, `personas.py` |
| Classes | `PascalCase` | `ConversationRunner`, `SynthesizerAgent` |
| Functions / methods | `snake_case` | `run_conversation`, `score_concept` |
| Constants | `UPPER_SNAKE_CASE` | `CONVERSATION_MODEL`, `SCORING_MODEL` |
| Private attributes | Leading underscore | `_db`, `_client` |
| Type variables | `PascalCase` | `T`, `PersonaT` |

Avoid abbreviations unless they are universally understood (`db`, `id`, `url`, `api`). Prefer descriptive names over short ones.

### Import Organization

Ruff handles import sorting automatically. Imports must follow this order (enforced by isort rules in Ruff):

1. Standard library (`os`, `asyncio`, `datetime`, `uuid`)
2. Third-party packages (`fastapi`, `pydantic`, `openai`, `aiosqlite`)
3. Local application imports (`src.db.queries`, `src.engine.conversation`)

Each group is separated by a blank line. Use absolute imports throughout — no relative imports.

```python
import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel

from src.config import settings
from src.db.queries import get_concepts
```

---

## Type Hints

Type hints are mandatory on all function signatures (parameters and return types). This project uses Pydantic throughout, making type safety a first-class concern.

### Rules

- All function parameters must have type annotations.
- All function return types must be annotated (use `-> None` explicitly when applicable).
- Use modern Python 3.12 syntax: `str | None` instead of `Optional[str]`, `list[str]` instead of `List[str]`.
- Use `Any` sparingly and only when genuinely needed. Prefer specific types.
- Pydantic models are the preferred way to define structured data — use them for API schemas, database results, agent responses, and conversation state.

```python
async def get_concepts(db: aiosqlite.Connection, limit: int = 20) -> list[Concept]:
    ...

def get_persona_pair(exclude: list[str] | None = None) -> tuple[Persona, Persona]:
    ...
```

### Pydantic Model Conventions

- All fields must have type annotations.
- Use `Field()` for default values, descriptions, and validation constraints.
- Use `model_config` for model-level settings (not the legacy `Config` inner class).
- Models used as API schemas should have descriptive field names — avoid single-letter abbreviations.

```python
class Concept(BaseModel):
    """A structured concept extracted by the synthesizer."""

    run_id: UUID
    title: str
    premise: str
    originality: str
    scores: list[AxisScore] | None = None
    status: str = Field(default="pending", description="pending | kept | discarded")
```

---

## Async Patterns

The stack is async-native (FastAPI, aiosqlite, OpenAI async client). Follow these conventions:

### Rules

- All I/O-bound functions must be `async`. This includes database queries, LLM API calls, and file operations.
- Never use synchronous blocking calls (`time.sleep`, synchronous `requests`) in async code. Use `asyncio.sleep` and `httpx`/`openai` async clients respectively.
- Use `asyncio.gather()` for concurrent independent operations (e.g., running multiple conversations in parallel).
- Use `asyncio.TaskGroup` (Python 3.11+) for structured concurrency when tasks are interdependent.
- Never catch `BaseException` or bare `except:` in async code — it can swallow cancellation signals.

### Database Connection Management

SQLite connections are created during application startup (via FastAPI lifespan) and passed as dependencies. Never create connections inside request handlers.

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = await aiosqlite.connect(settings.database_path)
    yield
    await app.state.db.close()
```

---

## Error Handling

### Rules

- Use specific exception types. Never raise bare `Exception` or catch broad exceptions without re-raising.
- Define custom exception classes for domain-specific errors. Place them in the module where they originate.
- API endpoints should catch domain exceptions and return structured error responses — never let raw tracebacks reach the client.
- Conversation runs should log errors and continue where possible. A single failed turn should not silently abort a batch.
- LLM calls (synthesis, scoring) should handle rate limits and transient failures with retries and clear logging.

```python
class ConversationError(Exception):
    """Raised when the conversation runner encounters a non-recoverable error."""

class InferenceError(ConversationError):
    """Raised when the local vLLM server fails to respond."""
```

### Logging

Use Python's built-in `logging` module with structured context. Every module should get its own logger.

```python
import logging

logger = logging.getLogger(__name__)

async def run_conversation(self, ...) -> Transcript:
    """Run a full conversation between two personas."""
    logger.info("Starting conversation", extra={"personas": [a.name, b.name], "turns": turns})
    ...
    logger.error("Inference failed on turn", extra={"turn": turn, "error": str(e)})
```

Do not use `print()` for any operational output. Use logging at the appropriate level: `DEBUG` for development detail, `INFO` for operational events, `WARNING` for recoverable issues, `ERROR` for failures.

---

## Architectural Boundaries

These boundaries are non-negotiable. They are enforced by module structure, not convention.

### System Components

| Component | Module | Responsibility |
|-----------|--------|---------------|
| Conversation Engine | `src/engine/` | Turn-taking, transcript generation, vLLM communication |
| Persona Library | `src/personas/` | Persona definitions, selection logic, pairing history |
| Synthesizer | `src/synthesis/` | Transcript analysis, structured concept extraction (Sonnet via API) |
| Scorer | `src/scoring/` | Concept evaluation across domain axes (Opus via API) |
| Data Layer | `src/db/` | All SQLite access, schema, typed queries |
| API / UI | `src/api/` | FastAPI endpoints for the review UI and batch setup |
| Configuration | `src/config.py` | All settings, env var loading, model configuration |

### Layer Dependencies

Dependencies flow downward only. No module may import from a module above it in the hierarchy.

```
API Layer          (src/api/)
       ↓
Scoring Layer      (src/scoring/)
       ↓
Synthesis Layer    (src/synthesis/)
       ↓
Engine Layer       (src/engine/)
       ↓
Persona Library    (src/personas/)
       ↓
Data Layer         (src/db/)
       ↓
Configuration      (src/config.py)
```

Cross-cutting rules:
- `src/engine/` communicates with the local vLLM server only — no Anthropic API calls.
- `src/synthesis/` and `src/scoring/` communicate with the Anthropic API only — no vLLM calls.
- `src/personas/` is pure data and selection logic — no LLM calls of any kind.
- `src/db/` is the only module that touches SQLite. No raw SQL anywhere else.

### Database Access

All database queries go through `src/db/queries.py`. No raw SQL in engine, synthesis, scoring, or API code. The query layer returns typed Pydantic models — never raw rows or dicts.

---

## Testing Conventions

### Rules

- Use **Pytest** with **pytest-asyncio** for all tests.
- Test files mirror the source structure: `tests/test_engine.py`, `tests/test_synthesis.py`, `tests/test_api.py`.
- Use fixtures in `tests/conftest.py` for shared setup (database connections, test clients, mock LLM responses).
- Mock LLM calls (both vLLM and Anthropic API) — never make real inference calls in tests.
- API tests should use `httpx.AsyncClient` with the FastAPI test client.

### Boundary Verification Tests

Include tests that verify architectural boundaries by inspecting imports:

```python
def test_engine_has_no_anthropic_imports():
    """Verify the engine module does not import the Anthropic SDK."""
    import ast
    # Parse engine source files and assert no anthropic imports

def test_personas_has_no_llm_imports():
    """Verify the persona module makes no LLM calls."""
    import ast
    # Parse persona source files and assert no openai or anthropic imports
```

### Test Naming

Test names should describe the behavior being verified, not the implementation:

```python
# Good
async def test_conversation_produces_transcript_with_correct_turn_count():
async def test_synthesizer_extracts_structured_concept_from_transcript():
async def test_scorer_provides_reasoning_for_each_axis():

# Bad
async def test_conversation_runner():
async def test_synthesizer():
```

---

## Dependency and Configuration Management

### Environment Variables

All configuration flows through environment variables loaded via `python-dotenv`. The canonical list lives in `.env.example` with comments explaining each variable.

- Never hardcode secrets, API keys, or connection strings.
- Use `src/config.py` as the single source of truth for loading and exposing configuration. Other modules import from `config.py` — they never read `os.getenv` directly.

Key configuration values:
- `VLLM_BASE_URL` — local vLLM server endpoint (default: `http://localhost:8000/v1`)
- `CONVERSATION_MODEL` — model name served by vLLM (default: `MythoMax-L2-13B`)
- `ANTHROPIC_API_KEY` — API key for synthesis and scoring
- `SYNTHESIS_MODEL` — Anthropic model for synthesis (default: `claude-sonnet-4-6`)
- `SCORING_MODEL` — Anthropic model for scoring (default: `claude-opus-4-6`)
- `DATABASE_PATH` — SQLite database file path (default: `data/yield_engine.db`)

### Package Management

- Use **uv** for all dependency management. Never use pip directly.
- All dependencies are declared in `pyproject.toml`.
- Lock files (`uv.lock`) are committed to the repository.
- Pin major versions for critical dependencies (Pydantic AI, FastAPI). Allow patch updates.

---

## Git and Workflow Conventions

### Commit Messages

Use conventional commit format:

```
feat: add conversation runner with configurable turn count
fix: handle vLLM timeout during long conversation turns
refactor: extract persona selection logic from engine
docs: add development setup guide to README
test: add boundary verification tests for engine imports
```

### Branch Strategy

- `main` is the stable branch. All merges go through pull requests.
- Feature branches: `feat/conversation-engine`, `feat/synthesizer-agent`.
- Fix branches: `fix/sqlite-connection-cleanup`.
- Keep branches short-lived. Merge frequently.

---

## Common Patterns

### Dependency Injection via FastAPI

Pass shared resources (database connection, configuration) through FastAPI's `app.state` or dependency injection — not through global variables.

```python
@router.post("/api/batch")
async def create_batch(request: Request, body: BatchRequest):
    db = request.app.state.db
    batch = await create_conversation_batch(db, body)
    return batch
```

### Repository Pattern for Database Access

`src/db/queries.py` acts as the repository layer. Every database operation is an async function that accepts a connection and returns typed models. This keeps SQL isolated and makes the data layer independently testable.

```python
async def get_concepts(
    db: aiosqlite.Connection,
    status: str | None = None,
    limit: int = 20,
) -> list[Concept]:
    """Fetch concepts, optionally filtered by review status."""
    ...
```

### Model-Agnostic Provider Pattern

The engine layer uses the OpenAI-compatible client pointed at the local vLLM server. The synthesis and scoring layers use the Anthropic client. Both are configured via `src/config.py`. Swapping models is an env var change, not a code change.

```python
from src.config import settings

# Engine layer — local inference
client = AsyncOpenAI(base_url=settings.vllm_base_url, api_key="unused")

# Synthesis layer — Anthropic API
client = AsyncAnthropic(api_key=settings.anthropic_api_key)
```

### Structured Output

All synthesis and scoring output uses Pydantic models. Never return unstructured strings from agents.

```python
class Concept(BaseModel):
    """Structured concept extracted from a conversation transcript."""

    title: str
    premise: str
    originality: str

class AxisScore(BaseModel):
    """Score and reasoning for a single evaluation axis."""

    axis: str
    score: float
    reasoning: str
```

---

## What Not to Do

- **Do not** add dependencies without adding them to `pyproject.toml` and running `uv sync`.
- **Do not** write synchronous database or HTTP code anywhere in the application.
- **Do not** import across architectural boundaries (see the boundary rules above).
- **Do not** put raw SQL in engine, synthesis, scoring, or API modules.
- **Do not** create global mutable state. Use FastAPI lifespan and dependency injection.
- **Do not** suppress or silence exceptions without logging them.
- **Do not** use `print()` for operational output. Use the `logging` module.
- **Do not** skip type hints on any function signature.
- **Do not** make real LLM calls in tests. Mock all inference.
- **Do not** hardcode model names in application code. Always pull from configuration.
