# Feature 3 — Milestone 4: Testing & Validation

**Parent feature**: [feature3-synthesizer-agent.md](feature3-synthesizer-agent.md)
**Tasks**: 7–8
**Goal**: Add comprehensive tests and run full validation suite
**Depends on**: Milestones 1–3 (all implementation must be complete)

---

## CONTEXT REFERENCES

### Relevant Codebase Files — MUST READ BEFORE IMPLEMENTING

- `tests/conftest.py` (lines 75-87) — Why: Shows `mock_openai_response` fixture pattern. A similar fixture is needed for mock synthesis responses.
- `tests/test_engine.py` (lines 16-41) — Why: Shows how vLLM calls are mocked — `patch.object(runner._client.chat.completions, "create", mock_create)`. Synthesis tests must mock `client.beta.chat.completions.parse` similarly.
- `tests/test_boundaries.py` (lines 34-49) — Why: Shows boundary test pattern. Need to add a test verifying synthesis uses `openai_api_key` (remote API) and does NOT reference `vllm_base_url`.
- `tests/test_db.py` — Why: Shows DB test pattern using the `db` fixture. New concept query tests follow the same pattern.
- `tests/test_api.py` — Why: Shows API test pattern using the `client` fixture.

### New Files to Create

- `tests/test_synthesis.py` — Unit tests for the synthesizer

### Files to Modify

- `tests/conftest.py` — Add mock synthesis response fixture
- `tests/test_boundaries.py` — Add synthesis boundary tests
- `tests/test_db.py` — Add concept query tests
- `tests/test_api.py` — Add concept endpoint tests

---

## IMPLEMENTATION PLAN

### Task 7: Add tests for synthesis

Create comprehensive tests covering the synthesizer, concept queries, boundary verification, and API endpoints.

- **UPDATE**: `tests/conftest.py` — add fixtures:
  - `mock_parse_response` fixture — factory that creates a mock `ParsedChatCompletion` with a `.choices[0].message.parsed` attribute containing a `ConceptExtraction` instance and `.choices[0].message.refusal` as `None`
  - `test_concept_extraction` fixture — returns a sample `ConceptExtraction(title="...", premise="...", originality="...")`
  - `test_transcript` fixture — returns a list of `Turn` objects for synthesis tests

- **CREATE**: `tests/test_synthesis.py` with tests:
  - `test_synthesizer_extracts_concept_from_transcript` — happy path: mock the parse call, verify `ConceptExtraction` is returned with correct fields
  - `test_synthesizer_raises_on_refusal` — mock `.parsed` as `None` with a refusal string, verify `ExtractionError` is raised
  - `test_synthesizer_raises_on_api_connection_error` — mock `APIConnectionError`, verify `ExtractionError`
  - `test_synthesizer_formats_transcript_correctly` — verify `_format_transcript()` produces readable text
  - `test_synthesizer_builds_messages_with_system_and_user` — verify message structure has system prompt + user transcript
  - `test_synthesis_prompt_contains_extraction_instructions` — verify the prompt instructs concept extraction

- **UPDATE**: `tests/test_db.py` — add concept query tests:
  - `test_create_concept` — create a concept linked to a run, verify fields
  - `test_get_concepts_filters_by_status` — create concepts with different statuses, filter
  - `test_get_concept_by_run_id` — fetch concept by run ID
  - `test_update_concept_status` — change status from pending to kept/discarded

- **UPDATE**: `tests/test_boundaries.py` — add synthesis boundary tests:
  - `test_synthesis_uses_remote_openai_api` — verify synthesis source references `openai_api_key` (confirming it uses the remote API)
  - `test_synthesis_does_not_use_vllm` — verify synthesis source does NOT reference `vllm_base_url`
  - `test_synthesis_does_not_import_engine` — verify synthesis does not import from `src.engine` (layer violation)

- **UPDATE**: `tests/test_api.py` — add concept endpoint tests:
  - `test_list_concepts_empty` — verify empty list on fresh DB
  - `test_get_run_concept` — create a run + concept, fetch via `/api/runs/{run_id}/concept`

- **PATTERN**: Mirror `test_engine.py` for mocking — use `patch.object()` on the client method
- **GOTCHA**: Mock `synthesizer._client.beta.chat.completions.parse` (note the `beta` path) not `synthesizer._client.chat.completions.create`
- **GOTCHA**: The mock return value needs `.choices[0].message.parsed` (the `ConceptExtraction` instance) and `.choices[0].message.refusal` (None for success)
- **VALIDATE**: `uv run pytest tests/test_synthesis.py tests/test_db.py tests/test_boundaries.py tests/test_api.py -v`

### Task 8: Run full validation suite

