# Feature 4 — Milestone 1: Data Foundation

**Parent plan**: `feature4-scoring-layer.md`
**Tasks**: 1–3
**Goal**: Create scoring Pydantic models, database table, and typed queries

---

## Feature Context

Add a scoring layer that evaluates concepts extracted by the synthesizer. A higher-capability model (OpenAI o3) scores each concept across domain-specific axes — uniqueness, scientific plausibility, and compelling factor — with written reasoning for each score. Scores are persisted in the database and exposed via the API.

## User Story

As a human reviewer of Medici Engine output
I want each concept scored across multiple axes with written reasoning
So that I can make faster, better-informed keep/discard decisions without reading the full transcript

---

## CONTEXT REFERENCES

### Relevant Codebase Files — READ BEFORE IMPLEMENTING

- `src/synthesis/models.py` (full file) — Why: Shows how to define Pydantic models used as `response_format` for OpenAI structured output. The scoring models follow this pattern.
- `src/db/queries.py` (full file) — Why: All new score queries must follow the existing patterns — `_row_to_*` helpers, typed models, parameterized SQL, `uuid4()` IDs. The `Concept` model and concept queries (lines 68-346) are the closest reference.
- `src/db/schema.py` (full file) — Why: The new `scores` table must be added here following the same DDL pattern — TEXT PRIMARY KEY, foreign keys, indexes, default timestamps.
- `CLAUDE.md` — Why: Architectural boundaries, layer dependency rules, documentation requirements.

### New Files to Create

- `src/scoring/__init__.py` — Package init for scoring module
- `src/scoring/models.py` — Pydantic models for scoring structured output (`AxisScore`, `ConceptScoring`)

### Files to Modify

- `src/db/schema.py` — Add `scores` table DDL
- `src/db/queries.py` — Add `Score` model, `ScoreCreate` model, score CRUD queries

### Patterns to Follow

**Database Row Mapping Pattern** (from `src/db/queries.py`):
```python
def _row_to_score(row: aiosqlite.Row) -> Score:
    """Map a database row to a Score model."""
    return Score(
        id=UUID(row["id"]),
        concept_id=UUID(row["concept_id"]),
        # ... fields ...
    )
```

**Naming Conventions:**
- Models: `AxisScore`, `ConceptScoring` (PascalCase, descriptive)
- Query models: `Score`, `ScoreCreate` (following `Concept`, `ConceptCreate`)

---

## IMPLEMENTATION PLAN

### Task 1: Create scoring Pydantic models for structured output

Define the Pydantic models that the OpenAI API will return as structured output. These are the response format models — they define what o3 must produce.

- **CREATE**: `src/scoring/__init__.py` — empty package init with module docstring
- **CREATE**: `src/scoring/models.py` — define `AxisScore` and `ConceptScoring` models
- **PATTERN**: Mirror `src/synthesis/models.py` structure exactly
- **IMPLEMENT**:
  - `AxisScore(BaseModel)`: `axis: str`, `score: float`, `reasoning: str` — a single axis evaluation
  - `ConceptScoring(BaseModel)`: `uniqueness: AxisScore`, `plausibility: AxisScore`, `compelling_factor: AxisScore` — the complete scoring result. Using named fields (not a list) satisfies OpenAI strict mode requirements where all fields must be present.
- **GOTCHA**: OpenAI structured output strict mode requires all fields — no `Optional` fields in the response model. Every field must be required.
- **VALIDATE**: `uv run ruff check src/scoring/ && uv run ruff format --check src/scoring/`

### Task 2: Add scores table to database schema

Add the `scores` table that stores per-axis scores linked to concepts.

- **UPDATE**: `src/db/schema.py` — append `scores` table DDL to `SCHEMA_SQL`
- **PATTERN**: Follow the `concepts` table pattern in `src/db/schema.py` (lines 45-57)
- **IMPLEMENT**: Table schema:
  ```sql
  CREATE TABLE IF NOT EXISTS scores (
      id TEXT PRIMARY KEY,
      concept_id TEXT NOT NULL UNIQUE,
      uniqueness_score REAL NOT NULL,
      uniqueness_reasoning TEXT NOT NULL,
      plausibility_score REAL NOT NULL,
      plausibility_reasoning TEXT NOT NULL,
      compelling_factor_score REAL NOT NULL,
      compelling_factor_reasoning TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      FOREIGN KEY (concept_id) REFERENCES concepts(id)
  );

  CREATE INDEX IF NOT EXISTS idx_scores_concept_id ON scores(concept_id);
  ```
- **DESIGN DECISION**: Flat column layout (not JSON) because there are exactly 3 fixed axes for the sci-fi domain. This keeps queries simple and SQLite-friendly. Future domain expansion (Feature 6) can add new score tables or columns.
- **DESIGN DECISION**: `concept_id UNIQUE` constraint — one score set per concept. Rescoring overwrites (delete + insert).
- **VALIDATE**: `uv run ruff check src/db/ && uv run python -c "import asyncio, aiosqlite; from src.db.schema import init_schema; asyncio.run((lambda: None)())"`

### Task 3: Add score query functions to data layer

Add typed queries for creating and retrieving scores.

- **UPDATE**: `src/db/queries.py`
- **PATTERN**: Follow `Concept`/`ConceptCreate`/`_row_to_concept` pattern (lines 68-87, 113-123)
- **IMPLEMENT**:
  - `Score(BaseModel)`: `id: UUID`, `concept_id: UUID`, `uniqueness_score: float`, `uniqueness_reasoning: str`, `plausibility_score: float`, `plausibility_reasoning: str`, `compelling_factor_score: float`, `compelling_factor_reasoning: str`, `created_at: str`
  - `ScoreCreate(BaseModel)`: same fields minus `id` and `created_at`
  - `_row_to_score(row) -> Score`: row mapper
  - `async def create_score(db, score: ScoreCreate) -> Score`: insert and return
  - `async def get_score_by_concept_id(db, concept_id: UUID) -> Score | None`: fetch score for a concept
  - `async def get_scores(db, limit: int = 20) -> list[Score]`: fetch recent scores
- **IMPORTS**: `UUID`, `uuid4`, `aiosqlite`, `BaseModel`, `Field` (all already imported)
- **GOTCHA**: Follow existing commit pattern — `await db.commit()` after insert
- **VALIDATE**: `uv run ruff check src/db/queries.py`

---

## VALIDATION CHECKPOINT

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest tests/test_db.py -v
```

**Expected**: Linting passes, existing DB tests still pass, schema creates cleanly with new `scores` table.

---

## ACCEPTANCE CRITERIA (Milestone 1)

- [ ] `src/scoring/__init__.py` exists with module docstring
- [ ] `src/scoring/models.py` defines `AxisScore` and `ConceptScoring` as structured output models
- [ ] `scores` table DDL added to `src/db/schema.py` with foreign key to `concepts`
- [ ] `Score`, `ScoreCreate` models added to `src/db/queries.py`
- [ ] `_row_to_score`, `create_score`, `get_score_by_concept_id`, `get_scores` query functions added
- [ ] All existing tests still pass (zero regressions)
- [ ] Ruff check and format pass
