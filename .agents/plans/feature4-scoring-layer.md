# Feature 4: Scoring Layer

The following plan should be complete, but validate documentation and codebase patterns before implementing.

Pay special attention to naming of existing utils, types, and models. Import from the right files.

## Feature Description

Add a scoring layer that evaluates concepts extracted by the synthesizer. A higher-capability model (OpenAI o3) scores each concept across domain-specific axes — uniqueness, scientific plausibility, and compelling factor — with written reasoning for each score. The scoring layer runs once per concept (not per turn), so cost scales linearly with run count. Scores and reasoning are persisted in the database and exposed via the API, enabling the human reviewer to make faster, better-informed keep/discard decisions.

## User Story

As a human reviewer of Medici Engine output
I want each concept scored across multiple axes with written reasoning
So that I can make faster, better-informed keep/discard decisions without reading the full transcript

## Problem Statement

After Feature 3, the system extracts structured concepts from conversation transcripts, but the reviewer has no evaluative signal beyond the raw concept text. With many concepts to review, there is no way to prioritize or quickly assess quality. The reviewer must read every concept equally, which doesn't scale.

## Solution Statement

Introduce a `src/scoring/` module that takes a `ConceptExtraction` (title, premise, originality) and sends it to the OpenAI o3 model with a structured output prompt requesting scores (0.0-10.0) and reasoning across three axes: uniqueness, scientific plausibility, and compelling factor. Results are persisted in a `scores` table linked to concepts and exposed via API endpoints. The CLI runner is updated to invoke scoring after synthesis.

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Medium
**Primary Systems Affected**: `src/scoring/` (new), `src/db/`, `src/api/`, `scripts/run_conversation.py`
**Dependencies**: OpenAI API (o3 model), existing synthesis output

---

## CONTEXT REFERENCES

### Relevant Codebase Files — READ BEFORE IMPLEMENTING

- `src/synthesis/synthesizer.py` (full file) — Why: The scoring module mirrors this pattern exactly — same OpenAI client setup, same structured output via `beta.chat.completions.parse`, same error hierarchy. This is the primary pattern to follow.
- `src/synthesis/models.py` (full file) — Why: Shows how to define Pydantic models used as `response_format` for OpenAI structured output. The scoring models follow this pattern.
- `src/db/queries.py` (full file) — Why: All new score queries must follow the existing patterns — `_row_to_*` helpers, typed models, parameterized SQL, `uuid4()` IDs. The `Concept` model and concept queries (lines 68-346) are the closest reference.
- `src/db/schema.py` (full file) — Why: The new `scores` table must be added here following the same DDL pattern — TEXT PRIMARY KEY, foreign keys, indexes, default timestamps.
- `src/api/routes.py` (full file) — Why: New score endpoints follow the same pattern — router prefix, `request.app.state.db` access, typed return values.
- `scripts/run_conversation.py` (lines 108-170) — Why: The `_run_synthesis` function is the pattern for `_run_scoring` — same try/except structure, same graceful failure with retry instructions.
- `src/config.py` (lines 48-52) — Why: `scoring_model` setting already exists (default `o3`). No config changes needed.
- `tests/test_synthesis.py` (full file) — Why: Scoring tests mirror these exactly — mock `beta.chat.completions.parse`, test success/refusal/connection error.
- `tests/conftest.py` (full file) — Why: New fixtures for scoring follow the same patterns as synthesis fixtures.
- `tests/test_boundaries.py` (full file) — Why: Must add boundary tests for the scoring module (uses remote API, no vLLM, no engine imports).
- `CLAUDE.md` — Why: Architectural boundaries, layer dependency rules, documentation requirements.

### New Files to Create

- `src/scoring/__init__.py` — Package init for scoring module
- `src/scoring/models.py` — Pydantic models for scoring structured output (`AxisScore`, `ConceptScoring`)
- `src/scoring/scorer.py` — `Scorer` class with OpenAI o3 integration
- `tests/test_scoring.py` — Unit tests for scorer module

