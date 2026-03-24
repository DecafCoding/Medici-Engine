# Feature 5: Review UI + Batch Setup

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Add a web interface to the Medici Engine that serves two functions: (1) configuring and launching batches of conversation runs, and (2) reviewing the scored concepts that come out the other end. This replaces the CLI workflow (`scripts/run_conversation.py`) with a browser-based experience optimized for fast batch configuration and fast informed review. The UI uses server-rendered Jinja2 templates with HTMX for interactive updates — no frontend build toolchain.

## User Story

As a Medici Engine operator
I want to configure and launch conversation batches from a browser, then browse and review the scored concepts
So that I can run the system at scale and make keep/discard decisions faster than via CLI output

## Problem Statement

Features 1–4 are fully functional but CLI-only. Running conversations, reviewing transcripts, reading concept extractions, and checking scores all happen in terminal output. There is no way to sort, filter, compare, or batch-review output. The CLI also limits batch runs to one conversation at a time with no parallelism control.

## Solution Statement

Build a web UI using FastAPI + Jinja2 + HTMX that provides:
- A batch setup page for selecting personas, shared objects, turn counts, and number of conversations, then launching them
- A concept review page with a sortable/filterable table, detail view with scores and reasoning, expandable transcript drawer, and keep/discard toggle
- Background batch execution so the UI remains responsive during long-running conversations

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: High
**Primary Systems Affected**: API layer (new UI routes), new template layer, new batch orchestration service
**Dependencies**: `jinja2>=3.1.0`, `python-multipart>=0.0.20`, HTMX 2.0 (vendored JS file)

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `src/main.py` (lines 1–76) — Why: FastAPI app setup, lifespan, router registration. New UI router and static file mount are added here
- `src/api/routes.py` (lines 1–90) — Why: Existing API routes pattern. UI routes mirror this structure but return HTML
- `src/db/queries.py` (lines 1–442) — Why: All available query functions. UI routes call these directly — no new data access code needed
- `src/db/schema.py` (lines 1–84) — Why: Database schema. A new `batches` table is needed
- `scripts/run_conversation.py` (lines 1–486) — Why: Current end-to-end flow (conversation → synthesis → scoring). The batch runner extracts this logic
- `src/engine/conversation.py` (lines 36–142) — Why: ConversationRunner.run() interface
- `src/engine/models.py` (lines 1–40) — Why: ConversationConfig, ConversationRequest models
- `src/synthesis/synthesizer.py` (lines 70–155) — Why: Synthesizer.synthesize() interface
- `src/scoring/scorer.py` (lines 69–148) — Why: Scorer.score() interface
- `src/personas/library.py` (lines 835–912) — Why: get_all_personas(), get_all_shared_objects(), get_persona_by_name(), get_persona_pair(), get_random_shared_object()
- `src/personas/models.py` (lines 1–75) — Why: Persona and SharedObject model fields
- `src/config.py` (lines 1–83) — Why: Settings — all config values available
- `tests/conftest.py` (lines 1–208) — Why: Test fixtures — db, client, mock factories
- `tests/test_api.py` (lines 1–116) — Why: Existing API test patterns to follow
- `pyproject.toml` (lines 1–58) — Why: Dependencies and tool config

### New Files to Create

- `src/ui/__init__.py` — UI module init
- `src/ui/routes.py` — HTML-returning routes for batch setup and review pages
- `src/batch/__init__.py` — Batch orchestration module init
- `src/batch/runner.py` — Background batch execution logic (extracted from CLI script)
- `src/batch/models.py` — Batch request/status models
- `src/templates/base.html` — Layout template with HTMX, minimal CSS
- `src/templates/batch.html` — Batch setup page
- `src/templates/review.html` — Concept review list page
- `src/templates/detail.html` — Concept detail page with scores and transcript
- `src/templates/fragments/concept_rows.html` — Partial: table body for HTMX swap
- `src/templates/fragments/transcript.html` — Partial: transcript drawer content
- `src/templates/fragments/batch_status.html` — Partial: batch progress indicator
- `src/templates/fragments/concept_status.html` — Partial: kept/discarded badge after toggle
- `src/static/htmx.min.js` — Vendored HTMX 2.0
- `src/static/style.css` — Minimal CSS
- `tests/test_ui.py` — UI route tests
- `tests/test_batch.py` — Batch runner tests

