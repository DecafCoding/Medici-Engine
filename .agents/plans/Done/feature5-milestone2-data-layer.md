# Feature 5 — Milestone 2: Data Layer

**Parent plan**: `feature5-review-ui-batch-setup.md`
**Tasks**: 4
**Goal**: Add batches table, batch queries, batch_id on runs, and concepts-with-scores join query

---

## Feature Context

The batch setup UI needs to track batch progress (how many conversations completed out of total), and the review UI needs to display concepts joined with their scores in a sortable table. This milestone adds the `batches` table, all batch-related query functions, the `batch_id` foreign key on `runs`, and a `get_concepts_with_scores` join query for the review table.

## User Story

As a Medici Engine operator
I want to configure and launch conversation batches from a browser, then browse and review the scored concepts
So that I can run the system at scale and make keep/discard decisions faster than via CLI output

---

## CONTEXT REFERENCES

### Relevant Codebase Files — READ BEFORE IMPLEMENTING

- `src/db/schema.py` (full file) — Why: Add `batches` table DDL here, add `batch_id` column to `runs` table. Follow existing DDL patterns.
- `src/db/queries.py` (full file) — Why: Add `Batch`, `BatchCreate`, `ConceptWithScore` models and query functions. Follow existing `_row_to_*`, model, and query patterns exactly.
- `tests/test_db.py` (full file) — Why: Add tests for new batch queries following existing test patterns.
- `CLAUDE.md` — Why: All database access must go through `src/db/queries.py`. No raw SQL elsewhere.

### Files to Modify

- `src/db/schema.py` — Add `batches` table, add `batch_id` to `runs` table
- `src/db/queries.py` — Add batch models, batch queries, update Run/RunCreate for batch_id, add ConceptWithScore join query
- `tests/test_db.py` — Add tests for new queries

### Patterns to Follow

**DDL Pattern** (from `src/db/schema.py`):
```sql
CREATE TABLE IF NOT EXISTS batches (
    id TEXT PRIMARY KEY,
    ...
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    ...
);

CREATE INDEX IF NOT EXISTS idx_batches_status ON batches(status);
```

**Model Pattern** (from `src/db/queries.py`):
```python
class Batch(BaseModel):
    """A batch of conversation runs."""
    id: UUID
    total_runs: int
    ...

class BatchCreate(BaseModel):
    """Input model for creating a new batch."""
    total_runs: int
```

**Row Mapper Pattern** (from `src/db/queries.py`):
```python
def _row_to_batch(row: aiosqlite.Row) -> Batch:
    """Map a database row to a Batch model."""
    return Batch(
        id=UUID(row["id"]),
        ...
    )
```

**Query Pattern** (from `src/db/queries.py`):
```python
async def create_batch(db: aiosqlite.Connection, batch: BatchCreate) -> Batch:
    """Insert a new batch record and return the hydrated model."""
    batch_id = str(uuid4())
    await db.execute(...)
    await db.commit()
    ...
```

---

## IMPLEMENTATION PLAN

### Task 4: Batch Data Layer

Add the `batches` table, batch queries, `batch_id` on runs, and the concepts-with-scores join query.

**Part A — Schema changes:**

- **UPDATE**: `src/db/schema.py` — add `batches` table to `SCHEMA_SQL` (BEFORE the `runs` table so the foreign key reference works):
  ```sql
  CREATE TABLE IF NOT EXISTS batches (
      id TEXT PRIMARY KEY,
      total_runs INTEGER NOT NULL,
      completed_runs INTEGER NOT NULL DEFAULT 0,
      failed_runs INTEGER NOT NULL DEFAULT 0,
      status TEXT NOT NULL DEFAULT 'running',
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      completed_at TEXT
  );

  CREATE INDEX IF NOT EXISTS idx_batches_status ON batches(status);
  ```
  Status values: `running`, `completed`, `failed`

- **UPDATE**: `src/db/schema.py` — add `batch_id TEXT REFERENCES batches(id)` column to the existing `runs` CREATE TABLE statement. Place it after `error_message`. This is a nullable column — old runs and CLI-triggered runs will have NULL.

- **GOTCHA**: The `batches` table DDL must appear BEFORE the `runs` table DDL in `SCHEMA_SQL` because `runs.batch_id` references `batches(id)` as a foreign key, and `PRAGMA foreign_keys=ON` is enabled. If `batches` doesn't exist when `runs` is created, the foreign key constraint will fail.

- **GOTCHA**: Adding `batch_id` to the `runs` CREATE TABLE statement means existing databases (created before this change) won't have the column. Since we use `CREATE TABLE IF NOT EXISTS`, the existing table won't be altered. For pre-v1.0, this is acceptable — users can delete `data/yield_engine.db` to recreate. Add a comment in schema.py noting this.

**Part B — Batch models and queries:**

