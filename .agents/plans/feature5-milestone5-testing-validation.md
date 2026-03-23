# Feature 5 — Milestone 5: Testing & Validation

**Parent plan**: `feature5-review-ui-batch-setup.md`
**Tasks**: 9–12
**Goal**: Write comprehensive tests for all new code, update existing tests, and validate the full suite

---

## Feature Context

Milestones 1–4 built the foundation, data layer, batch runner, and review UI. This milestone adds comprehensive test coverage for all new endpoints and services, ensures existing tests still pass after schema changes, and runs final lint/format validation.

## User Story

As a Medici Engine operator
I want to configure and launch conversation batches from a browser, then browse and review the scored concepts
So that I can run the system at scale and make keep/discard decisions faster than via CLI output

---

## CONTEXT REFERENCES

### Relevant Codebase Files — READ BEFORE IMPLEMENTING

- `tests/conftest.py` (full file) — Why: Existing test fixtures (`db`, `client`, `mock_openai_response`, `mock_parse_response`, `test_transcript`, `test_concept_extraction`, `test_concept_scoring`). Use these for new tests. May need minor updates for batch_id column.
- `tests/test_api.py` (full file) — Why: Pattern for testing HTTP endpoints. UI tests follow the same structure but assert on HTML content instead of JSON.
- `tests/test_batch.py` (created in Milestone 3) — Why: Already has batch runner tests. This milestone may add additional edge case tests or verify coverage is complete.
- `tests/test_db.py` (full file) — Why: Verify new batch query tests (added in Milestone 2) still pass. May need updates if conftest fixtures changed.
- `src/ui/routes.py` (created in Milestones 3–4) — Why: All UI endpoints that need test coverage.
- `src/batch/runner.py` (created in Milestone 3) — Why: Batch orchestration logic that needs test coverage.
- `src/db/queries.py` (full file) — Why: New query functions (batch queries, ConceptWithScore) that need test coverage.
- `CLAUDE.md` — Why: Testing conventions, mock requirements (never make real LLM calls in tests).

### New Files to Create

- `tests/test_ui.py` — UI route tests

### Files to Modify

- `tests/conftest.py` — Update fixtures if needed for batch_id column
- `tests/test_db.py` — Ensure batch query tests are comprehensive (may already be done in Milestone 2)

### Patterns to Follow

**API Test Pattern** (from `tests/test_api.py`):
```python
async def test_health_endpoint(client) -> None:
    """Verify the health endpoint returns ok status."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

**UI Test Pattern** (adapted — assert on HTML content):
```python
async def test_review_page_renders(client) -> None:
    """Verify the review page returns HTML with expected elements."""
    response = await client.get("/ui/review")
    assert response.status_code == 200
    assert "Medici Engine" in response.text
    assert "concept-table-body" in response.text
```

**Test Data Seeding** (from `tests/test_api.py`):
```python
async def _seed_score(db):
    run = await create_run(db, RunCreate(...))
    concept = await create_concept(db, ConceptCreate(run_id=run.id, ...))
    score = await create_score(db, ScoreCreate(concept_id=concept.id, ...))
    return run, concept, score
```

**Mock Pattern** (from `tests/conftest.py`):
```python
from unittest.mock import AsyncMock, patch

# Patch async methods
with patch.object(ConversationRunner, "run", new_callable=AsyncMock) as mock_run:
    mock_run.return_value = test_transcript
    ...