### Relevant Documentation — YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [FastAPI Templates](https://fastapi.tiangolo.com/advanced/templates/) — Jinja2Templates setup, returning HTMLResponse
- [FastAPI Static Files](https://fastapi.tiangolo.com/tutorial/static-files/) — StaticFiles mount for CSS/JS
- [FastAPI Form Data](https://fastapi.tiangolo.com/tutorial/request-forms/) — Requires python-multipart
- [FastAPI BackgroundTasks](https://fastapi.tiangolo.com/tutorial/background-tasks/) — For fire-and-forget batch launch
- [HTMX Documentation](https://htmx.org/docs/) — hx-get, hx-post, hx-patch, hx-swap, hx-target, hx-trigger, hx-indicator
- [Jinja2 Template Inheritance](https://jinja.palletsprojects.com/en/3.1.x/templates/#template-inheritance) — block/extends pattern

### Patterns to Follow

**Router Registration** (from `src/main.py:67`):
```python
app.include_router(router)
```

**Route Pattern** (from `src/api/routes.py`):
```python
router = APIRouter(prefix="/api", tags=["runs"])

@router.get("/runs")
async def list_runs(request: Request, status: str | None = None, limit: int = 20) -> list[queries.Run]:
    db = request.app.state.db
    return await queries.get_runs(db, status=status, limit=limit)
```

**Database Access** (always via request.app.state.db):
```python
db = request.app.state.db
```

**Query Functions Available** (from `src/db/queries.py`):
- `create_run(db, RunCreate) → Run`
- `get_runs(db, status?, limit?) → list[Run]`
- `get_run_by_id(db, run_id) → Run | None`
- `complete_run(db, run_id, transcript) → Run`
- `fail_run(db, run_id, error_message) → Run`
- `record_pairing(db, a_name, b_name, run_id) → None`
- `get_recent_pairings(db, limit?) → list[tuple[str, str]]`
- `create_concept(db, ConceptCreate) → Concept`
- `get_concepts(db, status?, limit?) → list[Concept]`
- `get_concept_by_id(db, concept_id) → Concept | None`
- `get_concept_by_run_id(db, run_id) → Concept | None`
- `update_concept_status(db, concept_id, status) → Concept`
- `create_score(db, ScoreCreate) → Score`
- `get_score_by_concept_id(db, concept_id) → Score | None`
- `get_scores(db, limit?) → list[Score]`

**Error Handling** (from `src/engine/conversation.py`):
```python
class ConversationError(Exception):
    """Raised when the conversation runner encounters a non-recoverable error."""
```

**Logging Pattern**:
```python
import logging
logger = logging.getLogger(__name__)
logger.info("Descriptive message", extra={"key": "value"})
```

**Test Pattern** (from `tests/test_api.py`):
```python
async def test_health_endpoint(client) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
```

---

## IMPLEMENTATION PLAN

### Task 1: Add Dependencies

Add `jinja2` and `python-multipart` to `pyproject.toml` and run `uv sync`.

- **UPDATE**: `pyproject.toml` — add `"jinja2>=3.1.0"` and `"python-multipart>=0.0.20"` to `dependencies` list
- **VALIDATE**: `uv sync && uv run python -c "import jinja2; import multipart; print('OK')"`

### Task 2: Vendor HTMX and Create Static Assets

Download HTMX and create the minimal CSS file.

- **CREATE**: `src/static/htmx.min.js` — download HTMX 2.0.4 minified from unpkg CDN
- **CREATE**: `src/static/style.css` — minimal CSS for the UI. Keep it simple: a clean sans-serif font, max-width container, table styling, form styling, badge colors for status (pending/kept/discarded), transcript drawer styling. No CSS framework — just enough to be usable
- **VALIDATE**: `ls src/static/htmx.min.js src/static/style.css`

### Task 3: Create Base Template

Create the Jinja2 layout template that all pages extend.

- **CREATE**: `src/templates/base.html` — HTML5 layout with:
  - `<link>` to `/static/style.css`
  - `<script>` loading `/static/htmx.min.js`
  - Navigation: links to Batch Setup (`/ui/batch`) and Review (`/ui/review`)
  - `{% block title %}` and `{% block content %}` blocks
  - Simple header with "Medici Engine" branding
- **PATTERN**: Standard Jinja2 template inheritance
- **VALIDATE**: Template file exists and has valid HTML structure

### Task 4: Batch Data Layer

Add a `batches` table and query functions so the UI can track batch progress.

- **UPDATE**: `src/db/schema.py` — add `batches` table to `SCHEMA_SQL`:
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
  ```
  Status values: `running`, `completed`, `failed`
- **UPDATE**: `src/db/queries.py` — add models and queries:
  - `Batch` model: id (UUID), total_runs, completed_runs, failed_runs, status, created_at, completed_at
  - `BatchCreate` model: total_runs (int)
  - `_row_to_batch()` helper
  - `create_batch(db, BatchCreate) → Batch`
  - `get_batch_by_id(db, batch_id) → Batch | None`
  - `get_batches(db, limit=20) → list[Batch]`
  - `increment_batch_completed(db, batch_id) → Batch`
  - `increment_batch_failed(db, batch_id) → Batch`
  - `complete_batch(db, batch_id) → Batch` — sets status to completed/failed, sets completed_at
- **UPDATE**: `src/db/schema.py` — add `batch_id` column to `runs` table:
  ```sql
  ALTER TABLE runs ADD COLUMN batch_id TEXT REFERENCES batches(id);
  ```
  Since this is SQLite and ALTER TABLE ADD COLUMN is limited, the cleanest approach is to add `batch_id TEXT` to the original CREATE TABLE statement (the schema uses CREATE IF NOT EXISTS, so existing DBs need the column added). Add it as nullable: `batch_id TEXT REFERENCES batches(id)` — old runs will have NULL.
- **UPDATE**: `src/db/queries.py` — update `Run` model to include `batch_id: UUID | None = None`, update `RunCreate` to include `batch_id: UUID | None = None`, update `_row_to_run` to handle the new column, add `get_runs_by_batch_id(db, batch_id) → list[Run]`
- **GOTCHA**: SQLite has limited ALTER TABLE support. Since we use `CREATE TABLE IF NOT EXISTS`, just add the column directly to the CREATE statement. For existing databases, users will need to delete and recreate (acceptable for pre-v1.0). Add a comment in schema.py noting this.
- **VALIDATE**: `uv run pytest tests/test_db.py -v`

### Task 5: Batch Runner Service

Extract the conversation→synthesis→scoring pipeline from the CLI script into a reusable async service.

- **CREATE**: `src/batch/__init__.py` — empty module init with module docstring
- **CREATE**: `src/batch/models.py` — Pydantic models:
  ```python
  class BatchRequest(BaseModel):
      """Specification for a batch of conversation runs."""
      persona_pairs: list[tuple[str, str]] | None = None  # None = random
      shared_object_indices: list[int] | None = None  # None = random
      num_conversations: int = 1
      turns_per_agent: int = 5
  ```
- **CREATE**: `src/batch/runner.py` — `BatchRunner` class:
  - Constructor takes `db: aiosqlite.Connection`
  - `async def run_batch(self, request: BatchRequest, batch_id: UUID) → None`:
    - For each conversation in num_conversations:
      - Select personas (from pairs list or random via `get_persona_pair`)
      - Select shared object (from indices or random via `get_random_shared_object`)
      - Create run record with batch_id
      - Run conversation via `ConversationRunner`
      - Complete run, record pairing
      - Run synthesis via `Synthesizer`
      - Create concept
      - Run scoring via `Scorer`
      - Create score
      - Increment batch completed/failed counts
    - After all conversations: call `complete_batch`
    - Each individual conversation is wrapped in try/except — one failure doesn't abort the batch
  - Follows the exact same flow as `scripts/run_conversation.py` lines 362–468
- **PATTERN**: Mirror `scripts/run_conversation.py` flow exactly
- **IMPORTS**: From `src.engine.conversation`, `src.engine.models`, `src.synthesis.synthesizer`, `src.scoring.scorer`, `src.db.queries`, `src.personas.library`, `src.config`
- **GOTCHA**: This module sits at the API layer level — it orchestrates across engine, synthesis, and scoring. This is acceptable because the API layer is the top of the dependency hierarchy. Do NOT place it inside `src/engine/` or `src/synthesis/`
- **GOTCHA**: The `ConversationRunner`, `Synthesizer`, and `Scorer` each create their own OpenAI client internally. Do not try to share clients across the batch — instantiate fresh for each run
- **VALIDATE**: `uv run pytest tests/test_batch.py -v`

### Task 6: UI Routes — Batch Setup

Create the batch setup page and form submission endpoint.

- **CREATE**: `src/ui/__init__.py` — empty module init with module docstring
- **CREATE**: `src/ui/routes.py` — UI routes module with:
  ```python
  """
  UI routes for the Medici Engine.

  Serves HTML pages for batch setup and concept review using Jinja2
  templates with HTMX for interactive updates. This module belongs
  to the API layer and returns HTML responses, not JSON.
  """
  import logging
  from pathlib import Path
  from fastapi import APIRouter, Request, BackgroundTasks
  from fastapi.responses import HTMLResponse
  from fastapi.templating import Jinja2Templates

  logger = logging.getLogger(__name__)

  router = APIRouter(prefix="/ui", tags=["ui"])
  templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
  ```

- **Endpoints**:
  - `GET /ui/batch` — render batch setup form with persona list and shared object list
  - `POST /ui/batch` — accept form data, create batch record, launch `BatchRunner.run_batch()` as a background task, return redirect or success fragment
  - `GET /ui/batch/{batch_id}/status` — return batch progress fragment (for HTMX polling via `hx-trigger="every 3s"`)

- **CREATE**: `src/templates/batch.html` — extends base.html:
  - Dropdown/checkboxes for persona selection (or "Randomize" option)
  - Dropdown/checkboxes for shared object selection (or "Randomize" option)
  - Number input for turns per agent (default 5)
  - Number input for number of conversations (default 1)
  - Submit button
  - After submission: show batch progress area that polls `/ui/batch/{batch_id}/status`

- **CREATE**: `src/templates/fragments/batch_status.html` — partial template:
  - Shows completed/total count, failed count
  - Progress indicator (e.g. "3/5 completed, 1 failed")
  - When batch is done, show link to review page filtered by batch

- **IMPORTS**: `from src.personas.library import get_all_personas, get_all_shared_objects`; `from src.batch.runner import BatchRunner`; `from src.batch.models import BatchRequest`; `from src.db.queries import create_batch, BatchCreate, get_batch_by_id`
- **GOTCHA**: Use `BackgroundTasks` from FastAPI for batch execution. The batch runs asynchronously after the response is sent. Do NOT use `asyncio.create_task` — FastAPI's BackgroundTasks integrates with the ASGI lifecycle
- **GOTCHA**: `python-multipart` must be installed for `request.form()` to work
- **VALIDATE**: `uv run pytest tests/test_ui.py -v -k batch`

### Task 7: UI Routes — Concept Review

Create the review list page, detail page, and interactive fragments.

- **Endpoints**:
  - `GET /ui/review` — render concept list table with filtering/sorting
    - Query params: `status` (all/pending/kept/discarded), `sort` (score_desc/score_asc/date_desc/date_asc), `limit`
    - For each concept, join with its score to show overall score in the table
    - Overall score = average of (uniqueness + plausibility + compelling_factor) / 3
  - `GET /ui/review/rows` — return just the `<tbody>` fragment for HTMX swap (same query params)
  - `GET /ui/review/{concept_id}` — render concept detail page with scores and reasoning
  - `GET /ui/review/{concept_id}/transcript` — return transcript fragment (lazy loaded by HTMX)
  - `PATCH /ui/review/{concept_id}/status` — toggle concept status, return updated status badge fragment

- **UPDATE**: `src/db/queries.py` — add a query for concepts joined with scores for the review table:
  - `get_concepts_with_scores(db, status?, sort_by?, limit?) → list[ConceptWithScore]`
  - `ConceptWithScore` model: extends Concept fields + `uniqueness_score`, `plausibility_score`, `compelling_factor_score`, `overall_score` (all `float | None`)
  - This is a JOIN query: `SELECT c.*, s.uniqueness_score, s.plausibility_score, s.compelling_factor_score FROM concepts c LEFT JOIN scores s ON s.concept_id = c.id`
  - Support sorting by `overall_score` (computed as average of three scores) or `created_at`

- **CREATE**: `src/templates/review.html` — extends base.html:
  - Filter controls: status dropdown (all/pending/kept/discarded) with `hx-get="/ui/review/rows"` `hx-target="#concept-table-body"` `hx-include="[name='sort']"`
  - Sort controls: dropdown for sort order, same HTMX pattern
  - Table: Title | Premise (truncated) | Score | Status | Date
  - Each row links to `/ui/review/{concept_id}`

- **CREATE**: `src/templates/fragments/concept_rows.html` — partial: just the `<tbody>` rows
  - Each row: title, premise[:100]+"...", overall score (formatted to 1 decimal), status badge, created_at date
  - Row is clickable → navigates to detail page

- **CREATE**: `src/templates/detail.html` — extends base.html:
  - Full concept: title, premise, originality
  - Score cards: one card per axis showing score/10 + full reasoning text
  - Overall score prominent at top
  - Keep/Discard buttons using `hx-patch="/ui/review/{concept_id}/status"` with `hx-vals='{"status": "kept"}'` or `"discarded"`, `hx-target="#status-badge"`, `hx-swap="outerHTML"`
  - Transcript drawer: a collapsible section, loads content lazily via `hx-get="/ui/review/{concept_id}/transcript"` `hx-trigger="click once"` `hx-swap="innerHTML"`
  - Persona info: persona_a_name, persona_b_name, shared_object_text (from the run record)
  - Back link to review list

- **CREATE**: `src/templates/fragments/transcript.html` — partial:
  - Renders the full transcript turn by turn
  - Each turn shows: turn number, persona name, content
  - Read-only, no interactions

- **CREATE**: `src/templates/fragments/concept_status.html` — partial:
  - Just the status badge element (pending/kept/discarded with appropriate styling)
  - Returned after PATCH to swap in the updated status

- **GOTCHA**: The PATCH endpoint for status toggle needs to read the request body. Use `request.form()` for HTMX form submissions or parse `hx-vals` JSON. HTMX sends `hx-vals` as form-encoded by default
- **GOTCHA**: When sorting by score, concepts without scores (no synthesis/scoring yet) should appear last
- **VALIDATE**: `uv run pytest tests/test_ui.py -v -k review`

### Task 8: Wire Up App — Static Files, Templates, Router

Register the UI router and static file mount in the FastAPI app.

- **UPDATE**: `src/main.py`:
  - Add `from fastapi.staticfiles import StaticFiles`
  - Add `from src.ui.routes import router as ui_router`
  - Mount static files: `app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent / "static")), name="static")`
  - Include UI router: `app.include_router(ui_router)`
  - Add root redirect: `GET /` redirects to `/ui/review` (the primary surface)
- **GOTCHA**: The `StaticFiles` mount must come AFTER router includes — or use a specific path prefix so it doesn't shadow routes. Mount it at `/static` which is distinct from `/ui` and `/api`
- **GOTCHA**: Static files directory path must be absolute or relative to CWD. Use `Path(__file__).resolve().parent / "static"` for reliability
- **VALIDATE**: `uv run uvicorn src.main:app --host 0.0.0.0 --port 8080` and verify `/static/style.css` and `/static/htmx.min.js` load in browser, `/ui/batch` and `/ui/review` render pages, `/` redirects to `/ui/review`

### Task 9: Tests — UI Routes

Write tests for all UI endpoints.

- **CREATE**: `tests/test_ui.py`:
  - Test batch page renders (`GET /ui/batch` returns 200 with HTML)
  - Test batch form submission creates batch and runs (`POST /ui/batch` with form data)
  - Test batch status endpoint returns progress (`GET /ui/batch/{id}/status`)
  - Test review page renders with empty database (`GET /ui/review` returns 200)
  - Test review page renders with seeded data (concepts + scores)
  - Test review rows fragment returns partial HTML (`GET /ui/review/rows`)
  - Test concept detail page renders (`GET /ui/review/{concept_id}`)
  - Test transcript lazy load (`GET /ui/review/{concept_id}/transcript`)
  - Test status toggle (`PATCH /ui/review/{concept_id}/status`)
  - Test filtering by status works
  - Test sorting by score works
- **PATTERN**: Follow `tests/test_api.py` — use `client` and `db` fixtures from conftest
- **GOTCHA**: UI routes return HTML, not JSON. Assert `response.status_code == 200` and check for expected content strings in `response.text` (e.g., concept title appears in HTML)
- **GOTCHA**: For the batch POST test, mock `ConversationRunner`, `Synthesizer`, and `Scorer` to avoid real LLM calls. The batch runner must be tested with mocked inference
- **VALIDATE**: `uv run pytest tests/test_ui.py -v`

### Task 10: Tests — Batch Runner

Write tests for the batch orchestration service.

- **CREATE**: `tests/test_batch.py`:
  - Test single conversation batch completes successfully (mock all LLM calls)
  - Test multi-conversation batch tracks progress correctly
  - Test batch continues when one conversation fails
  - Test batch status updates (completed_runs, failed_runs incremented correctly)
  - Test batch with specific persona pairs uses the specified pairs
  - Test batch with random personas calls get_persona_pair
  - Test batch with specific shared objects uses the specified objects
  - Test batch with random shared objects calls get_random_shared_object
  - Test batch without OpenAI key skips synthesis and scoring (logs warning)
- **PATTERN**: Mock `ConversationRunner.run()`, `Synthesizer.synthesize()`, `Scorer.score()` using `unittest.mock.AsyncMock`
- **VALIDATE**: `uv run pytest tests/test_batch.py -v`

### Task 11: Update Existing Tests

Ensure existing tests still pass after schema and query changes.

- **UPDATE**: `tests/test_db.py` — add tests for new batch queries (create_batch, get_batch_by_id, increment_batch_completed, etc.)
- **UPDATE**: `tests/conftest.py` — if any fixture changes are needed for the new batch_id column on runs
- **VALIDATE**: `uv run pytest tests/ -v`

### Task 12: Lint and Format

Run ruff to ensure all new code passes linting and formatting.

- **VALIDATE**: `uv run ruff check . && uv run ruff format --check .`
- If issues found, fix them: `uv run ruff check --fix . && uv run ruff format .`

---

## TESTING STRATEGY

### Unit Tests

- **Batch runner** (`tests/test_batch.py`): Test orchestration logic with all LLM calls mocked. Verify run creation, synthesis, scoring, and batch progress tracking. Test error handling — one failed conversation should not abort the batch.
- **Batch queries** (in `tests/test_db.py`): Test CRUD for batches table, increment operations, completion logic.

### Integration Tests

- **UI routes** (`tests/test_ui.py`): Test all endpoints return correct status codes and contain expected HTML content. Use the existing `client` fixture with `ASGITransport`. Test form submissions, HTMX fragment endpoints, and status toggle.

### Edge Cases

- Batch with 0 conversations (should reject or no-op)
- Concept with no scores yet (review table should handle gracefully)
- Run with no transcript (detail page transcript section should show "No transcript available")
- All personas paired recently (selection should still work — falls back to full library)
- Missing OpenAI API key (synthesis and scoring should skip with warning, not crash)
- Batch where all conversations fail (batch status should be "failed")

---

## VALIDATION COMMANDS

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
# Run all tests
uv run pytest tests/ -v

# Run only new tests
uv run pytest tests/test_ui.py tests/test_batch.py -v

# Run with coverage
uv run pytest tests/ -v --tb=short
```

### Level 3: Integration Tests

```bash
# Run API and UI tests specifically
uv run pytest tests/test_api.py tests/test_ui.py -v
```

### Level 4: Manual Validation

1. Start the server: `uv run uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload`
2. Open `http://localhost:8080/` — should redirect to `/ui/review`
3. Navigate to `/ui/batch` — should show batch setup form with persona/object dropdowns
4. Verify `/static/style.css` and `/static/htmx.min.js` load (check browser dev tools network tab)
5. If vLLM is running and OpenAI key is set: submit a single-conversation batch and verify it appears in the review table after completion
6. On the review page: test status filter dropdown, score sort dropdown
7. Click a concept row → detail page shows scores with reasoning
8. Click transcript drawer → loads transcript via HTMX
9. Click Keep/Discard → status updates without page reload

---

## ACCEPTANCE CRITERIA

- [ ] Batch setup page renders with all personas and shared objects listed
- [ ] Form submission creates a batch and launches conversations in the background
- [ ] Batch progress is visible via polling (completed/total counter)
- [ ] Review page shows concept list with title, premise snippet, overall score, status, date
- [ ] Review table is filterable by status (all/pending/kept/discarded)
- [ ] Review table is sortable by score and date
- [ ] Concept detail page shows full concept, per-axis scores with reasoning
- [ ] Transcript drawer loads lazily and displays full conversation
- [ ] Keep/Discard toggle updates status without page reload
- [ ] All validation commands pass with zero errors
- [ ] No regressions in existing tests (test_api, test_db, test_engine, test_synthesis, test_scoring, test_boundaries, test_config, test_personas)
- [ ] Code follows project conventions: type hints, docstrings, logging, async patterns

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully:
  - [ ] Level 1: ruff check, ruff format --check
  - [ ] Level 2: pytest (all tests)
  - [ ] Level 3: pytest (API + UI tests)
  - [ ] Level 4: Manual validation
- [ ] Full test suite passes
- [ ] No linting errors
- [ ] No formatting errors
- [ ] All acceptance criteria met
- [ ] Code reviewed for quality and maintainability

---

## EXECUTION STRATEGY

**Recommended approach**: Milestones

**Rationale**: Feature 5 has 12 tasks with natural phase boundaries. The data layer must exist before the batch runner, which must exist before the UI routes. Tasks within each phase are tightly coupled (e.g., templates and routes develop together), but phases are loosely coupled and each phase produces independently testable artifacts. Single-pass risks cascading failures across the schema change, new service, and template layer. Task-by-task is unnecessarily granular since templates and routes must co-develop.

### Milestones

Each milestone has its own detailed plan file with full context, implementation details, and acceptance criteria.

**Milestone 1: Foundation** (Tasks 1–3) → `feature5-milestone1-foundation.md`
- Add dependencies, vendor HTMX, create base template and static assets
- **Validation checkpoint**: `uv sync` succeeds, static files exist, base template has valid HTML structure

**Milestone 2: Data Layer** (Task 4) → `feature5-milestone2-data-layer.md`
- Add batches table, batch queries, batch_id on runs, concepts-with-scores join query
- **Validation checkpoint**: `uv run pytest tests/test_db.py -v` passes with new batch query tests

**Milestone 3: Batch Runner + Batch Setup UI** (Tasks 5–6) → `feature5-milestone3-batch-runner.md`
- Extract pipeline logic into BatchRunner service, create batch setup UI routes and templates
- **Validation checkpoint**: `uv run pytest tests/test_batch.py -v` passes, `/ui/batch` renders in browser

**Milestone 4: Review UI** (Tasks 7–8) → `feature5-milestone4-review-ui.md`
- Create review list, detail page, transcript drawer, status toggle, wire up app
- **Validation checkpoint**: `uv run pytest tests/test_ui.py -v` passes, all pages render, HTMX interactions work

**Milestone 5: Testing & Validation** (Tasks 9–12) → `feature5-milestone5-testing-validation.md`
- Write comprehensive tests, update existing tests, lint/format
- **Validation checkpoint**: `uv run pytest tests/ -v` all green, `uv run ruff check . && uv run ruff format --check .` clean

---

## NOTES

- **Architectural placement**: `src/ui/` and `src/batch/` both sit at the API layer level in the dependency hierarchy. They orchestrate across lower layers but do not violate the downward-only dependency rule.
- **No SPA**: The CLAUDE.md and DevPlan emphasize simplicity. Jinja2 + HTMX delivers the required interactivity without a frontend build toolchain. The entire UI is ~6 template files and one CSS file.
- **Background tasks**: FastAPI's `BackgroundTasks` is the right choice for batch execution. It runs after the response is sent within the same ASGI process. For the Medici Engine's scale (single user, local inference), this is sufficient. No task queue (Celery, etc.) is needed.
- **HTMX polling**: The batch status endpoint uses `hx-trigger="every 3s"` for progress polling. HTMX stops polling when the element is removed from the DOM or when the response includes `HX-Trigger: stop` header. Include a stop condition when the batch is complete.
- **Score sorting**: Computing overall_score as `(uniqueness + plausibility + compelling_factor) / 3` is done in the SQL query for efficiency. Concepts without scores get NULL and sort last.
- **Existing API preserved**: The JSON API at `/api/*` remains untouched. The UI routes at `/ui/*` are a separate parallel interface. Both use the same query layer.
