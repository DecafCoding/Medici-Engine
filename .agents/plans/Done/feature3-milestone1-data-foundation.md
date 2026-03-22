# Feature 3 — Milestone 1: Data Foundation

**Parent feature**: [feature3-synthesizer-agent.md](feature3-synthesizer-agent.md)
**Tasks**: 1–3
**Goal**: Create synthesis models, extend database schema, add concept queries

---

## CONTEXT REFERENCES

### Relevant Codebase Files — MUST READ BEFORE IMPLEMENTING

- `src/engine/models.py` — Why: Shows Pydantic model pattern for engine data structures. Mirror this for synthesis models.
- `src/db/queries.py` (lines 1-101) — Why: Shows the complete pattern for typed queries — `_row_to_model()` helper, `transaction()` context manager, model definitions (`Turn`, `Run`, `RunCreate`). New concept queries must follow this exact pattern.
- `src/db/schema.py` (lines 15-44) — Why: Shows how schema DDL is defined. New `concepts` table DDL must be appended to `SCHEMA_SQL`.
- `CLAUDE.md` (Architectural Boundaries table) — Why: Synthesis module communicates with OpenAI API only — no vLLM calls. Must not import from engine layer.

### New Files to Create

- `src/synthesis/__init__.py` — Package init for synthesis module
- `src/synthesis/models.py` — Pydantic models for structured concept output

### Files to Modify

- `src/db/schema.py` — Add `concepts` table DDL
- `src/db/queries.py` — Add `Concept` model and concept CRUD queries

### Patterns to Follow

**Query Layer Pattern (from `src/db/queries.py:71-89`):**
```python
def _row_to_concept(row: aiosqlite.Row) -> Concept:
    """Map a database row to a Concept model."""
    return Concept(
        id=UUID(row["id"]),
        run_id=UUID(row["run_id"]),
        # ... remaining fields
    )
```

---

## IMPLEMENTATION PLAN

### Task 1: Create synthesis Pydantic models

Define the structured output models that the OpenAI API will return and that the database will store.

- **CREATE**: `src/synthesis/__init__.py` — empty package init file
- **CREATE**: `src/synthesis/models.py` — synthesis-specific Pydantic models:
  - `ConceptExtraction` — a single extracted concept with `title: str`, `premise: str`, `originality: str` (what makes it original). This is the model passed to `response_format`.
  - Note: The database `Concept` model lives in `src/db/queries.py` (follows existing pattern where `Run`, `Turn` are defined there). `ConceptExtraction` is the API response shape; it gets mapped to the DB `Concept` after storage.
- **PATTERN**: Mirror `src/engine/models.py` — file-level docstring, Pydantic BaseModel with Field() descriptions, class docstrings
- **IMPORTS**: `from pydantic import BaseModel, Field`
- **GOTCHA**: All fields must be required (not Optional) for OpenAI structured output strict mode. The API guarantees all fields are populated.
- **GOTCHA**: Do NOT import `openai` in models.py — models are pure data structures
- **VALIDATE**: `uv run python -c "from src.synthesis.models import ConceptExtraction; print(ConceptExtraction.model_json_schema())"`

### Task 2: Add concepts table to database schema

Extend the SQLite schema to store synthesized concepts linked to their source runs.

- **UPDATE**: `src/db/schema.py` — append to `SCHEMA_SQL` string:
  ```sql
  CREATE TABLE IF NOT EXISTS concepts (
      id TEXT PRIMARY KEY,
      run_id TEXT NOT NULL,
      title TEXT NOT NULL,
      premise TEXT NOT NULL,
      originality TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'pending',
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      FOREIGN KEY (run_id) REFERENCES runs(id)
  );

  CREATE INDEX IF NOT EXISTS idx_concepts_run_id ON concepts(run_id);
  CREATE INDEX IF NOT EXISTS idx_concepts_status ON concepts(status);
  ```
- **PATTERN**: Follow the existing DDL style in `schema.py:15-44` — `CREATE TABLE IF NOT EXISTS`, TEXT columns, foreign keys, indexes
- **GOTCHA**: `status` column uses the same pattern as `runs.status` — values will be `'pending'` (default), `'kept'`, `'discarded'` (matches the DevPlan's binary keep/discard review action for Feature 5)
- **VALIDATE**: `uv run python -c "from src.db.schema import SCHEMA_SQL; assert 'concepts' in SCHEMA_SQL; print('concepts table found in schema')"`

### Task 3: Add concept queries to the data layer

Add Pydantic model and CRUD functions for concepts in the query layer.

- **UPDATE**: `src/db/queries.py` — add the following after the existing `Run`/`RunCreate` models:
  - `Concept` model (Pydantic BaseModel): `id: UUID`, `run_id: UUID`, `title: str`, `premise: str`, `originality: str`, `status: str = Field(default="pending")`, `created_at: str`
  - `ConceptCreate` model: `run_id: UUID`, `title: str`, `premise: str`, `originality: str`
  - `_row_to_concept()` helper function
  - `create_concept(db, concept: ConceptCreate) -> Concept` — insert and return
  - `get_concepts(db, status: str | None = None, limit: int = 20) -> list[Concept]` — list concepts with optional status filter
  - `get_concept_by_run_id(db, run_id: UUID) -> Concept | None` — fetch concept for a specific run
  - `update_concept_status(db, concept_id: UUID, status: str) -> Concept` — for keep/discard (Feature 5, but add now for completeness)
- **PATTERN**: Mirror the exact structure of `create_run()` (lines 107-127), `get_runs()` (lines 137-154), `_row_to_run()` (lines 71-89)
- **IMPORTS**: No new imports needed — `uuid4`, `UUID`, `BaseModel`, `Field`, `aiosqlite` all already imported
- **GOTCHA**: Use `str(uuid4())` for new concept IDs, same as `create_run()`
- **GOTCHA**: `_row_to_concept` must handle the same `aiosqlite.Row` access pattern as `_row_to_run`
- **VALIDATE**: `uv run python -c "from src.db.queries import Concept, ConceptCreate, create_concept, get_concepts, get_concept_by_run_id, update_concept_status; print('Concept queries OK')"`

---

## VALIDATION CHECKPOINT

Before proceeding to Milestone 2, verify:

```bash
# All synthesis models import cleanly
uv run python -c "from src.synthesis.models import ConceptExtraction; print(ConceptExtraction.model_json_schema())"

# All DB models and queries import cleanly
uv run python -c "from src.db.queries import Concept, ConceptCreate; print('Concept models OK')"

# Schema includes concepts table
uv run python -c "from src.db.schema import SCHEMA_SQL; assert 'concepts' in SCHEMA_SQL; print('Schema OK')"

# Lint passes
uv run ruff check src/synthesis/ src/db/
uv run ruff format --check src/synthesis/ src/db/
```

**Expected**: All commands pass with exit code 0