```

---

## IMPLEMENTATION PLAN

### Task 9: Tests — UI Routes

Write comprehensive tests for all UI endpoints.

- **CREATE**: `tests/test_ui.py`:

  Module docstring: `"""Tests for the web UI routes (batch setup and concept review)."""`

  **Helper to seed test data:**
  ```python
  async def _seed_review_data(db):
      """Create a run, concept, and score for review UI tests."""
      # Similar to _seed_score in test_api.py but also creates a batch
      batch = await create_batch(db, BatchCreate(total_runs=1))
      run = await create_run(db, RunCreate(
          persona_a_name="test_physicist",
          persona_b_name="test_builder",
          shared_object_text="A test scenario",
          batch_id=batch.id,
      ))
      # Complete the run with a transcript
      transcript = [Turn(turn_number=1, persona_name="test_physicist", content="Test content")]
      await complete_run(db, run.id, transcript)
      concept = await create_concept(db, ConceptCreate(
          run_id=run.id, title="Test Concept", premise="Test premise.", originality="Test originality.",
      ))
      score = await create_score(db, ScoreCreate(
          concept_id=concept.id,
          uniqueness_score=8.5, uniqueness_reasoning="Novel.",
          plausibility_score=6.0, plausibility_reasoning="Plausible.",
          compelling_factor_score=7.5, compelling_factor_reasoning="Compelling.",
      ))
      return batch, run, concept, score
  ```

  **Batch UI tests:**
  - `test_batch_page_renders(client)` — `GET /ui/batch` returns 200, HTML contains "Batch" and persona names from the library
  - `test_batch_page_contains_personas(client)` — verify all persona names appear in the dropdown HTML
  - `test_batch_page_contains_shared_objects(client)` — verify shared objects appear in dropdown
  - `test_batch_form_submission(client, db)` — `POST /ui/batch` with form data (`num_conversations=1`, `turns_per_agent=3`), mock `BatchRunner.run_batch` to no-op, verify 200 response, verify batch record created in DB
  - `test_batch_status_endpoint(client, db)` — create a batch, `GET /ui/batch/{batch_id}/status`, verify response contains progress info

  **Review UI tests:**
  - `test_review_page_renders_empty(client)` — `GET /ui/review` with empty DB returns 200, contains "No concepts found"
  - `test_review_page_renders_with_data(client, db)` — seed data, `GET /ui/review` returns 200, contains concept title
  - `test_review_rows_fragment(client, db)` — seed data, `GET /ui/review/rows` returns HTML fragment with concept title (no full page layout)
  - `test_review_filter_by_status(client, db)` — seed data, `GET /ui/review/rows?status=pending` returns concept, `GET /ui/review/rows?status=kept` returns empty
  - `test_review_sort_by_score(client, db)` — seed two concepts with different scores, `GET /ui/review/rows?sort=score_desc`, verify higher-scored concept appears first
  - `test_concept_detail_page(client, db)` — seed data, `GET /ui/review/{concept_id}` returns 200, contains concept title, premise, originality, score values, reasoning text
  - `test_concept_detail_not_found(client)` — `GET /ui/review/{random_uuid}` returns 404
  - `test_transcript_lazy_load(client, db)` — seed data with transcript, `GET /ui/review/{concept_id}/transcript` returns HTML with turn content
  - `test_transcript_no_transcript(client, db)` — seed data without transcript, verify "No transcript available" in response
  - `test_status_toggle_keep(client, db)` — seed data, `PATCH /ui/review/{concept_id}/status` with form data `status=kept`, verify response contains "kept" badge, verify DB updated
  - `test_status_toggle_discard(client, db)` — same but with `status=discarded`
  - `test_root_redirects_to_review(client)` — `GET /` returns redirect (302 or 307) to `/ui/review`

- **GOTCHA**: UI endpoints return HTML, not JSON. Assert on `response.text` (string contains checks), not `response.json()`.
- **GOTCHA**: For the batch POST test, mock `BatchRunner.run_batch` to prevent actual LLM calls. Use `patch("src.ui.routes.BatchRunner")` or similar.
- **GOTCHA**: The PATCH endpoint expects form-encoded data. Send with `client.patch(url, data={"status": "kept"})`.
- **GOTCHA**: The `client` fixture from conftest uses `ASGITransport` — it works with HTML responses the same as JSON.

- **VALIDATE**: `uv run pytest tests/test_ui.py -v`

### Task 10: Verify Batch Runner Test Coverage

Review `tests/test_batch.py` (created in Milestone 3) for completeness. Add any missing edge case tests.

- **VERIFY**: The following scenarios are covered:
  - Single conversation batch succeeds
  - Multi-conversation batch tracks progress
  - Batch continues when one conversation fails
  - Specified persona pairs are used correctly
  - Random personas are selected when none specified
  - Missing OpenAI key skips synthesis/scoring
  - Synthesis failure doesn't crash the batch
  - Scoring failure doesn't crash the batch

- **ADD** if missing:
  - `test_batch_with_zero_conversations` — `num_conversations=0`, verify batch completes immediately with 0 runs
  - `test_batch_all_conversations_fail` — all conversations raise ConversationError, verify batch status is "failed", `failed_runs == total_runs`, `completed_runs == 0`
  - `test_batch_with_specified_shared_objects` — provide specific indices, verify correct objects used

- **VALIDATE**: `uv run pytest tests/test_batch.py -v`

### Task 11: Update Existing Tests

Ensure all existing tests pass after schema and query changes.

- **CHECK**: `tests/conftest.py` — verify the `db` fixture still works with the updated schema (new `batches` table and `batch_id` column on `runs`). The fixture creates an in-memory database and initializes the schema, so the new DDL will run automatically. No changes should be needed unless the schema change breaks something.

- **CHECK**: `tests/test_db.py` — verify existing run tests still pass. The `RunCreate` model now has an optional `batch_id` field (default None), so existing test calls without `batch_id` should still work.

- **CHECK**: `tests/test_api.py` — verify existing API tests still pass. The `Run` response model now includes `batch_id` (null for old runs), which should serialize fine.

- **RUN**: `uv run pytest tests/ -v` — full test suite. If any test fails, investigate and fix.

- **GOTCHA**: If `_row_to_run` was updated to read `row["batch_id"]` but existing test runs don't have that column in the row, it will fail. The in-memory DB fixture re-creates the schema from scratch each test, so the column WILL exist. But if there's a mismatch between the schema DDL and the row mapper, it needs fixing.

- **VALIDATE**: `uv run pytest tests/ -v`

### Task 12: Lint and Format

Final validation pass across the entire codebase.

- **RUN**: `uv run ruff check .`
  - If errors: `uv run ruff check --fix .`
- **RUN**: `uv run ruff format --check .`
  - If errors: `uv run ruff format .`
- **RUN**: `uv run pytest tests/ -v` — one final full pass

- **VALIDATE**: All three commands pass with exit code 0

---

## VALIDATION CHECKPOINT

```bash
# Full validation suite
uv run ruff check . && uv run ruff format --check . && uv run pytest tests/ -v
```

**Expected**: Zero lint errors, zero format errors, all tests pass.

### Manual Validation Checklist

1. Start server: `uv run uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload`
2. `http://localhost:8080/` → redirects to `/ui/review`
3. `/ui/batch` → batch setup form with persona/object dropdowns, turn count, conversation count
4. `/static/style.css` → loads CSS
5. `/static/htmx.min.js` → loads HTMX
6. `/ui/review` → concept table (empty or with data)
7. Filter dropdown → table updates without page reload
8. Sort dropdown → table updates without page reload
9. Click concept row → detail page with scores and reasoning
10. Click transcript drawer → transcript loads lazily
11. Click Keep/Discard → status badge updates without page reload
12. `/api/runs` → still returns JSON (existing API untouched)
13. `/health` → still returns `{"status": "ok"}`

---

## ACCEPTANCE CRITERIA (Milestone 5)

- [ ] `tests/test_ui.py` covers all UI endpoints (batch page, batch submit, batch status, review list, review rows fragment, concept detail, transcript load, status toggle, root redirect)
- [ ] `tests/test_batch.py` covers all batch runner scenarios (success, failure, partial failure, edge cases)
- [ ] All existing tests pass without modification (or with minimal fixture updates)
- [ ] `uv run ruff check .` passes with zero errors
- [ ] `uv run ruff format --check .` passes with zero errors
- [ ] `uv run pytest tests/ -v` passes with all tests green
- [ ] Manual validation checklist completed successfully
- [ ] No regressions in existing functionality (API, health, database)
