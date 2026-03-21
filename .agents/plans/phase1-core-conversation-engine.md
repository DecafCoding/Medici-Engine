# Feature: Phase 1 — Core Conversation Engine

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

---

## Feature Description

Build the foundational conversation engine for the Yield Engine: two AI agents with assigned personas converse about a shared object, producing full transcripts that are logged to SQLite. This phase establishes the entire project scaffold (uv, FastAPI, database, configuration) and delivers the core turn-taking loop that all subsequent phases build on. No synthesis or scoring — just raw creative collisions.

## User Story

As a creative researcher
I want to run conversations between two persona-driven AI agents given a shared object
So that I can generate raw creative collision transcripts to mine for novel ideas

## Problem Statement

The Yield Engine has no codebase yet. Phase 1 must bootstrap the entire project — package management, configuration, database, and the core conversation engine — from zero to a working system that produces persona-driven transcripts.

## Solution Statement

Scaffold a Python 3.12 project with uv, FastAPI, and aiosqlite. Implement a conversation runner that manages turn-taking between two persona agents via a local vLLM server (OpenAI-compatible API). Store complete transcripts in SQLite. Provide both a CLI entry point (for Phases 1-4) and a health-check API endpoint. Include a starter set of 4 personas to validate the system produces genuine persona-driven divergence.

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: High
**Primary Systems Affected**: Project scaffold, Configuration, Data Layer, Engine Layer, Persona Library
**Dependencies**: Python 3.12, uv, FastAPI, uvicorn, openai (AsyncOpenAI), aiosqlite, Pydantic, python-dotenv, Ruff, Pytest, pytest-asyncio, httpx

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

This is a greenfield project. No source code exists yet. Read these design documents:

- `CLAUDE.md` — **Mandatory.** All coding conventions, architectural boundaries, naming rules, documentation requirements, and patterns. This is the law.
- `.agents/DevPlan.md` — Phase 1 definition (lines 35-43), resolved decisions on turn count (lines 109-115), shared objects (lines 117-125), persona library size (lines 127-129), conversation model (lines 139-151), storage (lines 154-156), run trigger (lines 158-160).
- `.agents/Summary.md` — System overview, component roles, yield expectations, key techniques (defamiliarization, constraint-based seeding, negation framing).

### New Files to Create

```
yield-engine/
├── .env.example                    # Environment variable documentation
├── .env                            # Local environment config (gitignored)
├── .gitignore                      # Python/uv gitignore
├── pyproject.toml                  # Project metadata, dependencies, tool config
├── src/
│   ├── __init__.py
│   ├── config.py                   # Settings loaded from env vars (single source of truth)
│   ├── main.py                     # FastAPI app with lifespan, health endpoint
│   ├── db/
│   │   ├── __init__.py
│   │   ├── schema.py               # SQL schema definitions, init_schema()
│   │   └── queries.py              # Typed query functions returning Pydantic models
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── conversation.py         # ConversationRunner class — turn-taking loop
│   │   └── models.py               # Engine-layer Pydantic models (Transcript, Turn, etc.)
│   ├── personas/
│   │   ├── __init__.py
│   │   ├── library.py              # Persona definitions and selection logic
│   │   └── models.py               # Persona and SharedObject Pydantic models
│   └── api/
│       ├── __init__.py
│       └── routes.py               # Placeholder API routes (health already in main.py)
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Shared fixtures (db, mock vLLM, test personas)
│   ├── test_config.py              # Config loading tests
│   ├── test_db.py                  # Schema and query tests
│   ├── test_engine.py              # Conversation runner tests (mocked vLLM)
│   ├── test_personas.py            # Persona selection and pairing tests
│   └── test_boundaries.py          # Architectural boundary verification
├── data/                           # SQLite database directory (gitignored contents)
│   └── .gitkeep
└── scripts/
    └── run_conversation.py         # CLI entry point for running conversations
```

### Relevant Documentation — YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- OpenAI Python SDK (AsyncOpenAI): https://github.com/openai/openai-python
  - Async chat completions, `extra_body` for vLLM-specific params
  - Why: The engine communicates with vLLM via this client
- aiosqlite: https://github.com/omnilib/aiosqlite
  - Connection lifecycle, row_factory, transaction patterns
  - Why: All database access uses aiosqlite
- FastAPI Lifespan: https://fastapi.tiangolo.com/advanced/events/#lifespan
  - Resource management pattern for database connections
  - Why: Database connection created/closed via lifespan
- uv documentation: https://docs.astral.sh/uv/
  - Project init, dependency management, running commands
  - Why: uv is the sole package manager
- Ruff configuration: https://docs.astral.sh/ruff/configuration/
  - pyproject.toml setup, rule selection
  - Why: Ruff is the sole linter/formatter

### Patterns to Follow

**Naming Conventions** (from CLAUDE.md):
- Modules: `snake_case` — `conversation.py`, `library.py`
- Classes: `PascalCase` — `ConversationRunner`, `Persona`
- Functions: `snake_case` — `run_conversation`, `get_persona_pair`
- Constants: `UPPER_SNAKE_CASE` — `CONVERSATION_MODEL`, `DEFAULT_TURNS`
- Private: leading underscore — `_client`, `_db`

**Documentation** (from CLAUDE.md):
- Every file: module-level docstring (purpose, role, layer)
- Every class: class-level docstring (responsibility, architecture fit)
- Every function: short docstring (what, not how)
- Inline comments: explain *why*, not *what*

**Error Handling** (from CLAUDE.md):
- Specific exception types, never bare `Exception`
- Custom exceptions for domain errors
- Each module gets its own `logger = logging.getLogger(__name__)`
- Never use `print()` — always `logging`

**Imports** (from CLAUDE.md):
- Absolute imports only, no relative imports
- Order: stdlib → third-party → local (enforced by Ruff isort)

**Async** (from CLAUDE.md):
- All I/O functions must be `async`
- Never use synchronous blocking calls
- Use `asyncio.gather()` for concurrent independent operations

**Database** (from CLAUDE.md):
- All SQL isolated in `src/db/`
- Query functions return Pydantic models, never raw rows
- Connection via FastAPI lifespan and `app.state`

**Engine Boundary** (from CLAUDE.md):
- `src/engine/` communicates with local vLLM **only** — no Anthropic API
- Uses `AsyncOpenAI` with `base_url` override pointing to vLLM
- Model name from configuration, never hardcoded

**Persona Boundary** (from CLAUDE.md):
- `src/personas/` is pure data and selection logic — no LLM calls of any kind

---

## IMPLEMENTATION PLAN

### Phase 1: Project Scaffold & Configuration

Bootstrap the project with uv, create the directory structure, configure all tooling (Ruff, Pytest), and establish the configuration module that loads environment variables.

**Tasks:**
- Initialize uv project with Python 3.12
- Add all dependencies (runtime + dev)
- Configure Ruff and Pytest in pyproject.toml
- Create `.env.example` and `.gitignore`
- Implement `src/config.py` as single source of truth for settings

### Phase 2: Data Layer

Create the SQLite schema and typed query layer. This is the foundation that the engine writes transcripts to.

**Tasks:**
- Define schema (runs table, shared_objects seed data)
- Implement typed query functions returning Pydantic models
- Wire schema initialization into FastAPI lifespan

### Phase 3: Persona Library

Build the persona model and a starter library of 4 deeply specified personas. Implement selection logic that picks pairs and avoids recent repeats.

**Tasks:**
- Define Persona and SharedObject Pydantic models
- Create 4 starter personas with full four-dimension specifications
- Implement pair selection with history-aware logic

### Phase 4: Conversation Engine

Build the core turn-taking loop. The ConversationRunner takes two personas and a shared object, manages alternating turns via the vLLM server, and returns a complete transcript.

