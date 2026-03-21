# PBI 5: API, CLI & Integration

**Feature**: 1 — Core Conversation Engine
**Tasks**: 15–19 of 28
**Dependencies**: PBI 1 (config), PBI 2 (database), PBI 3 (personas), PBI 4 (engine)
**Estimated Complexity**: Medium

---

## Objective

Wire everything together: FastAPI app with lifespan-managed database, API routes for run listing, CLI script for running conversations, and the `data/` directory. This PBI makes the system actually runnable.

## User Story

As a creative researcher
I want to run conversations from the command line and query results via API
So that I can operate the Yield Engine for Features 1-4 without a web UI

## Preconditions

- PBIs 1–4 complete (config, database, personas, engine all working)

## Context References — READ BEFORE IMPLEMENTING

- `CLAUDE.md` — Dependency injection via `request.app.state.db`, not global variables
- `CLAUDE.md` — FastAPI lifespan for database connection management
- `CLAUDE.md` — No `print()` for operational output — use `logging`
- `.agents/DevPlan.md` (lines 158-160) — CLI for Features 1-4, UI in Feature 5

### Patterns to Follow

**Lifespan**: Database connection created on startup, closed on shutdown. WAL mode and foreign keys enabled per-connection.

**API routes**: Access database via `request.app.state.db`. Return Pydantic models directly — FastAPI handles serialization.

**CLI**: Uses `asyncio.run()` as entry point. Manages its own database connection (not through FastAPI). Supports both random selection and explicit persona/object specification.

---

## TASKS

### Task 15: CREATE `src/api/__init__.py`

- **IMPLEMENT**: Empty file (package marker).
- **VALIDATE**: `test -f src/api/__init__.py && echo "exists"`

---

### Task 16: CREATE `src/api/routes.py`

Minimal API routes for Feature 1. Full API comes in Feature 5.

- **IMPLEMENT**:

```python
"""
API routes for the Yield Engine.

Provides REST endpoints for managing conversation runs and
reviewing results. This module belongs to the API layer.
Full implementation comes in Feature 5 — Feature 1 provides
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

- **PATTERN**: Database via `request.app.state.db`. Pydantic models returned directly.
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

- **GOTCHA**: `PRAGMA foreign_keys=ON` must be set per-connection — it does not persist. The data directory must be created before connecting (`mkdir parents=True`).
- **VALIDATE**: `uv run python -c "from src.main import app; print(f'App loaded: {app.title} v{app.version}')"`

---

### Task 18: CREATE `data/.gitkeep`

- **IMPLEMENT**: Empty file so git tracks the data directory (database files are gitignored).
- **VALIDATE**: `test -f data/.gitkeep && echo "exists"`

---

### Task 19: CREATE `scripts/run_conversation.py`

CLI entry point for running conversations (Features 1-4).

- **IMPLEMENT**:

```python
"""
CLI runner for the Yield Engine.

Runs a single conversation between two persona agents with a shared
object, stores the transcript in the database, and prints results.
This is the primary interface for Features 1-4.

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
from src.db.queries import (
    RunCreate,
    Turn,
    complete_run,
    create_run,
    fail_run,
    record_pairing,
)
from src.db.schema import init_schema
from src.engine.conversation import ConversationError, ConversationRunner
from src.engine.models import ConversationConfig, ConversationRequest
from src.personas.library import (
    get_all_personas,
    get_all_shared_objects,
    get_persona_by_name,
    get_persona_pair,
    get_random_shared_object,
)

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
                persona_a.title
                if turn.persona_name == persona_a.name
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

- **PATTERN**: CLI for Features 1-4 per DevPlan. Manages its own DB connection. Supports listing, random selection, and explicit specification.
- **GOTCHA**: `run_record` must be created before the try/except so `fail_run` can reference it. Note: `print()` is used here intentionally for CLI user output — this is a script, not operational application code.
- **VALIDATE**: `uv run python scripts/run_conversation.py --list-personas`

---

## FILES CREATED

| File | Purpose |
|------|---------|
| `src/api/__init__.py` | Package marker |
| `src/api/routes.py` | GET /api/runs, GET /api/runs/{id} |
| `src/main.py` | FastAPI app with lifespan, health endpoint |
| `data/.gitkeep` | Directory placeholder (DB files gitignored) |
| `scripts/run_conversation.py` | CLI entry point |

## VALIDATION COMMANDS

```bash
# App loads
uv run python -c "from src.main import app; print(f'{app.title} v{app.version}')"

# CLI help works
uv run python scripts/run_conversation.py --help

# CLI list commands work
uv run python scripts/run_conversation.py --list-personas
uv run python scripts/run_conversation.py --list-objects

# Lint
uv run ruff check src/api/ src/main.py scripts/
uv run ruff format --check src/api/ src/main.py scripts/

# Start server (Ctrl+C to stop) — manual verification
# uv run uvicorn src.main:app --reload --port 8080
# curl http://localhost:8080/health
# curl http://localhost:8080/api/runs
```

## DONE WHEN

- [ ] FastAPI app starts with lifespan-managed database
- [ ] `/health` endpoint returns `{"status": "ok"}` with DB check
- [ ] `/api/runs` returns run list (empty initially)
- [ ] `/api/runs/{id}` returns a single run
- [ ] CLI `--help` displays usage
- [ ] CLI `--list-personas` prints all persona names and titles
- [ ] CLI `--list-objects` prints all shared objects with types
- [ ] CLI runs a conversation when vLLM is available (full integration)
- [ ] Transcripts saved to SQLite after successful conversation
- [ ] Failed conversations stored with error message
- [ ] Ruff passes on all new files