- **UPDATE**: `src/db/queries.py` — add after the Score section:

  Models:
  - `Batch(BaseModel)`: `id: UUID`, `total_runs: int`, `completed_runs: int`, `failed_runs: int`, `status: str`, `created_at: str`, `completed_at: str | None`
  - `BatchCreate(BaseModel)`: `total_runs: int`

  Helper:
  - `_row_to_batch(row: aiosqlite.Row) -> Batch`

  Queries:
  - `async def create_batch(db, batch: BatchCreate) -> Batch` — insert and return
  - `async def get_batch_by_id(db, batch_id: UUID) -> Batch | None` — fetch single batch
  - `async def get_batches(db, limit: int = 20) -> list[Batch]` — fetch recent batches ordered by created_at DESC
  - `async def increment_batch_completed(db, batch_id: UUID) -> Batch` — `UPDATE batches SET completed_runs = completed_runs + 1 WHERE id = ?`
  - `async def increment_batch_failed(db, batch_id: UUID) -> Batch` — `UPDATE batches SET failed_runs = failed_runs + 1 WHERE id = ?`
  - `async def complete_batch(db, batch_id: UUID) -> Batch` — fetch the batch, set `completed_at` to now, set `status` to `'completed'` if `failed_runs == 0` else `'failed'` if `completed_runs == 0` else `'completed'` (partial success is still completed). Commit and return.

**Part C — Update Run model for batch_id:**

- **UPDATE**: `src/db/queries.py`:
  - Add `batch_id: UUID | None = None` to `Run` model
  - Add `batch_id: UUID | None = None` to `RunCreate` model
  - Update `_row_to_run` to include: `batch_id=UUID(row["batch_id"]) if row["batch_id"] else None`
  - Update `create_run` INSERT to include `batch_id` column and value: `str(run.batch_id) if run.batch_id else None`
  - Add `async def get_runs_by_batch_id(db, batch_id: UUID, limit: int = 100) -> list[Run]` — fetch runs for a batch

**Part D — Concepts with scores join query:**

- **UPDATE**: `src/db/queries.py` — add:
  - `ConceptWithScore(BaseModel)`: all Concept fields plus `uniqueness_score: float | None`, `plausibility_score: float | None`, `compelling_factor_score: float | None`, `overall_score: float | None`
  - `_row_to_concept_with_score(row: aiosqlite.Row) -> ConceptWithScore` helper
  - `async def get_concepts_with_scores(db, status?, sort_by?, limit?) -> list[ConceptWithScore]`:
    ```sql
    SELECT c.*, s.uniqueness_score, s.plausibility_score, s.compelling_factor_score
    FROM concepts c
    LEFT JOIN scores s ON s.concept_id = c.id
    ```
    - `sort_by` parameter accepts: `"score_desc"`, `"score_asc"`, `"date_desc"` (default), `"date_asc"`
    - For score sorting, compute overall as `(s.uniqueness_score + s.plausibility_score + s.compelling_factor_score) / 3.0` in SQL and ORDER BY it. NULLs sort last (use `COALESCE` or `NULLS LAST` — SQLite supports `ORDER BY col IS NULL, col DESC` pattern)
    - `overall_score` is computed in `_row_to_concept_with_score` from the three score columns

**Part E — Tests:**

- **UPDATE**: `tests/test_db.py` — add tests:
  - `test_create_and_get_batch` — create a batch, fetch by ID, verify fields
  - `test_increment_batch_completed` — create batch, increment, verify count
  - `test_increment_batch_failed` — create batch, increment, verify count
  - `test_complete_batch` — create batch, increment completed to match total, complete, verify status
  - `test_create_run_with_batch_id` — create batch, create run with batch_id, verify association
  - `test_get_runs_by_batch_id` — create batch, create multiple runs, fetch by batch_id
  - `test_get_concepts_with_scores` — create run, concept, score, verify join query returns all fields
  - `test_get_concepts_with_scores_no_score` — create concept without score, verify NULL score fields
  - `test_get_concepts_with_scores_sort_by_score` — create multiple concepts with different scores, verify sort order

- **VALIDATE**: `uv run pytest tests/test_db.py -v`

---

## VALIDATION CHECKPOINT

```bash
uv run ruff check src/db/ && uv run ruff format --check src/db/ && uv run pytest tests/test_db.py -v
```

**Expected**: Linting passes, all DB tests pass (existing + new batch/join query tests).

```bash
uv run pytest tests/ -v
```

**Expected**: All tests across the entire suite still pass (zero regressions).

---

## ACCEPTANCE CRITERIA (Milestone 2)

- [ ] `batches` table DDL added to `src/db/schema.py` with status index
- [ ] `batch_id` column added to `runs` table DDL (nullable, FK to batches)
- [ ] `Batch`, `BatchCreate` models added to `src/db/queries.py`
- [ ] `_row_to_batch`, `create_batch`, `get_batch_by_id`, `get_batches`, `increment_batch_completed`, `increment_batch_failed`, `complete_batch` query functions added
- [ ] `Run` and `RunCreate` models updated with `batch_id` field
- [ ] `_row_to_run` and `create_run` updated to handle `batch_id`
- [ ] `get_runs_by_batch_id` query function added
- [ ] `ConceptWithScore` model and `get_concepts_with_scores` join query added with sorting support
- [ ] Tests for all new queries pass
- [ ] All existing tests still pass (zero regressions)
- [ ] Ruff check and format pass