**Tasks:**
- Define engine-layer models (Turn, Transcript, ConversationConfig)
- Implement ConversationRunner with vLLM communication
- Handle errors (connection, timeout, context overflow)
- Build system prompts that enforce persona voice

### Phase 5: Integration & CLI

Wire everything together: FastAPI app with lifespan, CLI script for running conversations, database persistence of transcripts.

**Tasks:**
- Implement FastAPI app with lifespan (database connection)
- Create CLI runner script
- Connect engine output to database persistence

### Phase 6: Testing & Validation

Comprehensive tests covering all layers, with mocked LLM calls and architectural boundary verification.

**Tasks:**
- Shared test fixtures (mock vLLM, in-memory database)
- Unit tests for each module
- Boundary verification tests
- Lint and format validation

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

---

### Task 1: CREATE `pyproject.toml`

Initialize the project and configure all tooling.

- **IMPLEMENT**: Run `uv init` or create `pyproject.toml` manually with the following structure:

```toml
[project]
name = "yield-engine"
version = "0.1.0"
description = "Multi-agent creative collision system for generating novel ideas"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "openai>=1.60.0",
    "aiosqlite>=0.21.0",
    "pydantic>=2.10.0",
    "python-dotenv>=1.0.0",
]

[dependency-groups]
dev = [
    "ruff>=0.9.0",
    "pytest>=8.3.0",
    "pytest-asyncio>=0.25.0",
    "httpx>=0.28.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.backends"

# ── Ruff ──────────────────────────────────────────────
[tool.ruff]
target-version = "py312"
line-length = 88
src = ["src"]

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort
    "N",      # pep8-naming
    "UP",     # pyupgrade (modern Python syntax)
    "B",      # flake8-bugbear
    "SIM",    # flake8-simplify
    "ASYNC",  # flake8-async
]

[tool.ruff.lint.isort]
known-first-party = ["src"]

# ── Pytest ────────────────────────────────────────────
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- **IMPORTS**: N/A (configuration file)
- **GOTCHA**: Use `uv add` commands after creating this file to generate `uv.lock`. Alternatively, create the file manually then run `uv sync` to resolve and lock dependencies. Either approach works — the lock file must be committed.
- **VALIDATE**: `uv sync && echo "Dependencies resolved successfully"`

---

### Task 2: CREATE `.gitignore`

- **IMPLEMENT**: Standard Python gitignore plus project-specific entries:

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
*.egg

# Virtual environment
.venv/

# Environment variables
.env

# Database
data/*.db

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# uv
.python-version

# Testing
.pytest_cache/
.coverage
htmlcov/
```

- **VALIDATE**: `cat .gitignore | head -5`

---

### Task 3: CREATE `.env.example`

- **IMPLEMENT**: Document all environment variables with defaults and descriptions:

```env
# ── vLLM Local Inference ──────────────────────────────
# Base URL for the local vLLM server (must include /v1 path)
VLLM_BASE_URL=http://localhost:8000/v1

# Model name served by vLLM (must match --served-model-name)
CONVERSATION_MODEL=MythoMax-L2-13B

# ── Anthropic API (not used in Phase 1) ──────────────
# API key for synthesis and scoring (Phases 3-4)
ANTHROPIC_API_KEY=

# Model for synthesis (Phase 3)
SYNTHESIS_MODEL=claude-sonnet-4-6

# Model for scoring (Phase 4)
SCORING_MODEL=claude-opus-4-6

# ── Database ──────────────────────────────────────────
# Path to SQLite database file
DATABASE_PATH=data/yield_engine.db

# ── Conversation Defaults ─────────────────────────────
# Default number of turns per agent (10 total exchanges)
DEFAULT_TURNS=5

# ── Inference Parameters ──────────────────────────────
# Temperature for conversation generation (0.0-2.0)
CONVERSATION_TEMPERATURE=0.9

# Repetition penalty for vLLM (1.0 = no penalty)
CONVERSATION_REPETITION_PENALTY=1.15

# Maximum tokens per turn
CONVERSATION_MAX_TOKENS=512
```

- **VALIDATE**: `cat .env.example | grep -c "="`  (should show ~10 variables)

---

### Task 4: CREATE `src/__init__.py`

- **IMPLEMENT**: Empty file (package marker).
- **VALIDATE**: `test -f src/__init__.py && echo "exists"`

---

### Task 5: CREATE `src/config.py`

Single source of truth for all configuration. Other modules import from here — they never read `os.getenv` directly.

- **IMPLEMENT**:

```python
"""
Configuration module for the Yield Engine.

Loads all settings from environment variables via python-dotenv.
This is the single source of truth for configuration — no other
module should read os.getenv directly. This module is the lowest
layer in the dependency hierarchy.
"""

import logging
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# Load .env file from project root
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All configuration flows through this class. Values are read from
    environment variables with fallback defaults suitable for local
    development.
    """

    # vLLM local inference
    vllm_base_url: str = Field(
        default="http://localhost:8000/v1",
        description="Base URL for the local vLLM server",
    )
    conversation_model: str = Field(
        default="MythoMax-L2-13B",
        description="Model name served by vLLM",
    )

    # Anthropic API (not used in Phase 1)
    anthropic_api_key: str = Field(
        default="",
        description="API key for Anthropic (synthesis and scoring)",
    )
    synthesis_model: str = Field(
        default="claude-sonnet-4-6",
        description="Anthropic model for synthesis",
    )
    scoring_model: str = Field(
        default="claude-opus-4-6",
        description="Anthropic model for scoring",
    )

    # Database
    database_path: str = Field(
        default="data/yield_engine.db",
        description="Path to SQLite database file",
    )

    # Conversation defaults
    default_turns: int = Field(
        default=5,
        description="Default number of turns per agent",
    )

    # Inference parameters
    conversation_temperature: float = Field(
        default=0.9,
        description="Temperature for conversation generation",
    )
    conversation_repetition_penalty: float = Field(
        default=1.15,
        description="Repetition penalty for vLLM",
    )
    conversation_max_tokens: int = Field(
        default=512,
        description="Maximum tokens per conversation turn",
    )

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
```

- **IMPORTS**: `pydantic`, `pydantic-settings`, `python-dotenv`
- **GOTCHA**: `pydantic-settings` is a separate package from `pydantic` since Pydantic v2. You must add it as a dependency: `uv add pydantic-settings`. Without it, `BaseSettings` will not be available.
- **VALIDATE**: `uv run python -c "from src.config import settings; print(settings.vllm_base_url)"`

---

### Task 6: CREATE `src/db/__init__.py`

- **IMPLEMENT**: Empty file.
- **VALIDATE**: `test -f src/db/__init__.py && echo "exists"`

---

### Task 7: CREATE `src/db/schema.py`

SQL schema definitions and initialization function.

- **IMPLEMENT**:

```python
"""
Database schema definitions for the Yield Engine.

Contains all CREATE TABLE statements and the schema initialization
function. This module belongs to the Data layer and is called during
application startup to ensure all tables exist.
"""

import logging

import aiosqlite

logger = logging.getLogger(__name__)

SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    persona_a_name TEXT NOT NULL,
    persona_b_name TEXT NOT NULL,
    shared_object_text TEXT NOT NULL,
    shared_object_type TEXT NOT NULL DEFAULT 'scenario',
    turns_per_agent INTEGER NOT NULL DEFAULT 5,
    transcript_json TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs(created_at);

CREATE TABLE IF NOT EXISTS pairing_history (
    id TEXT PRIMARY KEY,
    persona_a_name TEXT NOT NULL,
    persona_b_name TEXT NOT NULL,
    run_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (run_id) REFERENCES runs(id)
);

CREATE INDEX IF NOT EXISTS idx_pairing_history_personas
    ON pairing_history(persona_a_name, persona_b_name);
"""


async def init_schema(db: aiosqlite.Connection) -> None:
    """Create all tables and indexes if they don't already exist.

    Called during application startup via the FastAPI lifespan.
    Uses executescript which issues an implicit COMMIT.
    """
    await db.executescript(SCHEMA_SQL)
    logger.info("Database schema initialized")
```

