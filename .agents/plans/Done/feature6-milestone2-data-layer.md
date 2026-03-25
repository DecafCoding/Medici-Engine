# Feature 6 — Milestone 2: Data Layer

**Tasks:** 5–6
**Goal:** Schema migration to JSON storage, query layer refactor
**Validation checkpoint:** In-memory DB creates successfully, Concept/Score models use dict/list fields, CRUD operations roundtrip JSON correctly
**Depends on:** Milestone 1 (domain config models must exist)

---

## Prerequisites

Read the parent plan for full context: [feature6-domain-expansion.md](feature6-domain-expansion.md)

### Relevant Codebase Files — MUST READ BEFORE IMPLEMENTING

- `src/db/schema.py` (lines 62-90) — Why: concepts and scores tables have hardcoded columns that must be replaced
- `src/db/queries.py` (lines 70-148) — Why: Concept, Score, ConceptWithScore models hardcode field names
- `src/db/queries.py` (lines 202-224) — Why: `_row_to_concept_with_score()` hardcodes overall score calculation
- `src/db/queries.py` (lines 654-686) — Why: `get_concepts_with_scores()` join query hardcodes score columns
- `src/db/queries.py` (lines 386-405) — Why: `create_concept()` writes hardcoded fields
- `src/db/queries.py` (lines 469-492) — Why: `create_score()` writes hardcoded score columns

### Design Decisions (from parent plan)

- **D1**: JSON storage — `fields_json TEXT` for concepts, `axes_json TEXT` for scores
- **D5**: Schema recreation (delete `data/yield_engine.db`), no formal migration

---

## IMPLEMENTATION TASKS

### Task 5: Database Schema Migration

Restructure the concepts and scores tables for domain-agnostic storage.

- **UPDATE** `src/db/schema.py` — Rewrite the `concepts` table:
  ```sql
  CREATE TABLE IF NOT EXISTS concepts (
      id TEXT PRIMARY KEY,
      run_id TEXT NOT NULL,
      domain TEXT NOT NULL,
      title TEXT NOT NULL,
      fields_json TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'pending',
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      FOREIGN KEY (run_id) REFERENCES runs(id)
  );
  ```
  - `domain` — which domain config produced this concept
  - `title` — denormalized primary label for list views (extracted from `fields_json` by the primary_field)
  - `fields_json` — JSON object with all extraction fields: `{"title": "...", "premise": "...", "originality": "..."}`

- **UPDATE** `src/db/schema.py` — Rewrite the `scores` table:
  ```sql
  CREATE TABLE IF NOT EXISTS scores (
      id TEXT PRIMARY KEY,
      concept_id TEXT NOT NULL UNIQUE,
      axes_json TEXT NOT NULL,
      overall_score REAL,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      FOREIGN KEY (concept_id) REFERENCES concepts(id)
  );
  ```
  - `axes_json` — JSON array of axis scores: `[{"axis": "uniqueness", "label": "Uniqueness", "score": 8.5, "reasoning": "..."}]`
  - `overall_score` — precomputed average for sort queries (avoids JSON computation in ORDER BY)

- **ADD** comment in schema file noting the breaking schema change and to delete `data/yield_engine.db` to recreate
- **VALIDATE**: `uv run python -c "import asyncio, aiosqlite; from src.db.schema import init_schema; db = asyncio.run(aiosqlite.connect(':memory:')); asyncio.run(init_schema(db)); print('Schema OK')"`

### Task 6: Query Layer Refactor

Update all Pydantic models and query functions for the new schema.

- **UPDATE** `src/db/queries.py` — Replace `Concept` model:
  ```python
  class Concept(BaseModel):
      id: UUID
      run_id: UUID
      domain: str
      title: str
      fields: dict[str, str]
      status: str = Field(default="pending")
      created_at: str
  ```

- **UPDATE** `ConceptCreate`:
  ```python
  class ConceptCreate(BaseModel):
      run_id: UUID
      domain: str
      title: str
      fields: dict[str, str]
  ```

- **ADD** new `AxisScoreRecord` model:
  ```python
  class AxisScoreRecord(BaseModel):
      axis: str
      label: str
      score: float
      reasoning: str
  ```

- **UPDATE** `Score` model:
  ```python
  class Score(BaseModel):
      id: UUID
      concept_id: UUID
      axes: list[AxisScoreRecord]
      overall_score: float | None
      created_at: str
  ```

- **UPDATE** `ScoreCreate`:
  ```python
  class ScoreCreate(BaseModel):
      concept_id: UUID
      axes: list[AxisScoreRecord]
  ```

- **UPDATE** `ConceptWithScore`:
  ```python
  class ConceptWithScore(BaseModel):
      id: UUID
      run_id: UUID
      domain: str
      title: str
      fields: dict[str, str]
      status: str
      created_at: str
      overall_score: float | None = None
  ```

- **UPDATE** `_row_to_concept()` — Parse `fields_json` with `json.loads()`
- **UPDATE** `_row_to_score()` — Parse `axes_json` with `json.loads()` into `list[AxisScoreRecord]`
- **UPDATE** `_row_to_concept_with_score()` — Read `overall_score` directly from row (precomputed), parse `fields_json`
- **UPDATE** `create_concept()` — Write `domain`, `title`, `fields_json` (json.dumps of fields dict)
- **UPDATE** `create_score()` — Write `axes_json` (json.dumps of axes list as dicts), compute and write `overall_score` as average of all axis scores
- **UPDATE** `get_concepts_with_scores()`:
  - Simplify the join query: no longer need to select individual score columns
  - Sort by `s.overall_score` instead of computing the average in SQL
  ```sql
  SELECT c.*, s.overall_score
  FROM concepts c
  LEFT JOIN scores s ON s.concept_id = c.id
  ```
- **REMOVE** `_row_to_concept_with_score()`'s hardcoded 3-axis average calculation (replaced by precomputed column)
- **VALIDATE**: `uv run python -c "from src.db.queries import Concept, Score, ConceptCreate, ScoreCreate, AxisScoreRecord; print('Models OK')"`

---

## MILESTONE VALIDATION

```bash
# Schema creates successfully
uv run python -c "import asyncio, aiosqlite; from src.db.schema import init_schema; db = asyncio.run(aiosqlite.connect(':memory:')); asyncio.run(init_schema(db)); print('Schema OK')"

# Models import correctly
uv run python -c "from src.db.queries import Concept, Score, ConceptCreate, ScoreCreate, AxisScoreRecord, ConceptWithScore; print('Models OK')"

# Lint must still pass
uv run ruff check .
uv run ruff format --check .
```

**Note:** Existing tests will be broken after this milestone because test files still use the old model shapes. This is expected — tests are updated in Milestone 5.
