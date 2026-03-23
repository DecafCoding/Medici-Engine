# Feature 5 — Milestone 3: Batch Runner + Batch Setup UI

**Parent plan**: `feature5-review-ui-batch-setup.md`
**Tasks**: 5–6
**Goal**: Extract pipeline logic into a reusable BatchRunner service and create the batch setup UI page

---

## Feature Context

The current CLI script (`scripts/run_conversation.py`) runs conversations one at a time. This milestone extracts that conversation→synthesis→scoring pipeline into a `BatchRunner` service that can execute multiple conversations in sequence, tracking progress in the `batches` table. It also creates the batch setup UI page where users configure and launch batches from the browser.

## User Story

As a Medici Engine operator
I want to configure and launch conversation batches from a browser, then browse and review the scored concepts
So that I can run the system at scale and make keep/discard decisions faster than via CLI output

---

## CONTEXT REFERENCES

### Relevant Codebase Files — READ BEFORE IMPLEMENTING

- `scripts/run_conversation.py` (full file) — Why: The batch runner extracts this exact pipeline. Lines 362–468 are the core flow: select personas → create run → run conversation → complete run → record pairing → synthesize → create concept → score → create score. Mirror this flow exactly.
- `src/engine/conversation.py` (lines 36–55, 56–142) — Why: `ConversationRunner.__init__()` and `ConversationRunner.run(request)` interface. Instantiate per batch, call `run()` per conversation.
- `src/engine/models.py` (lines 1–40) — Why: `ConversationConfig` and `ConversationRequest` — how to build a conversation request.
- `src/synthesis/synthesizer.py` (lines 70–155) — Why: `Synthesizer.__init__()` and `Synthesizer.synthesize(transcript, persona_a_name, persona_b_name, shared_object_text)` interface.
- `src/scoring/scorer.py` (lines 69–148) — Why: `Scorer.__init__()` and `Scorer.score(title, premise, originality)` interface.
- `src/db/queries.py` (full file) — Why: All query functions used by the batch runner: `create_run`, `complete_run`, `fail_run`, `record_pairing`, `get_recent_pairings`, `create_concept`, `create_score`, `create_batch`, `increment_batch_completed`, `increment_batch_failed`, `complete_batch` (last four added in Milestone 2).
- `src/personas/library.py` (lines 835–912) — Why: `get_persona_by_name`, `get_persona_pair`, `get_all_shared_objects`, `get_random_shared_object`.
- `src/config.py` (full file) — Why: Settings for conversation temperature, repetition penalty, max tokens, default turns, openai_api_key.
- `src/api/routes.py` (full file) — Why: Route pattern to follow for UI routes.
- `tests/conftest.py` (full file) — Why: Test fixtures — `db`, `client`, mock factories.
- `CLAUDE.md` — Why: Architectural boundaries. The batch module sits at the API layer level (top of hierarchy) — it orchestrates across engine, synthesis, and scoring. This is acceptable.

### Relevant Documentation — READ BEFORE IMPLEMENTING