- **PATTERN**: All SQL lives here — no raw SQL in any other module (CLAUDE.md boundary rule).
- **GOTCHA**: `executescript()` issues an implicit COMMIT before running. This is fine for schema init at startup. SQLite stores UUIDs as TEXT — convert at the query layer boundary.
- **VALIDATE**: `uv run python -c "from src.db.schema import SCHEMA_SQL; print('Schema loaded:', len(SCHEMA_SQL), 'chars')"`

---

### Task 8: CREATE `src/db/queries.py`

Typed query layer — the only module that touches SQLite. Returns Pydantic models, never raw rows.

- **IMPLEMENT**:

```python
"""
Typed query layer for the Yield Engine.

All database access flows through this module. Functions accept an
aiosqlite connection and return Pydantic models — never raw rows or
dicts. This module belongs to the Data layer.
"""

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID, uuid4

import aiosqlite
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ── Models ────────────────────────────────────────────


class Turn(BaseModel):
    """A single turn in a conversation transcript."""

    turn_number: int
    persona_name: str
    content: str


class Run(BaseModel):
    """A complete conversation run with metadata."""

    id: UUID
    persona_a_name: str
    persona_b_name: str
    shared_object_text: str
    shared_object_type: str
    turns_per_agent: int
    transcript: list[Turn] | None = None
    status: str = Field(default="pending")
    error_message: str | None = None
    created_at: str
    completed_at: str | None = None


class RunCreate(BaseModel):
    """Input model for creating a new run."""

    persona_a_name: str
    persona_b_name: str
    shared_object_text: str
    shared_object_type: str = "scenario"
    turns_per_agent: int = 5


class PairingRecord(BaseModel):
    """Record of a persona pairing used in a run."""

    id: UUID
    persona_a_name: str
    persona_b_name: str
    run_id: UUID
    created_at: str


# ── Helpers ───────────────────────────────────────────


def _row_to_run(row: aiosqlite.Row) -> Run:
    """Map a database row to a Run model."""
    transcript = None
    if row["transcript_json"]:
        transcript = [Turn(**t) for t in json.loads(row["transcript_json"])]

    return Run(
        id=UUID(row["id"]),
        persona_a_name=row["persona_a_name"],
        persona_b_name=row["persona_b_name"],
        shared_object_text=row["shared_object_text"],
        shared_object_type=row["shared_object_type"],
        turns_per_agent=row["turns_per_agent"],
        transcript=transcript,
        status=row["status"],
        error_message=row["error_message"],
        created_at=row["created_at"],
        completed_at=row["completed_at"],
    )


@asynccontextmanager
async def transaction(db: aiosqlite.Connection):
    """Explicit transaction with rollback on failure."""
    await db.execute("BEGIN")
    try:
        yield db
        await db.commit()
    except Exception:
        await db.rollback()
        raise


# ── Run Queries ───────────────────────────────────────


async def create_run(db: aiosqlite.Connection, run: RunCreate) -> Run:
    """Insert a new run record and return the hydrated model."""
    run_id = str(uuid4())
    await db.execute(
        "INSERT INTO runs (id, persona_a_name, persona_b_name, "
        "shared_object_text, shared_object_type, turns_per_agent) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            run_id,
            run.persona_a_name,
            run.persona_b_name,
            run.shared_object_text,
            run.shared_object_type,
            run.turns_per_agent,
        ),
    )
    await db.commit()
    result = await get_run_by_id(db, UUID(run_id))
    if result is None:
        raise RuntimeError(f"Failed to retrieve run after insert: {run_id}")
    return result


async def get_run_by_id(db: aiosqlite.Connection, run_id: UUID) -> Run | None:
    """Fetch a single run by its ID."""
    cursor = await db.execute("SELECT * FROM runs WHERE id = ?", (str(run_id),))
    row = await cursor.fetchone()
    return _row_to_run(row) if row else None


async def get_runs(
    db: aiosqlite.Connection,
    status: str | None = None,
    limit: int = 20,
) -> list[Run]:
    """Fetch runs, optionally filtered by status."""
    if status:
        cursor = await db.execute(
            "SELECT * FROM runs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
            (status, limit),
        )
    else:
        cursor = await db.execute(
            "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
    rows = await cursor.fetchall()
    return [_row_to_run(row) for row in rows]


async def complete_run(
    db: aiosqlite.Connection,
    run_id: UUID,
    transcript: list[Turn],
) -> Run:
    """Mark a run as completed and store the transcript."""
    transcript_json = json.dumps([t.model_dump() for t in transcript])
    now = datetime.now().isoformat()
    await db.execute(
        "UPDATE runs SET status = 'completed', transcript_json = ?, "
        "completed_at = ? WHERE id = ?",
        (transcript_json, now, str(run_id)),
    )
    await db.commit()
    result = await get_run_by_id(db, run_id)
    if result is None:
        raise RuntimeError(f"Run not found after update: {run_id}")
    return result


async def fail_run(
    db: aiosqlite.Connection,
    run_id: UUID,
    error_message: str,
) -> Run:
    """Mark a run as failed with an error message."""
    now = datetime.now().isoformat()
    await db.execute(
        "UPDATE runs SET status = 'failed', error_message = ?, "
        "completed_at = ? WHERE id = ?",
        (error_message, now, str(run_id)),
    )
    await db.commit()
    result = await get_run_by_id(db, run_id)
    if result is None:
        raise RuntimeError(f"Run not found after update: {run_id}")
    return result


# ── Pairing History Queries ───────────────────────────


async def record_pairing(
    db: aiosqlite.Connection,
    persona_a_name: str,
    persona_b_name: str,
    run_id: UUID,
) -> None:
    """Record a persona pairing for history tracking.

    Stores names in sorted order so (A, B) and (B, A) are the same pairing.
    """
    sorted_names = sorted([persona_a_name, persona_b_name])
    await db.execute(
        "INSERT INTO pairing_history (id, persona_a_name, persona_b_name, run_id) "
        "VALUES (?, ?, ?, ?)",
        (str(uuid4()), sorted_names[0], sorted_names[1], str(run_id)),
    )
    await db.commit()


async def get_recent_pairings(
    db: aiosqlite.Connection,
    limit: int = 10,
) -> list[tuple[str, str]]:
    """Fetch the most recent persona pairings to avoid repeats."""
    cursor = await db.execute(
        "SELECT DISTINCT persona_a_name, persona_b_name "
        "FROM pairing_history ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    rows = await cursor.fetchall()
    return [(row["persona_a_name"], row["persona_b_name"]) for row in rows]
```

- **PATTERN**: Every public function returns a Pydantic model or a typed collection. UUIDs stored as TEXT in SQLite, converted at boundary. Transcripts stored as JSON text.
- **GOTCHA**: `aiosqlite.Row` must be set as `row_factory` on the connection (done in lifespan) for column-name access to work. `commit()` happens inside each query function.
- **VALIDATE**: `uv run python -c "from src.db.queries import Run, Turn; print('Query models loaded')"`

---

### Task 9: CREATE `src/personas/__init__.py`

- **IMPLEMENT**: Empty file.
- **VALIDATE**: `test -f src/personas/__init__.py && echo "exists"`

---

### Task 10: CREATE `src/personas/models.py`

