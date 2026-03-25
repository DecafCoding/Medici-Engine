# Feature 7 — Milestone 1: Analytics Data Layer

**Parent plan**: `feature7-feedback-loop.md`
**Tasks**: 1–4
**Goal**: Add analytics Pydantic models, pairing performance query, shared object performance query, and their tests.

The following plan should be complete, but validate documentation and codebase patterns before implementing.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — READ BEFORE IMPLEMENTING

- `src/db/queries.py` (full file) — Why: All new analytics queries go here. Follow the existing patterns for typed query functions, `_row_to_*` mappers, and Pydantic response models.
- `src/db/schema.py` (full file) — Why: No schema changes needed — existing tables (runs, concepts, scores, pairing_history) already have all the data needed. Verify column names.
- `tests/test_db.py` (full file) — Why: Pattern for database query tests with `db` fixture.
- `tests/conftest.py` (full file) — Why: Shared fixtures including `db` and test data factories.

### New Files to Create

- `tests/test_insights.py` — Tests for analytics queries

### Patterns to Follow

**Query Function Pattern** (from `src/db/queries.py`):
```python
async def get_something(
    db: aiosqlite.Connection,
    limit: int = 20,
) -> list[SomeModel]:
    """Fetch something with typed return."""
    cursor = await db.execute("SELECT ...", (limit,))
    rows = await cursor.fetchall()
    return [_row_to_something(row) for row in rows]
```

**Pydantic Response Model Pattern** (from `src/db/queries.py`):
```python
class SomeModel(BaseModel):
    """Description of what this represents."""
    field_a: str
    field_b: float | None = None
```

**Row Mapper Pattern** (from `src/db/queries.py`):
```python
def _row_to_something(row: aiosqlite.Row) -> SomeModel:
    """Map a database row to a SomeModel."""
    return SomeModel(
        field_a=row["field_a"],
        field_b=row["field_b"],
    )
```

---

## IMPLEMENTATION TASKS

### Task 1: Analytics Pydantic Models

Add new Pydantic models to `src/db/queries.py` for the analytics query results.

- **ADD** to `src/db/queries.py` after the `ConceptWithScore` model (around line 146):
  - `PairingPerformance` model:
    - `persona_a_name: str`
    - `persona_b_name: str`
    - `total_runs: int`
    - `completed_runs: int`
    - `concepts_kept: int`
    - `concepts_discarded: int`
    - `concepts_pending: int`
    - `avg_score: float | None`
    - `max_score: float | None`
    - `kept_rate: float | None` — computed: `concepts_kept / (concepts_kept + concepts_discarded)` if any reviewed, else None
  - `SharedObjectPerformance` model:
    - `shared_object_text: str`
    - `shared_object_type: str`
    - `total_runs: int`
    - `completed_runs: int`
    - `concepts_kept: int`
    - `concepts_discarded: int`
    - `avg_score: float | None`
    - `max_score: float | None`
    - `kept_rate: float | None`
- **PATTERN**: Follow `ConceptWithScore` model structure at `src/db/queries.py:135-146`
- **VALIDATE**: `uv run ruff check src/db/queries.py`

### Task 2: Pairing Performance Query

Add the query function that aggregates concept outcomes and scores by persona pairing.

- **ADD** to `src/db/queries.py` in a new `# ── Analytics Queries ──────────────────` section at the bottom:
  - `get_pairing_performance(db, domain: str | None = None, min_runs: int = 1, limit: int = 50) -> list[PairingPerformance]`
  - SQL joins: `runs` → `concepts` (via `run_id`) → `scores` (via `concept_id`)
  - Group by sorted persona pair (persona_a_name, persona_b_name — note: `pairing_history` already stores sorted names, but `runs` does not. Group using `MIN(persona_a_name, persona_b_name), MAX(persona_a_name, persona_b_name)` to normalize)
  - Count concepts by status: use `SUM(CASE WHEN c.status = 'kept' THEN 1 ELSE 0 END)` pattern
  - Filter by domain if provided (concepts.domain)
  - Filter by `min_runs` (HAVING clause)
  - Order by `avg_score DESC NULLS LAST` by default
  - Helper: `_row_to_pairing_performance(row)` mapper
  - Compute `kept_rate` in the mapper, not SQL — cleaner and avoids division-by-zero in SQL