- [FastAPI BackgroundTasks](https://fastapi.tiangolo.com/tutorial/background-tasks/) — For fire-and-forget batch launch. The batch POST endpoint adds `BatchRunner.run_batch()` as a background task.
- [FastAPI Form Data](https://fastapi.tiangolo.com/tutorial/request-forms/) — `python-multipart` required for `request.form()`.
- [FastAPI Templates](https://fastapi.tiangolo.com/advanced/templates/) — `Jinja2Templates`, `templates.TemplateResponse`.

### New Files to Create

- `src/batch/__init__.py` — Batch module init
- `src/batch/models.py` — BatchRequest model
- `src/batch/runner.py` — BatchRunner class
- `src/ui/__init__.py` — UI module init
- `src/ui/routes.py` — UI routes (batch endpoints only in this milestone; review endpoints in Milestone 4)
- `src/templates/batch.html` — Batch setup page template
- `src/templates/fragments/batch_status.html` — Batch progress fragment
- `tests/test_batch.py` — Batch runner tests

### Patterns to Follow

**Pipeline Flow** (from `scripts/run_conversation.py:362–468`):
```python
# 1. Select personas
persona_a, persona_b = get_persona_pair()
# 2. Select shared object
shared_object = get_random_shared_object()
# 3. Create run record
run_record = await create_run(db, RunCreate(...))
# 4. Build config and request
config = ConversationConfig(turns_per_agent=args.turns, ...)
request = ConversationRequest(persona_a=persona_a, persona_b=persona_b, shared_object=shared_object, config=config)
# 5. Run conversation
runner = ConversationRunner()
turns = await runner.run(request)
# 6. Save transcript and pairing
await complete_run(db, run_record.id, turns)
await record_pairing(db, persona_a.name, persona_b.name, run_record.id)
# 7. Synthesize
synthesizer = Synthesizer()
extraction = await synthesizer.synthesize(transcript=turns, ...)
concept = await create_concept(db, ConceptCreate(...))
# 8. Score
scorer = Scorer()
result = await scorer.score(title=concept.title, premise=concept.premise, originality=concept.originality)
await create_score(db, ScoreCreate(...))
```

**Error Handling** (from `scripts/run_conversation.py`):
- Conversation errors: catch `ConversationError`, call `fail_run()`, continue to next conversation
- Synthesis errors: catch `SynthesisError`, log warning, skip scoring for this run, continue
- Scoring errors: catch `ScoringError`, log warning, continue
- Missing OpenAI key: skip synthesis and scoring entirely (log warning)

---

## IMPLEMENTATION PLAN

### Task 5: Batch Runner Service

Extract the conversation→synthesis→scoring pipeline into a reusable async service.

- **CREATE**: `src/batch/__init__.py`:
  ```python
  """
  Batch orchestration for the Medici Engine.

  Manages execution of multiple conversation runs as a batch,
  coordinating the full pipeline: conversation → synthesis → scoring.
  This module belongs to the API layer and orchestrates across
  Engine, Synthesis, and Scoring layers.
  """
  ```

- **CREATE**: `src/batch/models.py`:
  ```python
  """
  Data models for batch orchestration.

  Defines the request structure for configuring a batch of
  conversation runs. This module belongs to the API layer.
  """
  from pydantic import BaseModel, Field

  class BatchRequest(BaseModel):
      """Specification for a batch of conversation runs."""
      persona_pairs: list[tuple[str, str]] | None = Field(
          default=None,
          description="List of (persona_a_name, persona_b_name) tuples. None = random selection.",
      )
      shared_object_indices: list[int] | None = Field(
          default=None,
          description="List of shared object indices to use. None = random selection.",
      )
      num_conversations: int = Field(default=1, description="Number of conversations to run")
      turns_per_agent: int = Field(default=5, description="Turns per agent per conversation")
  ```

- **CREATE**: `src/batch/runner.py` — `BatchRunner` class:
  - Module docstring describing its role as the batch orchestration service
  - Constructor: `def __init__(self, db: aiosqlite.Connection) -> None`
  - Main method: `async def run_batch(self, request: BatchRequest, batch_id: UUID) -> None`
    - Loop `request.num_conversations` times
    - For each conversation (wrapped in try/except):
      1. Select persona pair — if `request.persona_pairs` is not None, cycle through the list (index % len); otherwise call `get_persona_pair(await get_recent_pairings(db))`
      2. Resolve personas via `get_persona_by_name()` (if from pairs list) or use returned Persona objects
      3. Select shared object — if `request.shared_object_indices` is not None, cycle through; otherwise call `get_random_shared_object()`
      4. Create run record via `create_run(db, RunCreate(batch_id=batch_id, ...))`
      5. Build `ConversationConfig` and `ConversationRequest`
      6. Instantiate `ConversationRunner()` and call `runner.run(request)`
      7. Call `complete_run(db, run_id, turns)` and `record_pairing(...)`
      8. If `settings.openai_api_key`: instantiate `Synthesizer()` and call `synthesize()`, create concept
      9. If synthesis succeeded and `settings.openai_api_key`: instantiate `Scorer()` and call `score()`, create score
      10. Call `increment_batch_completed(db, batch_id)`
    - On any exception per conversation: log error, call `fail_run(db, run_id, str(e))`, call `increment_batch_failed(db, batch_id)`, continue to next
    - After loop: call `complete_batch(db, batch_id)`

  - Custom exception: `class BatchError(Exception): """Raised when batch orchestration fails."""`

- **IMPORTS**: `ConversationRunner`, `ConversationError` from `src.engine.conversation`; `ConversationConfig`, `ConversationRequest` from `src.engine.models`; `Synthesizer`, `SynthesisError` from `src.synthesis.synthesizer`; `Scorer`, `ScoringError` from `src.scoring.scorer`; `RunCreate`, `ConceptCreate`, `ScoreCreate`, `create_run`, `complete_run`, `fail_run`, `record_pairing`, `get_recent_pairings`, `create_concept`, `create_score`, `increment_batch_completed`, `increment_batch_failed`, `complete_batch` from `src.db.queries`; `get_persona_by_name`, `get_persona_pair`, `get_all_shared_objects`, `get_random_shared_object` from `src.personas.library`; `settings` from `src.config`

- **GOTCHA**: Instantiate `ConversationRunner`, `Synthesizer`, and `Scorer` fresh — they create internal OpenAI clients. Do not try to share across conversations.
- **GOTCHA**: `get_persona_pair` returns `tuple[Persona, Persona]` directly. But if using `persona_pairs` from the request, those are `tuple[str, str]` (names) — must resolve via `get_persona_by_name()`.
- **GOTCHA**: If `get_persona_by_name()` returns None for a specified name, log an error and skip that conversation (increment failed).

- **VALIDATE**: `uv run ruff check src/batch/ && uv run ruff format --check src/batch/`

### Task 6: UI Routes — Batch Setup

Create the batch setup page and form submission endpoint.

- **CREATE**: `src/ui/__init__.py`:
  ```python
  """
  Web UI for the Medici Engine.

  Serves HTML pages for batch setup and concept review using Jinja2
  templates with HTMX for interactive updates. This module belongs
  to the API layer and returns HTML responses, not JSON.
  """
  ```

- **CREATE**: `src/ui/routes.py` — UI routes:
  ```python
  """
  UI routes for the Medici Engine.

  Provides HTML endpoints for batch configuration, batch progress
  monitoring, and concept review. Uses Jinja2 templates with HTMX
  for interactive updates without a frontend build toolchain.
  This module belongs to the API layer.
  """
  ```
  - Set up: `router = APIRouter(prefix="/ui", tags=["ui"])` and `templates = Jinja2Templates(directory=...)`
  - Template directory: `str(Path(__file__).resolve().parent.parent / "templates")`

  Batch endpoints:
  - `GET /ui/batch` — render batch setup form:
    - Pass `get_all_personas()` and `get_all_shared_objects()` to template context
    - Return `templates.TemplateResponse("batch.html", {"request": request, "personas": personas, "shared_objects": shared_objects})`
  - `POST /ui/batch` — handle form submission:
    - Parse form data: persona selections, shared object selections, num_conversations, turns_per_agent
    - Create batch record via `create_batch(db, BatchCreate(total_runs=num_conversations))`
    - Build `BatchRequest` from form data
    - Add `BatchRunner(db).run_batch(request, batch.id)` as a background task via `background_tasks.add_task()`
    - Return a response with the batch progress fragment (or redirect to a batch status page)
  - `GET /ui/batch/{batch_id}/status` — return batch progress fragment:
    - Fetch batch via `get_batch_by_id(db, batch_id)`
    - Return `templates.TemplateResponse("fragments/batch_status.html", {"request": request, "batch": batch})`
    - When batch is complete, include header or attribute to stop HTMX polling

- **CREATE**: `src/templates/batch.html` — extends `base.html`:
  - Form with `hx-post="/ui/batch"` `hx-target="#batch-result"` `hx-swap="innerHTML"`:
    - Persona A dropdown: `<select name="persona_a">` with `<option value="">Random</option>` + all persona names/titles
    - Persona B dropdown: same pattern
    - Shared object dropdown: `<select name="shared_object">` with `<option value="">Random</option>` + objects listed by index and truncated text
    - Turns per agent: `<input type="number" name="turns_per_agent" value="5" min="1" max="20">`
    - Number of conversations: `<input type="number" name="num_conversations" value="1" min="1" max="50">`
    - Submit button: "Launch Batch"
  - Result area: `<div id="batch-result"></div>` — receives the batch status fragment after submission

- **CREATE**: `src/templates/fragments/batch_status.html` — partial template:
  - Shows: "Batch {batch.id}: {batch.completed_runs}/{batch.total_runs} completed, {batch.failed_runs} failed"
  - If `batch.status == "running"`: include `hx-get="/ui/batch/{{ batch.id }}/status"` `hx-trigger="every 3s"` `hx-swap="outerHTML"` for auto-polling
  - If `batch.status` in `("completed", "failed")`: show final status, remove polling trigger, show link to review page

- **GOTCHA**: `BackgroundTasks` from FastAPI is the correct way to launch the batch. Import from `fastapi` directly. The background task function must be a coroutine (async def) — `run_batch` is async, so this works.
- **GOTCHA**: The `request` object must always be included in the template context dict (Jinja2Templates requires it).
- **GOTCHA**: Form data values are strings. Parse `num_conversations` and `turns_per_agent` as int. Handle empty string for persona/shared object selections (means "random").

- **VALIDATE**: `uv run ruff check src/ui/ && uv run ruff format --check src/ui/`

### Task 6b: Batch Runner Tests

Write tests for the batch runner service.

- **CREATE**: `tests/test_batch.py`:
  - Mock `ConversationRunner.run()` to return a fixed transcript (use `test_transcript` fixture pattern from conftest)
  - Mock `Synthesizer.synthesize()` to return a fixed `ConceptExtraction` (use `test_concept_extraction` fixture pattern)
  - Mock `Scorer.score()` to return a fixed `ConceptScoring` (use `test_concept_scoring` fixture pattern)
  - Use `unittest.mock.patch` as async context managers

  Tests:
  - `test_single_conversation_batch` — batch with 1 conversation completes, creates run + concept + score, batch status = completed
  - `test_multi_conversation_batch` — batch with 3 conversations, verify all 3 runs created, batch.completed_runs == 3
  - `test_batch_continues_on_conversation_failure` — mock ConversationRunner to raise ConversationError on 2nd call, verify batch still completes 3rd conversation, batch has 1 failed + 2 completed
  - `test_batch_with_specified_personas` — provide persona_pairs, verify those names are used in created runs
  - `test_batch_with_random_personas` — no persona_pairs, mock get_persona_pair, verify it's called
  - `test_batch_skips_synthesis_without_api_key` — mock `settings.openai_api_key` to empty string, verify no Synthesizer calls, no concepts created, batch still completes
  - `test_batch_handles_synthesis_failure` — mock Synthesizer to raise SynthesisError, verify scoring is skipped but run is still completed, batch increments completed (not failed)
  - `test_batch_handles_scoring_failure` — mock Scorer to raise ScoringError, verify concept is still created, batch increments completed

- **PATTERN**: Use `unittest.mock.AsyncMock` for mocking async methods. Use `@patch` decorators or `with patch(...)` context managers.
- **VALIDATE**: `uv run pytest tests/test_batch.py -v`

---

## VALIDATION CHECKPOINT

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest tests/test_batch.py tests/test_db.py -v
```

**Expected**: Linting passes, batch runner tests pass, DB tests still pass.

```bash
uv run pytest tests/ -v
```

**Expected**: Full test suite passes (zero regressions).

---

## ACCEPTANCE CRITERIA (Milestone 3)

- [ ] `src/batch/__init__.py` exists with module docstring
- [ ] `src/batch/models.py` defines `BatchRequest` with all fields
- [ ] `src/batch/runner.py` implements `BatchRunner` with full pipeline (conversation → synthesis → scoring)
- [ ] `BatchRunner` handles individual conversation failures without aborting the batch
- [ ] `BatchRunner` skips synthesis/scoring when OpenAI key is missing
- [ ] `src/ui/__init__.py` exists with module docstring
- [ ] `src/ui/routes.py` implements `GET /ui/batch`, `POST /ui/batch`, `GET /ui/batch/{batch_id}/status`
- [ ] `src/templates/batch.html` renders batch setup form with persona/object dropdowns
- [ ] `src/templates/fragments/batch_status.html` renders progress with HTMX polling
- [ ] `tests/test_batch.py` covers success, failure, partial failure, missing API key scenarios
- [ ] All existing tests still pass (zero regressions)
- [ ] Ruff check and format pass