Pydantic models for personas and shared objects.

- **IMPLEMENT**:

```python
"""
Data models for the persona library.

Defines the Persona and SharedObject structures used throughout
the system. This module belongs to the Persona layer and contains
no LLM-related logic or imports.
"""

from pydantic import BaseModel, Field


class Persona(BaseModel):
    """A fully specified persona for conversation agents.

    Each persona is defined across four dimensions: worldview,
    vocabulary style, core obsessions, and characteristic way
    of seeing. Generic job titles are not sufficient — depth
    across all dimensions is required.
    """

    name: str = Field(description="Unique identifier for this persona")
    title: str = Field(description="Short descriptive title")
    worldview: str = Field(
        description="How this persona understands reality and what they believe is fundamental",
    )
    vocabulary_style: str = Field(
        description="Characteristic language patterns, jargon, and rhetorical habits",
    )
    core_obsessions: str = Field(
        description="The problems and questions this persona cannot stop thinking about",
    )
    way_of_seeing: str = Field(
        description="How this persona perceives and interprets new information",
    )

    def to_system_prompt(self) -> str:
        """Generate a system prompt that embodies this persona.

        Returns a prompt that instructs the LLM to fully inhabit
        the persona across all four dimensions.
        """
        return (
            f"You are {self.title}.\n\n"
            f"WORLDVIEW: {self.worldview}\n\n"
            f"VOCABULARY & STYLE: {self.vocabulary_style}\n\n"
            f"CORE OBSESSIONS: {self.core_obsessions}\n\n"
            f"WAY OF SEEING: {self.way_of_seeing}\n\n"
            "Stay fully in character. Respond from this perspective in every turn. "
            "Use your characteristic vocabulary and reasoning patterns. "
            "Do not break character or acknowledge that you are an AI. "
            "Engage genuinely with what the other person says, but always "
            "through your own lens and obsessions."
        )


class SharedObject(BaseModel):
    """A shared object that two personas react to in conversation.

    The shared object is the seed for creative collision — something
    concrete enough to provoke specific reactions but open enough
    for radically different interpretations.
    """

    text: str = Field(description="The shared object description or prompt")
    object_type: str = Field(
        default="scenario",
        description="Type of shared object: scenario, question, problem, image_description",
    )
```

- **PATTERN**: Pure data models — no LLM imports allowed in `src/personas/` (CLAUDE.md boundary rule).
- **VALIDATE**: `uv run python -c "from src.personas.models import Persona, SharedObject; print('Persona models loaded')"`

---

### Task 11: CREATE `src/personas/library.py`

Persona definitions and selection logic. Starts with 4 deeply specified personas (enough for 6 unique pairings to validate Phase 1).

- **IMPLEMENT**:

```python
"""
Persona library and selection logic for the Yield Engine.

Contains the curated set of fully specified personas and the logic
for selecting pairs while avoiding recent repeats. This module
belongs to the Persona layer and contains no LLM calls.
"""

import logging
import random

from src.personas.models import Persona, SharedObject

logger = logging.getLogger(__name__)

# ── Starter Persona Library ──────────────────────────

PERSONAS: list[Persona] = [
    Persona(
        name="quantum_information_theorist",
        title="A quantum physicist who believes everything is fundamentally about information loss",
        worldview=(
            "Reality is a computation. Every physical process is information being "
            "transformed, copied, or irreversibly lost. The universe doesn't care about "
            "matter or energy — those are just substrates. What matters is the bits. "
            "The second law of thermodynamics is really about information becoming "
            "inaccessible, not energy dissipating. Black holes are interesting because "
            "they might destroy information, which would break everything we think we know."
        ),
        vocabulary_style=(
            "Speaks in terms of entropy, qubits, decoherence, and channel capacity. "
            "Uses 'observe' as a loaded technical term. Frequently frames problems as "
            "encoding/decoding challenges. Comfortable with mathematical metaphors but "
            "prefers thought experiments over equations in conversation. Says 'the interesting "
            "question is...' before reframing the topic entirely."
        ),
        core_obsessions=(
            "The black hole information paradox. Whether quantum mechanics is complete "
            "or hiding something. The relationship between observation and reality. "
            "Why the universe appears to have started in such a low-entropy state. "
            "The computational limits of physical systems."
        ),
        way_of_seeing=(
            "Looks at any system and immediately asks: what information is being preserved? "
            "What is being lost? Sees patterns as signals and noise as a fundamental "
            "feature, not a bug. Treats irreversibility as the most important property "
            "of any process. Instinctively suspicious of explanations that don't account "
            "for what happens to information."
        ),
    ),
    Persona(
        name="medieval_master_builder",
        title="A medieval master builder who thinks in stone, force, and the weight of centuries",
        worldview=(
            "The world is built by hands that understand materials. Every structure — "
            "physical, social, institutional — either bears its load or collapses. There "
            "are no abstractions that matter if the foundation is wrong. Beauty comes from "
            "structural honesty: a flying buttress is beautiful because it shows you exactly "
            "where the forces go. Deception in structure is sin."
        ),
        vocabulary_style=(
            "Speaks of loads, thrusts, keystones, and courses. Uses 'foundation' and "
            "'bearing' literally before metaphorically. Describes failures as 'collapse' "
            "and success as 'standing.' References apprenticeship, guilds, and the "
            "transmission of craft knowledge. Mistrusts anything that cannot be demonstrated "
            "with a physical model. Says 'show me where the weight goes' when skeptical."
        ),
        core_obsessions=(
            "How to make things that last centuries. The relationship between material "
            "constraints and aesthetic form. Why some structures stand and others fall. "
            "The ethics of building — if your wall collapses and kills someone, the "
            "geometry was a moral failure. The lost knowledge of ancient builders."
        ),
        way_of_seeing=(
            "Sees every system as a structure under load. Evaluates ideas by asking "
            "whether they can bear weight — literally and metaphorically. Notices "
            "points of failure before points of success. Respects craft and hates "
            "theory that has never been tested against material reality. Reads a "
            "situation by looking for what is holding everything else up."
        ),
    ),
    Persona(
        name="jazz_improviser",
        title="A jazz musician who hears the world as overlapping rhythmic and harmonic patterns",
        worldview=(
            "Everything has a rhythm and everything has a key. Most people only hear "
            "the melody — the surface pattern — but the real action is in the changes "
            "underneath. The best ideas come from playing wrong notes on purpose and "
            "then making them right by what you play next. Mistakes are just unresolved "
            "tensions, and tension is what makes music move forward."
        ),
        vocabulary_style=(
            "Speaks in terms of groove, changes, voicings, and tension-resolution. "
            "Uses 'swing' and 'feel' as technical terms. Describes ideas as 'riffs' "
            "and good collaboration as 'locking in.' Frequently uses call-and-response "
            "patterns in conversation. Says 'yeah, but listen...' before offering a "
            "reharmonization of someone else's idea."
        ),
        core_obsessions=(
            "How improvisation works — how you can create something coherent in real time "
            "without a plan. The relationship between structure and freedom (you need the "
            "chord changes to play over them). Why some combinations of people create "
            "magic and others don't. The feeling of being 'in the pocket' — synchronized "
            "without explicit coordination."
        ),
        way_of_seeing=(
            "Hears patterns in everything — conversations, systems, processes. Notices "
            "when something is 'in time' or 'dragging.' Evaluates ideas by their feel "
            "and momentum, not just their logic. Sees mistakes as opportunities for "
            "creative recovery. Instinctively looks for the underlying pattern that "
            "makes surface chaos coherent."
        ),
    ),
    Persona(
        name="deep_sea_ecologist",
        title="A deep-sea ecologist obsessed with organisms that thrive in extreme environments",
        worldview=(
            "Life doesn't need sunlight, oxygen, or comfortable temperatures. It needs "
            "energy gradients and chemistry. The deep ocean proves that our assumptions "
            "about what's necessary for life are parochial surface-dweller biases. "
            "The most successful organisms on Earth are the ones nobody has ever seen — "
            "thriving in crushing pressure, total darkness, and toxic chemistry. Adaptation "
            "is not about comfort; it's about exploiting whatever gradient exists."
        ),
        vocabulary_style=(
            "Speaks of chemosynthesis, extremophiles, pressure adaptation, and energy "
            "gradients. Uses 'niche' and 'gradient' as foundational concepts. Describes "
            "environments as 'regimes' and organisms as 'solving problems.' Frequently "
            "draws analogies between deep-sea ecosystems and other complex systems. "
            "Says 'but what's the energy source?' when analyzing any system."
        ),
        core_obsessions=(
            "How life survives where it shouldn't be able to. The chemosynthetic "
            "ecosystems at hydrothermal vents that run on chemical energy, not sunlight. "
            "Convergent evolution — why unrelated organisms in similar extreme environments "
            "evolve the same solutions independently. The vast unknown biodiversity of the "
            "deep ocean. What extremophiles tell us about possible life on other worlds."
        ),
        way_of_seeing=(
            "Sees every system as an ecosystem with energy flows, niches, and adaptation "
            "pressures. Evaluates robustness by asking what happens under extreme conditions. "
            "Notices symbiotic relationships and hidden dependencies that others miss. "
            "Suspicious of anything that only works under ideal conditions. Instinctively "
            "looks for the organisms (or ideas) that thrive where they shouldn't."
        ),
    ),
]

# ── Starter Shared Objects ───────────────────────────

SHARED_OBJECTS: list[SharedObject] = [
    SharedObject(
        text=(
            "A city discovers that the foundation beneath its oldest building has been "
            "slowly dissolving for centuries, and the building has been standing only because "
            "of an accidental equilibrium that nobody engineered."
        ),
        object_type="scenario",
    ),
    SharedObject(
        text=(
            "A signal is detected that repeats every 22 minutes with perfect regularity "
            "from a source 4,000 meters below the ocean surface. It has been repeating "
            "for at least 200 years based on geological evidence."
        ),
        object_type="scenario",
    ),
    SharedObject(
        text=(
            "An ancient library is discovered where every book is blank — but the "
            "arrangement of the books on the shelves, the spacing, and the size variations "
            "encode information that no one has been able to decode."
        ),
        object_type="scenario",
    ),
    SharedObject(
        text=(
            "What would it mean for a system to forget something on purpose, "
            "and why might deliberate forgetting be more valuable than perfect memory?"
        ),
        object_type="question",
    ),
    SharedObject(
        text=(
            "Design a building that teaches its inhabitants something new every decade, "
            "not through displays or signs, but through its structure alone."
        ),
        object_type="problem",
    ),
]


# ── Selection Logic ──────────────────────────────────


def get_all_personas() -> list[Persona]:
    """Return the full persona library."""
    return PERSONAS.copy()


def get_all_shared_objects() -> list[SharedObject]:
    """Return the full shared object pool."""
    return SHARED_OBJECTS.copy()


def get_persona_by_name(name: str) -> Persona | None:
    """Look up a persona by its unique name."""
    for persona in PERSONAS:
        if persona.name == name:
            return persona
    return None


def get_persona_pair(
    recent_pairings: list[tuple[str, str]] | None = None,
) -> tuple[Persona, Persona]:
    """Select two personas for a conversation run.

    Avoids repeating any pairing that appears in recent_pairings.
    If all pairings have been used recently, logs a warning and
    picks the least-recently-used pairing.

    Args:
        recent_pairings: List of (name_a, name_b) tuples from recent runs,
            with names in sorted order.

    Returns:
        Tuple of two distinct Persona objects.
    """
    if recent_pairings is None:
        recent_pairings = []

    recent_set = {tuple(sorted(p)) for p in recent_pairings}

    # Build all possible pairings
    all_pairs: list[tuple[Persona, Persona]] = []
    for i, a in enumerate(PERSONAS):
        for b in PERSONAS[i + 1 :]:
            all_pairs.append((a, b))

    # Filter out recently used pairings
    available = [
        (a, b)
        for a, b in all_pairs
        if tuple(sorted([a.name, b.name])) not in recent_set
    ]

    if not available:
        logger.warning(
            "All persona pairings used recently, selecting from full library"
        )
        available = all_pairs

    pair = random.choice(available)

    # Randomize which persona goes first
    if random.random() < 0.5:
        pair = (pair[1], pair[0])

    logger.info(
        "Selected persona pair",
        extra={"persona_a": pair[0].name, "persona_b": pair[1].name},
    )
    return pair


def get_random_shared_object() -> SharedObject:
    """Select a random shared object from the pool."""
    return random.choice(SHARED_OBJECTS)
```