### Files to Modify

- `src/db/schema.py` — Add `scores` table DDL
- `src/db/queries.py` — Add `Score` model, `ScoreCreate` model, score CRUD queries
- `src/api/routes.py` — Add score-related API endpoints
- `scripts/run_conversation.py` — Add `_run_scoring` step after synthesis
- `tests/conftest.py` — Add scoring-related fixtures
- `tests/test_boundaries.py` — Add scoring boundary tests
- `tests/test_db.py` — Add score query tests
- `tests/test_api.py` — Add score endpoint tests

### Patterns to Follow

**OpenAI Structured Output Pattern** (from `src/synthesis/synthesizer.py`):
```python
response = await self._client.beta.chat.completions.parse(
    model=settings.scoring_model,
    messages=messages,
    response_format=ConceptScoring,  # Pydantic model
    temperature=0.3,  # Lower than synthesis — scoring should be more deterministic
)
result = response.choices[0].message.parsed
if result is None:
    refusal = response.choices[0].message.refusal
    raise ScoringError(f"Model refused to score concept: {refusal}")
```

**Client Initialization Pattern** (from `src/synthesis/synthesizer.py`):
```python
self._client = AsyncOpenAI(
    api_key=settings.openai_api_key,
    timeout=httpx.Timeout(60.0, connect=5.0),
    max_retries=3,
)
```

**Error Hierarchy Pattern** (from `src/synthesis/synthesizer.py`):
```python
class ScoringError(Exception):
    """Raised when scoring encounters a non-recoverable error."""

class EvaluationError(ScoringError):
    """Raised when the OpenAI API fails to score."""
```

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
- Module: `scorer.py` (noun, like `synthesizer.py`)
- Class: `Scorer` (like `Synthesizer`)
- Method: `score()` (like `synthesize()`)
- Models: `AxisScore`, `ConceptScoring` (PascalCase, descriptive)
- Errors: `ScoringError`, `EvaluationError` (like `SynthesisError`, `ExtractionError`)

**Logging Pattern:**
```python
logger = logging.getLogger(__name__)
logger.info("Scoring concept", extra={"concept_title": title})
```

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

### Task 4: Build the scorer module

Create the `Scorer` class that sends concepts to o3 for evaluation.

- **CREATE**: `src/scoring/scorer.py`
- **MIRROR**: `src/synthesis/synthesizer.py` — same class structure, client init, error handling, message building
- **IMPLEMENT**:
  - Module docstring explaining the scoring layer's role
  - `SCORING_PROMPT` constant — system prompt instructing o3 to evaluate across three axes with reasoning. The prompt must:
    - Establish o3 as an evaluator of novel creative concepts
    - Define each axis clearly: uniqueness (has this been done before?), scientific plausibility (could the science work, even speculatively?), compelling factor (would someone want to read this?)
    - Instruct scoring on 0.0-10.0 scale
    - Require reasoning that explains the score — not just a number
    - Instruct that reasoning should help a human reviewer make a faster decision
  - `ScoringError(Exception)` and `EvaluationError(ScoringError)` — error hierarchy
  - `Scorer` class:
    - `__init__`: create `AsyncOpenAI` client with `settings.openai_api_key`
    - `async def score(self, title: str, premise: str, originality: str) -> ConceptScoring`: main entry point
    - `def _build_messages(self, title, premise, originality) -> list[dict[str, str]]`: build system + user messages
  - Use `settings.scoring_model` (already configured as `o3`)
  - Temperature: `0.3` — scoring should be more deterministic than synthesis
- **IMPORTS**: `logging`, `httpx`, `openai` (APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI), `src.config.settings`, `src.scoring.models.ConceptScoring`
- **GOTCHA**: The scoring layer must NOT import from `src.engine` or reference `vllm_base_url`. It uses the remote OpenAI API only.
- **VALIDATE**: `uv run ruff check src/scoring/ && uv run ruff format --check src/scoring/`