- **IMPORTS**: No new imports needed
- **GOTCHA**: `runs.persona_a_name` and `persona_b_name` are NOT stored in sorted order (unlike `pairing_history`). Must normalize in the query with `MIN/MAX` or equivalent.
- **GOTCHA**: Some runs may not have concepts (synthesis skipped or failed). Use LEFT JOINs from runs.
- **VALIDATE**: `uv run pytest tests/test_db.py -v --tb=short`

### Task 3: Shared Object Performance Query

Add the query function that aggregates concept outcomes and scores by shared object.

- **ADD** to `src/db/queries.py` in the analytics section:
  - `get_shared_object_performance(db, domain: str | None = None, min_runs: int = 1, limit: int = 50) -> list[SharedObjectPerformance]`
  - SQL joins: `runs` → `concepts` → `scores`
  - Group by `runs.shared_object_text, runs.shared_object_type`
  - Same aggregation pattern as pairing performance (counts by status, avg/max score)
  - Order by `avg_score DESC NULLS LAST`
  - Helper: `_row_to_shared_object_performance(row)` mapper
- **PATTERN**: Mirror the pairing performance query structure
- **GOTCHA**: Shared object text can be long — no truncation in the query, handle in templates
- **VALIDATE**: `uv run pytest tests/test_db.py -v --tb=short`

### Task 4: Analytics Query Tests

Add tests for both analytics queries.

- **CREATE** `tests/test_insights.py` with tests:
  - `test_pairing_performance_empty_db` — returns empty list
  - `test_pairing_performance_single_kept_concept` — one run with kept concept returns correct counts and score
  - `test_pairing_performance_multiple_runs_same_pairing` — aggregation across multiple runs
  - `test_pairing_performance_normalizes_persona_order` — (A,B) and (B,A) aggregate together
  - `test_pairing_performance_filters_by_domain` — domain filter works
  - `test_pairing_performance_min_runs_filter` — pairings below threshold excluded
  - `test_pairing_performance_kept_rate_calculation` — verify kept_rate = kept / (kept + discarded)
  - `test_pairing_performance_no_reviewed_concepts_null_kept_rate` — all pending = None kept_rate
  - `test_shared_object_performance_empty_db` — returns empty list
  - `test_shared_object_performance_aggregates_correctly` — correct counts and scores
  - `test_shared_object_performance_filters_by_domain` — domain filter works
- **IMPORTS**: `from src.db.queries import (PairingPerformance, SharedObjectPerformance, get_pairing_performance, get_shared_object_performance, ...)` plus existing create/update helpers
- **PATTERN**: Follow `tests/test_db.py` — use `db` fixture, `_create_test_run` helper pattern, `create_concept`, `create_score`, `update_concept_status`
- **GOTCHA**: Need to create runs, complete them, create concepts, create scores, AND update concept status to `kept`/`discarded` to test the full aggregation path. Build a local helper for this.
- **VALIDATE**: `uv run pytest tests/test_insights.py -v --tb=short`

---

## VALIDATION CHECKPOINT

```bash
# Must all pass before moving to Milestone 2
uv run ruff check src/db/queries.py
uv run ruff format --check src/db/queries.py
uv run pytest tests/test_insights.py tests/test_db.py -v --tb=short
```

**Done when**: Analytics queries return correct aggregations for seeded test data. All existing DB tests still pass.

---

## ACCEPTANCE CRITERIA (Milestone 1)

- [ ] `PairingPerformance` and `SharedObjectPerformance` models defined with all fields
- [ ] `get_pairing_performance()` returns correct aggregation of persona pair outcomes
- [ ] `get_shared_object_performance()` returns correct aggregation of shared object outcomes
- [ ] Persona pairs (A,B) and (B,A) are treated as the same pairing in analytics
- [ ] All analytics queries handle empty database gracefully (no errors, empty results)
- [ ] kept_rate is None when no concepts have been reviewed (no division by zero)
- [ ] All tests in `tests/test_insights.py` pass
- [ ] No regressions in existing `tests/test_db.py` tests

---

## NOTES

### Design Decision: No New Database Tables

The existing schema already contains all necessary data. Runs have persona names and shared object text. Concepts have run_id, domain, and status. Scores have concept_id and overall_score. The analytics queries join these existing tables — no migrations needed.

### Persona Order Normalization

The `runs` table stores personas in assignment order (A speaks first), not sorted order. The `pairing_history` table stores sorted order. Analytics queries must normalize using `MIN/MAX` on persona names to treat (A,B) and (B,A) as the same pairing. This is critical for correct aggregation.