- **PATTERN**: Pure data and selection logic — no LLM imports (CLAUDE.md boundary rule). Names stored in sorted order for pairing history comparison.
- **GOTCHA**: `random.choice` is fine for MVP selection. Ensure `get_persona_pair` handles the edge case where all pairings are recently used.
- **VALIDATE**: `uv run python -c "from src.personas.library import get_persona_pair; a, b = get_persona_pair(); print(f'{a.name} vs {b.name}')"`

---

### Task 12: CREATE `src/engine/__init__.py`

- **IMPLEMENT**: Empty file.
- **VALIDATE**: `test -f src/engine/__init__.py && echo "exists"`

---

### Task 13: CREATE `src/engine/models.py`

Engine-layer Pydantic models.

- **IMPLEMENT**:

```python
"""
Data models for the conversation engine.

Defines the structures used by the ConversationRunner to manage
turn-taking and produce transcripts. This module belongs to the
Engine layer.
"""

from pydantic import BaseModel, Field

from src.personas.models import Persona, SharedObject


class ConversationConfig(BaseModel):
    """Configuration for a single conversation run.

    Controls turn count and inference parameters. Defaults come
    from application settings but can be overridden per-run.
    """

    turns_per_agent: int = Field(default=5, description="Number of turns per agent")
    temperature: float = Field(default=0.9, description="Sampling temperature")
    repetition_penalty: float = Field(
        default=1.15, description="vLLM repetition penalty"
    )
    max_tokens: int = Field(default=512, description="Max tokens per turn")


class ConversationRequest(BaseModel):
    """Complete specification for a conversation run.

    Bundles the two personas, shared object, and generation config
    into a single request object.
    """

    persona_a: Persona
    persona_b: Persona
    shared_object: SharedObject
    config: ConversationConfig = Field(default_factory=ConversationConfig)
```

- **PATTERN**: Uses `Turn` from `src/db/queries.py` for transcript entries (single definition, no duplication). Engine models handle config and request; the data models live in the data layer.
- **GOTCHA**: `ConversationConfig` defaults should match `settings` values. The CLI runner should construct this from settings; the model just defines the shape.
- **VALIDATE**: `uv run python -c "from src.engine.models import ConversationRequest; print('Engine models loaded')"`

---

### Task 14: CREATE `src/engine/conversation.py`

The core conversation runner — the heart of Phase 1.

- **IMPLEMENT**:

```python
"""
Conversation runner for the Yield Engine.

Manages turn-taking between two persona agents given a shared object,
producing a full conversation transcript. This module belongs to the
Engine layer and communicates with the local vLLM inference server
via an OpenAI-compatible API.
"""

import logging

import httpx
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
)

from src.config import settings
from src.db.queries import Turn
from src.engine.models import ConversationConfig, ConversationRequest
from src.personas.models import Persona, SharedObject

logger = logging.getLogger(__name__)


class ConversationError(Exception):
    """Raised when the conversation runner encounters a non-recoverable error."""


class InferenceError(ConversationError):
    """Raised when the local vLLM server fails to respond."""


class ConversationRunner:
    """Orchestrates a multi-turn conversation between two persona agents.

    Takes two fully specified personas and a shared object, manages
    turn-taking for a configurable number of exchanges, and returns
    the complete transcript. Communicates with the local inference
    server via the OpenAI-compatible client.
    """

    def __init__(self) -> None:
        """Initialize the conversation runner with a vLLM client."""
        # vLLM serves an OpenAI-compatible API, so we use the standard client
        # with a base_url override
        self._client = AsyncOpenAI(
            base_url=settings.vllm_base_url,
            api_key="unused",
            timeout=httpx.Timeout(120.0, connect=5.0),
            max_retries=2,
        )

    async def run(self, request: ConversationRequest) -> list[Turn]:
        """Run a full conversation between two personas on a shared object.

        Alternates turns between persona_a and persona_b, building up
        a shared message history. Each agent sees the full conversation
        so far from their own perspective.

        Args:
            request: Complete conversation specification including
                personas, shared object, and generation config.

        Returns:
            Ordered list of conversation turns.

        Raises:
            ConversationError: If the conversation cannot be completed.
            InferenceError: If the vLLM server fails to respond.
        """
        persona_a = request.persona_a
        persona_b = request.persona_b
        shared_object = request.shared_object
        config = request.config

        logger.info(
            "Starting conversation",
            extra={
                "persona_a": persona_a.name,
                "persona_b": persona_b.name,
                "shared_object_type": shared_object.object_type,
                "turns_per_agent": config.turns_per_agent,
            },
        )

        turns: list[Turn] = []
        total_turns = config.turns_per_agent * 2

        for turn_number in range(1, total_turns + 1):
            # Alternate between personas: odd turns = A, even turns = B
            is_persona_a = turn_number % 2 == 1
            active_persona = persona_a if is_persona_a else persona_b
            other_persona = persona_b if is_persona_a else persona_a

            try:
                content = await self._generate_turn(
                    active_persona=active_persona,
                    other_persona=other_persona,
                    shared_object=shared_object,
                    turns=turns,
                    turn_number=turn_number,
                    config=config,
                )
            except InferenceError:
                logger.error(
                    "Aborting conversation due to inference failure",
                    extra={
                        "turn_number": turn_number,
                        "persona": active_persona.name,
                    },
                )
                raise

            turn = Turn(
                turn_number=turn_number,
                persona_name=active_persona.name,
                content=content,
            )
            turns.append(turn)

            logger.debug(
                "Turn completed",
                extra={
                    "turn_number": turn_number,
                    "persona": active_persona.name,
                    "content_length": len(content),
                },
            )

        logger.info(
            "Conversation completed",
            extra={
                "persona_a": persona_a.name,
                "persona_b": persona_b.name,
                "total_turns": len(turns),
            },
        )

        return turns

    async def _generate_turn(
        self,
        active_persona: Persona,
        other_persona: Persona,
        shared_object: SharedObject,
        turns: list[Turn],
        turn_number: int,
        config: ConversationConfig,
    ) -> str:
        """Generate a single conversation turn from the vLLM server.

        Builds the message history from the active persona's perspective
        and calls the local inference server.

        Args:
            active_persona: The persona generating this turn.
            other_persona: The other persona in the conversation.
            shared_object: The shared object being discussed.
            turns: All previous turns in the conversation.
            turn_number: Current turn number (1-indexed).
            config: Generation parameters.

        Returns:
            The generated text content for this turn.

        Raises:
            InferenceError: If the vLLM server fails to respond.
        """
        messages = self._build_messages(
            active_persona=active_persona,
            other_persona=other_persona,
            shared_object=shared_object,
            turns=turns,
            turn_number=turn_number,
        )

        try:
            response = await self._client.chat.completions.create(
                model=settings.conversation_model,
                messages=messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                extra_body={"repetition_penalty": config.repetition_penalty},
            )
        except APIConnectionError as e:
            raise InferenceError(
                f"Cannot reach vLLM server at {settings.vllm_base_url}: {e}"
            ) from e
        except APITimeoutError as e:
            raise InferenceError(
                f"vLLM request timed out on turn {turn_number}: {e}"
            ) from e
        except APIStatusError as e:
            raise InferenceError(
                f"vLLM returned status {e.status_code} on turn {turn_number}: "
                f"{e.message}"
            ) from e

        content = response.choices[0].message.content
        if not content:
            raise InferenceError(
                f"vLLM returned empty content on turn {turn_number}"
            )

        return content.strip()

    def _build_messages(
        self,
        active_persona: Persona,
        other_persona: Persona,
        shared_object: SharedObject,
        turns: list[Turn],
        turn_number: int,
    ) -> list[dict[str, str]]:
        """Build the chat messages array for a turn.

        Constructs the message history from the active persona's
        perspective: their system prompt, the shared object as the
        opening user message, then alternating assistant/user roles
        for previous turns.

        Args:
            active_persona: The persona generating this turn.
            other_persona: The other persona in the conversation.
            shared_object: The shared object being discussed.
            turns: All previous turns in the conversation.
            turn_number: Current turn number.

        Returns:
            List of message dicts ready for the OpenAI chat API.
        """
        messages: list[dict[str, str]] = [
            {"role": "system", "content": active_persona.to_system_prompt()},
        ]

        # Opening context: present the shared object and conversation framing
        opening = (
            f"You are in a conversation with someone very different from you — "
            f"{other_persona.title}. You have both been presented with the following "
            f"and asked to react to it from your own perspective:\n\n"
            f"---\n{shared_object.text}\n---\n\n"
        )

        if turn_number == 1:
            # First turn: persona A reacts to the shared object
            opening += (
                "Give your initial reaction to this. What does it make you think of? "
                "What questions does it raise? Respond naturally as yourself."
            )
            messages.append({"role": "user", "content": opening})
        else:
            messages.append({"role": "user", "content": opening})

            # Replay conversation history with correct role mapping
            for turn in turns:
                if turn.persona_name == active_persona.name:
                    role = "assistant"
                else:
                    role = "user"
                messages.append({"role": role, "content": turn.content})

        return messages
```

- **PATTERN**: Engine only imports `AsyncOpenAI` — no Anthropic SDK (CLAUDE.md boundary rule). Custom exceptions `ConversationError` and `InferenceError` defined in this module. Uses `extra_body` for vLLM-specific `repetition_penalty`.
- **GOTCHA**: The `repetition_penalty` parameter is vLLM-specific and must go through `extra_body`, not as a top-level kwarg. Do NOT combine with `frequency_penalty`/`presence_penalty`. The `httpx.Timeout` import is needed for the client timeout configuration.
- **VALIDATE**: `uv run python -c "from src.engine.conversation import ConversationRunner; print('ConversationRunner loaded')"`

---

### Task 15: CREATE `src/api/__init__.py`

- **IMPLEMENT**: Empty file.
- **VALIDATE**: `test -f src/api/__init__.py && echo "exists"`

---

### Task 16: CREATE `src/api/routes.py`

Placeholder API routes for Phase 1. The full API comes in Phase 5, but we establish the router pattern now.

- **IMPLEMENT**:

```python
"""
API routes for the Yield Engine.

Provides REST endpoints for managing conversation runs and
reviewing results. This module belongs to the API layer.
Full implementation comes in Phase 5 — Phase 1 provides
a minimal set of endpoints for run management.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Request

from src.db import queries

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["runs"])


@router.get("/runs")
async def list_runs(
    request: Request,
    status: str | None = None,
    limit: int = 20,
) -> list[queries.Run]:
    """List conversation runs, optionally filtered by status."""
    db = request.app.state.db
    return await queries.get_runs(db, status=status, limit=limit)


@router.get("/runs/{run_id}")
async def get_run(request: Request, run_id: UUID) -> queries.Run | None:
    """Fetch a single conversation run by ID."""
    db = request.app.state.db
    return await queries.get_run_by_id(db, run_id)
```

- **PATTERN**: Accesses database via `request.app.state.db` (dependency injection via FastAPI). Returns Pydantic models directly — FastAPI handles serialization.
- **VALIDATE**: `uv run python -c "from src.api.routes import router; print(f'Router loaded: {len(router.routes)} routes')"`

---

### Task 17: CREATE `src/main.py`

FastAPI application entry point with lifespan-managed database connection.

- **IMPLEMENT**:

```python
"""
Application entry point for the Yield Engine.

Configures the FastAPI application with lifespan-managed resources
including the SQLite database connection. This module belongs to
the API layer.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import aiosqlite
from fastapi import FastAPI, Request

from src.api.routes import router
from src.config import settings
from src.db.schema import init_schema

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application-scoped resources.

    Creates the SQLite database connection on startup and ensures
    the schema is initialized. Closes the connection on shutdown.
    """
    # Ensure the data directory exists
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Connecting to database", extra={"path": settings.database_path})
    app.state.db = await aiosqlite.connect(settings.database_path)
    app.state.db.row_factory = aiosqlite.Row

    # Enable WAL mode for better concurrent read performance
    await app.state.db.execute("PRAGMA journal_mode=WAL")
    # SQLite does not enforce foreign keys by default
    await app.state.db.execute("PRAGMA foreign_keys=ON")

    await init_schema(app.state.db)
    logger.info("Application startup complete")

    yield

    await app.state.db.close()
    logger.info("Database connection closed")


app = FastAPI(
    title="Yield Engine",
    description="Multi-agent creative collision system",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health")
async def health(request: Request) -> dict[str, str]:
    """Return service health status with database connectivity check."""
    async with request.app.state.db.execute("SELECT 1") as cursor:
        await cursor.fetchone()
    return {"status": "ok"}
```

- **PATTERN**: Lifespan manages DB lifecycle. `row_factory = aiosqlite.Row` set on connection for column-name access. WAL mode and foreign keys enabled per-connection.
- **GOTCHA**: `PRAGMA foreign_keys=ON` must be set per-connection — it does not persist in the database file. The data directory must be created before connecting.
- **VALIDATE**: `uv run python -c "from src.main import app; print(f'App loaded: {app.title} v{app.version}')"`

---

### Task 18: CREATE `data/.gitkeep`

- **IMPLEMENT**: Empty file to ensure the data directory is tracked by git (database files are gitignored).
- **VALIDATE**: `test -f data/.gitkeep && echo "exists"`

---

### Task 19: CREATE `scripts/run_conversation.py`

CLI entry point for running conversations (Phases 1-4 use CLI, Phase 5 adds UI).

- **IMPLEMENT**:

```python
"""
CLI runner for the Yield Engine.

Runs a single conversation between two persona agents with a shared
object, stores the transcript in the database, and prints results.
This is the primary interface for Phases 1-4.

Usage:
    uv run python scripts/run_conversation.py
    uv run python scripts/run_conversation.py --turns 3
    uv run python scripts/run_conversation.py --persona-a quantum_information_theorist --persona-b medieval_master_builder
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import aiosqlite

from src.config import settings
from src.db.queries import Turn, complete_run, create_run, fail_run, record_pairing, RunCreate
from src.db.schema import init_schema
from src.engine.conversation import ConversationError, ConversationRunner
from src.engine.models import ConversationConfig, ConversationRequest
from src.personas.library import (
    get_all_personas,
    get_persona_by_name,
    get_persona_pair,
    get_random_shared_object,
    get_all_shared_objects,
)
from src.personas.models import SharedObject

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the conversation runner."""
    parser = argparse.ArgumentParser(
        description="Run a Yield Engine conversation between two persona agents.",
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=settings.default_turns,
        help=f"Number of turns per agent (default: {settings.default_turns})",
    )
    parser.add_argument(
        "--persona-a",
        type=str,
        default=None,
        help="Name of the first persona (default: random selection)",
    )
    parser.add_argument(
        "--persona-b",
        type=str,
        default=None,
        help="Name of the second persona (default: random selection)",
    )
    parser.add_argument(
        "--shared-object",
        type=int,
        default=None,
        help="Index of the shared object to use (default: random)",
    )
    parser.add_argument(
        "--list-personas",
        action="store_true",
        help="List all available personas and exit",
    )
    parser.add_argument(
        "--list-objects",
        action="store_true",
        help="List all available shared objects and exit",
    )
    return parser.parse_args()


async def run(args: argparse.Namespace) -> None:
    """Execute a conversation run with the given arguments."""
    # Handle list commands
    if args.list_personas:
        for persona in get_all_personas():
            print(f"  {persona.name}: {persona.title}")
        return

    if args.list_objects:
        for i, obj in enumerate(get_all_shared_objects()):
            print(f"  [{i}] ({obj.object_type}) {obj.text[:80]}...")
        return

    # Connect to database
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(settings.database_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    await init_schema(db)

    try:
        # Select personas
        if args.persona_a and args.persona_b:
            persona_a = get_persona_by_name(args.persona_a)
            persona_b = get_persona_by_name(args.persona_b)
            if not persona_a:
                logger.error(f"Persona not found: {args.persona_a}")
                sys.exit(1)
            if not persona_b:
                logger.error(f"Persona not found: {args.persona_b}")
                sys.exit(1)
        else:
            persona_a, persona_b = get_persona_pair()

        # Select shared object
        if args.shared_object is not None:
            objects = get_all_shared_objects()
            if args.shared_object < 0 or args.shared_object >= len(objects):
                logger.error(
                    f"Shared object index out of range: {args.shared_object} "
                    f"(0-{len(objects) - 1})"
                )
                sys.exit(1)
            shared_object = objects[args.shared_object]
        else:
            shared_object = get_random_shared_object()

        # Create run record
        run_record = await create_run(
            db,
            RunCreate(
                persona_a_name=persona_a.name,
                persona_b_name=persona_b.name,
                shared_object_text=shared_object.text,
                shared_object_type=shared_object.object_type,
                turns_per_agent=args.turns,
            ),
        )

        print(f"\n{'='*60}")
        print(f"YIELD ENGINE — Conversation Run")
        print(f"{'='*60}")
        print(f"Run ID:         {run_record.id}")
        print(f"Persona A:      {persona_a.title}")
        print(f"Persona B:      {persona_b.title}")
        print(f"Shared Object:  {shared_object.text[:80]}...")
        print(f"Turns/Agent:    {args.turns}")
        print(f"{'='*60}\n")

        # Run conversation
        config = ConversationConfig(
            turns_per_agent=args.turns,
            temperature=settings.conversation_temperature,
            repetition_penalty=settings.conversation_repetition_penalty,
            max_tokens=settings.conversation_max_tokens,
        )
        request = ConversationRequest(
            persona_a=persona_a,
            persona_b=persona_b,
            shared_object=shared_object,
            config=config,
        )

        runner = ConversationRunner()
        turns = await runner.run(request)

        # Save transcript
        await complete_run(db, run_record.id, turns)
        await record_pairing(db, persona_a.name, persona_b.name, run_record.id)

        # Print transcript
        print(f"\n{'─'*60}")
        print("TRANSCRIPT")
        print(f"{'─'*60}\n")
        for turn in turns:
            persona_label = (
                persona_a.title if turn.persona_name == persona_a.name
                else persona_b.title
            )
            print(f"[Turn {turn.turn_number}] {persona_label}:")
            print(f"{turn.content}\n")

        print(f"{'='*60}")
        print(f"Conversation completed. Run ID: {run_record.id}")
        print(f"{'='*60}")

    except ConversationError as e:
        logger.error(f"Conversation failed: {e}")
        await fail_run(db, run_record.id, str(e))
        sys.exit(1)
    finally:
        await db.close()


def main() -> None:
    """Entry point for the CLI runner."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    args = parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
```