### Task 5: Add score API endpoints

Expose scores through the REST API.

- **UPDATE**: `src/api/routes.py`
- **PATTERN**: Follow existing concept endpoints pattern (lines 49-68)
- **IMPLEMENT**:
  - `GET /api/concepts/{concept_id}/scores` — fetch scores for a concept (returns `Score | None`)
  - `GET /api/scores` — list recent scores (returns `list[Score]`)
- **IMPORTS**: Add `get_score_by_concept_id`, `get_scores` from `src.db.queries`
- **VALIDATE**: `uv run ruff check src/api/`

### Task 6: Integrate scoring into CLI runner

Add scoring as a step after synthesis in the CLI pipeline.

- **UPDATE**: `scripts/run_conversation.py`
- **MIRROR**: The `_run_synthesis` function (lines 108-170) — same structure for `_run_scoring`
- **IMPLEMENT**:
  - `_run_scoring(db, concept_id, title, premise, originality) -> None`: async function
    - Check `settings.openai_api_key` — skip if not set (same as synthesis)
    - Create `Scorer`, call `scorer.score(title, premise, originality)`
    - Persist via `create_score(db, ScoreCreate(...))`
    - Print scores and reasoning to console
    - On `ScoringError`: log, print warning, do not raise (scoring can be retried)
  - Call `_run_scoring` after synthesis succeeds (inside the existing `_run_synthesis` function's success path, or as a separate call after `_run_synthesis` returns)
  - Add `--no-scoring` CLI flag (similar to `--no-synthesis`)
  - Add `--score-only <concept-id>` flag for re-scoring existing concepts
- **IMPORTS**: Add `Scorer`, `ScoringError`, `ScoreCreate`, `create_score`, `get_concept_by_id` imports
- **GOTCHA**: Scoring depends on synthesis output. If synthesis fails, scoring should not run. Handle the dependency in the flow: synthesis returns the concept, then scoring receives it.
- **VALIDATE**: `uv run ruff check scripts/ && uv run python scripts/run_conversation.py --help`

### Task 7: Add test fixtures for scoring

Add shared fixtures that scoring tests will use.

- **UPDATE**: `tests/conftest.py`
- **PATTERN**: Follow `mock_parse_response` and `test_concept_extraction` fixtures (lines 91-125)
- **IMPLEMENT**:
  - Import `ConceptScoring` and `AxisScore` from `src.scoring.models`
  - `mock_scoring_response()` fixture — factory for mock parse responses with `ConceptScoring`
  - `test_concept_scoring()` fixture — sample `ConceptScoring` with realistic scores and reasoning
- **VALIDATE**: `uv run ruff check tests/conftest.py`

### Task 8: Write scorer unit tests

Test the scorer module — all OpenAI calls mocked.

- **CREATE**: `tests/test_scoring.py`
- **MIRROR**: `tests/test_synthesis.py` — same test structure, same mocking approach
- **IMPLEMENT**:
  - `test_scorer_returns_concept_scoring_on_success` — mock parse, verify all three axes returned
  - `test_scorer_raises_on_refusal` — mock parse with refusal, verify `EvaluationError`
  - `test_scorer_raises_on_api_connection_error` — mock `APIConnectionError`, verify `EvaluationError`
  - `test_scorer_builds_messages_with_system_and_user` — verify message structure
  - `test_scoring_prompt_contains_evaluation_instructions` — verify prompt content
  - `test_scorer_scores_are_within_range` — verify returned scores are 0.0-10.0
- **PATTERN**: Mock `scorer._client.beta.chat.completions` parse method using `patch.object`
- **VALIDATE**: `uv run pytest tests/test_scoring.py -v`

### Task 9: Write database and API tests for scores

Test the score query layer and API endpoints.

- **UPDATE**: `tests/test_db.py` — add score query tests
- **UPDATE**: `tests/test_api.py` — add score endpoint tests
- **IMPLEMENT** (test_db.py):
  - `test_create_score` — verify score creation linked to concept
  - `test_get_score_by_concept_id` — verify retrieval
  - `test_get_score_by_concept_id_returns_none_for_missing` — verify None for nonexistent
- **IMPLEMENT** (test_api.py):
  - `test_get_concept_scores` — verify `GET /api/concepts/{id}/scores`
  - `test_list_scores` — verify `GET /api/scores`
- **PATTERN**: Follow existing test patterns in both files
- **VALIDATE**: `uv run pytest tests/test_db.py tests/test_api.py -v`

### Task 10: Add scoring boundary tests

Verify the scoring module respects architectural boundaries.

- **UPDATE**: `tests/test_boundaries.py`
- **PATTERN**: Follow synthesis boundary tests (lines 83-128)
- **IMPLEMENT**:
  - `test_scoring_uses_remote_openai_api` — verify source references `openai_api_key`
  - `test_scoring_does_not_use_vllm` — verify source does NOT reference `vllm_base_url`
  - `test_scoring_does_not_import_engine` — verify no `from src.engine` imports
  - `test_scoring_does_not_import_synthesis` — verify no `from src.synthesis` imports (scoring sits above synthesis in the hierarchy, so it should not import from it — it receives data, not modules)
- **VALIDATE**: `uv run pytest tests/test_boundaries.py -v`

### Task 11: Full validation pass

Run the complete test suite and linting to ensure zero regressions.

- **VALIDATE**: `uv run ruff check . && uv run ruff format --check . && uv run pytest -v`

---

## TESTING STRATEGY

### Unit Tests

- **Scorer tests** (`tests/test_scoring.py`): Mock all OpenAI API calls. Test success path, refusal handling, connection errors, message structure, prompt content.
- **DB query tests** (`tests/test_db.py`): Use in-memory SQLite. Test score CRUD, concept-score linking, missing concept handling.
- **API tests** (`tests/test_api.py`): Use httpx AsyncClient with FastAPI test app. Test score endpoints with seeded data.

### Integration Tests

- The CLI runner integration is tested manually (Task 11 Level 4). The scorer's integration with the DB is covered by the DB tests using real (in-memory) SQLite.

### Edge Cases

- Model refuses to score (refusal response) — verify `EvaluationError`
- API connection failure — verify `EvaluationError` with descriptive message
- API timeout — verify `EvaluationError`
- Empty concept fields — scorer should still attempt (let o3 handle it)
- Scoring a concept that already has scores — depends on UNIQUE constraint (error or overwrite)
- Missing `OPENAI_API_KEY` — CLI skips scoring with warning (like synthesis)

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

```bash
uv run ruff check .
uv run ruff format --check .
```

**Expected**: All pass with exit code 0

### Level 2: Unit Tests

```bash
uv run pytest tests/test_scoring.py -v
uv run pytest tests/test_db.py -v
uv run pytest tests/test_api.py -v
uv run pytest tests/test_boundaries.py -v
```

**Expected**: All tests pass

### Level 3: Full Test Suite

```bash
uv run pytest -v
```

**Expected**: All tests pass, zero regressions

### Level 4: Manual Validation

```bash
# Verify CLI help shows new flags
uv run python scripts/run_conversation.py --help

# Verify app starts without errors
uv run uvicorn src.main:app --host 0.0.0.0 --port 8001 &
curl http://localhost:8001/health
curl http://localhost:8001/api/scores
# Kill the server after verification
```

---

## ACCEPTANCE CRITERIA

- [ ] `src/scoring/models.py` defines `AxisScore` and `ConceptScoring` as structured output models
- [ ] `src/scoring/scorer.py` implements `Scorer` class using OpenAI o3 with structured output
- [ ] Scoring prompt instructs evaluation across uniqueness, plausibility, and compelling factor
- [ ] Each axis returns a 0.0-10.0 score with written reasoning
- [ ] `scores` table exists in schema with foreign key to `concepts`
- [ ] Score CRUD queries return typed Pydantic models
- [ ] API endpoints expose scores (`GET /api/concepts/{id}/scores`, `GET /api/scores`)
- [ ] CLI runner invokes scoring after synthesis (skippable with `--no-scoring`)
- [ ] CLI supports `--score-only <concept-id>` for re-scoring existing concepts
- [ ] All OpenAI calls mocked in tests — no real inference
- [ ] Boundary tests verify scoring uses remote API, not vLLM, no engine/synthesis imports
- [ ] Full test suite passes with zero regressions
- [ ] Ruff check and format pass with zero errors
- [ ] All code follows project conventions (docstrings, type hints, logging, error handling)

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed
- [ ] All validation commands executed:
  - [ ] Level 1: ruff check, ruff format
  - [ ] Level 2: unit tests per module
  - [ ] Level 3: full test suite
  - [ ] Level 4: manual CLI and server verification
- [ ] No linting errors
- [ ] No formatting errors
- [ ] All acceptance criteria met

---

## EXECUTION STRATEGY

**Recommended approach**: Milestones

**Rationale**: The feature has 11 tasks with clear natural phases — data models, data layer, service layer, integration, testing. Tasks within each phase are tightly coupled (e.g., schema + queries + model), but phases are loosely coupled. The medium complexity and multiple file touches across layers make a single pass risky, but task-by-task is unnecessarily granular for tightly coupled groups.

### Milestones

Each milestone has its own detailed plan file:

**Milestone 1: Data Foundation** (Tasks 1–3) — [`feature4-milestone1-data-foundation.md`](feature4-milestone1-data-foundation.md)
- Create scoring Pydantic models, database table, and typed queries
- **Validation checkpoint**: `uv run ruff check . && uv run pytest tests/test_db.py -v`

**Milestone 2: Scorer Core** (Tasks 4) — [`feature4-milestone2-scorer-core.md`](feature4-milestone2-scorer-core.md)
- Build the Scorer class with OpenAI o3 integration
- **Validation checkpoint**: `uv run ruff check src/scoring/`

**Milestone 3: Integration** (Tasks 5–6) — [`feature4-milestone3-integration.md`](feature4-milestone3-integration.md)
- Wire scoring into API endpoints and CLI runner
- **Validation checkpoint**: `uv run python scripts/run_conversation.py --help` shows new flags; `uv run ruff check .`

**Milestone 4: Testing & Validation** (Tasks 7–11) — [`feature4-milestone4-testing-validation.md`](feature4-milestone4-testing-validation.md)
- Add all test fixtures, unit tests, boundary tests; run full suite
- **Validation checkpoint**: `uv run pytest -v` — all tests pass, zero regressions

---

## NOTES

- **Scoring model (o3)** is already configured in `src/config.py` as `settings.scoring_model`. No config changes needed.
- **Temperature 0.3** for scoring — lower than synthesis (0.4) because scoring should be more consistent. Still non-zero to allow nuanced reasoning.
- **Flat column layout** for scores table — 3 fixed axes for sci-fi domain. Feature 6 (domain expansion) may need a different approach (JSON column or domain-specific score tables), but premature to design for that now.
- **Scoring depends on synthesis** — the pipeline is: conversation → synthesis → scoring. If synthesis fails, scoring doesn't run. The CLI runner handles this by only calling `_run_scoring` when a concept exists.
- **Cost consideration** — o3 runs once per concept. At typical volumes (tens of runs per session), this is negligible.
- **The scoring layer sits above synthesis in the dependency hierarchy** (`API → Scoring → Synthesis → Engine → ...`). The scorer must NOT import from `src/synthesis/` — it receives concept data as plain arguments, not synthesis module objects.