Final validation across all lint and test checks.

- **VALIDATE**: `uv run ruff check .`
- **VALIDATE**: `uv run ruff format --check .`
- **VALIDATE**: `uv run pytest -v`

---

## TESTING STRATEGY

### Unit Tests

**Synthesizer tests (`test_synthesis.py`):**
- Mock `client.beta.chat.completions.parse` to return controlled `ConceptExtraction` objects
- Test happy path, refusal handling, API errors, transcript formatting, message building
- Verify the synthesis prompt contains key instructions

**Concept query tests (additions to `test_db.py`):**
- Test CRUD operations against in-memory SQLite using existing `db` fixture
- Test status filtering, run linkage, and update operations

**API tests (additions to `test_api.py`):**
- Test concept endpoints using existing `client` fixture
- Verify response structure and status codes

### Boundary Tests

**Additions to `test_boundaries.py`:**
- Verify synthesis module uses remote OpenAI API (references `openai_api_key`)
- Verify synthesis module does NOT reference vLLM (`vllm_base_url`)
- Verify synthesis module does NOT import from engine layer

### Edge Cases

- OpenAI API returns a refusal (content policy) — must raise `ExtractionError`
- OpenAI API connection failure — must raise `ExtractionError` with clear message
- Empty or very short transcript — synthesizer should still attempt extraction
- Missing OpenAI API key — CLI should skip synthesis with a warning, not crash
- Concept already exists for a run (re-running synthesis) — handle gracefully

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
# Synthesis-specific tests
uv run pytest tests/test_synthesis.py -v

# Database tests including new concept queries
uv run pytest tests/test_db.py -v

# Boundary tests including new synthesis boundaries
uv run pytest tests/test_boundaries.py -v

# API tests including new concept endpoints
uv run pytest tests/test_api.py -v
```

### Level 3: Full Test Suite

```bash
uv run pytest -v
```

**Expected**: All tests pass with zero failures

### Level 4: Manual Validation

```bash
# Verify synthesis module imports cleanly
uv run python -c "from src.synthesis.synthesizer import Synthesizer; print('OK')"

# Verify synthesis models have correct schema
uv run python -c "from src.synthesis.models import ConceptExtraction; print(ConceptExtraction.model_json_schema())"

# Verify concept DB model is queryable
uv run python -c "from src.db.queries import Concept, ConceptCreate; print('Concept models OK')"

# Verify schema includes concepts table
uv run python -c "from src.db.schema import SCHEMA_SQL; assert 'concepts' in SCHEMA_SQL; print('Schema OK')"

# Verify CLI accepts new flags
uv run python scripts/run_conversation.py --help

# Verify API routes include concept endpoints
uv run python -c "from src.api.routes import router; paths = [r.path for r in router.routes]; print(paths); assert '/concepts' in str(paths)"
```

---

## ACCEPTANCE CRITERIA

- [ ] `src/synthesis/` module exists with `models.py` and `synthesizer.py`
- [ ] `ConceptExtraction` Pydantic model with `title`, `premise`, `originality` fields
- [ ] `Synthesizer` class uses `client.beta.chat.completions.parse()` with structured output
- [ ] `Synthesizer` handles refusals and API errors with clear exception types
- [ ] `concepts` table added to SQLite schema with run foreign key
- [ ] `Concept`, `ConceptCreate` models in `src/db/queries.py`
- [ ] Concept CRUD queries (`create_concept`, `get_concepts`, `get_concept_by_run_id`, `update_concept_status`)
- [ ] CLI runner calls synthesis after conversation completion (with `--no-synthesis` opt-out)
- [ ] CLI gracefully handles missing API key (warns, skips synthesis)
- [ ] API endpoints: `GET /api/concepts`, `GET /api/runs/{run_id}/concept`
- [ ] Synthesis prompt instructs model to extract transferable principles, reframings, novel compounds
- [ ] All synthesis tests pass with mocked OpenAI calls
- [ ] Boundary tests verify synthesis uses remote API (not vLLM) and doesn't import engine
- [ ] `uv run ruff check .` passes with 0 errors
- [ ] `uv run ruff format --check .` passes with 0 errors
- [ ] `uv run pytest -v` passes with all tests green
- [ ] No real LLM calls in tests

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully:
  - [ ] Level 1: ruff check, ruff format --check
  - [ ] Level 2: pytest per-module
  - [ ] Level 3: pytest full suite
  - [ ] Level 4: Manual validation
- [ ] Full test suite passes (unit + boundary + API)
- [ ] No linting errors
- [ ] No formatting errors
- [ ] All acceptance criteria met
- [ ] Code reviewed for quality and maintainability