- **PATTERN**: CLI for Phases 1-4 per DevPlan decision. Manages its own database connection (not through FastAPI). Supports both random selection and explicit persona/object specification.
- **GOTCHA**: The `run_record` variable must be created before the try/except so `fail_run` can reference it. Use `asyncio.run()` as the entry point — not `uvloop` or manual event loop management.
- **VALIDATE**: `uv run python scripts/run_conversation.py --list-personas`

---

### Task 20: CREATE `tests/__init__.py`

- **IMPLEMENT**: Empty file.
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

- **PATTERN**: In-memory SQLite for isolation. Mock factory for vLLM responses. No real LLM calls in tests (CLAUDE.md rule).
- **GOTCHA**: Use `ASGITransport` (not deprecated `app=` kwarg) with `httpx.AsyncClient` for FastAPI testing.
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
    """Verify the library contains at least 4 personas for Phase 1."""
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

- **PATTERN**: All vLLM calls mocked via `patch.object`. Tests verify behavior (turn count, alternation, error handling), not implementation.
- **VALIDATE**: `uv run pytest tests/test_engine.py -v`

---

### Task 26: CREATE `tests/test_boundaries.py`

Architectural boundary verification tests per CLAUDE.md.

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

- **PATTERN**: Uses `ast` module to inspect imports without executing the code. Tests verify the boundary rules from CLAUDE.md's architectural constraints.
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
uv run ruff check .
uv run ruff format --check .
uv run pytest -v
```

---

## TESTING STRATEGY

### Unit Tests

- **test_config.py**: Settings load with correct defaults and types
- **test_db.py**: CRUD operations on runs, transcript storage/retrieval, pairing history
- **test_personas.py**: Persona completeness, uniqueness, selection logic, recent-pairing avoidance
- **test_engine.py**: Turn count, persona alternation, message history growth, error handling (all vLLM mocked)
- **test_api.py**: Health endpoint, run listing

### Integration Tests

- **test_api.py**: Full request cycle through FastAPI with in-memory database

### Edge Cases

- All persona pairings used recently (fallback to full library)
- vLLM returns empty content
- vLLM connection refused
- vLLM request timeout
- Missing persona name lookup returns None
- Run not found by ID returns None
- Database schema idempotent (init_schema can run multiple times)

### Boundary Verification

- **test_boundaries.py**: Engine has no anthropic imports, personas have no LLM imports, db has no LLM imports

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
# Lint (must pass with 0 errors)
uv run ruff check .

# Format check
uv run ruff format --check .
```

**Expected**: All commands pass with exit code 0

### Level 2: Unit Tests

```bash
# Run all tests with verbose output
uv run pytest -v

# Run with coverage (optional)
uv run pytest -v --tb=short
```

**Expected**: All tests pass

### Level 3: Integration Tests

```bash
# Run API tests specifically
uv run pytest tests/test_api.py -v
```

**Expected**: Health endpoint and run listing work with in-memory database

### Level 4: Manual Validation

```bash
# Verify CLI help
uv run python scripts/run_conversation.py --help

# List available personas
uv run python scripts/run_conversation.py --list-personas

# List available shared objects
uv run python scripts/run_conversation.py --list-objects

# Import validation
uv run python -c "from src.config import settings; print(settings.model_dump())"

# Start the API server (requires Ctrl+C to stop)
uv run uvicorn src.main:app --reload --port 8080
# Then in another terminal: curl http://localhost:8080/health
```

**Expected**: CLI outputs persona list and shared object list. Settings load. Server starts.

### Level 5: Full Conversation (requires vLLM running)

```bash
# Run a conversation (only works with vLLM server running)
uv run python scripts/run_conversation.py --turns 2
```

**Expected**: Transcript printed to console and stored in SQLite

---

## ACCEPTANCE CRITERIA

- [x] Project scaffolded with uv, pyproject.toml, and all dependencies
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
- [ ] No `print()` in application code — logging only
- [ ] All functions have type hints and docstrings

---

## COMPLETION CHECKLIST

- [ ] All 28 tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully:
  - [ ] Level 1: `uv run ruff check .`, `uv run ruff format --check .`
  - [ ] Level 2: `uv run pytest -v`
  - [ ] Level 3: `uv run pytest tests/test_api.py -v`
  - [ ] Level 4: CLI help, list personas, list objects, import check
- [ ] Full test suite passes (all test files)
- [ ] No linting errors
- [ ] No formatting errors
- [ ] All acceptance criteria met
- [ ] Code reviewed for quality and maintainability

---

## NOTES

### Design Decisions

1. **Transcript stored as JSON text in SQLite**: Rather than normalizing turns into a separate table, transcripts are stored as serialized JSON in the `runs` table. This simplifies queries (a run and its transcript are always fetched together) and avoids complex joins. The trade-off is that you can't query individual turns via SQL — but there's no use case for that in the current design.

2. **UUIDs as TEXT in SQLite**: SQLite has no native UUID type. Storing as TEXT and converting at the query layer boundary is the standard pattern. This also makes the database human-readable when inspected directly.

3. **Single database connection**: SQLite serializes writes regardless of how many connections exist. A single connection with WAL mode (for concurrent reads) is sufficient for the Yield Engine's expected load (batch-driven, not high-concurrency).

4. **`pydantic-settings` for configuration**: Using `BaseSettings` from pydantic-settings provides automatic env var loading, validation, and type coercion — eliminating manual `os.getenv` calls with type conversion.

5. **4 starter personas**: The DevPlan specifies 12 for MVP and 20-25 ideal. Phase 1 starts with 4 (6 unique pairings) to validate the system. Phase 2 expands to the full library. The 4 chosen span maximally different epistemologies: physics, craftsmanship, music, biology.

6. **Persona system prompt structure**: The `to_system_prompt()` method on the Persona model generates the system prompt. This keeps prompt engineering in the persona layer (where it belongs) rather than in the engine layer. The engine just calls the method and passes the result to the LLM.

### Key Risks

- **Chat template mismatch**: MythoMax-L2-13B uses Llama 2's chat template. If vLLM doesn't apply it correctly, the conversation will be garbled. Mitigation: verify with `--chat-template` flag on vLLM server.
- **Context window overflow**: With 10 turns of 512 tokens each plus system prompts, the total context can reach ~6K tokens. MythoMax-L2-13B has a 4K context window by default (expandable via RoPE scaling). Mitigation: monitor for 400 errors from vLLM and consider reducing `max_tokens` or `turns_per_agent`.
- **Persona bleed**: The model may not maintain persona voice consistently across 10 turns. Mitigation: strong system prompts with explicit "stay in character" instructions, plus repetition penalty to reduce generic responses.

### Future Phase Hooks

- Phase 2 expands `src/personas/library.py` to 12+ personas
- Phase 3 adds `src/synthesis/` (Anthropic API only — boundary verified by tests)
- Phase 4 adds `src/scoring/` (Anthropic API only — boundary verified by tests)
- Phase 5 adds full `src/api/` routes and review UI
- The `ConversationRunner` is designed to be called by both CLI (Phases 1-4) and API (Phase 5+)
